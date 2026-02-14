import asyncio
import time

async def heartbeat():
    """机器人的心脏"""
    print("💓 [心脏] 扑通...")
    while True:
        await asyncio.sleep(0.5)
        print("💓 [心脏] 扑通...")

def blocking_io_operation():
    """模拟一个旧的、不支持异步的代码 (例如 requests)"""
    print("    💾 [线程] 开始执行老的同步代码...")
    time.sleep(3) # 仍然使用 time.sleep
    print("    💾 [线程] 完成！")
    return "Result"

async def async_wrapper():
    """【修复方案】使用 to_thread 把阻塞代码扔到别的线程去"""
    print("🟢 [修复版任务] 开始...")
    
    # 核心代码：asyncio.to_thread
    # 这就像你在排队时，专门开了一个“慢速通道”窗口，让那个睡着的收银员去那边睡
    # 你的主队伍（Event Loop）继续前进
    await asyncio.to_thread(blocking_io_operation)
    
    print("🟢 [修复版任务] 完成！")

async def main():
    heartbeat_task = asyncio.create_task(heartbeat())
    await asyncio.sleep(1)
    
    print("\n--- 场景: 使用 to_thread 修复阻塞 ---")
    print("👀 请观察：这次心脏会一直跳动吗？")
    
    await async_wrapper()
    
    print("🎉 演示结束")
    heartbeat_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
