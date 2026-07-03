# 异步请求的洋葱模型：先过闸门，再铺安全网，最后出海

写 `aiohttp` 或其他异步请求代码时，新手最容易被一层又一层的 `async with`、`try...except`、`await` 绕晕。

其实这套结构不是随便套出来的。它像一颗洋葱，也像一套水利防洪系统：外层先控制水量，中层准备事故处理，内层才真正让水流出海。

一句话记住：

```text
先领号排队 -> 再买保险 -> 最后扬帆出海
```

对应到代码就是：

```python
async with sem:
    try:
        async with session.get(url) as response:
            data = await response.json()
            return data
    except Exception:
        return None
```

## 1. 为什么叫“洋葱模型”

洋葱是一层包一层的。异步请求也一样：

- 最外层：并发闸门，决定这股水能不能进入系统。
- 中间层：异常拦截网，决定出事后怎么兜底。
- 最内层：真实请求，真正去对岸服务器取数据。

这三层的顺序非常重要。顺序对了，程序就像有秩序的水利工程；顺序乱了，就容易变成洪水冲闸。

## 2. 第一层：`async with sem` 是防洪闸门

```python
async with sem:
    ...
```

`Semaphore` 是最外层，因为它负责控制“同时有多少个任务可以进入请求区”。

如果你有 200 个任务，但 `Semaphore(50)`，那同一时刻最多只有 50 个任务能继续往里走，其余任务会在闸门外等待。

这层解决的问题是：不要让所有水流同时冲进河道。

为什么它要放在最外面？因为如果任务还没有拿到通行证，就不应该开始计时、发请求、占连接、打复杂日志。它应该安静地排队。

## 3. 第二层：`try...except` 是事故拦截网

```python
async with sem:
    try:
        ...
    except Exception as exc:
        ...
```

网络请求天然不稳定。可能 DNS 解析失败，可能服务器断开连接，可能超时，也可能对方返回了无法解析的数据。

所以，在真正出海前，要先铺一张安全网。

这层解决的问题是：单个任务失败，不要把整批任务拖垮。

尤其是配合 `asyncio.gather(*tasks)` 时，如果某个子任务没有处理异常，异常可能向外冒泡，导致整个批次的控制逻辑变得混乱。新手练习时，最稳的方式是在每个请求任务内部自己兜底：

```python
except Exception as exc:
    logger.warning(f"请求失败：{exc}")
    return None
```

这里的 `return None` 像是给下游收集池交一张“这股水失败了”的白卷。它不完美，但清楚、可控。

## 4. 第三层：`session.get()` 才是真正出海

```python
async with session.get(url) as response:
    data = await response.json()
```

这一层才是真正的 HTTP 请求。

`session.get(url)` 表示从统一的 `ClientSession` 水利中枢出发，沿着底层连接池这条物理河道，去对岸服务器取数据。

这一层要尽量只做和响应本身有关的事情：

- 检查状态码。
- 读取响应体。
- 解析 JSON 或文本。
- 返回业务数据。

不要在这一层临时创造新的 `ClientSession`，也不要把并发控制藏在这里面。否则系统边界会变得很乱。

## 5. 为什么不要把 `try...except` 放在闸门外面

有时你会看到这种写法：

```python
try:
    async with sem:
        async with session.get(url) as response:
            return await response.json()
except Exception:
    return None
```

它不是绝对错误，但对新手来说，不如把 `try...except` 放在 `async with sem` 里面清晰。

原因是：我们通常关心的是“这股水被闸门放行之后发生了什么”。耗时统计、请求日志、状态码处理，都应该围绕“已进入请求区”的这段生命周期展开。

更推荐的结构是：

```python
async with sem:
    start_time = time.time()
    try:
        async with session.get(url) as response:
            ...
    except Exception:
        ...
```

这样你的秒表从开闸后开始计时，不会把“排队等闸门”的时间和“真正请求耗时”混在一起。

## 6. 性能打点应该放在哪里

推荐放在闸门里面、请求之前：

```python
async with sem:
    start_time = time.time()

    try:
        async with session.get(url) as response:
            data = await response.json()
            elapsed = time.time() - start_time
            logger.info(f"请求成功，用时 {elapsed:.2f}s")
            return data
    except Exception as exc:
        elapsed = time.time() - start_time
        logger.warning(f"请求失败，用时 {elapsed:.2f}s，原因：{exc}")
        return None
```

这表示你统计的是“通过闸门以后，这股水完成请求用了多久”。

如果你想统计“从任务创建到最终完成”的总耗时，那可以在更外层打点。但初学阶段先把单次请求耗时测清楚就够了。

## 7. 一个更完整的洋葱模板

```python
import asyncio
import logging
import time

import aiohttp


logger = logging.getLogger(__name__)


async def fetch_data(
    session: aiohttp.ClientSession,
    url: str,
    sem: asyncio.Semaphore,
    task_id: int,
):
    async with sem:
        logger.info(f"任务 [{task_id:03d}] 被闸门放行")
        start_time = time.time()

        try:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()

                elapsed = time.time() - start_time
                logger.info(f"任务 [{task_id:03d}] 成功，用时 {elapsed:.2f}s")
                return data

        except aiohttp.ClientResponseError as exc:
            elapsed = time.time() - start_time
            logger.warning(
                f"任务 [{task_id:03d}] 状态码异常 {exc.status}，"
                f"用时 {elapsed:.2f}s"
            )
            return None

        except Exception as exc:
            elapsed = time.time() - start_time
            logger.warning(f"任务 [{task_id:03d}] 请求失败，用时 {elapsed:.2f}s：{exc}")
            return None
```

这份模板的结构很清楚：

- 先过 `Semaphore` 闸门。
- 再开始计时。
- 再进入 `try...except`。
- 再用 `session.get()` 出海。
- 成功就 `return data`。
- 失败就记录并 `return None`。

## 8. 洋葱模型不只适用于 aiohttp

这个模型也适用于很多异步场景。

比如写数据库任务：

```text
并发限制 -> 事务保护 -> 真正执行 SQL
```

比如写文件处理任务：

```text
并发限制 -> 异常保护 -> 真正读写文件
```

比如调用第三方 API：

```text
限流器 -> 异常和重试 -> 真正发请求
```

所以洋葱模型本质上不是 aiohttp 语法，而是一种组织复杂操作的顺序感。

## 9. 新手最容易犯的三个错误

第一个错误：没有闸门。

```python
tasks = [fetch(url) for url in urls]
await asyncio.gather(*tasks)
```

如果 URL 很多，这会让请求一股脑冲出去。练习时可能没事，真实网站可能直接限流、封 IP，甚至把你自己的程序拖垮。

第二个错误：没有安全网。

```python
async with session.get(url) as response:
    return await response.json()
```

只要某个请求失败，异常就会往外冲。高并发下，错误会混在一起，非常难排查。

第三个错误：把所有逻辑塞进最内层。

最内层应该专注处理响应。并发控制、日志、失败兜底、结果落盘，最好分层放置。层次清楚，后续你才知道该在哪里加限速、在哪里加重试、在哪里保存失败任务。

## 10. 最后再记一遍

```text
async with sem:              # 先过闸门，控制洪水
    start_time = time.time() # 再按秒表，统计开闸后的耗时
    try:                     # 铺安全网
        async with session.get(url) as response:
            ...              # 真正出海取数据
    except Exception:
        ...                  # 出事后兜底，不让整批任务崩掉
```

这就是异步请求里的洋葱模型。

它真正教你的不是“缩进怎么写”，而是：高并发代码必须先有边界，再有保护，最后才是动作。
