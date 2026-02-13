import requests
import json
import time

def ask_price():
    """
    这是一个使用 requests 库发送 HTTP 寄信的例子
    """
    # 1. 写信封 (URL)
    # 我们用 CoinGecko 的公开接口来查价格
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    
    print(f"📮 [寄信] 正在向 {url} 发送请求...")
    print("⏳ [等待] 正在等邮递员回信...")

    try:
        # 2. 寄信并等待回信 (GET Request)
        # requests.get 是同步的，它发出去之后，程序会卡在这里不动，直到收到回信
        response = requests.get(url, timeout=10)
        
        # 3. 收到回信 (Response)
        print(f"📩 [回信] 收到回复了！")
        print(f"🏷️ [状态码] {response.status_code}") # 200 表示成功
        
        # 4. 检查是否成功
        if response.status_code == 200:
            # 5. 拆信 (解析 JSON)
            data = response.json()
            
            print("📝 [内容] 信里写着：")
            print(json.dumps(data, indent=2)) # 漂亮打印
            
            # 6. 读取具体内容
            price = data['bitcoin']['usd']
            print("-" * 30)
            print(f"💰 [结论] 比特币现在的价格是: ${price}")
            print("-" * 30)
            
        else:
            print(f"❌ [错误] 对方拒收了，状态码不是 200，是 {response.status_code}")
            
    except Exception as e:
        print(f"💥 [意外] 寄信路上出事了：{e}")

if __name__ == "__main__":
    ask_price()
