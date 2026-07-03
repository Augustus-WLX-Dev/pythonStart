# HTTP 状态码新手指南：路通了，但对岸怎么回答你

写爬虫、接口调用、`aiohttp` 请求时，经常会看到这些结果：

- `200 OK`
- `404 Not Found`
- `429 Too Many Requests`
- `500 Internal Server Error`

这些就是 HTTP 状态码。

用河流的类比来讲：状态码不是“河道有没有断”，而是“水流已经到了对岸，对岸服务器给你回了一块牌子”。

这句话很关键：

```text
异常表示路可能断了；状态码表示路通了，但对岸给出了不同答复。
```

## 1. 状态码和异常不是一回事

很多新手会疑惑：我已经写了 `try...except`，为什么还要检查 `response.status`？

因为它们管的是两种不同问题。

异常通常表示网络层出事：

- DNS 解析失败。
- TCP 连接建立失败。
- 请求超时。
- 服务器中途断开连接。
- 本机网络或代理有问题。

这些情况像是河道断了、水闸坏了、船根本没到对岸。此时通常没有 HTTP 状态码，因为对岸服务器根本没有正常回信。

状态码表示 HTTP 层已经有响应：

- 你的请求到达了服务器。
- 服务器理解或至少接收了这次请求。
- 服务器给你返回了一个明确答复。

所以 `404`、`429`、`500` 都不是“没连上”。恰恰相反，它们说明路通了，对岸已经回话了，只是回话内容不一定好听。

## 2. aiohttp 默认不会把 404 或 500 当成异常

在 `aiohttp` 里，这段代码即使遇到 `404` 或 `500`，也不一定进入 `except`：

```python
async with session.get(url) as response:
    print(response.status)
    text = await response.text()
```

原因是：从 aiohttp 的角度看，只要 HTTP 响应正常回来，网络通信就是成功的。

如果你希望 `404`、`500` 这类非成功状态码直接变成异常，可以调用：

```python
response.raise_for_status()
```

完整写法：

```python
try:
    async with session.get(url) as response:
        response.raise_for_status()
        data = await response.json()
        return data
except aiohttp.ClientResponseError as exc:
    print(f"HTTP 状态码异常：{exc.status}")
    return None
```

`raise_for_status()` 像是水质检测口：发现对岸回的是失败牌子，就主动把它丢进异常处理流程。

## 3. 状态码的五大家族

HTTP 状态码第一位数字表示大类。

```text
1xx：临时信息，新手很少直接处理
2xx：成功
3xx：重定向
4xx：客户端请求有问题
5xx：服务器端出问题
```

真正写爬虫或调用 API 时，最常见的是 `2xx`、`4xx`、`5xx`。

## 4. `2xx`：成功，水流拿到了货

最常见的是：

- `200 OK`：请求成功，正常拿到响应。
- `201 Created`：创建成功，常见于提交表单或创建资源的 API。
- `204 No Content`：成功了，但没有响应体。

新手要特别注意 `204`。它不是失败，而是“对岸说成功，但没有东西给你”。如果你对 `204` 强行 `await response.json()`，可能会因为没有内容而解析失败。

可以这样处理：

```python
if response.status == 204:
    return None

data = await response.json()
```

## 5. `3xx`：重定向，对岸让你换个码头

常见状态码：

- `301 Moved Permanently`：永久换地址。
- `302 Found`：临时换地址。
- `304 Not Modified`：资源没变，常见于缓存。

`aiohttp` 默认会跟随重定向，所以很多时候你不会明显看到 `301` 或 `302`。

但如果你想自己观察重定向，可以关闭自动跳转：

```python
async with session.get(url, allow_redirects=False) as response:
    print(response.status)
    print(response.headers.get("Location"))
```

在河流模型里，`3xx` 就是对岸告诉你：“这个码头不用了，请去另一个入口。”

## 6. `4xx`：你的请求有问题

`4xx` 通常表示客户端这一侧的问题，也就是你发过去的请求不符合对方要求。

常见状态码：

- `400 Bad Request`：请求格式不对，参数可能写错了。
- `401 Unauthorized`：没有登录，或者 Token 缺失。
- `403 Forbidden`：服务器理解你是谁，但不允许你访问。
- `404 Not Found`：资源不存在，URL 可能错了。
- `408 Request Timeout`：服务器等待你的请求等太久。
- `429 Too Many Requests`：你请求太快，被限流了。

其中 `403` 和 `429` 对爬虫尤其重要。

`403` 像是对岸保安说：“我知道你来了，但你不能进。”可能原因包括 Cookie 不对、登录态失效、User-Agent 太明显、权限不足。

`429` 像是防洪闸门报警：“你放水太猛了。”这时不该无脑重试，而应该降速、休眠、加限流器。

示例：

```python
if response.status == 429:
    await asyncio.sleep(5)
    return None
```

更成熟的做法是使用指数退避和随机抖动，让重试请求错开时间，不要形成第二波洪峰。

## 7. `5xx`：对岸服务器出问题

`5xx` 通常表示服务器端问题。

常见状态码：

- `500 Internal Server Error`：服务器内部错误。
- `502 Bad Gateway`：网关从上游拿到了坏响应。
- `503 Service Unavailable`：服务暂时不可用，可能在维护或过载。
- `504 Gateway Timeout`：网关等上游服务器等超时。

在河流模型里，`5xx` 表示你的水流到了对岸，但对岸的仓库、调度站或中转码头出了问题。

处理方式一般是：

- 记录日志。
- 稍后重试。
- 控制重试次数。
- 不要所有任务同一秒重试。

示例：

```python
if response.status in {500, 502, 503, 504}:
    logger.warning(f"服务器暂时异常：{response.status}")
    return None
```

## 8. 手动检查状态码，还是用 `raise_for_status()`

有两种常见风格。

第一种：手动检查，适合你想对不同状态码做不同处理。

```python
async with session.get(url) as response:
    if response.status == 200:
        return await response.json()

    if response.status == 429:
        logger.warning("被限流，稍后重试")
        return None

    if response.status == 404:
        logger.warning("资源不存在")
        return None

    logger.warning(f"未知状态码：{response.status}")
    return None
```

第二种：使用 `raise_for_status()`，适合你想把非成功状态码统一丢给异常处理。

```python
try:
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.json()
except aiohttp.ClientResponseError as exc:
    logger.warning(f"HTTP 请求失败，状态码：{exc.status}")
    return None
```

新手建议：刚开始先手动检查几个关键状态码，能帮你建立感觉。等代码变多，再用 `raise_for_status()` 统一处理。

## 9. 一个适合新手的处理模板

```python
import asyncio
import logging

import aiohttp


logger = logging.getLogger(__name__)


async def fetch_json(session: aiohttp.ClientSession, url: str):
    try:
        async with session.get(url) as response:
            status = response.status

            if status == 200:
                return await response.json()

            if status == 204:
                logger.info(f"{url} 成功，但没有内容")
                return None

            if status == 401:
                logger.warning(f"{url} 缺少登录凭证或 Token")
                return None

            if status == 403:
                logger.warning(f"{url} 被拒绝访问，检查权限、Cookie 或请求头")
                return None

            if status == 404:
                logger.warning(f"{url} 不存在")
                return None

            if status == 429:
                logger.warning(f"{url} 请求太快，被限流")
                await asyncio.sleep(5)
                return None

            if 500 <= status < 600:
                logger.warning(f"{url} 服务器异常：{status}")
                return None

            logger.warning(f"{url} 未处理状态码：{status}")
            return None

    except aiohttp.ClientConnectorError:
        logger.warning(f"{url} 连接失败，可能是 DNS、网络或代理问题")
        return None

    except asyncio.TimeoutError:
        logger.warning(f"{url} 请求超时")
        return None

    except aiohttp.ClientError as exc:
        logger.warning(f"{url} aiohttp 客户端异常：{exc}")
        return None
```

这段模板刻意把“状态码”和“网络异常”分开写：

- 进了 `async with session.get(...)` 并拿到 `response`，说明对岸已经回话，可以看状态码。
- 进了 `except`，说明河道、连接、超时、协议解析等地方出了问题。

## 10. `response.status`、响应体和日志要一起看

只看状态码有时不够。

很多 API 会在响应体里告诉你更具体的错误原因，例如：

```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests"
}
```

所以排查问题时，建议记录三样东西：

- URL 或接口名。
- 状态码。
- 一小段响应体文本。

示例：

```python
text = await response.text()
logger.warning(f"状态码 {response.status}，响应片段：{text[:300]}")
```

注意不要把超大响应体全部打印到终端。终端只适合放警报，不适合当蓄水池。

## 11. 最后用一张图记住

```text
请求出发
   |
   v
河道断了 / 超时 / DNS 失败？
   |
   +--> 是：进入 except，处理网络异常
   |
   +--> 否：拿到 HTTP response
              |
              v
          查看 response.status
              |
              +--> 2xx：成功
              +--> 3xx：换地址或缓存
              +--> 4xx：你的请求、权限或频率有问题
              +--> 5xx：对岸服务器或网关有问题
```

状态码的本质不是神秘数字，而是对岸服务器给你的交通信号。

先判断路有没有通，再判断对岸回了什么牌子。这个顺序一旦清楚，`try...except`、`response.status`、`raise_for_status()` 就不会再混成一团。
