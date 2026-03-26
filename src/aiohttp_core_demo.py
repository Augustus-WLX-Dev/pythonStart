"""
aiohttp 核心心法实战 Demo (85分达成版)
涵盖：
1. ClientSession 全局工厂与连接池 (TCPConnector)
2. Semaphore 应用层大坝防洪
3. 精细化 ClientTimeout 四大参数
4. 可观测性 Error 拦截与异常分类
"""

import asyncio
import aiohttp
import time
import logging

# 配置基础的日志输出，带上时间戳方便观察并发排队的节奏
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# =================[ 核心参数配置区 ]=================
CONCURRENCY_LIMIT = 50   # 1. Semaphore: 水库大坝每次放行的水量（放行协程数）
CONNECTION_LIMIT = 50    # 2. TCPConnector: 底层真实的物理出海河道数
TOTAL_REQUESTS = 200     # 3. 模拟瞬间产生的发包洪峰（200 个并发）

# 目标地址 (使用 httpbin.org 的延迟接口测试)
# delay/2 表示服务器收到请求后，会强制读秒等待 2 秒才回传数据。
# 这样能极好地模拟高并发下，河道被慢速请求“霸占”排队的拥堵情况。
TARGET_URL = "https://httpbin.org/delay/2"
# ===================================================

async def fetch_data(session: aiohttp.ClientSession, url: str, sem: asyncio.Semaphore, task_id: int):
    """
    一股准备冲击大坝下泄的水流（执行单个网络请求的具体协程）
    """
    # 1. 第一道防线：排队等待应用层水闸（Semaphore）放行
    # 在这里排队的协程，几乎不消耗内存倒计时，也不会触发下方的 timeout 炸弹
    async with sem:
        logger.info(f"任务 [{task_id:03d}] 🚦 被大坝放行，准备占领物理河道并启动倒计时...")
        start_time = time.time()
        
        try:
            # 2. 第二道关卡：进入工厂连接池，向操作系统要 Socket，发起真正的网络请求
            # 缩进一旦结束，不管是否抛出报错，底层 Socket 都会被安全地归还给工厂连接池
            async with session.get(url) as response:
                
                # 3. 数据回流：等待 httpbin 把 2 秒的延迟数据吐回来
                data = await response.json()
                
                elapsed = time.time() - start_time
                logger.info(f"任务 [{task_id:03d}] ✅ 成功返回数据！状态码: {response.status}, 单次耗时: {elapsed:.2f}秒")
                return data

        # =============[ 异常拦截与可观测性 ]=============
        except asyncio.TimeoutError:
            # 错误拦截 1：水滴由于外部大坝放行过多，或者是 total 时间太苛刻，导致排队排老死
            logger.error(f"任务 [{task_id:03d}] ❌ 连环超时：排队排老死了 (TimeoutError)。")
            
        except aiohttp.ServerTimeoutError:
            # 错误拦截 2：河道通畅，请求成功发给对岸了，但等对岸回传数据时等干了心血（sock_read 超时）
            logger.error(f"任务 [{task_id:03d}] ❌ 面向系统拿到了Socket，但对面服务器慢得像蜗牛。")
            
        except aiohttp.ClientConnectorError as e:
            # 错误拦截 3：打不通目标服务器（比如断网、域名拼写错误、机房宕机）
            logger.error(f"任务 [{task_id:03d}] ❌ 目标服务器宕机或域名解析失败: {e}")
            
        except aiohttp.ServerDisconnectedError:
            # 错误拦截 4：你刚握手成功，对面服务器就把你拉黑踢下线了
            logger.error(f"任务 [{task_id:03d}] ❌ 对面服务器嫌弃你并主动挂断了电话。")
            
        except Exception as e:
            # 兜底拦截其他未知异常
            logger.error(f"任务 [{task_id:03d}] ❌ 发生未知灾难性错误: {e}")
            
        return None


async def main():
    logger.info("============== 🚜 开始组装现代化的水利系统 ==============")
    
    # 建阀门一：大坝控制阀（限制并发进场的协程数）
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    logger.info(f"✅ Semaphore(应用红绿灯) 设置完毕: 最大同时放行 {CONCURRENCY_LIMIT} 吨水")

    # 建阀门二：底层网卡池（限制向系统要的物理连接数）
    # 在 Mac 上如果不专门装证书很容易报 SSL 错误，这里加上 ssl=False 绕过证书检查，专注测并发
    connector = aiohttp.TCPConnector(limit=CONNECTION_LIMIT, ssl=False)
    logger.info(f"✅ TCPConnector(物理河道数) 设置完毕: 最大物理并发连接 {CONNECTION_LIMIT} 个")

    # 建阀门三：精细化 Timeout 定时器配置
    timeout = aiohttp.ClientTimeout(
        total=15,          # 全局生死线：从调用 get 开始算，最多活 15 秒
        connect=5,         # 获取河道的最大等待时间 + 挖渠时间（如果池子满了，排队别超 5 秒）
        sock_connect=5,    # 纯挖渠（三次握手 + TLS 握手）时间：5 秒
        sock_read=10       # 把数据运回来的时间（由于 httpbin 设置了 delay 2 秒，所以此值必须 > 2）
    )
    logger.info(f"✅ 超时引信(ClientTimeout) 设置完毕: {timeout}")

    # 4. 开启引力场，开张总厂房
    logger.info("🏭 工厂开启引力场，准备承受并发洪峰！")
    logger.info("========================================================\n")
    
    start_total = time.time()
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # 生成 200 个协程洪峰
        tasks = [
            fetch_data(session, TARGET_URL, sem, i) 
            for i in range(1, TOTAL_REQUESTS + 1)
        ]
        
        # 把大水瞬间倾泻到应用内存中去抢大坝的入场券（触发并发执行）
        await asyncio.gather(*tasks)

    elapsed_total = time.time() - start_total
    logger.info(f"\n============== 🏁 所有任务执行结束！总耗时: {elapsed_total:.2f} 秒 ==============")
    logger.info("============== 🏭 厂房坍塌缩进结束，所有长连接被自动安全炸毁，释放内存。 ==============")

if __name__ == "__main__":
    asyncio.run(main())
