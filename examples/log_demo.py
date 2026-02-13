import logging
import time

# 1. 简单的 Print（普通人的做法）
print("----- 1. 普通的 Print -----")
print("机器人启动了")
print("出错了：找不到文件")


# 2. 高级的 Logging（专业人士的做法）
print("\n----- 2. 专业的 Logging -----")

# 配置日志：告诉它我要看 INFO 级别以上的消息，并且要带上时间
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# 获取一个专属的记录员
logger = logging.getLogger("MyBot")

# 记录各种级别的日记
logger.info("机器人启动了 (INFO: 普通信息)")
logger.warning("警告：电池电量低 (WARNING: 需要注意)")
logger.error("错误：找不到文件 (ERROR: 出大问题了)")

# 3. 为什么不用 print？
# - print 只有一句话，不知道是什么时候发生的，也不知道是哪个模块说的。
# - logging 自动带上了时间 (16:20:35)、级别 (INFO/ERROR)、名字 (MyBot)。
# - 在真实项目里，我们可以轻松设置“只把 ERROR 存到文件里”，而 print 做不到。
