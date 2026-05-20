# collections_deque

```python
# Lib/asyncio/base_events.py
class BaseEventLoop:
    def __init__(self):
        self._ready = collections.deque()   # ← Ready Queue 本尊
        self._scheduled = []                # Scheduled Queue (heapq)
```

## 1. 概念与命名

`deque` 是数据结构名，是 **Double-Ended Queue** 的缩写，中文全称叫“**双端队列**”。在发音上，程序员们通常把它读作 `"deck"`（发音和扑克牌里的 deck 一样）。

我们可以把它拆开来看：
* **Double-Ended (双端的)**：意味着它的头和尾两头都是开的。
* **Queue (队列)**：就是排队的意思。

> 注：`collections` 是 Python 标准库里的一个模块（Module），`deque` 这个类就住在 `collections` 这个模块里面，所以我们创建的时候需要 `from collections import deque`，或者写 `collections.deque`。

## 2. 底层原理：由数组组成的双向链表 (双层架构体系)

`deque` 的底层数据结构并不是一个简单的单向或双向链表，而是一个 **“宏观靠指针关联，微观靠信标定位”** 的双层架构（在计算机科学中称为分块链表 Unrolled Linked List）。

## 2.1 架构拆解：

### 微观层面（Block 内部）：
  - 每个 Block 内部是一个物理内存连续的数组，拥有固定的容量（比如 64 个 Elements/Pointers/Address）。超出63固定容量后，就会有新的Block产生。
  - 极其重要的一点：座位上存储的并不是 Python 对象本身，而是对象的内存地址（C 语言层面的指针 PyObject*）。这使得无论你放入多庞大的对象，每个座位都只固定占用 8 字节（64位系统），彻底消除了巨大对象的拷贝开销。

### 宏观层面（Block 之间）：
  - Block 与 Block 之间在物理内存上不需要连续。
  - 它们纯粹通过结构体内部的两个指针（leftlink 和 rightlink）像虫洞一样互相连接。这完美解决了无上限动态扩容的问题。


## 2.2 总控室的两套信标

物理上的车厢（Block）和座位（数组）本身都是“无知”的，真正在指挥双端 FIFO 的，是 deque 这个列车总控室对象。总控室手里紧紧握着两套信标（Beacon）：

  - 宏观车厢信标：leftblock（队头目前在哪节车厢）、rightblock（队尾目前在哪节车厢）。
  - 微观座位信标：leftindex（这节车厢的队头在第几个座位）、rightindex（这节车厢的队尾在第几个座位）。

## 2.3 核心魔法：让 FIFO 永远保持 O(1)

在普通的 list（数组）中，把队头第一个人拿走（pop(0)），后面所有的 100 万个人都要往前挪动一个座位，极其耗时（O(N)）。

而在 deque 中，总控室通过精准控制两套信标，实现了 **“不挪数据，只平移信标”** 的神级操作：

  - 同一 Block 内：当第一个元素被 pop 掉后，第 2 到 64 个元素根本不需要往前移动。deque 仅仅是让队头的微观座位信标移动一步（leftindex += 1）。现在，系统的队头信标直接指在了第二个人头上，数组里的其他东西保持原样不动。

  - 跨越 Block：当一节车厢的人全部出队走空时，deque 利用 Block 之间的 **“指针（虫洞）”**，顺藤摸瓜找到下一节车厢，并把自己的 **“宏观车厢信标（leftblock）”** 平移过去。旧的空车厢直接报废并回收内存。

## 2.4 CPython 源码级操作演示
  结合上面的信标理论，我们来看看在极端边界情况下，底层源码是如何利用指针和信标进行极速接力的：


* **演示 A：在同一 Block 内部滑动**
  98% 的情况下，车厢既没有满，也没有空。底层的 CPython 源码做的事情极其简单粗暴：不修改任何 Block 指针，纯粹拨动微观信标（Index）。 

  * 平时排队 (进队)：往当前车厢的空座位上加元素。 
  ```c
  // CPython 底层逻辑（车厢未满时）：
  deque->rightindex += 1;  // 微观信标平移：队尾座位号往后挪一格
  deque->rightblock->data[deque->rightindex] = handle; // 把人的地址（指针）放在这个座位上
  ```

  - 这里没有任何 leftlink/rightlink 的连接操作，仅仅是对一个整数（rightindex）做加法，然后进行数组赋值。这是极致的 O(1) 性能。

  * 平时出队 (离队)：从当前车厢拿走第一个人。

  ```c
  // CPython 底层逻辑（车厢未空时）：
  handle = deque->leftblock->data[deque->leftindex]; // 根据当前的队头微观信标，把座位上的人拿出来
  deque->leftindex += 1;  // 微观信标平移：队头座位号往后挪一格（旧座位直接废弃不管）
  return handle;
  ```

  -  这里是 deque 秒杀普通 list 的精髓所在。拿走第一个人后，后面的 63 个人在物理内存中纹丝不动！底层仅仅是让 leftindex 变成了 1。原来的 0 号座位就像废土一样被抛在脑后了，等这节车厢全部走空报废时一起回收。

* **演示 B：跨越Block**

* **排队 (进队)**：瞬间把新 Block 加到队尾，只需把原来的队尾的指针指向新Block，并更新宏观信标。**
  ```python
  self._ready.append(handle)
  
  # CPython 底层逻辑（仅当右侧车厢满载时，才会挂载新车厢）：
  self.rightblock.rightlink = new_block # 原队尾车厢右向虫洞（指针Pointer），指向新车厢
  new_block.leftlink = self.rightblock # 新车厢左向虫洞（指针Pointer），指向原队尾车厢
  self.rightblock = new_block            # 总控室平移宏观信标：承认新车厢为真正的队尾
  self.rightindex = -1                   # 重置微观信标：新车厢的座位从 0 号重新开始排
  ```

  - 这两段代码分别是 Python 应用层的调用和 CPython 底层 C 语言实现的代码。
    - `self._ready.append(handle)` (Python 应用层)
    - `self.rightblock`：代表当前队伍最后面的那个Block（队尾）。
    - `new_block`：代表你要新加进来的这个block。
    - `rightlink` 和 `leftlink` ：也就是前面文档里提到的指针（虫洞），分别指向右边（后一个）和左边（前一个）的Block。

  - 这两行代码的执行过程就像是两个block跨越物理障碍手拉手：

    - `self.rightblock.rightlink = new_block`：原来队尾的Block，伸出右手（向右的指针），抓住了新来的Block。
    - `new_block.leftlink = self.rightblock`：新来的Block，伸出左手（向左的指针），抓住了原来队尾的Block。
  
>注意：为什么是 self.rightindex = -1 而不是0？
>  - 是为了兼容内部的其他代码，这里-1，后面+1就成了0。具体如下代码所示：

```C
// 第二部分：不论是否挂载了新车厢，所有人都必须经过这一步
deque->rightindex += 1;  // 座位号往前走一格
```



* **出队 (离队)**：如果当前车厢空了，只需要通过指针平移宏观信标。

瞬间从队头移除。后面的 Block 完全不需要往前挪动任何物理位置，因为它们之间是通过指针（虫洞）连在一起。只需要把“队头信标”直接插在第二个Block头上就行了：
  ```python
  handle = self._ready.popleft()
  
  # CPython 底层逻辑（仅当左侧车厢抽空时，才会废弃旧车厢，平移信标）：
  self.leftblock = old_block.rightlink # 总控室平移宏观信标：把写着“队头”的帽子从旧Block摘下，扣在右边连着的第二节Block上！
  self.leftindex = 0                 # 重置微观信标：告诉系统新车厢的 0 号位置就是新的队头
  ```
  - `handle = self._ready.popleft()` (Python 应用层)
    - `.popleft()` 顾名思义，就是从左边（队头）弹出一个元素。
    - 在 asyncio 的 Event Loop 中，这句话的意思是：“去 Ready Queue（就绪队列）的最前面，把排在第一位的那个执行卡片（handle）拿出来准备执行。”

  - 下面两行 CPython 底层逻辑
    - `old_block`：是刚刚被弹出的那个元素所在的块（即原来的队头）。
    - `self.leftblock = old_block.rightlink`： 这行代码把写着“队头”的那顶帽子（leftblock 指针），从第一个Block（old_block）头上摘下来，直接扣到了他右边的那个Block（old_block.rightlink，也就是原来的第二个Block）头上！
    - `self.leftindex = 0`： 因为底层是分块（block）存储的，当一个块空了，信标转移到下一个新的块时，我们要告诉系统：“这个新块里的第 0 个位置，就是现在的队头”。


`deque` 的核心魔法在于：无论是在队伍的最前面加/删element，还是在队伍的最后面加/删element，速度都极其快，**时间复杂度永远都是 O(1)**。（[点击查看时间复杂度讲解](time_complexity.md)）


因此，在所有需要处理海量“先进先出 (FIFO)”排队模型的地方（比如 `asyncio` 的内部等待队列、业务消息队列），Python 官方永远推荐使用 `collections.deque()` 而不是用普通的 `list`（数组）。


## 3. 在 asyncio 中的两大应用场景

在 Python 的 `asyncio` 源码中，无论是高并发控制层（如 `Semaphore`、`Lock`），还是底层引擎层（如 Event Loop 的 `Ready Queue`），底层都完全依赖 `collections.deque` 来做排队管理。

虽然它们用的都是同一个“排队领班”，但**队伍里排队的Element（载荷）完全不同**：

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