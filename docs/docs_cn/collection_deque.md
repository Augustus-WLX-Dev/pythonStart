# collections_deque ｜ Ready Queue

```python
# Lib/asyncio/base_events.py
class BaseEventLoop:
    def __init__(self):
        self._ready = collections.deque()   # ← Ready Queue 本尊
        self._scheduled = []                # Scheduled Queue (heapq)
```

## 1. 概念与命名

`deque` 是 **Double-Ended Queue** 的缩写，中文全称叫“**双端队列**”。在发音上，程序员们通常把它读作 `"deck"`（发音和扑克牌里的 deck 一样）。

我们可以把它拆开来看：
* **Double-Ended (双端的)**：意味着它的头和尾两头都是开的。
* **Queue (队列)**：就是排队的意思。

## 2. 底层原理：双向链表 (虫洞接力)

`deque` 的底层数据结构是**双向链表**（或者类似双向链表的块状结构）。

在 `deque` 这个队伍里，所有的人（节点 Node）都只有前后两个指针（Pointer）。这些指针就像**虫洞 (Wormhole)** 一样，`deque` 通过它们能快速找到前后的人（Node）。前后的人（Node）可能散落在完全不同的物理内存空间。

它的核心魔法在于：无论是在队伍的最前面加/删人，还是在队伍的最后面加/删人，速度都极其快，**时间复杂度永远都是 O(1)**。（[点击查看时间复杂度讲解](Time_complexity.md)）

* **排队 (进队)**：瞬间把新人加到队尾，只需把原来的队尾的指针指向新人：
  ```python
  self._ready.append(handle)
  
  # CPython 底层接力：
  self.rightblock.rightlink = new_block
  new_block.leftlink = self.rightblock
  ```

* **出队 (离队)**：瞬间从队头移除。后面的人完全不需要往前挪动任何物理位置，因为他们之间是通过指针（虫洞）连在一起的。只需要切断第一个人和第二个人相连的指针，把“队头信标”直接插在第二个人头上就行了：
  ```python
  handle = self._ready.popleft()
  
  # CPython 底层平移信标：
  self.leftblock = old_block.rightlink
  self.leftindex = 0
  ```

因此，在所有需要处理海量“先进先出 (FIFO)”排队模型的地方（比如 `asyncio` 的内部等待队列、业务消息队列），Python 官方永远推荐使用 `collections.deque()` 而不是用普通的 `list`（数组）。

## 3. 在 asyncio 中的两大应用场景

在 Python 的 `asyncio` 源码中，无论是高并发控制层（如 `Semaphore`、`Lock`），还是底层引擎层（如 Event Loop 的 `Ready Queue`），底层都完全依赖 `collections.deque` 来做排队管理。

虽然它们用的都是同一个“排队领班”，但**队伍里排队的人（载荷）完全不同**：

### 场景一：Ready Queue (Event Loop 层)
* **源码变量**：`self._ready = collections.deque()`
* **载荷（排队的人）**：**`asyncio.Handle`** （即带着函数和参数的“执行卡片”）。
* **排队目的**：等待 CPU 去真正执行。只要轮到自己出队（`popleft()`），事件循环就会立刻执行这张卡片上的回调函数。

### 场景二：Semaphore / Lock (并发控制层)
* **源码变量**：`self._waiters = collections.deque()`
* **载荷（排队的人）**：**`asyncio.Future`** （代表一个个因为拿不到锁而被迫“进入睡眠”的协程）。
* **排队目的**：排队等号。当 Semaphore 有空余名额释放时，会从队头 `popleft()` 拿出一个 Future，并给它标记为“已解决 (`set_result`)”。这会唤醒背后挂在这张 Future 上的协程（Task），将其包装成 Handle，送到上方的 **Ready Queue** 里去重新排队等 CPU 叫号。

**总结**

它们之间其实是一个**上下游的关系**：
协程往往先在 `Semaphore._waiters` 这个 `deque` 里排队休眠。当它苏醒时，就会离开沙发，跑到高层的 `BaseEventLoop._ready` 的 `deque` 里重新排队等候 CPU 叫号执行。