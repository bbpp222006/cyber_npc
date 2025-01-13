import asyncio
import random

async def task(n):
    """
    模拟一个异步任务，随机等待0.5到2秒后返回结果。
    """
    delay = random.uniform(0.5, 2.0)
    await asyncio.sleep(delay)
    return f"任务 {n} 完成，耗时 {delay:.2f} 秒"

async def producer(queue):
    """
    a模块：并行启动10个任务，并按顺序将结果放入队列。
    """
    print("a模块：开始启动10个并行任务")
    
    # 创建10个任务
    tasks = [asyncio.create_task(task(i)) for i in range(1, 11)]
    
    # 按任务提交的顺序等待每个任务完成，并将结果放入队列
    for i, t in enumerate(tasks, start=1):
        result = await t  # 等待第i个任务完成
        await queue.put(result)  # 将结果放入队列
        print(f"a模块：任务 {i} 的结果已放入队列")
    
    # 所有任务完成后，向队列发送结束信号
    await queue.put(None)
    print("a模块：所有任务已完成，发送结束信号")

async def consumer(queue):
    """
    b模块：按顺序等待并处理队列中的结果。
    """
    print("b模块：开始监听队列")
    
    while True:
        result = await queue.get()  # 等待队列中的下一个结果
        if result is None:
            # 接收到结束信号，退出循环
            print("b模块：接收到结束信号，停止处理")
            break
        # 处理结果（这里简单地打印出来）
        print(f"b模块：处理结果 -> {result}")
        queue.task_done()

async def main():
    # 创建一个异步队列
    queue = asyncio.Queue()
    
    # 启动生产者和消费者任务
    producer_task = asyncio.create_task(producer(queue))
    consumer_task = asyncio.create_task(consumer(queue))
    
    # 等待生产者和消费者完成
    await asyncio.gather(producer_task, consumer_task)

if __name__ == "__main__":
    asyncio.run(main())
