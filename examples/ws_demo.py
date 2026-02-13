import asyncio
import random
import json

# 这是一个“模拟”的简单版 websocket 库，为了方便奶奶理解原理
# 真正的 live 交易中我们会用 `import websockets`
class MockWebSocket:
    """假如这是交易所那边的电话线"""
    async def __aenter__(self):
        print("📞 [电话] 嘟...嘟... 电话接通了！")
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        print("📴 [电话] 咔哒，电话挂断了。")

    def __aiter__(self):
        return self

    async def __anext__(self):
        """模拟交易所不停地喊价格"""
        await asyncio.sleep(1) # 每秒钟喊一次
        
        # 随机生成一个价格
        price = 20000 + random.randint(-100, 100)
        
        # 模拟偶尔电话断了（用来练习退出）
        if random.random() < 0.1: 
            print("⚡️ [信号] 滋滋滋... 信号不好了...")
            raise StopAsyncIteration
            
        # 把价格打包成 JSON 格式发过来
        msg = json.dumps({"symbol": "BTC", "price": price})
        return msg

class TickerBot:
    """这是奶奶的接线员机器人"""
    
    async def listen_to_market(self):
        print("🤖 [接线员] 我戴好耳机了，准备记录...")
        
        # 魔法时刻：建立连接
        # 这就是“拨通电话”
        async with MockWebSocket() as ws:
            
            # 魔法循环：守着电话听
            # 只要那边喊一句，我们就循环一次
            async for message in ws:
                
                # 1. 收到消息（听到喊话）
                # message 是个字符串，就像 '{"symbol": "BTC", "price": 20050}'
                
                # 2. 翻译消息（把字符串变成字典）
                data = json.loads(message)
                
                # 3. 记在本子上
                btc_price = data["price"]
                print(f"👂 [听到] 比特币现在的价格是: ${btc_price}")
                
                # 奶奶可以在这里加点逻辑，比如：
                # 如果价格超过 20080，就报警？

    async def start(self):
        await self.listen_to_market()

if __name__ == "__main__":
    bot = TickerBot()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print("\n奶奶挂断了电话")
