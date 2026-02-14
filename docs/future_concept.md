# 🗝️ The Future Object: The Meta-Theory of Asyncio

This document records the refined mental model of the `Future` object—the fundamental building block of the Asyncio universe.

## 🎭 1. Status Machine: The Contract State

*   **Three States**: `Pending` (Processing), `Finished` (Settled), `Cancelled` (Annulled).
*   **Irreversibility**: Once a Future moves from `Pending` to another state, it is "Frozen" (凝固). It cannot be restarted.
*   **Correction**: 
    *   **Finished**: Includes both success return and `RuntimeError` (Settled with injury).
    *   **Cancelled**: Only triggered by an explicit `task.cancel()` call.
    *   Any state change immediately triggers the **Pager (Call Machine)**.

## 📬 2. Mailbox: The Dual-Compartment Storage

*   **Content**: Holds either a `Result` or an `Exception`.
*   **Result**: Defaults to `None` (placeholder). If the coroutine returns a value, it fills this compartment.
*   **Exception (The Bomb)**: If an error occurs, it is placed here. 
    *   > [!CAUTION]
    *   An uncaught `Exception` in the mailbox is a **Live Bomb**. If you `await` it without `try...except`, it will detonate, triggering a chain reaction (meltdown) of the Task or TaskGroup.
*   **Delivery**: Once either compartment is filled, the contract is "Delivered" (送达).

## 📟 3. Pager (Call Machine): The Signal Dispatcher

*   **Await (The Wormhole)**:
    *   When a Task hits `await`, it yields control and "hangs" its execution context on this Future's signal tower.
    *   It acts as a wormhole that transports the result (or explosion) back to the Task during the chain reaction.
*   **Callback**:
    *   A list of "Sentinels" (Callbacks) managed by the Task (e.g., `_on_task_done`).
    *   As soon as the Status Machine freezes, the Pager automatically triggers every sentinel in the list to report back to the next layer of management.

---

# 🗝️ Future 对象：Asyncio 的元理论

本文记录了对 `Future` 对象的深度心智模型构建——它是 Asyncio 宇宙中最根本的基石。

## 🎭 1. 状态机：契约效力

*   **三种状态**：`Pending`（处理中）、`Finished`（已结算）、`Cancelled`（已注销）。
*   **不可逆性**：一旦 Future 从 `Pending` 切换到其他状态，它就“凝固”（Frozen）了，无法重启。
*   **纠偏与理解**：
    *   **Finished**：既包括成功返回结果，也包括抛出 `RuntimeError`（带伤结算）。
    *   **Cancelled**：仅由显式的 `task.cancel()` 调用触发。
    *   任何状态改变都会立即触发 **呼叫机 (Pager)**。

## 📬 2. 信箱：双层储物格

*   **内容物**：告知完成度，存放 `Result` (结果) 或 `Exception` (异常)。
*   **Result 格**：默认为 `None`（占位符）。如果协程有 `return` 返回值，则填入此格。
*   **Exception 格（炸弹）**：如果运行出错，异常会被塞入此格。
    *   > [!CAUTION]
    *   信箱中未捕获的报错就是**定时炸弹**。如果你直接 `await` 它而没有使用 `try...except` 捕获，它会原地引爆，并引发整个 Task 或 TaskGroup 的连锁熔断。
*   **投递**：无论哪个格子被填入，这份契约都算作“已送达”（Delivered）。

## 📟 3. 呼叫机：信号分发器

*   **Await（虫洞）**：
    *   既是悬挂 `task()` 内部参数函数的信号灯，也是把结果/异常通过 `Yield` 链式反应传回任务的虫洞。
    *   当任务遇到 `await` 时，它会主动进入“虫洞”挂起，直到呼叫机将其唤醒。
*   **Callback（回调）**：
    *   由任务（Task）设置的回调清单（哨兵），例如 `_on_task_done`。
    *   一旦状态机从 `Pending` 变为 `Finished` 或 `Cancelled`，信箱汇报结果，呼叫机便会自动按顺序触发清单中的所有回调。

---

> "You don't just write async code; you manage the lifecycle of these invisible contracts."
> "你不仅仅是在写异步代码，你是在管理这些隐形契约的整个生命周期。"
