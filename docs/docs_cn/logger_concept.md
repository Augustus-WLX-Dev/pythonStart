# 日志总结

## 日志配置代码
	
```python
logging.basicConfig(
	level = logging.INFO, 
	format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	datefmt = '%H:%M:%S',
	filename = 'app.log'
)
```

* **asctime**：当前精准时间，默认带毫秒，YYYY-MM-DD HH:MM:SS,mmm。
* **level = logging.INFO**：设定门槛，只有INFO以上等级的消息，才被记录。
* **levelname**：当前级别
* **message**：当前信息
* **datefmt**：时间格式，%H:%M:%S —— 时:分:秒。
* **filename = ‘app.log’** ： 将日志打印的内容保存到文件app.log。
	

## 配置名

```python
logger = logging.getLogger("MyBot")
```

* 给日志取名为MyBot

```python
logger = logging.getLogger(__name__)
```
	
* 如果运行的文件是本文件，那么日志名就会是main，如果本文件是被当作模块引入别的文件，日志名就会是puppet name: 原文件夹/此文件名，or 此文件名。这样做的原因是区分本文件是作为主程序运行，还是引用模块运行。

* 前后有双下划线的变量叫魔术变量（Magic Variable），而魔术变量就是会根据你如何使用这个文件（主程序or被import）来改变赋值。

* **身份证**：在企业级项目中，`logger = logging.getLogger(__name__)`赋予了本文件一个专属身份证，只要format 中添加了name，系统报错就会打印文件真实模块名，能快速定位BUG在哪个文件。


## 日志等级

从低到高： DEBUG(调试）-INFO（信息）-WARNING（警告）-ERROR（异常）-CRITICAL（严重）

1. **DEBUG（调试）**：只有开发时才看，比如“开始循环第一次”。
2. **INFO（信息）**：正常运行时才有，比如“xxx系统开启”
3. **WARNING（警告）**：有点不对劲但还能跑，比如“网络有点慢”
4. **ERROR（异常）**：出错了，比如“下单失败”
5. **CRITICAL（严重）**：程序崩溃。


## 搭配格式

* **:.2f** ：显示2位浮点数（自动四舍五入）。
* **:.3d**：显示3位整数，不足3位前面补0。


	
## 优势

**logger**（日志记录器）是个超级广播系统。
	
1. **Handlers机制**，一稿多发，支持不同管道（Handler）。
* **StreamHandler**(屏幕管道）：类似print（），把信息打印在终端。
* **FlieHandler**（文件管道）：把每一句话写入文件永久保存（.log or .txt)。
* **RotatingFileHandler**（自动换卷管道）：当日志文件写满10MB时，自动创建新文件（比如app.log.1, app.log.2)，防止把服务器硬盘写爆。
* 更牛的管道：配置成“只要出现logger.error()， 就自动给老板/程序员发一封报警邮件或钉钉消息”。

2. 自带时间戳和上下文环境（**Format机制**）

3. 过滤开关（**Level机制**）
只要把`logging.basicConfig(level=logging.ERROR, ...)` 的level级别更改，就能过滤设置级别以下的信息。


logger 是一种可以被精细控制的、既能实时打印、又能自动存档、还能随时“静音”的高级飞机黑匣子！







## AI总结：

你可以把整个 logging 系统想象成一个**“新闻发布中心”**，它只有四个核心组件：

1. **记录器 (Logger)** —— “谁来发新闻？”（身份与入口）
* 对应你的笔记：`logger = logging.getLogger(__name__)`
* 核心逻辑：这就是那个“身份证”。在复杂的大型项目里（比如你以后要写的 Web3 脚本或者量化交易代码），可能有几十个文件在同时运行。Logger 负责标记“这句话是谁说的”，有了 `__name__` 魔术变量，一旦出错，你瞬间就能定位到具体是哪个模块在拉警报。

2. **级别 (Level)** —— “这条新闻有多重要？”（过滤与门槛）
* 对应你的笔记：DEBUG -> INFO -> WARNING -> ERROR -> CRITICAL
* 核心逻辑：它是新闻的审查过滤器。你设置了 `level = logging.INFO`，这就意味着“鸡毛蒜皮的 DEBUG 小事不要来烦我，只有 INFO 级别以上的正经事才允许发布”。这就是你说的“随时静音”功能。

3. **格式化器 (Formatter)** —— “新闻稿长什么样？”（排版与上下文）
* 对应你的笔记：format 和 datefmt，以及 `%(asctime)s`、`%(message)s`
* 核心逻辑：负责把光秃秃的一句报错，包装成有时间、有地点、有级别的标准公文。自带时间戳不仅看起来专业，更是以后排查时间线 BUG 的救命稻草。

4. **处理器 (Handler)** —— “新闻要发布到哪些渠道？”（分发与归档）
* 对应你的笔记：StreamHandler、FileHandler、RotatingFileHandler
* 核心逻辑：这就是你提到的“一稿多发”的管道。这也是 logging 碾压普通 print() 的根本原因。print() 只能干巴巴地把字打在屏幕上，关了终端就没了；而 Handler 可以同时做到：把 INFO 打在屏幕上给你看，把 ERROR 偷偷写进 app.log 硬盘里存起来，甚至在遇到 CRITICAL 时触发报警代码。
