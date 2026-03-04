# The Core Logic of asyncio.Semaphore

## 1. Core Positioning
`Semaphore` is a general-purpose **traffic controller** that can be used across **processes, coroutines, and threads**.
Its essence is like a **"pager machine" (waiter buzzer)** at the entrance of a nightclub. It is responsible for controlling the maximum number of people entering the "bar (critical section code)" and managing the queuing area outside the gate.

## 2. The Perfect Queuing Area (Deque)
The data structure that Semaphore uses internally to manage the waiting area is `collections.deque` (double-ended queue).
This is a **two-way queuing mechanism**, which allows elements to enter and exit from both ends, strictly following the **FIFO (First-In-First-Out)** rule.

## 3. The "Invisible" Queuers (Coroutines Scattered in Memory)
The most ingenious design is: **There is no need for every person (the Task itself) to physically go to the waiting area and stand in line.**
In fact, the queue manager (`deque`) will issue a pager (`Future` object) to each person who tries to enter but cannot get a ticket, and then **only use this lightweight pager to line up!**
The people (coroutines) can comfortably scatter in various places in the memory space and sleep deeply (suspended). `self.acquire()` finally only needs the "head" and "tail" pointers held by the queue manager (that is, the first and last positions of the `deque`) to accurately find everyone in the queue through the wormhole (Pointer) and wake them up.

## 4. Entry Protocol: The Main Backbone of `acquire()` Source Code
Aside from initialization (`__init__`), the most core action of Semaphore is using `self.acquire()` to attempt entry.
Its internal logic is as follows:

1. **Check if locked:** See if the place is full, or if there are already other people waiting outside. If there are empty seats and no one is waiting, let them in immediately:
    ```python
    if not self.locked():
        self._value -= 1
        return True
    ```
2. **Build a fence (if necessary):** Check if there is a queuing area (due to the extremely frugal lazy loading, the default queuing area is `None` until someone is actually forced to queue, then the fence is created):
    ```python
    if self._waiters is None:
        self._waiters = collections.deque()
    ```
3. **Issue a pager:** Create a dedicated `Future` and distribute it to the queuing area:
    ```python
    fut = self._get_loop().create_future()
    self._waiters.append(fut)
    ```
4. **The Ultimate Defense:** It uses two nested `try...finally...` blocks and a fallback `except CancelledError`. Whether you are normally woken up to enter, or bombed out because your boss forcibly aborted you (Task cancelled), it guarantees:
    * Scratch off the invalid pager from the queue (clear the corpse): `self._waiters.remove(fut)`
    * Return your quota back to the system (prevent ticket loss deadlocks): `self._value += 1`
    
    > **Core Insight:** The logical boundaries between the inner `finally` and outer `except` are very clear. Whether entering the bar normally or leaving abnormally, the `Future` pager in the queue must be returned (handled by `finally`). When leaving abnormally (when a task cancellation is caught), the extremely precious entry quota must also be returned (handled by `except`).

```python
        try:
            try:
                # Sleeping with hope, entrusting life to the pager (fut)
                await fut
            finally:
                # No matter how you wake up, you must cross off your queuing pager
                self._waiters.remove(fut)
        except exceptions.CancelledError:
            # If awakened by a forced cancellation, and happen to be holding an entry ticket
            if fut.done() and not fut.cancelled():
                # Spit out the precious ticket quota back to the system scoreboard
                self._value += 1
            raise
```

> **Extreme Concurrency Race Condition Handling:** Why check `if fut.done() and not fut.cancelled():` when handling the cancellation exception?
> This is an extremely rare "trio" coincidence: It indicates that **the subject (coroutine/Task) is cancelled by the outside + the object (the actual pager future in hand) is called (gets a ticket) + the object has completed normally (not cancelled)**.
> In other words: Your coroutine was sniped by aliens, but exactly at the moment of your death, the doorman successfully shoved an entry quota (key) into your pager. To prevent this key from being cremated along with you (causing system deadlocks), your last action before dying must be `self._value += 1` to throw it back to the system.

5. **Successful Entry Clearance:** After surviving a narrow escape, it finally executes `return True`.

## 5. `locked()`: The Strict "Lock Status" Inspector
Determining whether it is currently "locked" (i.e. whether newcomers must queue) is not simply a matter of glancing at the remaining quota; it comprehensively considers **FIFO queuing fairness**.

```python
    def locked(self):
        """Returns True if semaphore cannot be acquired immediately."""
        # Due to state, or FIFO rules (must allow others to run first).
        return self._value == 0 or (
            any(not w.cancelled() for w in (self._waiters or ())))
```

The goal of the entire function is to **return a crisp boolean value (`True` or `False`), which is used to judge whether the current beacon can be acquired immediately.**
It achieves this through the following extremely refined logical chain:

*   **1. Short-circuiting and Quota Check (`self._value == 0 or ...`)**:
    This is the first checkpoint, utilizing `==` to check if the remaining quota is 0.
    - If the quota is exhausted (is 0), the left side is `True`, triggering the short-circuit feature of the `or` operator, and the function directly does a `return True` (beacon is locked).
    - If the quota is not empty, the left side is `False`, and the `or` operator must proceed to evaluate the queuing status on the right side.

*   **2. The Inspector (`any(...)`)**:
    `any()` is a built-in function responsible for checking a stream. Its sole task is: check if there is **even a single `True`** in the passed generator.
    - If it finds `True` (meaning someone is queuing), it immediately stops and returns `True`, causing the entire `locked()` function to `return True` (the beacon is locked to newcomers, preserving FIFO fairness).
    - Otherwise, it returns `False`.

*   **3. Generator Expression (`not w.cancelled() for w in ...`)**:
    This is the assembly line provided to the `any()` inspector.
    - On the left is the **target of operation**: `not w.cancelled()`, which is asking each queuer: "Have you not given up queuing yet?".
    - On the right is the **scope of operation**: `for w in (self._waiters or ())`, dictating where to "grab" these queuers from.

*   **4. Defensive Default Value (`self._waiters or ()`)**:
    This is an exceptionally elegant anti-error mechanism (Fallback).
    Because `self._waiters` defaults to `None` when no one is queuing, if `None` is involved in a `for` loop, it will inevitably throw a `TypeError` crash.
    The `or` here cleverly capitalizes on the "if left is false then yield right" characteristic: when `_waiters` is `None` (falsy value), it directly yields a safe, safely-traversable empty tuple `()` as a substitute.

*   **5. Chain Reaction in Boundary Cases (Empty Queue Deduction)**:
    If there is currently no one queuing (`self._waiters` is `None`):
    1. `(self._waiters or ())` yields an empty tuple `()`.
    2. The generator assembly line `not w.cancelled() for w in ()` directly produces an empty stream since the scope is empty.
    3. Faced with an empty stream, the `any()` inspector directly rules it as `False`.
    4. At this point, the result on the right side of `or` is also `False`.
    5. Whether the entire `locked()` function is locked or not then relies entirely and exclusively on how many spare tickets are left from the first step.

## 6. The Art of the Dealer: `_wake_up_next()`
When there are tickets to distribute, how do you accurately deliver the tickets to the people who truly need them without being hindered by concurrency chaos (like people who have already given up queueing)? This all relies on the "mine clearance" mechanism of the `_wake_up_next` micro-execution function.

```python
    def _wake_up_next(self):
        """Wake up the first waiter that isn't done."""
        if not self._waiters:
            return False

        for fut in self._waiters:
            if not fut.done():
                self._value -= 1
                fut.set_result(True) # Wakes up the sleeping coroutine
                return True
        return False
```

Its core responsibility is: **distribute only one ticket at a time, clear the minefield, and deliver it with precision.**

1. **Empty Queue Interception**: First, check `if not self._waiters:`. If no one is really queueing, the security guard returns empty-handed with `False`, reporting the work as finished.
2. **"Magic Mirror" Iteration Detection**: The security guard (the `for` loop) walks down the line from front to back, using the magic mirror `if not fut.done():` to identify each person (by calling `fut.done()` to check the status).
   - **Mine Clearance & Precision Anti-Duplicate**: Under high concurrency, there might be "afterimages/ghosts" in the queue — i.e., some people **just got a ticket but haven't had time to remove themselves from the queue** (including normal people who got a ticket and are about to enter, as well as unlucky guys who got struck by lightning/cancelled right as they got a ticket and are about to return it). The pager `fut.done()` in their hands is already `True`. Using this magic mirror, the security guard will jump over them like stepping over a corpse or an empty seat, **absolutely never multiple-ticketing the same person or throwing tickets at an invalid afterimage**.
   - **Precise Delivery**: Until the first `not fut.done()` is found (a living person whose pager hasn't buzzed yet), deduces a ticket quota (`self._value -= 1`), buzzes their pager (`fut.set_result(True)`), and then immediately turns around to report **ticket successfully issued (`return True`)**!
3. **Out of Ammunition (Ghost Queue)**: If, due to the staggering of extreme concurrency, the long queue is entirely filled with dead people/empty seats, the security guard reaches the end of the line with nothing to show for it and has no choice but to `return False` at the very end.

## 7. Dual-Engine Drive Mechanism: The Leak-Proof Symphony of `release()` and `acquire()`
This is the most intelligent part of the entire Semaphore design. How do you guarantee that a precious "blank ticket" can definitely be allocated to a person in the waiting area? The system adopts an "one apparent, one hidden" dual-engine mechanism:

1. **The Regular Engine (Apparent): The On-Duty Guard of `release()`**
   This is the most intuitive mechanism: when someone leaves the bar, they return a ticket and wake up the next person in line (which means executing `_wake_up_next`). This maintains the equilibrium of one-out-one-in under normal conditions.

2. **The Fallback Sweeper (Hidden): The Night Watchman of `acquire().finally`**
   At the end of `acquire()` normally finishing or being interrupted by an exception (like Task being Cancelled), there is a final `finally` block.
   ```python
        finally:
            while self._value > 0:
                if not self._wake_up_next():
                    break  
   ```
   **Why do we still need to call people here (and with a `while` loop)?**
   In extreme race conditions: if Task-x, who was first in line, just got a ticket (pager buzzed), and was forced killed by the outside before entering the door. Task-x will return the quota to the scoreboard before dying (`self._value += 1`). However! Returning the quota to the scoreboard doesn't mean the ticket was issued! Since the rest of the queue outside the door is still dead asleep, if Task-x disappears right after returning the ticket, that ticket will become **"a dead ticket hung on the scoreboard known to no one"**!
   
   Thus, this `while` loop in the `finally` is the "night watchman" that must execute no matter what happens, leaving no dead angles.
   - As long as any coroutine finishes executing or dies halfway through and prepares to leave, as its final obligation before death, it will shine a flashlight on the scoreboard.
   - As long as it finds idle tickets (`_value > 0`), it will tirelessly send someone to issue the tickets again and again (calling `_wake_up_next()`).
   - Until there are no tickets left in hand, or the dealer returns and reports "no one is queueing outside" (`break`), it can close its eyes and leave with peace of mind.

This design of **"Separation of Responsibilities (Separating the ticketing decision from the ticketing action)"** and **"Exception Fallback (Never letting a single isolated ticket slip by)"** is the stabilizing anchor that allows the Python foundation to withstand hurricane-level concurrency.

## 8. The Art of Encapsulation
`acquire()` and `release()`'s life-and-death games and dual-engine drive are ultimately perfectly encapsulated in two magic methods: `__aenter__` and `__aexit__`.
In the face of the extremely elegant syntactic sugar `async with api_bouncer:`, the developer doesn't need to know any of this at all (queuing areas, pagers, exception fallback, or night watchmen), and can directly flow from "entry judgment" to the business code level to execute the core business. This is the true romance of foundational architects: **Keep all the complexity and dirtiness to yourself, and give the user the ultimate simplicity and elegance.**

### Line-by-Line Source Code Analysis and Core Mechanisms

```python
import collections
from asyncio import exceptions

class Semaphore:
    """A Semaphore implementation.

    A semaphore manages an internal counter which is decremented by each
    acquire() call and incremented by each release() call. The counter
    can never go below zero; when acquire() finds that it is zero, it blocks,
    waiting until some other task calls release().

    Semaphores also support the context management protocol.

    The optional argument gives the initial value for the internal
    counter; it defaults to 1. If the value given is less than 0,
    ValueError is raised.
    """

    def __init__(self, value=1):
        if value < 0:
            raise ValueError("Semaphore initial value must be >= 0")
        self._waiters = None
        self._value = value

    def __repr__(self):
        res = super().__repr__()
        extra = 'locked' if self.locked() else f'unlocked, value:{self._value}'
        if self._waiters:
            extra = f'{extra}, waiters:{len(self._waiters)}'
        return f'<{res[1:-1]} [{extra}]>'

    def locked(self):
        """Returns True if semaphore cannot be acquired immediately."""
        # Due to state, or FIFO rules (must allow others to run first).
        return self._value == 0 or (
            any(not w.cancelled() for w in (self._waiters or ())))

    async def acquire(self):
        """Acquire a semaphore.

        If the internal counter is larger than zero on entry,
        decrement it by one and return True immediately.  If it is
        zero on entry, block, waiting until some other task has
        called release() to make it larger than 0, and then return
        True.
        """
        if not self.locked():
            # Maintain FIFO, wait for others to start even if _value > 0.
            self._value -= 1
            return True

        if self._waiters is None:
            self._waiters = collections.deque()
        
        # Create a Future object effectively giving the coroutine a "pager"
        fut = self._get_loop().create_future()
        self._waiters.append(fut)

        try:
            try:
                # Coroutine goes to sleep here, yielding control to Event Loop
                await fut
            finally:
                self._waiters.remove(fut)
        except exceptions.CancelledError:
            # Currently the only exception designed be able to occur here.
            if fut.done() and not fut.cancelled():
                # Our Future was successfully set to True via _wake_up_next(),
                # but we are not about to successfully acquire(). Therefore we
                # must undo the bookkeeping already done and attempt to wake
                # up someone else.
                self._value += 1
            raise

        finally:
            # New waiters may have arrived but had to wait due to FIFO.
            # Wake up as many as are allowed.
            while self._value > 0:
                if not self._wake_up_next():
                    break  # There was no-one to wake up.
        return True

    def release(self):
        """Release a semaphore, incrementing the internal counter by one.

        When it was zero on entry and another task is waiting for it to
        become larger than zero again, wake up that task.
        """
        self._value += 1
        self._wake_up_next()

    def _wake_up_next(self):
        """Wake up the first waiter that isn't done."""
        if not self._waiters:
            return False

        for fut in self._waiters:
            if not fut.done():
                self._value -= 1
                fut.set_result(True) # Buzz the pager! Wakes up the sleeping coroutine
                # `fut` is now `done()` and not `cancelled()`.
                return True
        return False

    # ------------------------------------------------------------------------
    # Magic methods for `async with` context manager (Inherited from Mixin)
    # ------------------------------------------------------------------------
    
    async def __aenter__(self):
        """Triggered upon entering the `async with` block."""
        await self.acquire()
        # We have no use for the "as ..." clause in the with statement for locks.
        return None
        
    async def __aexit__(self, exc_type, exc, tb):
        """Triggered upon exiting the `async with` block."""
        self.release()
```

#### 1. Module Imports and Initialization
```python
import collections
from asyncio import exceptions
```
*   `import collections`: Imports the built-in library. Here, `collections.deque` (double-ended queue) is used to efficiently implement the queuing mechanism for waiters.

*   `from asyncio import exceptions`: Imports the internal exception module of asyncio (primarily `CancelledError`). Importing a specific exception module rather than the entire `asyncio` reduces circular dependencies and memory overhead.

```python
    def __init__(self, value=1):
        if value < 0:
            raise ValueError("Semaphore initial value must be >= 0")
        self._waiters = None
        self._value = value
```
*   `if value < 0`: The remaining value of the semaphore must be greater than or equal to 0.
*   `self._waiters = None`: The factory default for the waiting area is `None`, meaning the queue is not created initially (saving memory, created on demand).
*   `self._value = value`: The internal capacity of the lock set by the user, defaulting to 1 (equivalent to a standard Mutex Lock).

#### 2. Object State Representation (`__repr__`)
```python
    def __repr__(self):
        res = super().__repr__()
        extra = 'locked' if self.locked() else f'unlocked, value:{self._value}'
        if self._waiters:
            extra = f'{extra}, waiters:{len(self._waiters)}'
        return f'<{res[1:-1]} [{extra}]>'
```
*   `super().__repr__()`: Calls the `__repr__()` method of the root object `object`. If undefined, it defaults to returning a string containing the class name and memory address, for example: `'<Semaphore object at 0x10d8a4a50>'`.

*   `extra` state evaluation:
    *   If locked -> displays `locked`
    *   If unlocked -> displays `unlocked` + current remaining capacity (`value: x`)
*   `if self._waiters`: If there are objects in the waiting area (and it's not empty), the number of waiting tasks is appended to the status information.
*   **Final Output Demonstrations**:
    *   Scenario A (Just created, unoccupied): `<Semaphore object at 0x... [unlocked, value:1]>`
    *   Scenario B (Acquired, no one queuing): `<Semaphore object at 0x... [locked]>`
    *   Scenario C (Completely exhausted, 3 people queuing): `<Semaphore object at 0x... [locked, waiters:3]>`

#### 3. Checking Lock Status (`locked`)
```python
    def locked(self):
        return self._value == 0 or (
            any(not w.cancelled() for w in (self._waiters or ())))
```
The entire function returns `True` or `False`:
1.  **Quota Check (`self._value == 0`)**: First checks if the remaining capacity is 0. If it is 0, it short-circuits and returns `True` (lock is engaged); if there is capacity, it then checks the logic to the right of `or`.
2.  **Defensive Default Value (`self._waiters or ()`)**: This is an exceptionally elegant anti-error mechanism (Fallback). Because `_waiters` defaults to `None`, to prevent a `TypeError` in the for loop, replacing `None` with an empty tuple `()` provides safe iteration.
3.  **Generator Expression (`not w.cancelled() for w in ...`)**: This is a generator expression that iterates over the waiting area looking for **whether there exists any living waiter who hasn't been cancelled**.
4.  **Core Logic Conclusion**: As long as the capacity is 0, **or** there is any living applicant in the line, this Semaphore appears "locked" to the outside (newcomers must continue queuing).

#### 4. Acquiring the Lock (`acquire()`)
```python
    async def acquire(self):
        if not self.locked():
            self._value -= 1
            return True
```
*   **Direct Clearance**: Checks if it's locked. If not locked (has capacity and no one is queuing), it directly deducts the capacity by 1, issues a ticket, and executes `return True` for clearance.

```python
        if self._waiters is None:
            self._waiters = collections.deque()
        
        fut = self._get_loop().create_future()
        self._waiters.append(fut)
```
*   **Creating the Waiting Area**: If locked, checks if a waiting area exists; if not, creates a double-ended queue `deque`.
*   **Receiving the Pager**: Creates a `Future` object bound to the current Event Loop (equivalent to taking a number in line) and appends this `future` to the end of the waiting queue.

```python
        try:
            try:
                # Coroutine goes to sleep here, yielding control to Event Loop
                await fut
            finally:
                self._waiters.remove(fut)
```
*   **(Inner) Yielding Control**: `await fut` appears. The Task falls into a deep sleep here, suspended, yielding CPU control to the Event Loop. This line of code is the **atomic boundary of concurrent programming**.
*   **(Inner) Unconditional Exit Cleanup**: `finally: self._waiters.remove(fut)`. Whether this Task wakes up successfully with a ticket or is forcibly awakened by an exception, as long as it exits the queueing state, it must **immediately destroy its number plate (fut) from the queuing area** (preventing dead tasks from occupying spots).

```python
        except exceptions.CancelledError:
            if fut.done() and not fut.cancelled():
                self._value += 1
            raise
```
*   **(Outer) Handling Race Conditions**: This is the most ingenious exception catching in Semaphore. When a coroutine is forcibly cancelled externally by `task.cancel()` and detonates a `CancelledError` here before dying:
    *   If `fut.done()` is true and it's not Cancelled: This means that 0.0001 seconds before the exception detonated, another Task happened to release the lock, not only shoving the ticket into the currently dying Task but also deducting `_value` on its behalf!
    *   `self._value += 1`: Because the current Task is about to die with an exception and cannot use this ticket, it must return the ticket before dying.
    *   `raise`: Regardless of whether a ticket was mistakenly shoved in its pocket, after returning the ticket (if any), the `CancelledError` must continue to be tossed upwards to complete the coroutine's fatal exit.

```python
        finally:
            while self._value > 0:
                if not self._wake_up_next():
                    break  # There was no-one to wake up.
        return True
```
*   **(Outer) Final Heritage Distribution (Preventing Chain Deadlocks)**: Because the Race Condition mentioned above could cause a dying Task to return a ticket (`_value += 1`). Whether picking up a ticket and leaving normally, or dying with an exception, as long as exiting this massive block reveals that **there is capacity left on the table (`_value > 0`)**, there is an obligation to conveniently wake up the next person in line.

#### 5. Releasing the Lock (`release()`)
```python
    def release(self):
        self._value += 1
        self._wake_up_next()
```
*   **Bar Exit Logic**: When a person leaves the bar, they first return a ticket (`_value += 1`) and shout for the next person to enter (`_wake_up_next()`).

#### 6. Waking Up the Next Waiter (`_wake_up_next()`)
```python
    def _wake_up_next(self):
        if not self._waiters:
            return False

        for fut in self._waiters:
            if not fut.done():
                self._value -= 1
                fut.set_result(True)
                return True
        return False
```
*   If there is no waiting area, meaning no one is waiting, it simply returns `False`.
*   If there is a waiting area, it checks the queued people one by one to see if they are still alive:
    *   `if not fut.done():`: The core validation (**finding pending future objects**)! It checks for "ghost Futures" that, due to a time gap, have been marked as cancelled at the base level (`task.cancel()` flags the future as cancelled) but haven't had the time to trigger an exception and self-clean via the Event Loop (the exception detonation requires the Event Loop to shift focus to this task in the next round of `await`).
    *   Spots a living person, issues a ticket: `self._value -= 1`.
    *   `fut.set_result(True)`: Buzzes their pager, waking them up from the suspended `await fut` state.
    *   `return True`: Ends the current function after successfully waking up at least one person.
*   If iterating through the waiting area reveals it's completely filled with "ghosts (futures already marked as done)", it can only jump out of the loop to the final `return False`.

#### 7. Magic Methods (Asynchronous Context Manager)
```python
    async def __aenter__(self):
        await self.acquire()
        return None
        
    async def __aexit__(self, exc_type, exc, tb):
        self.release()
```
*   `__aenter__` (Entry Protocol): Executes `await self.acquire()` to automatically queue up and gather a ticket. Subsequently, `return None` means no excess object instantiations are provided. If a user forces the use of `async with Semaphore as s:`, the variable `s` will only receive `None`, because the semaphore functions purely as a blocking switch and its methods don't need to be additionally manipulated in the business logic.
*   `__aexit__` (Exit Protocol): Ensures safe execution of `self.release()` to return the ticket, regardless of whether exceptions were encountered upon departure.


---

# Semaphore 核心逻辑通俗解析


## 1. 核心定位
`Semaphore` 是一个可以在**进程、协程、线程**中通用的**流量控制器**。
它的本质是一个夜店门口的 **“叫号机”** 。它负责控制进入“酒吧（临界区代码）”的人数上限，并负责管理大门外的排队区域。

## 2. 完美的排队区（双端队列）
Semaphore 内部管理等待区域的数据结构是 `collections.deque`（双端队列）。
这是一种**双向移动的排队机制**，可进可出，严格遵循 **FIFO（先进先出）** 规则。

## 3. “隐身”的排队者（散落内存的协程）
最精妙的设计在于：**不需要每个人（Task 本尊）都傻傻地跑到排队区域列队站好。**
实际上，排队管理者（`deque`）会给试图进门但拿不到票的人，每人发一个叫号机（`Future` 对象），然后**只用这个轻飘飘的叫号机去排队！**
人（协程）可以舒服地散落在内存空间里的各个地方死睡（休眠挂起）。`self.acquire()`最后只需通过排队管理者手中攥着的“头部”和“尾部”这两个指针（也就是 `deque` 第一和最后一个位置），就能精准地通过虫洞（Pointer）找到队伍中的每一个人并唤醒他们。

## 4. 进门协议：`acquire()` 源码主干

*   **终极防线（异常兜底）：** 使用两个 `try...finally...` 嵌套和一个 `except CancelledError` 兜底。无论协程（Task）是正常被唤醒进门的，还是因为报错被外部强行中止炸飞的，都能保证：
    * 把作废的叫号机从队伍里划掉（清尸体）：`self._waiters.remove(fut)`
    * 把手里的名额还给系统（防门票流失死锁）：`self._value += 1`
    
    > **核心洞察：** 内层 `finally` 和外层 `except` 的逻辑边界非常清晰。不管是正常进入酒吧，还是非正常离开（外部取消任务），需要归还排队区的 `Future` 叫号机（由内层 `finally` 兜底），和归还极其珍贵的进入名额（由 `except` 兜底截获）。

```python
        try:
            try:
                # 满怀希望地睡着了，把命交给了叫号机 (fut)
                await fut
            finally:
                # 无论如何醒来，必须划掉自己排队的叫号机
                self._waiters.remove(fut)
        except exceptions.CancelledError:
            # 如果因为被强制取消而炸醒，且手里刚好攥着进门门票
            if fut.done() and not fut.cancelled():
                # 把珍贵的门票名额吐出来还给系统计分板
                self._value += 1
            raise
```

> **并发极速竞态处理（Race Condition）：** 为什么要在处理取消异常时判断 `if fut.done() and not fut.cancelled():`？
> **其实就是为了检查 Future 的状态是否为 Finished（已发票）。**
> 也就是说：你的协程被外部射杀了，但刚好在这个死去的瞬间，门童成功把进门名额（钥匙）塞进了叫号机。为了防止这把钥匙跟着你一起火化（导致系统死锁），你死前的最后一个动作，必须是 `self._value += 1` 把它扔回给系统。

*   **成功放行：** 历经九死一生，最终执行到 `return True`。

## 5. `locked()`：严谨的“锁状态”质检员
判定当前是否“锁住”（即新来者是否必须排队），并不是简单地看一眼剩余名额，而是综合考量了 **FIFO 排队公平性**。

```python
    def locked(self):
        """Returns True if semaphore cannot be acquired immediately."""
        # Due to state, or FIFO rules (must allow others to run first).
        return self._value == 0 or (
            any(not w.cancelled() for w in (self._waiters or ())))
```

整个函数的目标是 **返回一个干脆的布尔值（`True` 或 `False`），用于判断当前信标是否可被立即获取。**
它是通过以下极其精炼的逻辑链条实现的：

*   **1. or 语句的短路机制与名额检查 (`self._value == 0 or ...`)**：
    这是第一道关卡，利用 `==` 检查剩余名额是否为 0。
    - 如果名额用光（为 0），左侧为 `True`，触发 `or` 操作符的短路特性，函数直接 `return True`（信标已锁）。
    - 如果名额没用光，左侧为 `False`，`or` 操作符必须继续去评估右侧的排队情况。

*   **2. 质检员 (`any(...)`)**：
    `any()` 是一个负责检查流水的内置函数。它唯一的任务就是：检查传入的生成器里有没有**哪怕一个 `True`**。
    - 如果发现了 `True`（意味着有人在排队），它本身就立即结束并返回 `True`，进而使得整个 `locked()` 函数 `return True`（信标对新来者锁定，保持 FIFO 公平）。
    - 否则返回 `False`。

*   **3. 生成器表达式 (`not w.cancelled() for w in ...`)**：
    这是提供给 `any()` 质检员的流水线。
    - 左边是**操作目标**：`not w.cancelled()`，也就是向每个排队者发问：“你是不是还没有放弃排队？”。
    - 右边是**操作范围**：`for w in (self._waiters or ())`，规定了去哪里去“抓取”这些排队者。

*   **4. 防御性默认值 (`self._waiters or ()`)**：
    这是一个极其优雅的防报错机制（Fallback）。
    由于 `self._waiters` 在无人排队时默认是 `None`，如果有 `None` 参与 `for` 循环必定抛出 `TypeError` 崩溃。
    这里的 `or` 巧妙地利用了“若左假则抛右”的特性：当 `_waiters` 是 `None`（假值）时，直接抛出一个安全的、可安全遍历的空元组 `()` 作为替补。

*   **5. 边界情况下的连锁反应（空队列推演）**：
    如果当前没有任何人排队（`self._waiters` 是 `None`）：
    1. `(self._waiters or ())` 抛出空元组 `()`。
    2. 生成器流水线 `not w.cancelled() for w in ()` 因为范围是空的，直接产生了一个空的流出。
    3. `any()` 质检员面对空流水线，直接裁定为 `False`。
    4. 此时，`or` 右侧的结果也就是 `False`。
    5. 整个 `locked()` 函数是否锁定，便完全、且仅仅取决于第一步的余票有多少了。

## 6. 发牌官的艺术：`_wake_up_next()`
当有票可发时，如何精准地把票送到真正需要的人手里，而不被并发乱象（如已经放弃排队的人）干扰？这全靠 `_wake_up_next` 这个微观执行函数的“排雷”机制。

```python
    def _wake_up_next(self):
        """Wake up the first waiter that isn't done."""
        if not self._waiters:
            return False

        for fut in self._waiters:
            if not fut.done():
                self._value -= 1
                fut.set_result(True) # 唤醒休眠的协程
                return True
        return False
```

它的核心职责是：**每次只发一张票，摸排雷区，精准投递。**

1. **空队列拦截**：一开始检查 `if not self._waiters:`，如果是真没人排队，保安就直接两手空空返回 `False` 汇报工作结束。
2. **“照妖镜”遍历探测**：保安（`for` 循环）沿着队伍从前往后走，并用 `if not fut.done():` 这面照妖镜甄别每一个人（运行`fut.done()`查看状态，判断有没有还在pending的future）。

   - **排雷与精准防重发**：在高并发下，队列里可能存在“残影”——即某些人 **刚刚拿到票，但还没来得及把自己从队伍里剔除**（包括拿到票正要进门的正常人，以及拿到票瞬间被雷劈死正准备退票的倒霉蛋）。他们手中的叫号机 `fut.done()` 都已经是 `True` 了。保安通过这面照妖镜，会像跨过他们一样直接跳过，**绝对不会对同一个人一票多发，也不会把票扔给无效的残影**。
   - **精准投递**：直到找到第一个 `not fut.done()`（叫号机还没响的活人，处在 pending 的人），给出一张门票（`self._value -= 1`），按响他的叫号机（`fut.set_result(True)`），然后立马调头回去汇报**发票成功（`return True`）**！
3. **弹尽粮绝（幽灵队列）**：如果因为极端并发错落，导致长长的队伍里全是死人/空座（finished 或 cancelled）。保安走到队尾一无所获，就会无奈地在最后 `return False`。

## 7. 双擎驱动机制：`release()` 与 `acquire()` 的防漏网交响曲
这是整个 Semaphore 设计中最具智慧的部分。如何保证珍贵的“空票”一定能分配到等候区的人手里？系统采用了“一明一暗”的双引擎机制：

1. **常规引擎（明）：`release()` 的当班保安**
   这是最符合直觉得机制：有人离开酒吧，就归还一张票，并叫醒下一个排队的人（也就是执行 `_wake_up_next`）。维持常态下的一出一进均衡。

2. **兜底清道夫（暗）：`acquire().finally` 的巡夜保安**
   在 `acquire()` 执行完、或被异常中断（比如 Task 被 Cancelled）的最后，都有一个终极的 `finally` 块。
   ```python
        finally:
            while self._value > 0:
                if not self._wake_up_next():
                    break  
   ```
   **为什么这里还要叫人（而且是一个 While 循环）？**
   在极端竞态下：如果排第一的 Task-x 刚拿到票（叫号机响了），还没进门就被外部强杀了。Task-x 死前会把名额退回记分板（`self._value += 1`）。但是！退回记分板不等于发了票。由于门外剩下的队伍还在死睡，如果 Task-x 退完票直接消失，那张票就会变成 **“挂在记分板上无人知晓的死票”**！
   
   而这个 `finally` 的 `while` 循环，就是那个不管发生什么都要执行的、绝不留存死角的“巡夜保安”。
   - 只要任何协程执行完毕或中途死掉准备离开，作为生前的最后一项义务，它都会用手电筒照一下计分板。
   - 只要发现有闲置的票（`_value > 0`），它就会不厌其烦地一次次派人去发票（调用 `_wake_up_next()`）。
   - 直到手里没票了，或者发牌员回来报告“门外没人排队了”(`break`)，它才放心闭眼离开。

这才是 Python 并发底座能抗住狂风骤雨的定海神针。

## 8. 封装的艺术
`acquire()` 和 `release()` 的所有生死博弈与双擎驱动，最终都被完美地封装在了两个魔法方法中：`__aenter__` 和 `__aexit__`。
而在极其优雅的语法糖 `async with api_bouncer:` 面前，开发者根本不需要知道所谓的排队区、叫号机、异常兜底和巡夜保安，就可以直接从“进门判定”流转到业务代码层面，开始执行核心业务。这就是底层架构师真正的浪漫：**把所有的复杂与肮脏留给自己，把极致的简单与优雅交给用户。**


---

### Semaphore 逐行源码解析与核心机制图解

```python
import collections
from asyncio import exceptions

class Semaphore:
    """A Semaphore implementation.

    A semaphore manages an internal counter which is decremented by each
    acquire() call and incremented by each release() call. The counter
    can never go below zero; when acquire() finds that it is zero, it blocks,
    waiting until some other task calls release().

    Semaphores also support the context management protocol.

    The optional argument gives the initial value for the internal
    counter; it defaults to 1. If the value given is less than 0,
    ValueError is raised.
    """

    def __init__(self, value=1):
        if value < 0:
            raise ValueError("Semaphore initial value must be >= 0")
        self._waiters = None
        self._value = value

    def __repr__(self):
        res = super().__repr__()
        extra = 'locked' if self.locked() else f'unlocked, value:{self._value}'
        if self._waiters:
            extra = f'{extra}, waiters:{len(self._waiters)}'
        return f'<{res[1:-1]} [{extra}]>'

    def locked(self):
        """Returns True if semaphore cannot be acquired immediately."""
        # Due to state, or FIFO rules (must allow others to run first).
        return self._value == 0 or (
            any(not w.cancelled() for w in (self._waiters or ())))

    async def acquire(self):
        """Acquire a semaphore.

        If the internal counter is larger than zero on entry,
        decrement it by one and return True immediately.  If it is
        zero on entry, block, waiting until some other task has
        called release() to make it larger than 0, and then return
        True.
        """
        if not self.locked():
            # Maintain FIFO, wait for others to start even if _value > 0.
            self._value -= 1
            return True

        if self._waiters is None:
            self._waiters = collections.deque()
        
        # Create a Future object effectively giving the coroutine a "pager"
        fut = self._get_loop().create_future()
        self._waiters.append(fut)

        try:
            try:
                # Coroutine goes to sleep here, yielding control to Event Loop
                await fut
            finally:
                self._waiters.remove(fut)
        except exceptions.CancelledError:
            # Currently the only exception designed be able to occur here.
            if fut.done() and not fut.cancelled():
                # Our Future was successfully set to True via _wake_up_next(),
                # but we are not about to successfully acquire(). Therefore we
                # must undo the bookkeeping already done and attempt to wake
                # up someone else.
                self._value += 1
            raise

        finally:
            # New waiters may have arrived but had to wait due to FIFO.
            # Wake up as many as are allowed.
            while self._value > 0:
                if not self._wake_up_next():
                    break  # There was no-one to wake up.
        return True

    def release(self):
        """Release a semaphore, incrementing the internal counter by one.

        When it was zero on entry and another task is waiting for it to
        become larger than zero again, wake up that task.
        """
        self._value += 1
        self._wake_up_next()

    def _wake_up_next(self):
        """Wake up the first waiter that isn't done."""
        if not self._waiters:
            return False

        for fut in self._waiters:
            if not fut.done():
                self._value -= 1
                fut.set_result(True) # Buzz the pager! Wakes up the sleeping coroutine
                # `fut` is now `done()` and not `cancelled()`.
                return True
        return False

    # ------------------------------------------------------------------------
    # Magic methods for `async with` context manager (Inherited from Mixin)
    # ------------------------------------------------------------------------
    
    async def __aenter__(self):
        """Triggered upon entering the `async with` block."""
        await self.acquire()
        # We have no use for the "as ..." clause in the with statement for locks.
        return None
        
    async def __aexit__(self, exc_type, exc, tb):
        """Triggered upon exiting the `async with` block."""
        self.release()
```

#### 1. 模块导入与初始化
```python
import collections
from asyncio import exceptions
```
*   `import collections`：引入内置库。这里用到的是 `collections.deque`（双端队列），用于高效实现等待者的排队机制。

*   `from asyncio import exceptions`：引入 asyncio 内部的异常模块（主要是 `CancelledError`）。这里只 import 具体的 exception 模块而不是整个 `asyncio`，可以减少循环引用和内存开销。

```python
    def __init__(self, value=1):
        if value < 0:
            raise ValueError("Semaphore initial value must be >= 0")
        self._waiters = None
        self._value = value
```
*   `if value < 0`：信号量的余量值必须大于等于 0。
*   `self._waiters = None`：等候区出厂设置是 `None`，也就是一开始不创建队列（省内存，按需创建）。
*   `self._value = value`：用户设定的锁内部容量，默认值是 1（等同于普通的互斥锁 Lock）。

#### 2. 对象状态打印 (`__repr__`)
```python
    def __repr__(self):
        res = super().__repr__()
        extra = 'locked' if self.locked() else f'unlocked, value:{self._value}'
        if self._waiters:
            extra = f'{extra}, waiters:{len(self._waiters)}'
        return f'<{res[1:-1]} [{extra}]>'
```
*   `super().__repr__()`：调用根对象 `object` 的 `__repr__()` 方法。如果没有定义它，默认返回包含类名和内存地址的字符串，例如：`'<Semaphore object at 0x10d8a4a50>'`。

*   `extra` 状态判断：
    *   如果锁住了 -> 显示 `locked`
    *   如果没锁住 -> 显示 `unlocked` + 当前余量（`value: x`）
*   `if self._waiters`：如果等候区有对象存在（而且非空），则追加等待人数到状态信息里。
*   **最终输出效果演示**：
    *   场景 A（刚建立没人用）： `<Semaphore object at 0x... [unlocked, value:1]>`
    *   场景 B（被拿走了，没人排队）： `<Semaphore object at 0x... [locked]>`
    *   场景 C（不仅用光了，还有 3 个人在排队）： `<Semaphore object at 0x... [locked, waiters:3]>`

#### 3. 判断是否上锁 (`locked`)
```python
    def locked(self):
        return self._value == 0 or (
            any(not w.cancelled() for w in (self._waiters or ())))
```
整个函数返回 `True` 或 `False`：
*   `self._value == 0`：先检查余量是否为 0。如果是 0，直接短路返回 True（已落锁）；如果有余量，再检查 `or` 右边的逻辑。
*   `self._waiters or ()`：这是一个利用 Python 短路特性的安全防御。因为 `_waiters` 默认是 `None`，为了防止在 for 循环中出现 `TypeError`，遇到 `None` 时会抛出一个空元组 `()` 供安全遍历。
*   `not w.cancelled() for w in ...`：这是一个生成器表达式，遍历等候区，寻找**有没有尚未被取消的活着的排队者**。
*   **核心逻辑结论**：只要余量为 0，**或者**队伍里还有任意一个活着的申请者，这个 Semaphore 在外部看来就是“锁定”状态（新来的人必须继续排队）。

#### 4. 获取锁 (`acquire()`)
```python
    async def acquire(self):
        if not self.locked():
            self._value -= 1
            return True
```
*   **直接放行**：检查是否落锁。如果没有落锁（有余量且没人排队），直接把余量减 1 发放门票，并 `return True` 放行。

```python
        if self._waiters is None:
            self._waiters = collections.deque()
        
        fut = self._get_loop().create_future()
        self._waiters.append(fut)
```
*   **创建排队区**：如果落锁了，查看有无等候区，没有的话创建一个双端队列 `deque`。
*   **领取寻呼机**：创建一个绑定当前 Event Loop 的 `Future` 对象（相当于排队拿号），并把这个 `future` 放进等候区排队的尾部。

```python
        try:
            try:
                # Coroutine goes to sleep here, yielding control to Event Loop
                await fut
            finally:
                self._waiters.remove(fut)
```
*   **（内层）让出控制权**：`await fut` 出现，Task 在此陷入沉睡被挂起，交出 CPU 控制权给 Event Loop。这行代码是并发编程的**原子性分界线**。
*   **（内层）无条件退场清理**：`finally: self._waiters.remove(fut)`。不管这个 Task 是成功拿到门票从而苏醒，还是因为异常被迫苏醒，只要它退出排队状态，都必须**第一时间把自己的号码牌（fut）从排队区里销毁**（防止死人占坑）。

```python
        except exceptions.CancelledError:
            if fut.done() and not fut.cancelled():
                self._value += 1
            raise
```
*   **（外层）处理并发竞态条件（Race Condition）**：这是 Semaphore 最精妙的异常捕获。当协程被外部 `task.cancel()` 强行取消而在此引爆 `CancelledError` 准备赴死之前：
    *   如果 `fut.done()` 为真且不是被 Cancelled：说明在异常引爆的 `0.0001` 秒前，别的 Task 刚好释放了锁，不仅把门票塞给了当前即将死去的 Task，还替它把 `_value` 给扣掉了！
    *   `self._value += 1`：因为当前 Task 即将带着异常死掉，无法使用这个门票，它必须在死前把门票还回去。
    *   `raise`：不论兜里有没有误塞进来的门票，还完票之后，必须继续将 `CancelledError` 向上抛出以完成协程死亡退场。

```python
        finally:
            while self._value > 0:
                if not self._wake_up_next():
                    break  # There was no-one to wake up.
        return True
```
*   **（外层）最后的遗产分配（防链式死锁）**：因为上述竞态条件（Race Condition）可能导致死去的 Task 归还了门票（`_value += 1`）。无论是正常拿票走人，还是带着异常死去，只要离开这个大 block 时发现**桌面上是有余量的（`_value > 0`）**，就有义务顺手去拍醒队伍里的下一个人。

#### 5. 释放锁 (`release()`)
```python
    def release(self):
        self._value += 1
        self._wake_up_next()
```
*   **酒吧出门逻辑**：酒吧里离开一个人，就先归还一张门票（`_value += 1`），并且大喊下一个人进场（`_wake_up_next()`）。

#### 6. 唤醒下一个等待者 (`_wake_up_next()`)
```python
    def _wake_up_next(self):
        if not self._waiters:
            return False

        for fut in self._waiters:
            if not fut.done():
                self._value -= 1
                fut.set_result(True)
                return True
        return False
```
*   如果没有等候区，也就是没有人在等，直接 `return False`。
*   有等候区时，挨个去查看排队的人是否还活着：
    *   `if not fut.done():`：核心验证（**找寻还在 pending 的 future 对象**）！检查由于时间差导致虽然被底层标记了 cancelled (`task.cancel()`把 future 标记为 cancelled )，但还没来得及由 Event Loop 引发异常自我清理的“幽灵 Future ”（异常的引爆需要在下一轮的`await`中，Event Loop镜头给到这个task才能引爆异常）。
    *   发现活人，发门票：`self._value -= 1`。
    *   `fut.set_result(True)`：拨响他的寻呼机，将其从挂起的 `await fut` 状态中唤醒。
    *   `return True`：成功唤醒至少一人后结束当前函数。
*   如果在等候区遍历一圈，发现全都是“幽灵（已经 done 的废票）”，只能跳出循环走到最后的 `return False`。

#### 7. 魔法方法（异步上下文管理器）
```python
    async def __aenter__(self):
        await self.acquire()
        return None
        
    async def __aexit__(self, exc_type, exc, tb):
        self.release()
```
*   `__aenter__`（进门协议）：执行 `await self.acquire()` 自动排队并拿票。随后 `return None` 意味着不提供多余的对象实例化。如果用户强行使用 `async with Semaphore as s:`，变量 `s` 接到的只会是 `None`，因为信号量仅仅用作阻塞开关，不需要在业务中被额外操作其方法。
*   `__aexit__`（出门协议）：不论离开时是否夹带异常，都会确保安全执行 `self.release()` 归还门票。
