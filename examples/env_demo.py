import os
# 如果报错 ModuleNotFoundError，请运行: pip3 install python-dotenv
from dotenv import load_dotenv

# 1. 加载保险箱 (.env 文件)
# 默认它会在当前目录找 .env，找不到就会去上一级目录找
# 我们显式地告诉它在当前文件的同级目录下找
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, '.env')
load_dotenv(dotenv_path=env_path)

def main():
    print(f"📂 正在尝试从这个保险箱读取: {env_path}")
    
    # 2. 尝试取出钥匙
    secret = os.getenv("MY_SECRET_KEY")

    if secret:
        print("-" * 30)
        print(f"✅ 成功打开保险箱！")
        print(f"🔑 拿到的钥匙是: {secret}")
        print("-" * 30)
    else:
        print("❌ 失败：保险箱是空的，或者没找到 .env 文件")

if __name__ == "__main__":
    main()
