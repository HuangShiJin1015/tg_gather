# -*- coding:utf-8 -*-
# @Author: KeyH
# @Date: 2023年6月5日16:14:23

import asyncio
import unittest
import time

from telethon.tl.types.messages import ChatFull
from tornado import gen

from common.const import Const
from models.teleclient import TeleClient
from services.parser import Parser
from services.publisher import Publisher
from services.mediaprocessor import MediaProcessor


class TeleClientTest(unittest.TestCase):

    # 测试获取TG群/频道详情
    def test_get_channel(self):
        asyncio.get_event_loop().run_until_complete(self.get_channel())

    # 测试通过地理位置获取周边的群组
    def test_get_group_by_location(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.get_group_by_location())

    # 测试通过channel_id来获取群信息
    def test_get_channel_by_id(self):
        asyncio.get_event_loop().run_until_complete(self.get_channel_by_id())

    def test_get_more_channel(self):
        asyncio.get_event_loop().run_until_complete(self.get_more_channel())

    def test_get_users(self):
        asyncio.get_event_loop().run_until_complete(self.get_users())

    def test_get_personal_user(self):
        asyncio.get_event_loop().run_until_complete(self.get_personal_user())

    def test_get_user_by_phone(self):
        asyncio.get_event_loop().run_until_complete(self.get_user_by_phone())

    def test_get_channel_admin_user(self):
        asyncio.get_event_loop().run_until_complete(self.get_channel_admin_user())

    def test_get_messages(self):
        asyncio.get_event_loop().run_until_complete(self.get_messages())

    def test_get_ququn_bot_messages(self):
        asyncio.get_event_loop().run_until_complete(self.get_ququn_bot_messages())

    def test_get_hao1234bot_messages(self):
        asyncio.get_event_loop().run_until_complete(self.get_hao1234bot_messages())

    def test_do_request_parallel(self):
        asyncio.get_event_loop().run_until_complete(self.do_request_parallel())

    def test_send_message(self):
        asyncio.get_event_loop().run_until_complete(self.send_msg())

    def test_send_bot_message(self):
        asyncio.get_event_loop().run_until_complete(self.send_bot_msg())

    def test_get_dialogs(self):
        asyncio.get_event_loop().run_until_complete(self.get_dialogs())

    def test_receive_msg(self):
        pub = Publisher(url=Const.pub_url, task_queue=message_queue,
                        publish_queue=Const.pub_queue, concurrency=Const.pub_concurrency)
        loop = asyncio.get_event_loop()
        loop.create_task(pub.start())
        loop.create_task(self.get_client())
        loop.run_forever()

    def test_leave_channel(self):
        asyncio.get_event_loop().run_until_complete(self.leave_channel())

    def test_join_channel(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.join_channel())

    # 通过地理位置获取周边的群组
    async def get_group_by_location(self):
        from telethon.tl.types import InputGeoPoint
        geo_point = InputGeoPoint(
            lat=22.2625258,
            long=114.0695733
        )
        # self_expires = 10
        client = await self.get_client()
        original_info = await client.get_group_by_location(geo_point=geo_point)
        print(original_info)

        media_processor = MediaProcessor()
        channels_info = await Parser.parse_nearby_group(original_info, client, media_processor)
        res = await Parser.parse_nearyby_group_distance(original_info, channels_info)
        for r in res:
            print(r)

    # 获取telegram群/频道详细信息
    async def get_channel(self):
        channel = 'shenzhenU'
        # channel_id = -1001423171297

        client = await self.get_client()
        current_phone = client.phone
        channel = await client.get_channel(username=channel, current_phone=current_phone)
        print(channel)

        media_processor = MediaProcessor()
        assert isinstance(channel, ChatFull)
        dmp_channel = await Parser.parse_channel(channel, client, media_processor)
        print(dmp_channel)

    # 通过channel_id获取频道信息
    async def get_channel_by_id(self):
        channel_id = 1116410516
        access_hash = 2436286571861344023

        client = await self.get_client()
        channel = await client.get_channel_by_id(channel_id=channel_id, access_hash=access_hash)
        print(channel)

        # channel_address = channel.full_chat.location.address
        # print(channel_address)

        # media_processor = MediaProcessor()
        # assert isinstance(channel, ChatFull)
        # dmp_channel = await Parser.parse_channel(channel, client, media_processor)
        # print(dmp_channel)

    async def get_more_channel(self):
        channel_list = ['xiwangzaixian', 'HorsesBoom', 'Nas699', 'DLGTA', 'USstockXC', 'chunyao3', ]
        print(len(channel_list))

        # client = await self.get_client()
        # channel = await client.get_more_channel(channel_list)
        # print(type(channel))
        # print(channel)

        client = await self.get_client()
        count = 0
        for i in channel_list:
            channel_name = i
            # client = await self.get_client()
            channel = await client.get_channel(channel_name)
            media_processor = MediaProcessor()
            dmp_channel = await Parser.parse_channel(channel, client, media_processor)

            count += 1
            print(dmp_channel)

        print(count)

    async def get_users(self):
        client = await self.get_client()
        channel = 'james666232323'
        channel_id = -1001423171297

        current_phone = client.phone
        users = await client.iter_channel_users(username=channel, channel_id=channel_id, current_phone=current_phone)
        media_processor = MediaProcessor()

        print(users)
        count = 0
        async for i in users:
            dmp_users = await Parser.parse_user(i, client, media_processor)
            count += 1
            print(dmp_users)
        print(count)

    async def get_personal_user(self):
        client = await self.get_client()
        username = 'Kn1ght_Dark'
        media_processor = MediaProcessor()

        user_info = await client.get_personal_user(username)
        print(user_info)
        dmp_user_info = await Parser.parse_personal_user(user_info, client, media_processor)
        print(dmp_user_info)

    async def get_user_by_phone(self):
        client = await self.get_client()
        phone = ['85251377034', '85297101842', '85295192756']
        media_processor = MediaProcessor()

        user_info = await client.get_user_by_phones(phone)

        for i in user_info:
            dmp_user_info = await Parser.parse_user(i, client, media_processor)
            print(dmp_user_info)

    async def get_channel_admin_user(self):
        client = await self.get_client()
        current_phone = client.phone
        channel = 'test_transpond'
        # channel_id = -1001347278956

        users = await client.get_channel_admin_user(username=channel, current_phone=current_phone)
        media_processor = MediaProcessor()

        count = 0
        async for i in users:
            dum_users = await Parser.parse_user(i, client, media_processor)
            count += 1
            print(dum_users)
        print(count)

    async def get_messages(self):
        client = await self.get_client()
        channel = "pythonzh"
        media_processor = MediaProcessor()
        current_phone = client.phone
        messages = await client.get_messages(channel, limit=10, current_phone=current_phone)
        messages = [await Parser.parse_message(msg, client, media_processor) for msg in messages]
        assert isinstance(messages, list)
        # assert len(messages) == 3
        # assert messages[0].get("actionType") is not None
        # assert messages[2].get("actionType") is None

        for m in messages:
            print(m)
        print("获取群组信息通过测试!")

    async def get_ququn_bot_messages(self):
        client = await self.get_client()
        username = 'ququn_bot'
        messages = await client.get_bot_messages(username, limit=1)
        print(messages)
        media_processor = MediaProcessor()
        dmp_messages = [await Parser.parse_ququn_bot_message(msg, client, media_processor) for msg in messages]
        assert isinstance(dmp_messages, list)
        for k, v in dmp_messages[0].items():
            print(k, ':', v)
        # print(type(messages))
        # print(messages)

    async def get_hao1234bot_messages(self):
        client = await self.get_client()
        username = 'hao1234bot'
        messages = await client.get_bot_messages(username, limit=1)
        media_processor = MediaProcessor()
        dmp_messages = [await Parser.parse_hao1234bot_message(msg, client, media_processor) for msg in messages]
        assert isinstance(dmp_messages, list)
        for k, v in dmp_messages[0].items():
            print(k, ':', v)

    async def send_msg(self):
        msg = "Hello，World!"
        channel = "TG128"
        client = await self.get_client()
        current_phone = client.phone
        _msg = await client.send_message(channel=channel, message=msg, current_phone=current_phone)
        assert _msg.message == msg
        print("发送消息 {} 成功!".format(msg))

    async def send_bot_msg(self):
        msg = '新闻资讯'
        username = 'hao1234boTCN'
        client = await self.get_client()
        _msg = await client.send_bot_message(username, msg)
        # assert _msg.message == msg
        print("发送消息 {} 成功!".format(msg))

    async def do_request_parallel(self):
        client = await self.get_client()
        current_phone = client.phone
        channel = "acgcn"

        c1 = client.get_messages(username=channel, limit=1, offset_id=4, current_phone=current_phone)
        c2 = client.get_messages(username="JSshengyuan", limit=3, current_phone=current_phone)
        await gen.multi([c1, c2])

    async def get_client(self) -> TeleClient:
        client = TeleClient(Const.client_phones[0], Const.client_proxy)
        await client.connect()
        assert client.connected is True
        return client

    async def join_channel(self):
        client = await self.get_client()
        current_phone = client.phone
        cid = await client.join_channel(username="jin10news", current_phone=current_phone)
        print("加入群组: {} 完成！".format(cid))

    async def leave_channel(self):
        client = await self.get_client()
        current_phone = client.phone
        cid = await client.leave_channel(username="xbl985", current_phone=current_phone)
        print("离开群组：{} 完成".format(cid))

    async def get_dialogs(self):
        client = await self.get_client()
        dialogs = await client.get_dialogs()
        print(dialogs)
        for dia in dialogs:
            print("Channle(id=%s, name=%s, username=%s)" % (client.get_full_id(dia.entity), dia.name, dia.entity.username))

    async def new_message_callback(self, event):
        pass


if __name__ == '__main__':
    T = TeleClientTest()
    # T.test_get_group_by_location()
    # T.test_get_channel()
    # T.test_get_channel_by_id()
    # T.test_get_dialogs()
    # T.test_get_users()
    # T.test_join_channel()
    # T.test_leave_channel()
    # T.test_send_message()
    # T.test_get_messages()
    # T.test_get_personal_user()
    # T.test_send_bot_message()
    # T.test_get_ququn_bot_messages()
    # T.test_get_hao1234_bot_messages()
    T.test_get_user_by_phone()
    # T.test_get_more_channel()
    # T.test_get_channel_admin_user()

