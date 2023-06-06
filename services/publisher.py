# -*- coding:utf-8 -*-
# @Author: KeyH
# @Date: 2023年6月5日16:03:05

import json
import typing

import aiormq
from telethon.errors.rpcerrorlist import ChatAdminRequiredError
from tornado import gen
from tornado.queues import Queue as AsyncQueue

from common.const import Const
from common.logger import Logger
from common.utils import Hash
from services.cryptor import AesCryptor
from services.parser import Parser


class PublisherTask:
    TYPE_MSG = 0
    TYPE_USER = 1

    def __init__(self, entity=None, client=None, media_processor=None, channel=None, task_type=None,
                 target_queue=None):
        self.entity = entity
        self.client = client
        self.media_processor = media_processor
        self.channel = channel
        self.task_type = task_type
        self.target_queue = target_queue

    async def resolve(self) -> typing.Union[dict, list, None]:
        result = None
        if self.task_type == PublisherTask.TYPE_MSG:
            result = await Parser.parse_message(self.entity, self.client, self.media_processor)
        elif self.task_type == PublisherTask.TYPE_USER:
            result = []
            try:
                async for user_entity in self.entity:
                    user = await Parser.parse_user(user_entity, self.client, self.media_processor)
                    result.append(user)
            except ChatAdminRequiredError:
                Logger.error("Chat admin permission required for getting user list of channel '%s'", self.channel)
            except Exception as e:
                Logger.error(
                    "An error occurred while getting users from channel '%s', message: %s", self.channel, str(e))
        return result


class Publisher:
    def __init__(self, url: str = None, task_queue: AsyncQueue = None, concurrency: int = 1):
        """
        数据结果发布器，发送实时消息到RabbitMQ

        :param url: RabbitMQ连接, 默认为 None
        :param task_queue: 数据队列, 默认为 None
        :param publish_queue: 发布目标队列, 默认为 None
        :param concurrency: 并发数, 默认为 1
        """
        self.__url = url
        self.__connection = None
        self.__channel = None
        self.__task_queue = task_queue
        self.__concurrency = concurrency

    async def start(self):
        # 因为没有消息订阅，这里关闭了发布器，如果以后需要开启消息订阅，取消注释即可
        # self.__connection = await aiormq.connect(url=self.__url)
        # self.__channel = await self.__connection.channel()
        # await gen.multi([self.__worker() for _ in range(self.__concurrency)])
        pass

    async def add_task(self, task: PublisherTask) -> bool:
        if isinstance(task, PublisherTask):
            await self.__task_queue.put(task)
            return True
        return False

    async def __worker(self):
        Logger.info("Publisher start...")
        async for task in self.__task_queue:
            pub_data = await task.resolve()
            crypto_task = self.__encrypt(pub_data)
            try:
                await self.__channel.queue_declare(task.target_queue)
                await self.__channel.basic_publish(crypto_task, routing_key=task.target_queue)
                Logger.info("Publish data(%s) finished!", pub_data)
            except Exception as err:
                Logger.error("Publish data(%s) error, message: %s", pub_data, err)
            finally:
                self.__task_queue.task_done()

    @staticmethod
    def __encrypt(data: dict) -> bytes:
        result = dict(body=None, iv=None)
        Logger.debug("Encrypt response data...")
        key = Const.crypto_key
        iv = Hash.sha("response_iv", "aes_iv")[0:16]
        result["iv"] = iv
        body = json.dumps(data)
        encrypt_body = AesCryptor.encrypt(body.encode("utf8"), key=key, iv=iv)
        result["body"] = encrypt_body
        Logger.debug("Encrypt response data complete.")
        return json.dumps(result).encode(encoding="utf8")
