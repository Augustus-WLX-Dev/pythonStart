import asyncio
import random

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

async def system_monitor():
    """实时监控系统。"""
    try:
        while True:
            print("🔍 [监控] 系统运行正常...")
            await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        print("🛑 [监控] 收到停止信号，安全关闭。")

async def main():
    """
    使用 TaskGroup 展示“结构化并发”。
    就像一个‘安全屋’，如果屋子里任何一个任务搞砸了，所有人都会被安全撤离。
    """
    print("🚀 [总控] 启动能源矩阵任务组...")
    
    try:
        # TaskGroup 是 Python 3.11+ 的‘安全屋’
        async with asyncio.TaskGroup() as tg:
            # 启动一个永久监控任务
            monitor = tg.create_task(system_monitor())
            
            # 同时启动多个电力单元
            units = [tg.create_task(power_unit(i)) for i in range(1, 4)]
            
            # 等待所有电力单元结束（无论成功还是失败）
            # 使用 asyncio.wait 让我们能在所有单元有了结果后，拿回控制权
            await asyncio.wait(units)
            
            print("⏳ [总控] 所有单元已结束，正在关闭监控...")
            monitor.cancel()
            
        print("✅ [总控] 能源矩阵部署成功！")
        
    except* RuntimeError as eg:
        # 注意：这里使用的是 except* (Python 3.11+)
        # 它可以捕获异常组中的多种异常
        print(f"\n⚠️ [报警] 捕获到集群故障！")
        for error in eg.exceptions:
            print(f"  - 故障明细: {error}")
        print("🆘 [总控] 由于部分单元故障，整个任务组已安全回滚/取消。")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
