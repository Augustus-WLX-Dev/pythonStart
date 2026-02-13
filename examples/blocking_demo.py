import asyncio
import time

async def heartbeat():
    """这个任务就像机器人的心脏，每0.5秒跳动一次"""
    print("💓 [心脏] 扑通...")
    while True:
        await asyncio.sleep(0.5)
        print("💓 [心脏] 扑通...")

async def blocking_task():
    """【错误示范】这是一个阻塞任务，比如使用了 requests.get 或者 time.sleep"""
    print("🔴 [阻塞任务] 开始执行耗时操作 (同步阻塞)...")
    
    # 注意：这里用的是 time.sleep (同步)，不是 await asyncio.sleep
    # 这就像你在排队结账时，收银员突然睡着了，整个队伍（整个程序）都停了
    time.sleep(3) 
    
    print("🔴 [阻塞任务] 完成！")

async def non_blocking_task():
    """【正确示范】这是一个非阻塞任务，使用了 await"""
    print("🟢 [非阻塞任务] 开始执行耗时操作 (异步)...")
    
    # 这里使用了 await，就像收银员在等待扫码结果时，转身去帮另一个顾客打包
    await asyncio.sleep(3)
    
    print("🟢 [非阻塞任务] 完成！")

async def main():
    # 1. 启动心脏跳动
    heartbeat_task = asyncio.create_task(heartbeat())
    
    # 等心脏跳几次
    await asyncio.sleep(1)
    print("\n--- 场景 1: 正确的异步等待 ---")
    await non_blocking_task()
    
    print("\n--- 场景 2: 错误的同步阻塞 ---")
    print("⚠️ 注意观察：心脏停止跳动了！")
    await blocking_task()
    
    print("🎉 演示结束")
    heartbeat_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
