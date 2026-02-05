import asyncio
import random
import time

async def producer(queue: asyncio.Queue, id: int):
    """
    生产者: 生产数据并放入队列。
    """
    for i in range(5):
        item = f"数据-{id}-{i}"
        
        # 模拟生产数据的耗时
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        # put(): 将数据放入队列
        # 如果队列满了 (达到了 maxsize)，这里会阻塞 (等待)，直到队列有空位。
        await queue.put(item)
        print(f"[生产] 生产者 {id} 放入了 {item} (队列当前长度: {queue.qsize()})")
    
    print(f"✅ 生产者 {id} 完成任务")

async def consumer(queue: asyncio.Queue, id: int):
    """
    消费者: 从队列取出数据并处理。
    """
    while True:
        # get(): 从队列取出数据
        # 如果队列为空，这里会阻塞 (等待)，直到队列里有数据。
        item = await queue.get()
        
        print(f"  [消费] 消费者 {id} 取出了 {item}")
        
        # 模拟处理数据的耗时
        await asyncio.sleep(random.uniform(1.0, 2.0))
        
        # task_done(): 告诉队列，刚才取出的这个 item 已经处理完毕了。
        # 这是为了配合 queue.join() 使用的。
        queue.task_done()
        print(f"  [完成] 消费者 {id} 处理完了 {item}")

async def main():
    # 创建一个容量为 2 的队列
    # maxsize=2 意味着队列里最多只能积压 2 个未被取出处理的数据
    queue = asyncio.Queue(maxsize=2)
    
    # 创建 2 个生产者任务
    producers = [
        asyncio.create_task(producer(queue, 1)),
        asyncio.create_task(producer(queue, 2))
    ]
    
    # 创建 2 个消费者任务
    # 消费者通常是“后台服务”，因为它们是死循环 (while True)
    consumers = [
        asyncio.create_task(consumer(queue, 1)),
        asyncio.create_task(consumer(queue, 2))
    ]
    
    # 等待所有生产者完成
    # 生产者生产完指定数量的数据后就会自动结束函数
    await asyncio.gather(*producers)
    print("📢 所有生产者已停止生产")
    
    # 等待队列中的 backlog (积压数据) 被处理完
    # join() 会阻塞，直到队列中所有被 put 进去的 item 都被 task_done() 了
    print("⏳ 等待队列清空...")
    await queue.join()
    print("🎉 队列已清空，所有数据处理完毕")
    
    # 取消消费者任务
    # 因为消费者是 while True 死循环，它们不会自己结束，必须手动 cancel
    for c in consumers:
        c.cancel()
    
    # 等待消费者任务取消 (可选，为了代码更干净)
    await asyncio.gather(*consumers, return_exceptions=True)

if __name__ == "__main__":
    asyncio.run(main())
