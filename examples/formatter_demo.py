#!/usr/bin/env python3
"""
演示 RawDescriptionHelpFormatter 的效果
"""

import argparse

print("=" * 60)
print("【情况1】默认格式（没有 formatter_class）")
print("=" * 60)

parser1 = argparse.ArgumentParser(
    description='这是程序描述',
    epilog="""
示例：
    命令1: python script.py --option value
    命令2: python script.py --another-option
    """
)
# 注意：这里我们不运行 parse_args()，只是展示帮助信息
parser1.print_help()

print("\n" + "=" * 60)
print("【情况2】使用 RawDescriptionHelpFormatter")
print("=" * 60)

parser2 = argparse.ArgumentParser(
    description='这是程序描述',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
示例：
    命令1: python script.py --option value
    命令2: python script.py --another-option
    """
)
parser2.print_help()

print("\n" + "=" * 60)
print("对比：RawDescriptionHelpFormatter 保留了原始格式（换行和缩进）")
print("=" * 60)

