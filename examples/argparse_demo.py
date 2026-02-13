#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最简单的 argparse 演示
"""

import argparse

# 创建解析器
parser = argparse.ArgumentParser(description='这是一个简单的 argparse 演示')

# 添加参数
parser.add_argument('--name', type=str, default='World',
                    help='你的名字（默认: World）')
parser.add_argument('--age', type=int, help='你的年龄')

# 解析参数
args = parser.parse_args()

# 使用参数
print(f"你好, {args.name}!")
if args.age:
    print(f"你 {args.age} 岁了")
else:
    print("你没有告诉我你的年龄")

