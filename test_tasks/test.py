import asyncio


class Media:

    def __init__(self, loop, task_size=3):
        self.loop = loop
        self.queue = asyncio.Queue()
        self.tasks = []
        self.task_size = task_size

    async def init_task_thread(self):
        print('创建新的携程任务')
        for i in range(self.task_size):
            await self.create_task(i)

    async def add_msg(self, msg):
        await self.queue.put(msg)
        print('当前队列长度', self.queue.qsize())
        if self.queue.qsize() >= 5:
            print('任务开始积压，取消旧携程任务，创建新的携程任务')
            for task in self.tasks:
                task.cancel()
            await self.init_task_thread()
            # 休息一段时间，让携程任务消费一些积压的任务
            # await asyncio.sleep(10)

    async def create_task(self, task_id):
        self.tasks.append(self.loop.create_task(self.do_task(task_id)))

    async def do_task(self, task_id):
        count = 0
        while True:
            if self.queue.qsize() == 0:
                await asyncio.sleep(5)
                continue
            count += 1
            json_data = await self.queue.get()
            print('携程id:{}'.format(task_id), '消费数据个数:{}'.format(count), '数据:'.format(json_data))
            await asyncio.sleep(1)
            if count == 5:
                print('携程id:{}'.format(task_id), '模拟携程任务异常，暂停任务消费')
                await asyncio.sleep(1000)


async def main(loop):
    media = Media(loop)
    await media.init_task_thread()
    for i in range(1000):
        await media.add_msg('消息{}'.format(i))
        await asyncio.sleep(2)


if __name__ == "__main__":
    LOOP = asyncio.new_event_loop()
    LOOP.run_until_complete(main(LOOP))
