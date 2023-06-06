# -*- coding:utf-8 -*-
# @Author: ZhengYang
# @Date: 19-2-22 下午1:47

import asyncio

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.queues import Queue as AsyncQueue
from tornado.web import Application

from common.const import Const
from common.logger import Logger
from models.joinmap import JoinMap
from models.teleclient import TeleClient, TeleClients
from services.handlers import DataHandler, LoginHandler, PingHandler
from services.mediaprocessor import MediaProcessor
from services.publisher import Publisher, PublisherTask


class Server(object):
    def __init__(self, clients: TeleClients, media_processor: MediaProcessor, msg_callback, message_queue: AsyncQueue):
        """
        服务器对象

        :param clients: 账号资源池
        :param media_processor: 媒体处理器
        :param msg_callback: 新消息回调
        :param message_queue: 消息异步队列
        """
        self.__clients = clients
        self.__media_processor = media_processor
        self.__msg_callback = msg_callback

        self.__publisher = Publisher(url=Const.pub_url, task_queue=message_queue, concurrency=Const.pub_concurrency)
        self.__join_map = JoinMap()
        self.__running = False

    def start(self):
        loop = asyncio.get_event_loop()                                             # 获取当前线程的事件循环
        loop.run_until_complete(self.__clients.initialize(self.__msg_callback))     # 初始化客户端资源池
        loop.create_task(self.__media_processor.start())                            # 初始化媒体文件处理器
        loop.create_task(self.__publisher.start())                                  # 初始化结果发布器

        # Tornado路由映射
        http = HTTPServer(Application([
            (r"/{}".format(Const.server_path), DataHandler, dict(clients=self.__clients,
                                                                 media_processor=self.__media_processor,
                                                                 join_map=self.__join_map,
                                                                 publisher=self.__publisher)),
            (r"/{}/login".format(Const.server_path), LoginHandler, dict(clients=self.__clients)),
            (r"/ping", PingHandler)
        ], debug=Const.server_debug))
        http.bind(Const.server_port)
        http.start()
        mode = "DEVLOPMENT" if Const.server_debug else "DEPLOYMENT"

        self.__running = True
        Logger.info("Server start at localhost:%s/%s, mode: %s", Const.server_port, Const.server_path, mode)
        try:
            IOLoop.current().start()
        except KeyboardInterrupt:
            IOLoop.current().stop()


if __name__ == "__main__":
    tel_clients = TeleClients(Const.client_phones)
    mp = MediaProcessor(Const.mp_upload_server, Const.mp_upload_chunk_size,
                        Const.mp_download_size_limit, Const.mp_upload_retry, Const.mp_download_concurrency)
    msg_queue = AsyncQueue()

    # 订阅的群收到新消息后的回调函数
    async def new_message_event(event):
        message = event.message
        Logger.debug("Receiving a message: %s", message)
        if type(message).__name__ in ["Message", "MessageService"]:
            c = TeleClient()
            c.client = event.client
            task = PublisherTask(message, c, mp, None, PublisherTask.TYPE_MSG, Const.pub_msg_queue)
            await msg_queue.put(task)

    # 启动服务器
    Server(tel_clients, mp, new_message_event, msg_queue).start()
