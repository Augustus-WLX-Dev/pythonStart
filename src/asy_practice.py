import asyncio
import random

class RainCatcher:
    def __init__(self):
        self.water_bucket = 0
        self.stop_flag = False
        # 星际信号塔：默认是红灯（False）
        self.green_light = asyncio.Event()

    async def left_hand_catch(self):
        print("🤖 [左手] 只有我自己在工作...")
        while not self.stop_flag:
            await asyncio.sleep(random.uniform(0.5, 1.5))
            if random.random() > 0.3:
                self.water_bucket += 1
                print(f"💧 [左手] 接到了 ({self.water_bucket})")
                
                # 触发量子纠缠：由于某种引力阈值（5滴），信号塔变绿
                if self.water_bucket >= 5 and not self.green_light.is_set():
                    print("🌟 [信号] 能量蓄满 5 滴！发射量子信号！--> 🟢")
                    self.green_light.set()

    async def right_hand_throw(self):
        print("🔒 [右手] 被引力锁住，处于冻结状态...")
        
        # 等待信号：在这里一直暂停，直到看到绿灯
        await self.green_light.wait()
        
        print("🔓 [右手] 接收到信号！解除封印！开始工作！")
        while not self.stop_flag:
            if self.water_bucket > 0:
                print(f"🌊 [右手] 泼水！ (剩 {self.water_bucket - 1})")
                self.water_bucket -= 1
                await asyncio.sleep(random.uniform(0.5, 1.5))
            else:
                await asyncio.sleep(random.uniform(0.5, 1.5))
    async def start_game(self):
        task1 = asyncio.create_task(self.left_hand_catch())
        task2 = asyncio.create_task(self.right_hand_throw())

        await asyncio.sleep(15) # 多睡会儿，让大家看清过程

        self.stop_flag = True
        
        await task1
        await task2

if __name__ == "__main__":
    catcher = RainCatcher()
    try:
        asyncio.run(catcher.start_game())
    except KeyboardInterrupt:
        pass
