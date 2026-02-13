import asyncio
import random
import time

class RainCatcher:
    """
    接雨水小游戏：
    左手（账号A）负责接雨水。
    右手（账号B）负责把水泼出去。
    """
    def __init__(self):
        self.water_bucket = 0  # 桶里的水
        self.stop_flag = False

    async def left_hand_catch(self):
        """左手：每隔一会儿接一滴水"""
        print("🤖 [左手] 准备好了，开始接雨水...")
        while not self.stop_flag:
            await asyncio.sleep(1)  # 假装在等雨水，不阻塞右手
            
            # 模拟有时候接到，有时候没接到
            if random.random() > 0.3:
                self.water_bucket += 1
                print(f"💧 [左手] 接到了！桶里现在有 {self.water_bucket} 滴水")
            else:
                print("💨 [左手]哎呀，没接到...")

    async def right_hand_throw(self):
        """右手：盯着桶，有水就泼"""
        print("🤖 [右手] 准备好了，随时泼水...")
        while not self.stop_flag:
            # 盯着桶，如果没有水，就歇0.1秒再看
            if self.water_bucket > 0:
                print(f"🌊 [右手] 发现有水！泼出去！(桶里剩 {self.water_bucket - 1})")
                self.water_bucket -= 1
                await asyncio.sleep(0.5) # 泼水也需要时间
            else:
                # 歇一会儿，把CPU让给左手去接水
                await asyncio.sleep(0.1)

    async def start_game(self):
        """开始游戏"""
        print("=== 🌧️ 接雨水游戏开始 (按 Ctrl+C 停止) ===")
        
        # 创建两个任务，让他们同时跑
        task1 = asyncio.create_task(self.left_hand_catch())
        task2 = asyncio.create_task(self.right_hand_throw())

        # 让它们跑10秒钟给奶奶看
        await asyncio.sleep(10)
        
        print("\n=== 🛑 游戏结束 ===")
        self.stop_flag = True
        
        # 等待任务真正结束
        await task1
        await task2

if __name__ == "__main__":
    # 只要是有 async 的地方，就要用 asyncio.run 来启动
    catcher = RainCatcher()
    try:
        asyncio.run(catcher.start_game())
    except KeyboardInterrupt:
        print("奶奶手动停止了游戏")
