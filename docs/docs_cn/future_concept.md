# Future

`future` 是一个对象。

它是一个状态机、信箱、呼叫机。

## 1. 状态机（State Machine）

* **pending**：处理中。
* **cancelled**：仅由主动取消触发 `task.cancel()`。
* **finished**：既包括正常返回结果，也包括抛出异常。

`task.done()` 包括 cancelled 和 finished，仅这个代码不知状态具体是哪一个。
**状态不可逆**：从 pending 到 done 状态，没有任何方法可以从 done 逆流到 pending。

## 2. 信箱

当 future 变成 finished 状态后，它的信箱会有其任何一种 content：Result（结果） 或 Exception（异常）。

* **Result**：默认值 `None`（作占位符），但如果协程有 return 其他内容，则这内容赋值给 Result。
* **Exception**：异常被填入此格。
  * 如果写的程序不使用 `try…except` 去包裹这颗炸弹，在 `await` 语句拿到 result 的时候，炸弹就会在取出这行代码结果的时候原地引爆，炸毁 Task。

## 3. 呼叫机（Pager）：信号分发器

* **callback**：task 都是由 future 唤醒，至于唤醒后是拿到结果正常运行，还是看到猩红取消戳，自我了结，就要看具体情况。

## 4. 与 await 的关系

在 asyncio 宇宙里面，当 task 遇到 `await`，task 通过 `await` 的底层 Yield 链式反应悬挂自己，future 登场。task 把 callback 交给 future，自己开始休眠。

`await （某某task） = await future`，CPU 主权交给 Event loop，Event loop 把镜头对准下一个任务，而 future 在等待外界的信息回传。

当 Future 接收到了回传（Result 被填入），状态机凝固，立即触发 Pager（呼叫机），执行了 callback。callback 把 task 塞入 Ready Queue，Event loop 镜头对准 task，task 被唤醒。
task 通过 `await` 的底层 Yield 链式反应回传，拿到信箱的 content，继续往下运行（不管是正常运行还是异常引爆）。

### AI总结与 await 的关系：

1. **睡前操作**：挂起自己，留 Callback 给 Future，让出 CPU 给 Event Loop。
2. **等待过程**：Event Loop 将主镜头移开，去处理其他事；Future 作为静态的数据结构默默等待回传。
3. **被叫醒后**：回传到达 -> Pager 摇人 -> 回到 Ready Queue 排队 -> Event Loop 镜头切回 -> 顺着 Yield 爬回来拿结果（如果是报错，就在这行当场炸毁）。