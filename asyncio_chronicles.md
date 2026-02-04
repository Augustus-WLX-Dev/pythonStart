# A 的 Python 异步宇宙编年史

## Line 1: 创世纪
`import asyncio`
引入 asyncio 和 Event Loop 蓝图。

## Line 51: 实例化
`catcher = RainCatcher()`
从蓝图 RainCatcher 创建实例 catcher。
*   **Line 5** `def __init__(self)` 引力场内代码运行。
*   **Line 6** `self.water_bucket = 0` 是这个代码文件的共享变量。
*   **Line 9** `self.green_light = asyncio.Event()` 是星际信号塔，默认红灯。创造出一个等待名单 `_waiters=[]` 和一个开关 `_flag = False`（红灯）。

## Line 53: 启动宇宙
`asyncio.run()` 创造 Event Loop。
*   把 `start_game()` 协程（Coroutine）扔进 Event Loop 的调度池（Ready Queue）中。
*   **协程（Coroutine）**：一个像录像带一样的东西，可以暂停可以继续播放。
*   **Event Loop**：是这个文件宇宙中，掌管时间的神/丞相/调度官。

## Line 40-41: 发射火箭
*   `task1 = asyncio.create_task(self.left_hand_catch())`
*   `task2 = asyncio.create_task(self.right_hand_throw())`
*   task1、2 两个火箭进入 Event Loop 的调度池（Ready Queue）中，并且被并行发射到太空，两个火箭内的代码开始运行。

## Line 43: 宇宙时间
`await asyncio.sleep(15)`
主神/帝皇给予这个宇宙运行的时间。如果没有这 15s，task1、task2 刚发射还没升空，主程序结束，宇宙就坍塌了。

## Line 20: 信号检查
`if not self.green_light.is_set()`
检查布尔值。

## Line 22: 绿灯与幂等性
`self.green_light.set()` 能解锁 `.wait()`，asyncio.Event() 变绿灯。
*   `if not self.green_light.is_set(): self.green_light.set()`：幂等性运用，转换一次绿灯和多次按绿灯按钮一样效果。
*   `set()` 会遍历 `_waiters[]`，找到对应的 Future 呼叫器并按下（`set_result`）。

## Line 28: 星际信号锁
`await self.green_light.wait()`
*   检查星际信号灯，如果是绿灯马上放行。
*   如果是红灯，`asyncio.Event()` 会创建一个 `Future` 对象（呼叫器），贴在当前 Task（包裹）上，放入 `_waiters[]` 名单中。
*   **Await** (骑士) 把包裹和 Future 交给 **Event Loop** (丞相)。
*   Event Loop 把包裹挂起（冻结），去处理别的任务。
*   直到 **Line 22** `self.green_light.set()` 把星际信号灯变成绿色。
*   Event Loop 收到手中 Future 的通知，把包裹通过 **Await**（虫洞）送回原位，右手异步函数继续执行。

## Line 46-47: 宇宙终焉
`await task1`
`await task2`
等待左手右手函数“收拾好东西”（跑完逻辑）后，结束主程序，宇宙坍塌。

## 核心概念总结

### 关于 Await 和 Event Loop
*   Loop 是个死循环，不断从调度池（Ready Queue）里拿出 Task。
*   Task 运行到 Await 就 Yield，把控制权给 Event Loop，自己挂起来。
*   Loop 去跑别的 Task，直到 Future 传来信号。
*   Loop 根据 Future 对应的 Task 和暂停的点，Resume Task。

### 关于 Future 的本质
*   **状态机**：有三种状态（Pending, Finished, Cancelled）。不可逆。
*   **信箱**：有一个属性 `_result`。当状态变成 Finished，result 必须装一个值（默认是 None）。
*   **遥控器**：它有一堆 Callbacks（回调函数列表）。一旦状态改变，自动触发回调（叫醒 Await 它的那个 Task）。
