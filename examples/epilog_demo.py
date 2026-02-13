#!/usr/bin/env python3
"""
演示 description 和 epilog 的区别
"""

import argparse

parser = argparse.ArgumentParser(
    # description: 显示在帮助信息的开头
    description='这是一个演示程序\n'
                '用于说明 description 和 epilog 的区别',
    
    # formatter_class: 保留原始格式
    formatter_class=argparse.RawDescriptionHelpFormatter,
    
    # epilog: 显示在帮助信息的结尾
    epilog="""
使用示例：
    python epilog_demo.py --name 张三 --age 25
    python epilog_demo.py --name 李四
    
注意事项：
    - 所有参数都是可选的
    - 如果不传参数，使用默认值
    """
)

parser.add_argument('--name', type=str, default='World',
                    help='你的名字（默认: World）')
parser.add_argument('--age', type=int, help='你的年龄')

args = parser.parse_args()
print(f"你好, {args.name}!")
if args.age:
    print(f"你 {args.age} 岁了")

