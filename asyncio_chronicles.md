# Chronicles of A's Python Asyncio Universe / A 的 Python 异步宇宙编年史

## Line 1: Genesis / 创世纪
`import asyncio`

**English**: Importing `asyncio` and the Event Loop blueprint.
**中文**: 引入 `asyncio` 和 Event Loop 蓝图。

## Line 51: Instantiation / 实例化
`catcher = RainCatcher()`

**English**: Creating the instance `catcher` from the `RainCatcher` blueprint.
*   **Line 5** `def __init__(self)`: Code running within the gravitational field.
*   **Line 6** `self.water_bucket = 0`: This is the shared variable of this code file.
*   **Line 9** `self.green_light = asyncio.Event()`: The Interstellar Signal Tower, default is Red Light. It creates a waiting list `_waiters=[]` and a switch `_flag = False` (Red Light).

**中文**: 从蓝图 `RainCatcher` 创建实例 `catcher`。
*   **Line 5** `def __init__(self)` 引力场内代码运行。
*   **Line 6** `self.water_bucket = 0` 是这个代码文件的共享变量。
*   **Line 9** `self.green_light = asyncio.Event()` 是星际信号塔，默认红灯。创造出一个等待名单 `_waiters=[]` 和一个开关 `_flag = False`（红灯）。

## Line 53: Launching the Universe / 启动宇宙
`asyncio.run()`

**English**: Creates the Event Loop.
*   Throws the `start_game()` Coroutine into the Event Loop's Ready Queue.
*   **Coroutine**: Like a videotape that can be paused and resumed.
*   **Event Loop**: The God/Prime Minister/Dispatcher controlling time in this file universe.

**中文**: `asyncio.run()` 创造 Event Loop。
*   把 `start_game()` 协程（Coroutine）扔进 Event Loop 的调度池（Ready Queue）中。
*   **协程（Coroutine）**：一个像录像带一样的东西，可以暂停可以继续播放。
*   **Event Loop**：是这个文件宇宙中，掌管时间的神/丞相/调度官。

## Line 40-41: Rocket Launch / 发射火箭
*   `task1 = asyncio.create_task(self.left_hand_catch())`
*   `task2 = asyncio.create_task(self.right_hand_throw())`

**English**: Tasks 1 & 2 enter the Event Loop's Ready Queue and are launched into space in parallel. The code inside the two rockets begins to run.

**中文**: task1、2 两个火箭进入 Event Loop 的调度池（Ready Queue）中，并且被并行发射到太空，两个火箭内的代码开始运行。

## Line 43: Universal Time / 宇宙时间
`await asyncio.sleep(15)`

**English**: The Prime Creator/Emperor grants time for this universe to run. Without these 15s, tasks 1 & 2 would be launched but the main program would end before they could ascend, causing the universe to collapse.

**中文**: 主神/帝皇给予这个宇宙运行的时间。如果没有这 15s，task1、task2 刚发射还没升空，主程序结束，宇宙就坍塌了。

## Line 20: Signal Check / 信号检查
`if not self.green_light.is_set()`

**English**: Checking a boolean value.
**中文**: 检查布尔值。

## Line 22: Green Light & Idempotency / 绿灯与幂等性
`self.green_light.set()`

**English**: Unlocks `.wait()`, turning `asyncio.Event()` into a Green Light.
*   `if not self.green_light.is_set(): self.green_light.set()`: Application of Idempotency. Turning the light green once has the same effect as pressing the button multiple times.
*   `set()` iterates through `_waiters[]`, finds the corresponding Future/Pager, and presses it (`set_result`).

**中文**: `self.green_light.set()` 能解锁 `.wait()`，`asyncio.Event()` 变绿灯。
*   `if not self.green_light.is_set(): self.green_light.set()`：幂等性运用，转换一次绿灯和多次按绿灯按钮一样效果。
*   `set()` 会遍历 `_waiters[]`，找到对应的 Future 呼叫器并按下（`set_result`）。

## Line 28: Interstellar Signal Lock / 星际信号锁
`await self.green_light.wait()`

**English**:
*   Checks the interstellar signal light. If Green, proceed immediately.
*   If Red, `asyncio.Event()` creates a `Future` object (Pager), attaches it to the current Task (Package), and puts it in the `_waiters[]` list.
*   **Await** (The Knight) hands the Package and Future to the **Event Loop** (The Prime Minister).
*   Event Loop suspends (freezes) the package and goes to handle other tasks.
*   Until **Line 22** `self.green_light.set()` turns the signal light Green.
*   Event Loop receives notification from the Future in hand, and uses `Await` (The Wormhole) to send the package back to its place. The right-hand async function continues execution.

**中文**:
*   检查星际信号灯，如果是绿灯马上放行。
*   如果是红灯，`asyncio.Event()` 会创建一个 `Future` 对象（呼叫器），贴在当前 Task（包裹）上，放入 `_waiters[]` 名单中。
*   **Await** (骑士) 把包裹和 Future 交给 **Event Loop** (丞相)。
*   Event Loop 把包裹挂起（冻结），去处理别的任务。
*   直到 **Line 22** `self.green_light.set()` 把星际信号灯变成绿色。
*   Event Loop 收到手中 Future 的通知，把包裹通过 **Await**（虫洞）送回原位，右手异步函数继续执行。

## Line 46-47: The End of the Universe / 宇宙终焉
`await task1`
`await task2`

**English**: Waits for the Left Hand and Right Hand functions to "pack up" (finish logic), then ends the main program. The universe collapses.
**中文**: 等待左手右手函数“收拾好东西”（跑完逻辑）后，结束主程序，宇宙坍塌。

## Core Concepts Summary / 核心概念总结

### About Await and Event Loop / 关于 Await 和 Event Loop
*   **Loop**: An infinite loop that constantly pulls Tasks from the Ready Queue.
*   **Task**: Yields control to the Event Loop when hitting Await, suspending itself.
*   **Loop**: Runs other Tasks until a signal comes from a Future.
*   **Loop**: Resumes the Task based on the Future and the pause point.

### About The Nature of Future / 关于 Future 的本质
*   **State Machine**: Has three states (Pending, Finished, Cancelled). Irreversible.
*   **Mailbox**: Has a `_result` attribute. When Finished, result must hold a value (default None).
*   **Remote/Pager**: Has a list of Callbacks. Triggered automatically once state changes (waking up the Task awaiting it).

## Line 19: Launch & Catch / 发射与捕获
*   **Launch (Put)**: `await queue.put(item)`. Miners push crystals into the gravitational field. Blocks if full.
*   **Catch (Get)**: `item = await queue.get()`. Factories suck crystals from the gravitational field. Blocks if empty.

## Line 42: Gravitational Balance (Join & Task Done) / 引力平衡 (Join & Task Done)
*   **Task Done**: `queue.task_done()`. After a factory processes a crystal, it must signal "Processing Complete" to the field.
*   **Join**: `await queue.join()`. The Prime Creator (Main) can wait here. It blocks until every item Put into the field has received a corresponding Task Done signal. This means the universe returns to peace.
