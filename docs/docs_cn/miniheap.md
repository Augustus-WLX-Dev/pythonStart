# 深入理解 Asyncio：Minheap 与 Event Loop 的 scheduled queue

在 Python 的 `asyncio` 中，Event Loop 需要同时处理两类事情：

1. 已经可以马上执行的回调。
2. 未来某个时间点才应该执行的回调。

第一类放在 `_ready` 里，底层是 `collections.deque`。第二类放在 `_scheduled` 里，底层是普通 `list`，但这份 `list` 会被 `heapq` 维护成 **min-heap（最小堆）**。

最小堆在这里解决的核心问题很简单：Event Loop 每次只需要快速知道“下一个最早到期的定时任务是谁”，然后根据它计算自己最多能阻塞多久。

---

## 零、什么是 Minimum Heap？

Minimum Heap 通常叫 **最小堆**。它是一种用数组表示的完全二叉树，并满足一个关键约束：

> 每个 parent 节点都不大于自己的子节点。

所以，最小堆不保证整个数组从小到大有序；它只保证 **堆顶 `data[0]` 一定是当前最小值**。

这正好适合 Event Loop 的 scheduled queue：不需要每次都完整排序，只要最快拿到“最早到期”的 `TimerHandle`。

一个最小堆可以这样模拟：

```python
class MinHeap:
    def __init__(self):
        self.data = []

    def push(self, value):
        self.data.append(value)
        self._sift_up(len(self.data) - 1)

    def pop(self):
        if not self.data:
            raise IndexError("pop from empty heap")

        root = self.data[0]
        last = self.data.pop()

        if self.data:
            self.data[0] = last
            self._sift_down(0)

        return root

    def peek(self):
        if not self.data:
            raise IndexError("peek from empty heap")
        return self.data[0]

    def _sift_up(self, index):
        while index > 0:
            parent = (index - 1) // 2

            if self.data[parent] <= self.data[index]:
                break

            self.data[parent], self.data[index] = self.data[index], self.data[parent]
            index = parent

    def _sift_down(self, index):
        size = len(self.data)

        while True:
            left = 2 * index + 1
            right = 2 * index + 2
            smallest = index

            if left < size and self.data[left] < self.data[smallest]:
                smallest = left

            if right < size and self.data[right] < self.data[smallest]:
                smallest = right

            if smallest == index:
                break

            self.data[index], self.data[smallest] = self.data[smallest], self.data[index]
            index = smallest
```

这里的 `self.data = []`，就可以类比成 Event Loop 里的 `self._scheduled = []`。不过真正的 `asyncio` 不会自己写这个类，而是使用标准库的 `heapq`。

---

## 一、堆的三个核心动作：peek、push、pop

### 1. `peek()`：只看堆顶，不改变堆

```python
def peek(self):
    if not self.data:
        raise IndexError("peek from empty heap")
    return self.data[0]
```

`peek()` 的作用是看一眼堆顶。

在最小堆里，`data[0]` 一定是最小值。对应到 `_scheduled`，`self._scheduled[0]` 就是最早到期的 `TimerHandle`。

复杂度是 `O(1)`。

### 2. `push()`：追加到末尾，再向上冒泡

```python
def push(self, value):
    self.data.append(value)
    self._sift_up(len(self.data) - 1)
```

`push()` 分两步：

1. 先把新元素追加到数组末尾。
2. 再通过 `_sift_up()` 向上冒泡，直到 parent 节点不比它大。

因为完全二叉树的高度是 `log n`，所以 `push()` 的复杂度是 `O(log n)`。

### 3. `pop()`：弹出堆顶，再向下下沉

```python
def pop(self):
    if not self.data:
        raise IndexError("pop from empty heap")

    root = self.data[0]
    last = self.data.pop()

    if self.data:
        self.data[0] = last
        self._sift_down(0)

    return root
```

`pop()` 的步骤是：

1. 记住堆顶 `root`。
2. 删除数组最后一个元素 `last`。
3. 如果堆里还有元素，就用 `last` 覆盖堆顶。
4. 从堆顶开始 `_sift_down()`，恢复最小堆结构。
5. 返回之前记住的 `root`。

- 先检查是否空数组(`if not self.data:`)，是就向上抛出异常(`raise IndexError("pop from empty heap")`)。

- 第二步总得来说就是把头部拿出去(`root = self.data[0]` + `return root` )， 最后的数值放到头部(`self.data[0] = last`)，然后从头部往下沉(`self._sift_down(0)`)。


为什么不直接 `self.data.pop(0)`？

因为 `list.pop(0)` 是 `O(n)`，会导致后面所有元素整体左移。最小堆要让弹出堆顶保持 `O(log n)`，所以采用“尾部补堆顶，再下沉”的方式。

对应到 `asyncio`，不会写：

```python
loop._scheduled.pop(0)
```

而是写：

```python
heapq.heappop(loop._scheduled)
```

---

## 二、向上冒泡：`_sift_up()`

```python
def _sift_up(self, index):
    while index > 0:
        parent = (index - 1) // 2

        if self.data[parent] <= self.data[index]:
            break

        self.data[parent], self.data[index] = self.data[index], self.data[parent]
        index = parent
```

`_sift_up()` 从新插入的元素开始，不断和 parent 节点比较：

1. `parent = (index - 1) // 2` 找到 parent 节点下标。（[点击查看：二叉树公式剖析](binarytree.md)）
2. 如果 parent 节点 `<=` 当前节点，说明最小堆约束已经满足，停止。
3. 如果 parent 节点更大，就交换parent 和 子 位置。
4. 交换后，新元素移动到了 parent 节点的位置，所以把 `index` 更新为 `parent`，继续向上检查。

> 详细拆解：
- `sift_up()` 函数是一个死循环：从最后一个数（自己）开始，不断地和自己的parent级别打擂台，一直打到自己成为root(`while index > 0:`)，或者自己比parent小(if self.data[parent]<= self.data[index]: break)。
- `parent = (index - 1) // 2` 是一个寻找自己的parent的公式。（[点击查看：二叉树公式剖析](binarytree.md)）
- `//` 是整除的意思，只要整数商，不要余数，不要小数点。
- 找到 parent 后，比较 parent 的值和自己的值(`f self.data[parent] <= self.data[index]:`)，parent 小于自己，说明已经到了最合适的位置，不需要再继续比较(`break`)。
- parent的值大于自己，则两者数值交换(`self.data[parent], self.data[index] = self.data[index], self.data[parent]`)。
-   交换后，“自己”到了新的位置，所以要更新index。

这里只更新 `index`，是因为这个函数真正要追踪的是“新插入的那个元素”。其他节点原本已经满足堆结构，只有这一个新元素可能破坏了从当前位置到堆顶的路径。

> 详细解说
>    - 首先当数值交换之后，在外部的 scheduled queue 看来，parent 的位置已经变了，index也就变了。
>    - 其次是，在 `sift_up()` 函数里，index是内部的定位器，我们主要跟踪新来的数（也就是我们说的“自己”），所以需要在交换后改变定位器，而其他的数我们不管，因为其他的数的位置，已经是最优解（除了和新来的自己比）。

---

## 三、向下下沉：`_sift_down()`

```python
def _sift_down(self, index):
    size = len(self.data)

    while True:
        left = 2 * index + 1
        right = 2 * index + 2
        smallest = index

        if left < size and self.data[left] < self.data[smallest]:
            smallest = left

        if right < size and self.data[right] < self.data[smallest]:
            smallest = right

        if smallest == index:
            break

        self.data[index], self.data[smallest] = self.data[smallest], self.data[index]
        index = smallest
```

`_sift_down()` 用在弹出堆顶之后。最后一个叶子节点被搬到堆顶，它可能比自己的子节点大，所以要一路往下找位置：

1. `left = 2 * index + 1` 找左子节点。
2. `right = 2 * index + 2` 找右子节点。
3. `smallest = index` 先假设当前节点最小。
4. 如果左子节点存在且更小，就把 `smallest` 改成左子节点。
5. 如果右子节点存在且比当前 `smallest` 还小，就把 `smallest` 改成右子节点。
6. 如果 `smallest == index`，说明当前节点已经比两个子节点都小，停止。
7. 否则交换当前节点和更小的子节点，然后继续向下检查。

这个过程也只会走树高那么多层，所以复杂度是 `O(log n)`。

> 详细拆解：
- `sift_down()` 重点是从上往下和自己的左子、右子 **打擂台** ，目的是找出冠军，不理会亚军、季军。
- 用公式找出左右子(`left = 2 * index + 1` 和 `right = 2 * index + 2`)[点击查看：二叉树公式剖析](binarytree.md)）
- `smallest = index` 这里先把“新来的自己”复制到 `smallest`, 因为“我自己”要去打谁是最小的擂台，所以先坐在 `smallest` 王座上，这时还没开始比较（打擂台）。
- `if left < size` 和 `if right < size` 是判断左右子是否存在，如果不存在就不需要打擂台。
- `if left < size and self.data[left] < self.data[smallest]: smallest = left`左子存在，并且左子的数值小于“坐在 `smallest` 王座上的我”，就交换位置(`smallest = left`)，左子坐在了 `smallest` 王座上了。这时 `smallest` 王座已经换人了。
- `if right < size and self.data[right] < self.data[smallest]:`右子存在，并且右子的数值小于“坐在 `smallest` 王座上的数值”，就交换位置(`smallest = right`)，右子坐在了 `smallest` 王座上了。这时 `smallest` 王座又换人了。
- 如果上述两种情况都没有发生，也就是两次打擂台，王座上(`smallest`)都是我，那就是(`if smallest == index: break`)，新来的我，已经下沉到了最合适的位置。
- 如果我并不没有在王座上，那么上面和左右子打擂台，最后坐在王座上的某一子的数值和我的数值交换位置(`self.data[index], self.data[smallest] = self.data[smallest], self.data[index]`)。
- 因为位置换了，而我还需要继续去打下一个擂台，还要被追踪，所以追踪器也需要更新(`index = smallest`)。


---

## 四、Asyncio 里的 `_scheduled`：一个由 `heapq` 维护的 list

`asyncio` 的事件循环初始化时，会创建两个关键队列：

```python
# asyncio/base_events.py 简化版
class BaseEventLoop:
    def __init__(self):
        self._ready = collections.deque()
        self._scheduled = []
```

`_ready` 是就绪队列：已经可以执行的 `Handle` 在这里排队。

`_scheduled` 是计划队列：未来某个时间点才应该执行的 `TimerHandle` 在这里排队。它看起来只是一个普通 list，但所有插入和弹出都通过 `heapq` 完成，因此它在逻辑上是一个最小堆。

`heapq` 不是类，而是一组操作堆的函数，例如：

```python
heapq.heappush(heap, item)
heapq.heappop(heap)
heapq.heapify(items)
```

---

## 五、堆里的元素：`TimerHandle`

`_scheduled` 里存的不是裸时间戳，而是 `TimerHandle` 对象。

简化后可以这样理解：

```python
# asyncio/events.py 简化版
class TimerHandle(Handle):
    def __init__(self, when, callback, args, loop, context=None):
        super().__init__(callback, args, loop, context)
        self._when = when
        self._scheduled = False

    def __lt__(self, other):
        if isinstance(other, TimerHandle):
            return self._when < other._when
        return NotImplemented
```

几个关键字段：

1. `when`：计划执行的绝对时间，对应 `loop.time()` 的时钟体系。
2. `callback`：到期后要执行的回调函数。
3. `args`：传给回调函数的位置参数。
4. `loop`：绑定的事件循环。
5. `context`：`contextvars` 上下文。
6. `_scheduled`：这个 handle 是否还在 scheduled heap 中。
7. `_cancelled`：这个 handle 是否已经被取消。

`TimerHandle` 继承自 `Handle`。`Handle` 负责保存通用的回调、参数、上下文和取消状态；`TimerHandle` 额外增加了“什么时候执行”的 `_when`。

`heapq` 在比较两个 `TimerHandle` 时，会调用 `__lt__()`。这相当于告诉堆算法：

> 谁的 `_when` 更小，谁就更小，谁就更应该靠近堆顶。

于是，最早到期的定时任务会出现在 `self._scheduled[0]`。

一个重要细节：如果两个 `TimerHandle` 的 `_when` 完全相同，`__lt__()` 会返回 `False`。所以 `asyncio` 不承诺同一时间点的 timer 严格按插入顺序执行。通常这不影响业务，因为同一 tick 的回调本来就不应该依赖微观顺序。

---

## 六、任务如何进入 `_scheduled`：`call_later()` 与 `call_at()`

常见的 `await asyncio.sleep(5)` 底层会创建一个 `Future`，然后通过 `loop.call_later()` 注册一个未来回调：时间到了，就把这个 `Future` 的结果设置好，从而唤醒等待它的 Task。

`call_later()` 本质上是语法糖：

```python
def call_later(self, delay, callback, *args, context=None):
    return self.call_at(self.time() + delay, callback, *args, context=context)
```

`call_at()` 才是真正把定时回调塞进堆里的地方：

```python
def call_at(self, when, callback, *args, context=None):
    timer = events.TimerHandle(when, callback, args, self, context)
    heapq.heappush(self._scheduled, timer)
    timer._scheduled = True
    return timer
```

流程是：

1. 计算目标时间 `when`。
2. 创建 `TimerHandle`。
3. 用 `heapq.heappush()` 放入 `_scheduled`。
4. `heappush()` 内部触发向上冒泡，让更早到期的 handle 更靠近堆顶。
5. 标记 `timer._scheduled = True`。
6. 返回这个 handle，调用方之后可以用它取消定时任务。

流程对应代码：
1. `call_later`里面的`self.call_at(self.time() + delay)`。
2. `timer = events.TimerHandle(when, callback, args, self, context)`。
3. `heapq.heappush(self._scheduled, timer)`。
4. `heapq.heappush(self._scheduled, timer)`。
5. `timer._scheduled = True`。
6. `return timer`。

---

## 七、`_run_once()` 如何使用堆顶计算 timeout

Event Loop 每转一圈，本质上是在执行一次 `_run_once()`。它会根据当前状态计算 selector 最多可以阻塞多久。

简化逻辑如下：

```python
timeout = None

if self._ready or self._stopping:
    timeout = 0
elif self._scheduled:
    timeout = self._scheduled[0]._when - self.time()
    if timeout > MAXIMUM_SELECT_TIMEOUT:
        timeout = MAXIMUM_SELECT_TIMEOUT
    elif timeout < 0:
        timeout = 0

event_list = self._selector.select(timeout)
```

这里有三个分支：

1. 如果 `_ready` 里已经有任务，`timeout = 0`，Event Loop 不阻塞，马上回来执行。
2. 如果 `_ready` 为空但 `_scheduled` 有任务，就看堆顶的 `_when`，计算距离最近 timer 到期还有多久。
3. 如果两个队列都没有任务，`timeout = None`，selector 可以一直阻塞，直到 I/O 或外部唤醒。

`timeout < 0` 时要修正为 `0`。因为如果程序卡顿导致当前时间已经超过 `_when`，这个 timer 已经过期，Event Loop 应该立刻回来处理它，而不是把负数传给底层 selector。

`MAXIMUM_SELECT_TIMEOUT` 是另一个防御：避免传入过大的阻塞时间。

---

## 八、到期后不是立刻执行，而是先搬进 `_ready`

selector 返回后，Event Loop 会处理 I/O 事件，然后把已经到期的定时任务从 `_scheduled` 搬到 `_ready`。

简化逻辑如下：

```python
end_time = self.time() + self._clock_resolution

while self._scheduled:
    handle = self._scheduled[0]
    if handle._when >= end_time:
        break

    handle = heapq.heappop(self._scheduled)
    handle._scheduled = False
    self._ready.append(handle)
```

这里有一个非常关键的逻辑点：

> `TimerHandle` 到期后，并不是在 `_scheduled` 里被直接执行，而是先 `heappop()` 出来，再追加到 `_ready`，最后由统一的 ready 队列执行。

这让 Event Loop 的执行模型保持一致：不管是 `call_soon()`、I/O 回调，还是到期的 timer，最终都会变成 `_ready` 里的 `Handle`，然后统一执行 `handle._run()`。

后面真正执行回调的是这一段：

```python
ntodo = len(self._ready)

for i in range(ntodo):
    handle = self._ready.popleft()
    if handle._cancelled:
        continue
    handle._run()
```

注意：这里先固定 `ntodo = len(self._ready)`。这意味着本轮执行过程中新增到 `_ready` 的回调，不会在本轮继续执行，而是留到下一轮 `_run_once()`。

---

## 九、取消定时任务：懒删除 + 必要时重建堆

取消 scheduled timer 的时候，`asyncio` 不会每次都立刻从堆中删除它。原因是：从堆的中间找某个元素并删除，需要先线性搜索，通常是 `O(n)`。

所以常规取消是 **懒删除**：

```python
handle.cancel()
```

它会把 handle 标记为 `_cancelled = True`，并记录取消数量。真正清理通常发生在 `_run_once()` 开头。

如果堆顶就是已取消任务，Event Loop 会连续弹掉它们：

```python
while self._scheduled and self._scheduled[0]._cancelled:
    handle = heapq.heappop(self._scheduled)
    handle._scheduled = False
```

但还有一种情况：堆里取消的 timer 太多，而且很多不在堆顶。如果一直懒删除，堆会被大量废弃 handle 占着。于是 `asyncio` 会在取消比例过高时批量重建堆：

```python
new_scheduled = []

for handle in self._scheduled:
    if handle._cancelled:
        handle._scheduled = False
    else:
        new_scheduled.append(handle)

heapq.heapify(new_scheduled)
self._scheduled = new_scheduled
```

所以更准确的说法是：

> `asyncio` 取消定时任务时，通常先打取消标记，不立刻从堆里删除；Event Loop 会在堆顶清理它们，或在取消数量过多时批量过滤并 `heapify()` 重建堆。

---

## 十、复杂度总结

`_scheduled` 使用最小堆，是在下面几个操作之间做平衡：

| 操作 | 含义 | 复杂度 |
| --- | --- | --- |
| `self._scheduled[0]` | 查看最早到期任务 | `O(1)` |
| `heapq.heappush()` | 插入新的 timer | `O(log n)` |
| `heapq.heappop()` | 弹出最早到期 timer | `O(log n)` |
| `heapq.heapify()` | 批量重建堆 | `O(n)` |
| 从堆中间删除某个指定 timer | 需要搜索，不适合频繁做 | 通常 `O(n)` |

这就是为什么 scheduled queue 适合最小堆，而不是普通排序 list：

1. Event Loop 每轮都要频繁查看“最早到期任务”，所以堆顶查询必须便宜。
2. 定时任务会不断插入和到期弹出，所以插入、弹出都要稳定在 `O(log n)`。
3. 不需要完整排序，只需要保证堆顶最小。

---

## 结语

从 `asyncio.sleep()` 出发，底层会一路走到：

1. `sleep()` 创建 `Future`。
2. `loop.call_later()` 注册未来回调。
3. `call_at()` 创建 `TimerHandle`，并用 `heapq.heappush()` 放入 `_scheduled`。
4. Event Loop 在 `_run_once()` 中读取 `_scheduled[0]`，计算 selector 的 timeout。
5. 到期后，`heapq.heappop()` 把 timer 从 `_scheduled` 弹出。
6. 到期 timer 被放入 `_ready`。
7. Event Loop 统一从 `_ready` 里取出 handle 并执行。

Minheap 的价值不在于“把所有任务排成完整顺序”，而在于它用很低的成本维护了一个 Event Loop 最关心的问题：

> 下一个最早到期的任务是谁？

这就是 scheduled queue 的核心。
