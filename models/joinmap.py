# -*- coding:utf-8 -*-
# @Author: KeyH
# @Date: 2023年6月5日16:01:20

import sqlite3
import typing

from common.const import Const
from common.logger import Logger
from models.teleclient import TeleClient


class JoinMap:
    def __init__(self):
        # SQLite连接对象
        self.__connection = sqlite3.connect(Const.project_root + "/joinmap/joinmap.sqlite", isolation_level=None)
        self.__connection.row_factory = sqlite3.Row  # SQLite查询结果以Row对象的形式给出，Row是针对优化过的类字典对象
        self.__cursor = self.__connection.cursor()  # SQLite游标
        self.__cache = dict()                       # 缓存

        # 初始化SQLite映射表
        self.__cursor.execute(
            "CREATE TABLE IF NOT EXISTS map(channel_id INTEGER PRIMARY KEY NOT NULL, phone VARCHAR(50))")
        self.__connection.commit()

    def get(self, channel_id: int) -> typing.Union[str, None]:
        """
        根据群组ID获取到加入该群组的Telegram账号对应的手机号

        :param channel_id: channle_id
        :return: 手机号，如果未获取到，返回None
        """
        if channel_id not in self.__cache.keys():
            row = self.__get_row(channel_id)
            if row:
                phone = row["phone"]
                channel_id = row["channel_id"]
                self.__cache[channel_id] = phone
        return self.__cache.get(channel_id)

    def add(self, channel_id: int, client: typing.Union[TeleClient, str]) -> bool:
        """
        添加群组-手机号映射关系

        :param channel_id: 群组ID
        :param client: 手机号或TeleClient客户端
        :return: 添加结果，成功为True，失败为False
        """
        if not isinstance(client, (TeleClient, str)):
            return False

        if isinstance(client, TeleClient):
            phone = client.phone
        else:
            phone = client

        if channel_id in self.__cache.keys():
            return False

        if channel_id > 0:
            channel_id = int("-100" + str(channel_id))
        try:
            self.__add_row(channel_id, phone)
            self.__cache[channel_id] = phone
            return True
        except Exception as e:
            Logger.error("Recording subscribe map failed, message: %s", e)
        return False

    def delete(self, channel_id: int) -> bool:
        """
        根据群ID删除某条记录

        :param channel_id: 群ID
        :return: 删除是否成功
        """
        row = self.__get_row(channel_id)
        if row:
            channel_id = row["channel_id"]
            n = self.__del_row(channel_id)
            if n > 0:
                if channel_id in self.__cache.keys():
                    del self.__cache[channel_id]
                return True
        return False

    def __get_row(self, channel_id: int) -> sqlite3.Row:
        if channel_id > 0:
            channel_id = int("-100" + str(channel_id))

        sql = "SELECT * FROM map WHERE channel_id=?"
        self.__cursor.execute(sql, (channel_id,))
        return self.__cursor.fetchone()

    def __add_row(self, channel_id: int, phone: str) -> None:
        sql = "INSERT INTO map(channel_id, phone) VALUES(?, ?)"
        self.__cursor.execute(sql, (channel_id, phone))
        self.__connection.commit()

    def __del_row(self, channel_id: int) -> int:
        if channel_id > 0:
            channel_id = int("-100" + str(channel_id))

        sql = "DELETE FROM map WHERE channel_id=?"
        self.__cursor.execute(sql, (channel_id,))
        return self.__cursor.rowcount
