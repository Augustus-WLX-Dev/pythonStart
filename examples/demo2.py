import asyncio
import time
import json
import requests
import random


class MockWebSocket:
    """模拟WebSocket连接的类"""

    async def __aenter__(self):
        print("Entering ws.")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        print("Exiting ws.")

    def __aiter__(self):
        return self

    async def __anext__(self):
        await asyncio.sleep(1)

        price = 100000 + random.randint(-1000, 1000)

        if random.random() < 0.1:
            print("Something went wrong!")
            raise StopAsyncIteration

        msg = json.dumps({"symbol": "BTC", "price": price})
        return msg


class Dipbot:
    """模拟交易机器人类"""

    def __init__(self):
        self.target_price = 100000
        self.is_purchased = False

    async def listen_to_market(self):
        async with MockWebSocket() as ws:

            async for msg in ws:

                data = json.loads(msg)

                price = data["price"]
                print(f"Current price: {price}")

                if price <= self.target_price and not self.is_purchased:
                    print(f"Price dropped to {price}. Buying now!")
                    url = "https://httpbin.org/post"
                    order_data = {"action": "BUY",
                                  "symbol": data["symbol"], "price": price}
                    response = requests.post(url, json=order_data)
                    print(f"Buy response: {response.status_code}")

                    if response.status_code == 200:
                        self.is_purchased = True
                    else:
                        print(
                            f"Failed to place buy order: {response.status_code}")

                else:
                    print("No action taken.")

    async def start(self):
        await self.listen_to_market()


if __name__ == "__main__":
    bot = Dipbot()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print("Bot stopped by user.")
