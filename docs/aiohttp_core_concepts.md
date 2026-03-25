# 🚀 aiohttp 极速实战与核心心法笔记

## 一、 核心心法模型（底层逻辑）

在写 `aiohttp` 代码时，不要在大脑里想底层代码，要想**“开工厂发物流”**的概念：

1. **`aiohttp.ClientSession()` = 建厂房 + 建车队（连接池）**
   这是全场最重量级的对象。它内部包含了 `TCPConnector`（装满了 HTTP Keep-Alive 维持的 TCP Socket 货车）和 `CookieJar`（维护登录状态）。
   * **铁律**：永远不要在单一请求里去实例化一个新的 `ClientSession`。它是一个工厂，必须长期复用。
   * **作用**：极大节省 TCP 三次握手和 SSL 证书校验的耗时。

2. **`async with session` = 工厂的“引力场” (作用域)**
   所有想要复用池子里 Socket 的请求代码，在时间线上，都必须运行在这个 `async with` 的缩进块以内。一旦缩进结束，相当于炸毁工厂，所有长连接全部断开释放，强行保护系统内存。

3. **没有 `await` 的魔法**
   看到 `async with session.get(url)` 没写 `await` 不要慌。因为 `async with` 本质上是触发了魔术方法 `__aenter__()`，这个动作本身就是一个必须要挂起等待的耗时网络 IO 动作（隐式的 `await`）。

---

## 二、 工业级实战代码模板

真实的工程结构叫：**“高层建厂，把厂长（Session 对象）作为参数派发给底层工人”**。

```python
import aiohttp
import asyncio

# 1. 底层工人：只负责拿传入的 session 去干某个具体的活（无需关心厂子怎么建）
async def fetch_user_data(session, user_id):
    url = f"https://api.example.com/users/{user_id}"
    # 再次使用 async with 是为了保证无论报错与否，用完的 Socket 都能安全还给连接池
    async with session.get(url) as response:
        return await response.json()  # aiohttp 自动把返回数据转成 Python 字典

# 2. 高层架构师：负责统筹资源（开启引力场）
async def main():
    # 建立唯一的厂房（开启引力场）
    async with aiohttp.ClientSession() as session:
        # 并发派发任务给 100 个工人，大家共享这一个厂房的连接池
        tasks = [fetch_user_data(session, i) for i in range(100)]
        results = await asyncio.gather(*tasks)
        print(f"成功获取 {len(results)} 条数据")

# 启动引擎
if __name__ == "__main__":
    asyncio.run(main())
```

---

## 三、 高阶扫雷区：高并发的“连环超时陷阱”

如果你要向对方服务器瞬间发射 10000 个请求，切记网络请求分为 **应用层 (Python 内存里)** 和 **底层网卡 (Socket 池子里)**。两者必须同时加锁！否则即使网卡撑得住，那些排不到队的代码也会在你本地的排队列表里因为等到“活活老死”而抛出 `TimeoutError`！

**终极护身符搭配法：口诀“`Semaphore` 和 `Connector.limit` 是一对保命双煞，高并发压测时，两者必须同时存在！”**

```python
import aiohttp
import asyncio

async def fetch_safe(session, url, sem):
    # 【应用层红绿灯】：控制并发进场的协程数，保护内存，防止还未连网就超时惨死
    async with sem:
        async with session.get(url) as response:
            return await response.text()

async def main():
    # 1. 阀门一：创建应用层红绿灯（Semaphore），假设最大承载放行 100 辆车
    sem = asyncio.Semaphore(100)
    
    # 2. 阀门二：在建厂时，配置底层网卡连接池的并发上限极限（Connector limit）
    connector = aiohttp.TCPConnector(limit=100)
    
    # 将网卡阀门组装进工厂
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_safe(session, f"http://example.com/{i}", sem) for i in range(10000)]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
```
