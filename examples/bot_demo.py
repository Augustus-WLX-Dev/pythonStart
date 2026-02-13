import asyncio
import time
import json
import logging
import requests
import os
from ws_demo import MockWebSocket
from dotenv import load_dotenv


class PriceWatchBot:
    def __init__(self, target_buy_price, target_sell_price, current_position):
        self.target_buy_price = target_buy_price
        self.target_sell_price = target_sell_price
        self.url = "https://httpbin.org/post"
        self.current_position = current_position

        # 加载环境变量
        current_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(current_dir, '.env')
        load_dotenv(dotenv_path=env_path)
        self.key = os.getenv("MY_SECRET_KEY")

        # 1. 配置日志 (这是全局配置，不需要写 self)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # 2. 这里的技巧是 "Child Loggers" (子日志)
        # 我们创建一个主 Logger 叫 "Bot"
        # 然后创建两个子 Logger 叫 "Bot.Buy" 和 "Bot.Sell"
        # 这样在打印时，名字会自动区分，而且不需要重复创建
        self.logger = logging.getLogger("Bot")
        self.buy_logger = logging.getLogger("Bot.Buy")   # 专门负责记录买
        self.sell_logger = logging.getLogger("Bot.Sell") # 专门负责记录卖

    async def buy(self, price):
        self.headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.key
        }

        self.payload = {
            "symbol": "BTC-USD",
            "side": "BUY",
            "type": "LIMIT",
            "quantity": 0.1,
            "price": price
        }

        try:
            # 模拟发请求
            self.response = requests.post(self.url, headers=self.headers, json=self.payload) # 记得加上 headers
            
            # 3. 填入具体内容
            # response 不会自动打印，你得把它的 .status_code 或 .json() 拿出来变成字符串，放进括号里
            if self.response.status_code == 200:
                self.current_position += 0.1
                self.buy_logger.info(f"✅ 买入成功! 响应: {self.response.json()['json']}")
            else:
                self.buy_logger.error(f"❌ 买入失败: {self.response.status_code}")

        except Exception as e:
            self.buy_logger.error(f"💥 发生意外: {e}")

    async def sell(self):
        self.headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.key
        }

        self.payload = {
            "symbol": "BTC-USD",
            "side": "Sell",
            "type": "Market",
            "quantity": 0.1,
        }

        try:
            self.response = requests.post(self.url, headers=self.headers, json=self.payload)
            
            if self.response.status_code == 200:
                self.current_position -= 0.1 # 卖出要减仓位
                self.sell_logger.info(f"✅ 卖出成功! 响应: {self.response.json()['json']}")
            else:
                self.sell_logger.error(f"❌ 卖出失败: {self.response.status_code}")

        except Exception as e:
            self.sell_logger.error(f"💥 发生意外: {e}")

    async def listen_to_market(self):
        # 记得加括号 ()
        async with MockWebSocket() as ws:
            async for message in ws:
                data = json.loads(message)
                price = data['price']

                # 4. 用主 Logger 记录行情
                self.logger.info(f"👂 听到价格: {price} | 当前仓位: {self.current_position :.1f}")

                if price <= self.target_buy_price:
                    try:
                        await self.buy(price) # 记得加 await，因为 buy 是 async 函数
                    except Exception as e:
                        self.logger.error(f"调用买入函数出错: {e}")

                # 5. 这里的逻辑修好了：用 and 代替 &，并且加上 price 条件
                elif price >= self.target_sell_price and self.current_position > 0:
                    try:
                        await self.sell() # 记得加 await
                    except Exception as e:
                        self.logger.error(f"调用卖出函数出错: {e}")

    async def start(self):
        await self.listen_to_market()


if __name__ == "__main__":
    bot = PriceWatchBot(20000, 20020, 0)

    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print("\n奶奶挂断了电话")
