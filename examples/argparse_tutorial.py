#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
argparse 从零开始学习教程
这个文件会教你如何使用 argparse 处理命令行参数
"""

import argparse

# ============================================
# 第1课：最简单的例子
# ============================================
def lesson1_basic():
    """最简单的 argparse 例子"""
    print("=== 第1课：最简单的例子 ===\n")
    
    # 步骤1：创建解析器（ArgumentParser 对象）
    parser = argparse.ArgumentParser(description='这是我的第一个程序')
    
    # 步骤2：添加一个参数
    parser.add_argument('--name', type=str, help='你的名字')
    
    # 步骤3：解析命令行参数
    args = parser.parse_args()
    
    # 步骤4：使用参数
    print(f"你好, {args.name}!")
    print(f"参数对象的内容: {args}")
    print(f"参数的类型: {type(args)}")
    
    print("\n" + "="*50 + "\n")
    print("使用方式:")
    print("  python argparse_tutorial.py --name 张三")
    print("  python argparse_tutorial.py --help  (查看帮助)")


# ============================================
# 第2课：带默认值的参数
# ============================================
def lesson2_default():
    """学习如何设置默认值"""
    print("=== 第2课：带默认值的参数 ===\n")
    
    parser = argparse.ArgumentParser(description='带默认值的例子')
    
    # 不传 --name 时，默认使用 'World'
    parser.add_argument('--name', type=str, default='World',
                        help='你的名字（默认: World）')
    
    args = parser.parse_args()
    print(f"你好, {args.name}!")
    
    print("\n" + "="*50 + "\n")
    print("使用方式:")
    print("  python argparse_tutorial.py  (不传参数，用默认值)")
    print("  python argparse_tutorial.py --name 李四")


# ============================================
# 第3课：多个参数
# ============================================
def lesson3_multiple():
    """学习如何添加多个参数"""
    print("=== 第3课：多个参数 ===\n")
    
    parser = argparse.ArgumentParser(description='多个参数的例子')
    
    parser.add_argument('--name', type=str, default='朋友',
                        help='你的名字')
    parser.add_argument('--age', type=int, help='你的年龄')
    parser.add_argument('--city', type=str, help='你所在的城市')
    
    args = parser.parse_args()
    
    print(f"你好, {args.name}!")
    if args.age:
        print(f"你 {args.age} 岁了")
    if args.city:
        print(f"你来自 {args.city}")
    
    print("\n" + "="*50 + "\n")
    print("使用方式:")
    print("  python argparse_tutorial.py --name 王五 --age 25 --city 北京")
    print("  python argparse_tutorial.py --name 王五 --age 25  (city 可选)")


# ============================================
# 第4课：必需参数
# ============================================
def lesson4_required():
    """学习如何设置必需参数"""
    print("=== 第4课：必需参数 ===\n")
    
    parser = argparse.ArgumentParser(description='必需参数的例子')
    
    # required=True 表示这个参数必须提供
    parser.add_argument('--api-key', type=str, required=True,
                        help='API 密钥（必须提供）')
    parser.add_argument('--name', type=str, default='用户',
                        help='你的名字（可选）')
    
    args = parser.parse_args()
    
    print(f"API 密钥: {args.api_key}")
    print(f"名字: {args.name}")
    
    print("\n" + "="*50 + "\n")
    print("使用方式:")
    print("  python argparse_tutorial.py --api-key MY_SECRET_KEY")
    print("  python argparse_tutorial.py --api-key MY_KEY --name 张三")


# ============================================
# 第5课：不同类型
# ============================================
def lesson5_types():
    """学习不同的参数类型"""
    print("=== 第5课：不同的参数类型 ===\n")
    
    parser = argparse.ArgumentParser(description='不同类型参数的例子')
    
    parser.add_argument('--name', type=str, help='字符串类型')
    parser.add_argument('--age', type=int, help='整数类型')
    parser.add_argument('--price', type=float, help='浮点数类型')
    parser.add_argument('--verbose', action='store_true',
                        help='布尔类型（开关）')
    
    args = parser.parse_args()
    
    print(f"名字 (str): {args.name}, 类型: {type(args.name)}")
    print(f"年龄 (int): {args.age}, 类型: {type(args.age)}")
    print(f"价格 (float): {args.price}, 类型: {type(args.price)}")
    print(f"详细模式 (bool): {args.verbose}, 类型: {type(args.verbose)}")
    
    print("\n" + "="*50 + "\n")
    print("使用方式:")
    print("  python argparse_tutorial.py --name 测试 --age 25 --price 99.99")
    print("  python argparse_tutorial.py --verbose  (开关，不需要值)")


# ============================================
# 第6课：位置参数（不用 -- 前缀）
# ============================================
def lesson6_positional():
    """学习位置参数（没有 -- 前缀的参数）"""
    print("=== 第6课：位置参数 ===\n")
    
    parser = argparse.ArgumentParser(description='位置参数的例子')
    
    # 没有 -- 前缀，这是位置参数，必须提供且按顺序
    parser.add_argument('filename', type=str, help='文件名')
    parser.add_argument('--mode', type=str, default='read',
                        help='操作模式（可选）')
    
    args = parser.parse_args()
    
    print(f"要处理的文件: {args.filename}")
    print(f"操作模式: {args.mode}")
    
    print("\n" + "="*50 + "\n")
    print("使用方式:")
    print("  python argparse_tutorial.py data.txt")
    print("  python argparse_tutorial.py data.txt --mode write")


# ============================================
# 第7课：实际应用示例（类似你的代码）
# ============================================
def lesson7_real_world():
    """实际应用：模拟你的交易机器人"""
    print("=== 第7课：实际应用示例 ===\n")
    
    parser = argparse.ArgumentParser(
        description='交易机器人配置',
        # epilog 是帮助信息的结尾说明
        epilog='示例: python argparse_tutorial.py --ticker BTC --size 100'
    )
    
    # 交易所名称（可选）
    parser.add_argument('--exchange', type=str,
                        help='交易所名称')
    
    # 交易对（有默认值）
    parser.add_argument('--ticker', type=str, default='BTC',
                        help='交易对符号（默认: BTC）')
    
    # 每次交易数量（可选）
    parser.add_argument('--size', type=str,
                        help='每次交易的数量')
    
    # 迭代次数（整数）
    parser.add_argument('--iter', type=int,
                        help='运行迭代次数')
    
    # 超时时间（有默认值）
    parser.add_argument('--fill-timeout', type=int, default=5,
                        help='等待成交的超时时间（秒，默认: 5）')
    
    # 休眠时间（有默认值）
    parser.add_argument('--sleep', type=int, default=0,
                        help='每步之间的休眠时间（秒，默认: 0）')
    
    # 调试模式（开关）
    parser.add_argument('--debug', action='store_true',
                        help='开启调试模式')
    
    args = parser.parse_args()
    
    # 使用参数
    print("=== 程序配置 ===")
    print(f"交易所: {args.exchange or '未指定'}")
    print(f"交易对: {args.ticker}")
    print(f"数量: {args.size or '未指定'}")
    print(f"迭代次数: {args.iter or '未指定'}")
    print(f"超时时间: {args.fill_timeout} 秒")
    print(f"休眠时间: {args.sleep} 秒")
    print(f"调试模式: {'开启' if args.debug else '关闭'}")
    
    # 模拟使用这些参数
    if args.size and args.iter:
        print(f"\n将执行 {args.iter} 次交易，每次 {args.size} 个币")


# ============================================
# 第8课：常用技巧
# ============================================
def lesson8_tips():
    """常用技巧和最佳实践"""
    print("=== 第8课：常用技巧 ===\n")
    
    parser = argparse.ArgumentParser(
        description='常用技巧示例',
        # formatter_class 控制帮助信息的格式
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 1. 短参数名（-t 是 --ticker 的简写）
    parser.add_argument('-t', '--ticker', type=str, default='BTC',
                        help='交易对符号')
    
    # 2. 多个值（可以传多次）
    parser.add_argument('--tags', action='append',
                        help='标签（可以传多次）')
    
    # 3. 选择项（只能从给定的几个值中选择）
    parser.add_argument('--mode', type=str, choices=['buy', 'sell', 'both'],
                        default='both', help='交易模式')
    
    # 4. 布尔开关（store_true 表示存在就是 True）
    parser.add_argument('--force', action='store_true',
                        help='强制执行')
    
    # 5. 存储为常量（store_const）
    parser.add_argument('--verbose', action='store_const', const=2, default=0,
                        help='详细输出级别')
    
    args = parser.parse_args()
    
    print(f"交易对: {args.ticker}")
    print(f"标签: {args.tags or '无'}")
    print(f"模式: {args.mode}")
    print(f"强制执行: {args.force}")
    print(f"详细级别: {args.verbose}")
    
    print("\n" + "="*50 + "\n")
    print("使用方式:")
    print("  python argparse_tutorial.py -t ETH")
    print("  python argparse_tutorial.py --tags 标签1 --tags 标签2")
    print("  python argparse_tutorial.py --mode buy")
    print("  python argparse_tutorial.py --force --verbose")


# ============================================
# 主函数：选择要运行的课程
# ============================================
if __name__ == '__main__':
    import sys
    
    # 如果没有传入参数，显示所有课程
    if len(sys.argv) == 1:
        print("""
╔═══════════════════════════════════════════════════════════╗
║        argparse 从零开始学习教程                          ║
╚═══════════════════════════════════════════════════════════╝

请选择要学习的课程：

python argparse_tutorial.py --lesson 1  # 最简单的例子
python argparse_tutorial.py --lesson 2  # 带默认值的参数
python argparse_tutorial.py --lesson 3  # 多个参数
python argparse_tutorial.py --lesson 4  # 必需参数
python argparse_tutorial.py --lesson 5  # 不同类型
python argparse_tutorial.py --lesson 6  # 位置参数
python argparse_tutorial.py --lesson 7  # 实际应用（类似你的代码）
python argparse_tutorial.py --lesson 8  # 常用技巧

或者直接运行特定课程：
python argparse_tutorial.py lesson1
python argparse_tutorial.py lesson2
等等...

查看帮助：
python argparse_tutorial.py --help
        """)
    
    # 解析课程选择
    parser = argparse.ArgumentParser(description='argparse 学习教程')
    parser.add_argument('--lesson', type=int, choices=[1, 2, 3, 4, 5, 6, 7, 8],
                        help='选择要学习的课程（1-8）')
    
    # 也支持直接传课程名
    parser.add_argument('lesson_name', nargs='?', 
                        choices=['lesson1', 'lesson2', 'lesson3', 'lesson4',
                                'lesson5', 'lesson6', 'lesson7', 'lesson8'],
                        help='课程名称')
    
    args = parser.parse_args()
    
    # 根据选择运行相应的课程
    lesson_num = args.lesson or (int(args.lesson_name.replace('lesson', '')) if args.lesson_name else None)
    
    if lesson_num == 1:
        lesson1_basic()
    elif lesson_num == 2:
        lesson2_default()
    elif lesson_num == 3:
        lesson3_multiple()
    elif lesson_num == 4:
        lesson4_required()
    elif lesson_num == 5:
        lesson5_types()
    elif lesson_num == 6:
        lesson6_positional()
    elif lesson_num == 7:
        lesson7_real_world()
    elif lesson_num == 8:
        lesson8_tips()
    else:
        print("请选择一个课程！使用 --lesson 1 到 8")


