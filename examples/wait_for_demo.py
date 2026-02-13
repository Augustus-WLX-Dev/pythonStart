import asyncio
import random

async def slow_server_response():
    """模拟一个不稳定的交易所服务器"""
    delay = random.uniform(0.5, 5.0)
    print(f"🌍 [服务器] 处理请求中... (预计耗时 {delay:.1f}秒)")
    await asyncio.sleep(delay)
    return "💰 订单成交！"

async def unsafe_client():
    """【不安全】傻傻等待的客户端"""
    print("\n--- 场景 1: 无限等待 (Unsafe) ---")
    print("🤖 [Bot] 发送请求，等待结果...")
    
    # 如果服务器卡了 10 分钟，这里就会卡 10 分钟
    result = await slow_server_response()
    print(f"🤖 [Bot] 终于收到了: {result}")

async def safe_client():
    """【安全】带有超时控制的客户端"""
    print("\n--- 场景 2: 超时控制 (Safe) ---")
    print("🤖 [Bot] 发送请求 (最多只等 2 秒)...")
    
    try:
        # 👑 核心代码：asyncio.wait_for
        # 这就像你跟服务器说：“给你 2 秒钟，过期不候！”
        result = await asyncio.wait_for(slow_server_response(), timeout=2.0)
        print(f"🤖 [Bot] 成功收到: {result}")
        
    except asyncio.TimeoutError:
        print("⏰ [Bot] 等太久了！取消任务，回家吃饭！")
        # 在这里你可以做重试逻辑，或者切换备用服务器
        
async def main():
    # 模拟一次快速响应
    print(">>> 测试 1: 运气好，服务器很快 <<<")
    random.seed(1) # 固定随机数，保证很快 (0.5s + small)
    await safe_client()
    
    # 模拟一次慢速响应
    print("\n>>> 测试 2: 运气不好，服务器很慢 <<<")
    random.seed(2) # 固定随机数，保证很慢 (> 4s)
    await safe_client()
    
if __name__ == "__main__":
    asyncio.run(main())
