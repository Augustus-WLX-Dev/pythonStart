import asyncio
import time


async def heartbeat():
    """异步心跳，每0.5秒跳动一次。"""
    print("💓 [心脏] 扑通...")
    while True:
        await asyncio.sleep(0.5)
        print("💓 [心脏] 扑通...")


def blocking_io_operation():
    """将同步阻塞，模拟request等类似的任务"""
    print("    💾 [线程] 开始执行老的同步代码...")
    time.sleep(3)
    print("    💾 [线程] 完成！")
    return "Result"


async def async_wrapper():
    """将同步阻塞任务包装成异步任务，防止其‘卡死’主事件循环。"""
    print("🟢 [修复版任务] 开始...")
    # 核心：将同步阻塞任务外包给'线程池'，通过asyncio.to_thread监工
    # 监工看着同步在另一个theadPool工作，完工后通过Future通知async_wrapper
    await asyncio.to_thread(blocking_io_operation)
    print("🟢 [修复版任务] 完成！")


async def main():
    """
    主函数，模拟在一个心脏跳动的情况下，把另一个同步阻塞任务放进ThreadPool。
    同步在不阻碍心脏跳动的情况下完成任务拿到结果。
    """
    heartbeat_task = asyncio.create_task(heartbeat())
    await asyncio.sleep(1)

    print("\n--- 场景: 使用 to_thread 修复阻塞 (练习版) ---")
    print("👀 请观察：当你填对代码后，心脏会一直跳动吗？")

    await async_wrapper()

    print("🎉 演示结束")
    # 主动停止后台心跳，防止资源泄漏或程序退出异常。
    heartbeat_task.cancel()  

if __name__ == "__main__":
    asyncio.run(main())
