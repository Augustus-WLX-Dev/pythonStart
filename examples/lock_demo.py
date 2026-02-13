import asyncio
import random

class BankAccount:
    def __init__(self):
        self.balance = 0
        self.lock = asyncio.Lock() # 🔒 这就是我们的防盗门（资源锁）

    async def unsafe_deposit(self, amount, task_name):
        """【不安全】甚至没有意识到危险的存款操作"""
        print(f"Checking balance for {task_name}...")
        
        # 1. 模拟读取余额 (比如需要去数据库查，所以有 await)
        current = self.balance 
        print(f"📖 [{task_name}] 读到余额: {current}")
        
        # ⚠️ 危险时刻！在这里发生了网络延迟 (await)，控制权交出去了！
        # 就在这发呆的 0.1 秒，另一个任务可能也读到了旧的余额
        await asyncio.sleep(0.1) 
        
        # 2. 计算新余额
        new_balance = current + amount
        
        # 3. 写入余额
        self.balance = new_balance
        print(f"📝 [{task_name}] 写入余额: {new_balance}")

    async def safe_deposit(self, amount, task_name):
        """【安全】使用了 Lock 的存款操作"""
        
        # 🔒 进门前先上锁！
        # 如果别人锁了，我就在这里排队等，绝不插队
        async with self.lock:
            print(f"🔒 [{task_name}] 拿到锁了，开始办理业务...")
            
            # 这里的逻辑和上面一模一样
            current = self.balance
            print(f"📖 [{task_name}] (安全) 读到余额: {current}")
            
            await asyncio.sleep(0.1) # 即使这里睡着了，也没人能进来乱动数据
            
            new_balance = current + amount
            self.balance = new_balance
            print(f"📝 [{task_name}] (安全) 写入余额: {new_balance}")
            
            print(f"🔓 [{task_name}] 办理完毕，释放锁")

async def main():
    account = BankAccount()
    
    print("--- 场景 1: 不加锁的混乱现场 ---")
    # 比如：你的 Lighter 机器人既想根据 WebSocket 更新订单簿，
    # 又想根据策略逻辑修改订单簿，如果不加锁，数据就乱了。
    
    # 启动两个任务同时存钱，每人存 100，结果应该是 200
    task1 = asyncio.create_task(account.unsafe_deposit(100, "小明"))
    task2 = asyncio.create_task(account.unsafe_deposit(100, "小红"))
    
    await task1
    await task2
    
    print(f"😱 最终余额: {account.balance} (预期: 200) -> {account.balance == 200}\n")
    
    # 重置
    account.balance = 0
    print("--- 场景 2: 加锁后的井然有序 ---")
    
    task3 = asyncio.create_task(account.safe_deposit(100, "小明"))
    task4 = asyncio.create_task(account.safe_deposit(100, "小红"))
    
    await task3
    await task4
    
    print(f"✅ 最终余额: {account.balance} (预期: 200) -> {account.balance == 200}")

if __name__ == "__main__":
    asyncio.run(main())
