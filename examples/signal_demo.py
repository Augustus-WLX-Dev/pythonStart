import asyncio
import signal
import sys

# 1. 定义一个全局标志位
stop_flag = False

def handle_exit(signum, frame):
    """
    这是一个同步回调函数。当操作系统检测到 Ctrl+C 时，会立刻强行插入执行这个函数。
    就像你的妈妈突然冲进房间喊“吃饭了！”
    """
    global stop_flag
    print(f"\n🛑 [信号中断] 收到信号 {signum}！正在通知机器人停止...")
    # 我们只修改标志位，不直接在这里做耗时操作（因为这是同步的，而且是在信号中断上下文中）
    stop_flag = True

async def trading_bot():
    """模拟一个正在交易的机器人"""
    print("🤖 [机器人] 启动！开始交易循环...")
    step = 0
    
    # 2. 也是 while True，但我们多了一个退出条件
    while not stop_flag:
        step += 1
        print(f"📈 [第 {step} 步] 正在分析行情...", end="", flush=True)
        
        # 模拟耗时操作 (1秒)
        # 如果在这一秒内按 Ctrl+C，stop_flag 会变成 True
        # 但我们要等这一秒睡完，这行代码执行完，循环回到开头检查时才会退出
        # 这就是“优雅”的关键：把手头的事做完再走
        try:
            await asyncio.sleep(1)
            print(" ✅ 分析完毕，无操作。")
        except asyncio.CancelledError:
            print(" ❌ 任务被取消了！")
            break

    # 3. 循环结束后的收尾工作
    print("\n🧹 [收尾] 正在取消未成交订单...")
    await asyncio.sleep(1) # 模拟网络请求
    print("💾 [收尾] 正在保存交易日志到 CSV...")
    await asyncio.sleep(0.5) # 模拟写文件
    print("✅ [退出] 所有数据已安全保存。再见！")

async def main():
    # 4. 注册信号处理器
    # 告诉 Python: "如果收到 SIGINT (Ctrl+C)，请执行 handle_exit"
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    await trading_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # 这是一个双重保险。
        # 即使 handle_exit 没有生效，Event Loop 也可能抛出这个异常
        print("\n💀 [系统] 强制退出了 (KeyboardInterrupt)")
