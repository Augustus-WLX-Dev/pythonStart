# Asyncio TaskGroup 源码级深度解析

本文档详细解析了 `asyncio.TaskGroup` 的工作原理，从应用层代码 (`asy_taskgroups.py`) 到底层源码实现 (`taskgroups.py`)。

## 1. 电力单元模拟 (Simulation)

```python
async def power_unit(unit_id):
    """模拟电力单元，可能发生故障。"""
    delay = random.uniform(0.5, 2.0)
    await asyncio.sleep(delay)
    
    # 模拟 30% 的概率发生故障
    if random.random() < 0.3:
        print(f"❌ [电力单元 {unit_id}] 发生爆炸！💥")
        raise RuntimeError(f"Power Unit {unit_id} failed!")
    
    print(f"⚡ [电力单元 {unit_id}] 正常启动 (用时 {delay:.2f}s)")
    return f"Unit {unit_id} Online"
```

## 2. 模拟延迟与主权交接 (Await & Yield)
```python
    delay = random.uniform(0.5, 2.0)
    await asyncio.sleep(delay)
```
**解析**：
*   **模拟延迟**：模拟现实中的耗时操作。
*   **主权交接**：关键是 `await`。如果没有它，程序就是同步卡死。这里通过 `await` 将 CPU 运行权交还给 **Event Loop**，从而使得其他任务有机会运行。

## 3. 模拟故障与 TaskGroup 感知
```python
    if random.random() < 0.3:
        print(f"❌ [电力单元 {unit_id}] 发生爆炸！💥")
        raise RuntimeError(f"Power Unit {unit_id} failed!")
```
**解析**：
*   一旦出现故障抛出异常，`TaskGroup` 会立即感知到，并触发其内部的取消机制。

## 4. 模拟成功结果
```python
    print(f"⚡ [电力单元 {unit_id}] 正常启动 (用时 {delay:.2f}s)")
    return f"Unit {unit_id} Online"
```
**解析**：
*   模拟任务成功完成，返回结果。

## 5. 后台监管系统 (System Monitor)
```python
async def system_monitor():
    """实时监控系统。"""
    try:
        while True:
            print("🔍 [监控] 系统运行正常...")
            await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        print("🛑 [监控] 收到停止信号，安全关闭。")
```
**解析**：
*   这是一个死循环任务。

### 5.1 并发死循环
```python
    try:
        while True:
            print("🔍 [监控] 系统运行正常...")
            await asyncio.sleep(0.5)
```
**解析**：
*   虽然是 `while True`，但配合 `await` 使用，实现了并发。
*   它不会阻塞主线程（Process）。
*   每打印一次，它就释放主权给 **Event Loop**。

### 5.2 响应取消信号
```python
    except asyncio.CancelledError:
        print("🛑 [监控] 收到停止信号，安全关闭。")
```
**解析**：
*   模拟接收到 `TaskGroup` 传来的取消异常（`CancelledError`），从而冲破死循环，安全退出。

## 6. 主函数 (Main)与结构化并发

```python
async def main():
    """
    使用 TaskGroup 展示“结构化并发”。
    就像一个‘安全屋’，如果屋子里任何一个任务搞砸了，所有人都会被安全撤离。
    """
    print("🚀 [总控] 启动能源矩阵任务组...")
    
    try:
        # TaskGroup 是 Python 3.11+ 的‘安全屋’
        async with asyncio.TaskGroup() as tg:
            # ... (代码省略)
            
            print("⏳ [总控] 等待所有单元部署完毕...")
            
        print("✅ [总控] 能源矩阵部署成功！")
        
    except* RuntimeError as eg:
        # ... (代码省略)
```

### 6.1 意图与定义
```python
    """
    使用 TaskGroup 展示“结构化并发”。
    就像一个‘安全屋’，如果屋子里任何一个任务搞砸了，所有人都会被安全撤离。
    """
```
**解析**：建立一个“安全屋”（Scope）。在这个屋子里的所有任务（monitor 和 units）被视为一个整体，同生共死。

### 6.2 进门协议 (`__aenter__`)
```python
        async with asyncio.TaskGroup() as tg:
```
**当程序运行到 `async with` 这一行时，触发了 `TaskGroup` 的 `__aenter__` (进门协议)**：

1.  **敲门**：解释器先创建空 `TaskGroup()` 对象。检查是否初次进门 (`self._entered`)。
2.  **获取 Loop**：`loop = asyncio.get_running_loop()`，获取当前线程的事件循环内存地址。
3.  **确认家长**：`root_task = asyncio.current_task(loop)`，确认监护关系，谁在运行 `async with`（本例中是 `main()`）。
4.  **孤儿检查**：检查 parent 是否为空，防止孤儿任务造成资源泄漏。
5.  **落锁**：`self._entered = True`，标记为“已在这个安全屋中”，防止重入。
6.  **交权**：`return self`。将 `TaskGroup` 实例本身交给 `as tg` 变量。

### 6.3 任务入队 (Ready Queue)
```python
            monitor = tg.create_task(system_monitor())
            units = [tg.create_task(power_unit(i)) for i in range(1, 4)]
```
**解析**：
*   创建 `monitor` 和 `units` 任务。
*   所有任务被装进 `TaskGroup`。
*   所有任务进入 **Event Loop Ready Queue** 排队等待执行。

### 6.4 任务就绪与挂起
```python
            print("⏳ [总控] 等待所有单元部署完毕...")
```
**解析**：
*   宣告所有任务就绪。
*   **注意**：程序从 L37 走到 L46 都没有交出运行主权。只有在退出缩进块时，才会真正开始并发。

## 7. 出门协议 (`__aexit__`) 深度解析

当代码执行完 L46，根据协议，触发出门仪式 `__aexit__`。程序一只脚踏出了 `async with`，Python 自动触发该协议。

**核心机制：内层负责逻辑完备，外层负责内存安全。**

### 7.1 外层：内存安全与清理 (Wrapper)
源代码位置：`taskgroups.py:L69-81`

```python
    async def __aexit__(self, et, exc, tb):
        tb = None
        try:
            return await self._aexit(et, exc)
        finally:
            # Exceptions are heavy objects that can have object
            # cycles (bad for GC); let's not keep a reference to
            # a bunch of them.
            self._parent_task = None
            self._errors = None
            self._base_error = None
            exc = None
```
**解析**：
*   **真正的毁灭**：外层 wrapper 做的才是**“属性级”**的毁灭，防止内存泄漏。
*   `self._errors = None`：扔掉整个错误列表。
*   `self._parent_task = None`：切断和父任务的联系（解绑）。
*   `exc = None`：清空异常对象，打破循环引用。
*   `self._base_error`：记录 `async with` 语句本身抛出的错误（如 `1/0`），不同于子任务的 `self._errors`。

### 7.2 内层：逻辑完备 (`_aexit`)
内层 `_aexit` 主要处理 4 种情况：

#### 情况 1：封锁现场 (Abort)
源代码位置：`taskgroups.py:L83-110`

如果 `async with` 内部出现 Error（如 `1/0`）或 Parent 被取消：
```python
        if et is not None:
            if not self._aborting:
                self._abort()
```
**解析**：立即封锁现场，停止其他代码运行 (`self._abort()`)。

#### 情况 2：死等到底 (The Wait Loop)
源代码位置：`taskgroups.py:L116-137`

```python
        while self._tasks:
            # ...
            try:
                await self._on_completed_fut
            except exceptions.CancelledError as ex:
                if not self._aborting:
                    propagate_cancellation_error = ex
                    self._abort()
```
**解析**：
*   运行到底。
*   使用 `while` + `try await` ... `except CancelledError` 结构。
*   **承诺**：让子任务一直运行，哪怕 parent 任务出错要死掉，也要先等子任务结束或异常。

#### 情况 3：验尸与异常打包 (Exception Group)
源代码位置：`taskgroups.py:L139-159`

```python
        if self._base_error is not None:
            try:
                raise self._base_error
            finally:
                exc = None
        
        # ... (Processing cancellation)

        try:
            if propagate_cancellation_error is not None and not self._errors:
                try:
                    raise propagate_cancellation_error
                finally:
                    exc = None
```
**解析**：
*   收集异常：区分是 parent 传来的取消，还是子任务运行出错。
*   将收集到的 Error 打包成 `ExceptionGroup` 抛出去。

#### 情况 4：自我清理 (Cleanup) 与取消计数维护
源代码位置：`taskgroups.py:L160-179`

```python
        if self._errors:
            # If the parent task is being cancelled from the outside
            # of the taskgroup, un-cancel and re-cancel the parent task,
            # which will keep the cancel count stable.
            if self._parent_task.cancelling():
                self._parent_task.uncancel()
                self._parent_task.cancel()
            try:
                raise BaseExceptionGroup(
                    'unhandled errors in a TaskGroup',
                    self._errors,
                ) from None
            finally:
                exc = None
```
**解析**：
*   **取消计数维护**：这段看似“脱裤子放屁”（先 `uncancel` 再 `cancel`）的操作，其实是为了维护取消计数（Cancel Count）的准确性。在 Python 3.11+ 中，Task 可以被多次取消，这样做确保父任务的取消状态在异常抛出后依然保持“最新鲜”的状态。
