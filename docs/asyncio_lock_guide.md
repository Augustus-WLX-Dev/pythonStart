# Asyncio Lock Source Code and Underlying Mechanism Deep Dive

> [!TIP]
> **Prerequisite Reading**: It is highly recommended to read the [**Semaphore Master Guide (Deep Dive)**](asyncio_semaphore_guide.md) before reading this document.

This document is a study guide of the underlying architecture of `Lock` and its related mixin classes in Python's `asyncio` standard library. It covers the core design philosophy, responsibility isolation strategies, exception defense mechanisms, and thread-safety guarantees in concurrent programming.

```python
import collections
from asyncio import exceptions, mixins

class _ContextManagerMixin:
    async def __aenter__(self):
        await self.acquire()
        return None

    async def __aexit__(self, exc_type, exc, tb):
        self.release()

class Lock(_ContextManagerMixin, mixins._LoopBoundMixin):
    """Primitive lock objects.

    A primitive lock is a synchronization primitive that is not owned
    by a particular task when locked.  A primitive lock is in one
    of two states, 'locked' or 'unlocked'.

    It is created in the unlocked state.  It has two basic methods,
    acquire() and release().  When the state is unlocked, acquire()
    changes the state to locked and returns immediately.  When the
    state is locked, acquire() blocks until a call to release() in
    another task changes it to unlocked, then the acquire() call
    resets it to locked and returns.  The release() method should only
    be called in the locked state; it changes the state to unlocked
    and returns immediately.  If an attempt is made to release an
    unlocked lock, a RuntimeError will be raised.

    When more than one task is blocked in acquire() waiting for
    the state to turn to unlocked, only one task proceeds when a
    release() call resets the state to unlocked; successive release()
    calls will unblock tasks in FIFO order.

    Locks also support the asynchronous context management protocol.
    'async with lock' statement should be used.

    Usage:

        lock = Lock()
        ...
        await lock.acquire()
        try:
            ...
        finally:
            lock.release()

    Context manager usage:

        lock = Lock()
        ...
        async with lock:
             ...

    Lock objects can be tested for locking state:

        if not lock.locked():
           await lock.acquire()
        else:
           # lock is acquired
           ...

    """

    def __init__(self):
        self._waiters = None
        self._locked = False

    def __repr__(self):
        res = super().__repr__()
        extra = 'locked' if self._locked else 'unlocked'
        if self._waiters:
            extra = f'{extra}, waiters:{len(self._waiters)}'
        return f'<{res[1:-1]} [{extra}]>'

    def locked(self):
        """Return True if lock is acquired."""
        return self._locked

    async def acquire(self):
        """Acquire a lock.

        This method blocks until the lock is unlocked, then sets it to
        locked and returns True.
        """
        # Implement fair scheduling, where thread always waits
        # its turn. Jumping the queue if all are cancelled is an optimization.
        if (not self._locked and (self._waiters is None or
                all(w.cancelled() for w in self._waiters))):
            self._locked = True
            return True

        if self._waiters is None:
            self._waiters = collections.deque()
        fut = self._get_loop().create_future()
        self._waiters.append(fut)

        try:
            try:
                await fut
            finally:
                self._waiters.remove(fut)
        except exceptions.CancelledError:
            # Currently the only exception designed be able to occur here.

            # Ensure the lock invariant: If lock is not claimed (or about
            # to be claimed by us) and there is a Task in waiters,
            # ensure that the Task at the head will run.
            if not self._locked:
                self._wake_up_first()
            raise

        # assert self._locked is False
        self._locked = True
        return True

    def release(self):
        """Release a lock.

        When the lock is locked, reset it to unlocked, and return.
        If any other tasks are blocked waiting for the lock to become
        unlocked, allow exactly one of them to proceed.

        When invoked on an unlocked lock, a RuntimeError is raised.

        There is no return value.
        """
        if self._locked:
            self._locked = False
            self._wake_up_first()
        else:
            raise RuntimeError('Lock is not acquired.')

    def _wake_up_first(self):
        """Ensure that the first waiter will wake up."""
        if not self._waiters:
            return
        try:
            fut = next(iter(self._waiters))
        except StopIteration:
            return

        # .done() means that the waiter is already set to wake up.
        if not fut.done():
            fut.set_result(True)

```
---

## I. Core Execution Mechanism Analysis of Lock

### 1. Queue Jumping and Optimization

```python
if (not self._locked and (self._waiters is None or
        all(w.cancelled() for w in self._waiters))):
    self._locked = True
    return True
```
**Analysis**: This is an excellent performance optimization. `all(w.cancelled() for w in self._waiters)`. If all tasks in the waiting queue have been cancelled, there is no need for the new task to foolishly line up at the end of the queue. It can simply acquire the lock and enter directly.

### 2. Happy Path and Waiting Queue Cleanup Strategy

```python
async def acquire(self):
    # ... queueing logic ...
    try:
        try:
            await fut
        finally:
            self._waiters.remove(fut)
    except exceptions.CancelledError:
        # ... exception handling ...

    self._locked = True
    return True
```
**Analysis**:
*   **Happy Path**: `await fut` puts the current Task to sleep. Once awakened, it smoothly flows down, executes `self._locked = True`, and `return True` to lock and proceed.


### 3. State Validation of Releasing Lock (Release)

```python
def release(self):
    if self._locked:
        self._locked = False
        self._wake_up_first()
    else:
        raise RuntimeError('Lock is not acquired.')
```
**Analysis**: `raise RuntimeError('Lock is not acquired.')`. If `release()` is called without acquiring the lock first, it raises an error directly. This is a basic state safety validation mechanism.

### 4. Wake-up Mechanism and Defensive Programming (StopIteration)

```python
def _wake_up_first(self):
    if not self._waiters: 
        return
    try:
        fut = next(iter(self._waiters)) # <--- Deep dive
    except StopIteration:
        return
```
**Analysis**:
*   **Pointer and Caller**: `iter(self._waiters)` creates an iterator, which is a pointer pointing to the head of the queue. `next(...)` is a command to call the name, reporting the name of the person the pointer is currently pointing to, and then moves the pointer forward by one. Since it's a newly created iterator, `fut` inevitably extracts the very first Future.

*   **Why use `next()` instead of `popleft()`? (Core Design Philosophy: Responsibility Isolation)**:
    In the design of `acquire()`, to handle possible external Task cancellations, the waiter has its own `finally: self._waiters.remove(fut)` responsible for removing itself from the queue. If this line of code in the wake-up phase oversteps and uses the queue's `popleft()` to forcefully kick the person out, when that Future wakes up and executes `remove(fut)` in its own `finally` block, it will throw a `ValueError` (not in queue) because it's no longer in the queue, leading to a crash.

    This exquisitely reflects the **responsibility isolation** of the underlying source code:
    *   **The Waker (`_wake_up_first`)** is only responsible for waking up using `next()`, **absolutely not overstepping to touch the additions/deletions of the queue**;
    *   **Whoever leaves cleans up themselves; this is the Waiter's (`acquire`) own responsibility**. This allows the Task to quickly find and remove itself, regardless of whether it is at the front or in the middle of the queue.

*   **Why `except StopIteration`? (The Ultimate Secret of Defensive Programming)**:
    `except StopIteration` is because when the `next()` function iterates over container contents, if the container has nothing left, it will throw a `StopIteration` exception. In this example, when no one is in the waiting queue, `next()` throws this exception.

    **The Master's Approach**: As long as `next()` appears in the code, regardless of how many layers of non-empty checks have been done before (e.g., the `if not self._waiters: return` on the first line above), always wrap an `except StopIteration:` layer on the outside as a safety net. This ensures that even under extremely rare or unexpected underlying modifications, the program can safely reach `return` without causing a direct crash.

### 5. Isolated Return

```python
return
```
**Analysis**: In Python, when you write an isolated `return` (followed by nothing), it is exactly equivalent to `return None`.

---

## II. \_ContextManagerMixin: Context Manager and Mixin Pattern

```python
class _ContextManagerMixin:
    async def __aenter__(self):
        await self.acquire()
        return None

    async def __aexit__(self, exc_type, exc, tb):
        self.release()

class Lock(_ContextManagerMixin, mixins._LoopBoundMixin):
    # ...
```

### 1. ContextManager (Context Manager)
In Python, anything that can be placed after `with` or `async with` is called a "context manager".
For example, given `async with data_lock:`, the Python interpreter actually does two things under the hood:
1. **Before entering**: Automatically calls `data_lock.__aenter__()`
2. **After exiting**: Automatically calls `data_lock.__aexit__(...)`

### 2. The Essence of Mixin Pattern
Mixin is a naming convention for special classes.

If a class name ends with `Mixin`, it is telling the code reader: "I am not a complete, standalone entity class. I am just an 'expansion pack' or 'plugin' with specific functionality. As long as other classes add my name into their parentheses (inherit from me), they can instantly piggyback off my features!"

Using a Mixin is equivalent to letting `_ContextManagerMixin` grant the universal exo-armor of `async with` syntactic sugar. In concurrency tools, whether it's Lock or Semaphore, as long as `acquire()` and `release()` are implemented internally, inheriting `_ContextManagerMixin` equips the class with `async with` capabilities.

**Subtext**: "Bro, as long as you provide the `acquire` and `release` functionalities yourself, put on this set of armor, and others can directly control you using the elegant async with syntax. I'll wrap up the dirty work of entering and exiting for you!"

---

## III. \_LoopBoundMixin and Double-Checked Locking (DCL) Pattern

`_LoopBoundMixin` (Event Loop Binding Mixin Class) is designed by the `asyncio` base layer to prevent **"cross-server chatting" (cross-thread interference)** in multi-threading / multi-event-loop environments.

By default, the code only has one event loop running, but advanced (or haphazardly written) code will spin up multiple real threads in the same process, with each thread running an independent event loop. This could cause a Lock within Thread A to run over to Thread B and be unexpectedly called, throwing an exception or deadlocking. To solve this problem, the Lock needs to be bound to the memory address of the current event loop (acknowledging its master).

### Source Code Analysis: Double-Checked Locking (DCL)

```python
class _LoopBoundMixin:
    _loop = None  # Records which event loop this lock "acknowledges as master"

    def _get_loop(self):
        # 1. Get the currently running event loop
        loop = events._get_running_loop() 

        # 2. If this lock hasn't "acknowledged a master" yet (called for the first time)
        if self._loop is None:
            with _global_lock: # Thread-safe lock
                if self._loop is None:
                    self._loop = loop # Bound by blood, forcefully binds it to the current event loop!
                    
        # 3. If the currently running loop is not the master of this lock
        if loop is not self._loop:
            raise RuntimeError(f'{self!r} is bound to a different event loop')
            
        return loop
```

A **double `if self._loop is None`** appears here, interleaved with `with _global_lock`. The combination of these two ifs and a global lock is exactly the famous **Double-Checked Locking (DCL)** pattern in concurrent programming.

### Why is DCL needed?
This is to prevent multi-thread variable overwriting (shadowing) at the OS thread level.
The first layer `if self._loop is None` checks whether an Event loop memory address is bound. If not, it acquires the global lock `with _global_lock` — this is a mutually exclusive giant lock at the Python interpreter level (`threading.Lock`).

**Why use `threading.Lock`?**
Because if in the same microsecond, the main thread and the sub-thread both attempt to grab this unbound Lock:
*   If `with _global_lock` is not added, the main thread and the sub-thread will reach `self._loop = loop` at the same time. Since this is operating-system-level parallelism, the C-language underlying memory might be torn, causing a fatal overwrite at the logical level (Logical Race Condition) or a Core Dump.
*   With `with _global_lock`, all threads must line up. In this microsecond, only one thread can get the key and enter the writing action. After it finishes writing and leaves, the second thread gets the lock and enters, but then it will be **intercepted by the second `if`** (at this point `self._loop` is no longer `None`, so it won't be overwritten).

### Double-Checked Locking (DCL) Summary:
1. **Outer if**: Performance filter, yielding a direct pass in 99% of cases, avoiding the need to go through the heavy thread mutex lock every time it's called.
2. **Global lock (`_global_lock`)**: Forces concurrent real threads to line up here, forcefully serializing parallel execution.
3. **Inner if**: Used to intercept threads that have lined up for a long time but have already been overwritten by earlier threads in the queue while waiting, preventing duplicate assignments.

---

# Asyncio Lock 源码与底层机制深度剖析

> [!TIP]
> **前置阅读推荐**：在阅读本文档之前，强烈建议您先阅读 [**Semaphore 核心指南（深度剖析）**](asyncio_semaphore_guide.md)。

本文档是对 Python `asyncio` 标准库中 `Lock` 及其相关混入类（Mixin）底层架构的学习总结。涵盖了并发编程中的核心设计哲学、责任划分策略、异常防御机制以及多线程安全保障机制。



## 一、 Lock 核心运行机制解析

### 1. 插队拿锁与优化 (Queue Jumping)

```python
if (not self._locked and (self._waiters is None or
        all(w.cancelled() for w in self._waiters))):
    self._locked = True
    return True
```
**解析**：这是一个极佳的性能优化。`all(w.cancelled() for w in self._waiters)`。如果所有排队区的 Task 都已经取消（cancelled），新来的任务就没必要傻乎乎地去排在队尾。它可以直接拿锁进场。

### 2. 顺利拿锁 (Happy Path) 与等待队列清理策略

```python
async def acquire(self):
    # ... 前置排队逻辑 ...
    try:
        try:
            await fut
        finally:
            self._waiters.remove(fut)
    except exceptions.CancelledError:
        # ... 异常处理 ...

    self._locked = True
    return True
```
**解析**：
*   **顺利运行**：`await fut` 让当前 Task 陷入休眠，一旦被唤醒，顺利流转到下面，执行 `self._locked = True` 并 `return True` 上锁走人。


### 3. 释放锁的状态校验 (Release)

```python
def release(self):
    if self._locked:
        self._locked = False
        self._wake_up_first()
    else:
        raise RuntimeError('Lock is not acquired.')
```
**解析**：`raise RuntimeError('Lock is not acquired.')`。如果没有上锁就调用 `release()`，直接报错。基本的状态安全校验机制。

### 4. 唤醒机制与防御性编程 (StopIteration)

```python
def _wake_up_first(self):
    if not self._waiters: 
        return
    try:
        fut = next(iter(self._waiters)) # <--- 深入剖析
    except StopIteration:
        return
```
**解析**：
*   **指针与点名器**：`iter(self._waiters)` 创造一个迭代器，它是一个指向队伍最前头的指针。`next(...)` 这是一个命令点名器，报出指针当前指的人的名字，然后指针往后挪一位。因为是初次创建出来的迭代器，所以 `fut` 提取的必然是第一个 Future。

*   **为什么不用 `popleft()` 而是 `next()`？（核心设计哲学：责任区分）**：
    在 `acquire()` 的设计中，为了应对可能的外部取消 Task 的情况，等待者有自己的 `finally: self._waiters.remove(fut)` 负责将自己从队伍中剔除。如果唤醒阶段的这行代码越权使用了队列的 `popleft()` 强行把人踢出队伍，等那个 Future 醒来执行自己 `finally` 里的 `remove(fut)` 时，就会因为队伍里已经没自己了而抛出 `ValueError` (不在队列中) 导致崩溃。

    这极其精妙地体现了底层源码的**责任划分隔离**：
    *   **唤醒者（`_wake_up_first`）**只负责用 `next()` 叫醒，**绝对不越权碰队列的增删**；
    *   **谁走谁删是等待者（`acquire`）自己的责任**，这样能让 Task 快速找到并剔除它自己，不管它此时是在队伍的前头还是中间。

*   **为什么要有 `except StopIteration`？（防御性编程的终极奥义）**：
    `except StopIteration` 是因为 `next()` 函数在遍历容器内容时，如果容器已经没有东西了，它就会抛出 `StopIteration` 异常。例子中就是排队区没有人排队时，`next()` 会抛出该异常。

    **高手的做法**：只要代码里出现了 `next()`，不管前面做了多少重非空判断（例如上文第一行的 `if not self._waiters: return`），外面永远套一层 `except StopIteration:` 来兜底。这保证了哪怕在极其罕见或意外的底层修改下，程序也能安全走到 `return`，而不会引起直接崩溃。

### 5. 孤立的 Return

```python
return
```
**解析**：在 Python 中，当你写一个孤零零的 `return`（后面不跟任何东西）时，它完全等价于 `return None`。

---

## 二、 \_ContextManagerMixin：上下文管理器与混入类模式

```python
class _ContextManagerMixin:
    async def __aenter__(self):
        await self.acquire()
        return None

    async def __aexit__(self, exc_type, exc, tb):
        self.release()

class Lock(_ContextManagerMixin, mixins._LoopBoundMixin):
    # ...
```

### 1. ContextManager 上下文管理器
在 Python 里，凡是可以放在 `with` 或者 `async with` 后面的东西，都叫“上下文管理器”。
比如 `async with data_lock:` 时，Python 解释器在底层其实会做两件事：
1. **进门前**：自动调用 `data_lock.__aenter__()`
2. **出门后**：自动调用 `data_lock.__aexit__(...)`

### 2. Mixin 模式的本质
Mixin是一种特殊类的命名规范。

如果一个类的名字以 `Mixin` 结尾，这是在告诉看代码的人：“我不是一个完整的、可以独立存在的实体类。我只是一个带有特定功能的‘扩展包’或‘插件’。别的类只要把我的名字加到它的括号里（继承我），就能瞬间白嫖我的功能！”

使用 Mixin 相当于让 `_ContextManagerMixin` 赋予 `async with` 语法糖的通用外挂盔甲。在并发工具中，不论是 Lock 还是 Semaphore，只要内部实现了 `acquire()` 和 `release()`，在此类名后继承 `_ContextManagerMixin`，这个类就拥有了 `async with` 的能力。

**潜台词**：“兄弟，只要你本身提供了 `acquire` 和 `release` 的功能，把这套机甲套身上，别人就可以直接用优雅的 async with 语法来控制你了，进门出门的粗活我来帮你包装好！”

---

## 三、 \_LoopBoundMixin 与双重检查锁 (DCL) 模式

`_LoopBoundMixin`（事件循环绑定混入类）是 `asyncio` 底层为了防止多线程/多事件循环环境下的 **“跨服聊天”** 而设计的。

默认情况代码只有一个事件循环在运行，但是高级别（或者乱写）的代码，会在同一个进程开多个真实线程，每个线程跑一个独立的事件循环。这可能会导致线程A内部的 Lock，跑到线程B去被意外调用抛出异常或死锁。为了解决这个问题，需要让 Lock 绑定到当前的事件循环内存地址（认主）。

### 源码解析：双重检查锁 (Double-Checked Locking)

```python
class _LoopBoundMixin:
    _loop = None  # 记录这把锁“认主”的事件循环是谁

    def _get_loop(self):
        # 1. 获取当前正在跑的事件循环
        loop = events._get_running_loop() 

        # 2. 如果这把锁还没“认主”（第一次被调用）
        if self._loop is None:
            with _global_lock: # 线程安全锁
                if self._loop is None:
                    self._loop = loop # 滴血认亲，把它和当前的事件循环强行绑定！
                    
        # 3. 如果当前跑的事件循环，不是这把锁的主人
        if loop is not self._loop:
            raise RuntimeError(f'{self!r} is bound to a different event loop')
            
        return loop
```

这里出现了**双重 `if self._loop is None`**，并且夹杂了 `with _global_lock`。这两个 if 和全局锁的组合，正是并发编程中著名的 **双重检查锁 (Double-Checked Locking, DCL)** 模式。

### 为什么需要 DCL？
这是为了防止线程级别的多线程覆盖（shadow）。
第一层 `if self._loop is None` 是检测有没有绑定 Event loop 的内存地址。如果没有，开启全局锁 `with _global_lock` —— 这是 Python 解释器级别的一把互斥大锁（`threading.Lock`）。

**为什么要用 `threading.Lock`？**
因为如果在同一微秒，主线程和副线程同时试图拿到这把还没被绑定的 Lock：
*   如果没有加 `with _global_lock`，主线程和副线程同时走到 `self._loop = loop`。由于这是操作系统级别的并行，C语言底层的内存可能会被撕裂，发生逻辑层面的致命相互覆盖（Logical Race Condition）或者核心转储 (Core Dump)。
*   有了 `with _global_lock`，所有线程都必须排队。这一微秒中只有一个线程能拿到钥匙，进入写入动作。等它写完离开后，第二个线程拿到锁进门，此时就会**被第二个 `if` 拦截**（此时 `self._loop` 已经不再是 `None`，不会进行覆写）。

### 双重检查锁 (DCL) 总结：
1. **外层 if**：性能过滤器，99%的情况直接命中放行，避免了每次调用都需要走沉重的线程互斥锁。
2. **全局锁 (`_global_lock`)**：让并发的真实线程在此排队，把并行强行卡成串行。
3. **内层 if**：用来拦截排队很久，但是在等待排队期间已经被排在前面的线程覆写过的线程，防止重复赋值。
