# Event loop

* **Ready queue**
    - `collections.deque`
        - 时间复杂度
* **Scheduled queue**
    - minimum heap

Event loop 主要任务就是循环交权。它内部有一个巨大的死循环 `while True`，它在死循环里一边监控任务是否超时，一边拿过 CPU 执行权，把它交给 Ready Queue 的下一个任务。

在 Event loop initiate 时，会创建两大核心队伍：**Ready Queue** 和 **Scheduled Queue**。

**Ready Queue 是一个等候区。**
* Event loop 会依次交权给 Ready Queue 里排队的任务，让它们走到内存里，运行起来。
* Ready Queue 是一个双端队列。（[点击查看：双端队列剖析](collection_deque.md)）

**Scheduled Queue 是一个地雷监控区。**（后续插入 Minimum heap 讲解）
* 它是一个基于时间调度的最小堆计划队列（Minimum heap），也就是时间越短排在越前。
* Event loop 每循环一次 `while True`，第一步先去看一眼堆顶。当有任务超时，Event loop 就会 pop 掉 Scheduled Queue 的堆顶，把地雷放进 Ready Queue，让它准备引爆自己()。

***

### 一、核心概念：Task 的双轨竞态（Race Condition）

一个 `Task` 有两条生命线，一条是正常运行，一条是超时自杀。这两条生命线互相竞争，在时间上先跑完的那一条，将获得杀死对方的权利。

**开局布阵（埋下地雷）**
1. `t = 0`, 配置超时 5 秒爆炸的地雷（`loop.call_later(5, 撕票回调)`）制造一个 Handle，这个 Handle 被埋进 Scheduled Queue。同时 `call_later` 把这个 handle 对象存进名叫 `timeout_handle` 的局部变量里（Scheduled Queue 里的 handle 和 `timeout_handle` 其实是同一个对象）。

2. 代码在遇到 `await` 后，task 把 callback 绑定到 future, 自己悬挂休眠，交出 CPU 控权。future 负责接收信号，等待回传，Event loop 则拿走控制权。

> **剧情走向概述：**
> * **生还线**：信息及时回传 -> future 状态改变 -> 唤醒 task -> task 重新拿到 CPU -> 继续运行并顺手拆除炸弹。
> * **自杀线**：Event loop 发现超时 -> 炸弹被放进 Ready Queue排队 -> 炸弹拿到 CPU 后引爆 -> 强制杀死 task。

---

### 二、底层机制：Task 的唤醒与“十字路口”

在详细推演这生死两线之前，我们需要先了解 Task 苏醒的通用底层链路：

当 Future 收到反馈时（无论是因为成功拿到了 result 还是被取消），Future 的状态都会凝固（Frozen），并触发 **Pager（呼叫机）**。它的底层是 `Future.add_done_callback()`。

Pager 会通过 `loop.call_soon(Task._wakeup, future)`，将回调函数（`self._wakeup`）包装成一个 Handle 对象，塞进 Event loop 的 Ready Queue 末尾。Event loop 每循环一圈，就会去 Ready Queue 弹出一个个 Handle 并无脑执行（`handle.run()`）。

这个 `handle.run()` 真正调用的就是 `Task._wakeup()`。它会检查 future 的状态，然后调用核心驱动器 `Task._step`。

**源码解析：决定命运的十字路口**
`self._wakeup` 负责查看 future 状态，随后将走入不同的代码分支。`self._step` 会带着异常或 `None`（有 result）去运行，task 醒来看到手里不同的结果，将走不同的路线：

```python
def _wakeup(self, future):
    try:
        future.result()  # 检查点：尝试获取结果或抛出异常
    except BaseException as exc:
        # 路线 A（异常路线）：如果 future 被取消或报错，捕捉到异常 exc
        self._step(exc)
    else:
        # 路线 B（正常路线）：如果 future 成功了，注意这里！
        # 它并没有把 future.result() 传进去，而是传了 None！
        self._step(None)


def _step(self):
    # 清理Waiter（解绑）
    self._fut_waiter = None

    # 核销取消标记（消费指令）
    if self._must_cancel:
        if not isinstance(exc, exceptions.CancelledError):
            exc = self._make_cancelled_error()
        self._must_cancel = False
    
    # 向协程内部抛入异常（驱动业务）
    try:
        if exc is None:
            # 对应路线 B：手里是空的 (None)
            # 告诉协程：“底层的活儿干完了，你继续往下跑吧”
            result = coro.send(None)
        else:
            # 对应路线 A：手里拿着异常 (比如 CancelledError)
            # 告诉协程：“底层出事了，接招！”
            result = coro.throw(exc) # 关键爆发点！
    
    # 捕获协程的阵亡并盖棺定论（状态变更）
    except exceptions.CancelledError as exc:
        super().cancel()  # 这里调用的是父类 Future.cancel()
```

---

### 三、情景实战：两条生命线的物理推演

结合铺垫好的底层链路与代码路线，我们可以非常清晰地还原那两场生死时速的内部物理细节。

#### 情况一、生还线：走入路线 B（正常运行）
1. `t < 5`, 信息回传， future 的信箱收到 result，状态由 pending 变成 finished，**触发 Pager** 生成唤醒 Handle 塞进 Ready Queue。
2. Event loop 转到 Ready Queue 执行 `handle._run()`，进而运行 `self.wakeup()`。
3. 因为 future 获取到了 result，**代码走入路线 B**，调用 `self._step(None)`。
4. `Task._step()` 执行 `task._coro.send(None)` 唤醒协程。
5. task 在内存醒来获得控制权。它通过 `await` 的底层 Yield 链式反应回传（如穿越虫洞一般），回到 `await` 断点，调用 `future.result()` 提取到结果。
6. **拆弹的物理过程**：（如果外层套了 `wait_for`），Task 往下走会执行 `timeout_handle.cancel()` 进行拆弹。当 Task 手里捏着遥控器按下取消时，底层会在这颗地雷 Handle 对象的内存里，悄悄把 `self._cancelled` 变量改成 `True`，打上取消标记。
7. 到了第 5 秒，Event loop 监控到超时，它从 Scheduled Queue 取出这个地雷，但看到取消戳（`if handle._cancelled:`），于是直接把它扔进垃圾桶，彻底无视它的回调。

#### 情况二、自杀线：走入路线 A（超时死亡）
1. 在 `t < 5` 秒时，Scheduled Queue 的地雷并没有被拆除。
2. `t = 5`， Event loop 监控到 Scheduled Queue 的堆顶超时。Event loop 把超时地雷 pop 出来， 塞进 Ready Queue。
3. 当 Event loop 交权（`handle.run()` ） 给地雷，地雷运行，地雷的火药（`task.cancel()` ）被触发。
4. `task.cancel()` 做了两件事：一是跑到 task 内部，给 task 盖上猩红的取消戳（`self._must_cancel = True`）；二是跑到底层还在傻等的 future 对象（即 `self._fut_waiter`）内部，强制把它的状态改为 cancelled。
5. Future 状态凝固，同上文一样**触发 Pager**，引发回调，把 Task 的唤醒钩子塞进 Ready Queue。
6. 稍后 Event loop 交权，`task.wakeup()` 被运行，它查看 future 发现被取消，**代码走入路线 A**，截获 exc 并把 `CancelledError` 塞进 `self._step(CancelledError)`。
7. `task._step` 带着巨大的异常无奈执行自杀命令（`self._coro.throw(asyncio.CancelledError)`）。异常顺着 Yield 链式反应回到 `await` 断点引爆炸弹，协程的业务逻辑在内存里刚一醒来就被炸死了。

***

### 极限竞速
在“自杀线”里，这两条线确实是完全竞争的（Race Condition）。万一极端巧合发生了呢？

假设在 `t = 4.999999` 秒的时候，Future 刚好拿到了结果，把唤醒 Handle 塞进了 Ready Queue；但几乎在同一瞬间 `t = 5.0`，Event Loop 也把超时地雷塞进了 Ready Queue。这俩 Handle 都在 Ready Queue 里排队了，会发生什么？

**答案是：以 Event Loop 的执行顺序为准，谁先被 `handle._run()` 跑完，谁就赢了。**

* **如果超时地雷先运行**：`task.cancel()` 会被触发，任务被盖上猩红戳。哪怕紧接着生还线的 Handle 被运行，它也会因为任务已经被取消而宣告无效（抛出 `CancelledError`）。

* **如果生还线先运行**：Task 会苏醒并执行拆弹逻辑，把地雷的 `_cancelled` 设为 `True`。紧接着轮到超时地雷运行时，Event Loop 看到它已经被拆除了，就会直接扔进垃圾桶，Task 逃过一劫。



### 架构设计美学

**1. 类型擦除（Type Erasure）与统一接口（Uniform Interface）**
在 Event loop的 Ready Queue 中，无论是简单的函数回调，还是复杂的协程，所有 task 都被包装成统一的`Handle`对象。Event loop 不需要去分辨上层不同的数据和类型差异，只需要在死循环中无脑执行`handle.run()`。这种设计极大地减少了运行的摩擦力，让 Event loop 专注发货，让业务层面专注业务逻辑。


**2. 信号传递与提货的解耦（轻量化路由）**
在 task 的唤醒机制中，`self._wakeup` 也有着异曲同工的提效逻辑。当底层数据成功回传时，`self._wakeup` 并没有把真实的回传数据塞进去，而是仅仅将 `None` 传入 `self._step(None)`。
此时的 `None` 只是一个极其轻量的占位符和“唤醒信号”。代码只需要带着这个没有任何负担的 `None` 在中间层跨过山和大海；直到 task 顺着 Yield 链条一路冲刺，回到最表层的业务代码（`await` 断点）时，task 才依靠自己执行 `future.result()` 去提取真正的实物 result。




### 后续将添加Selector（I/O 多路复用器，如 epoll/kqueue） 部分