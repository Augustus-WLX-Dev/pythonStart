import asyncio
import random

# ---------------------------------------------------------
# 1. Semaphore (信号量) - 比喻：夜店保安 (The Bouncer)
# 作用：限制并发数量，防止服务器被冲垮。
# ---------------------------------------------------------
api_bouncer = asyncio.Semaphore(2)  # 这里的 2 代表夜店只能同时进 2 个人

async def fetch_crypto_price(exchange_id):
    async with api_bouncer:  # 保安：目前里面有几个人？满了就在门口排队。
        print(f"📡 [请求] 正在访问交易所 {exchange_id}...")
        # 模拟网络延迟
        await asyncio.sleep(random.uniform(1.0, 2.0))
        price = random.randint(40000, 60000)
        print(f"✅ [结果] 交易所 {exchange_id} 返回价格: ${price}")
        return price

# ---------------------------------------------------------
# 2. Lock (互斥锁) - 比喻：洗手间的钥匙 (The Key)
# 作用：保护共享变量，防止多个任务同时修改导致“脑裂”。
# ---------------------------------------------------------
data_lock = asyncio.Lock()
shared_balance = 1000  # 假设这是你的账户余额

async def update_balance(amount, task_id):
    global shared_balance
    async with data_lock:  # 只有拿到钥匙的人才能进入财务室修改余额
        print(f"💰 [任务 {task_id}] 正在修改余额...")
        current_val = shared_balance
        await asyncio.sleep(2)  # 模拟计算过程中的上下文切换
        shared_balance = current_val + amount
        print(f"💰 [任务 {task_id}] 修改完成。新余额: {shared_balance}")

async def main():
    print("🚦 [系统] 启动 Phase 2：流量与安全管控...\n")
    
    print("--- 综合场景: 流量控制(Semaphore) 与 状态保护(Lock) 混合并发 ---")
    print("系统将【同时】涌入 5 个查价格请求 和 5 个修改余额请求。")
    print("请观察：\n  1. 修改余额时即使遇到延迟，事件循环也会去处理查价格请求，绝不卡死。")
    print("  2. 在门外等钥匙的任务会优雅地挂起，让出 CPU 给其他任务。\n" + "="*50 + "\n")
    
    # 把所有任务打包在一起
    tasks = []
    for i in range(1, 6):
        tasks.append(fetch_crypto_price(i))
        tasks.append(update_balance(100, i))
        
    # 打乱任务顺序，模拟真实世界中杂乱无章的并发请求涌入
    random.shuffle(tasks)
    
    # 一次性全部并发执行！
    await asyncio.gather(*tasks)
    
    print(f"\n🎉 [完工] 最终账户余额: {shared_balance} (预期应为 1500)")

if __name__ == "__main__":
    asyncio.run(main())
