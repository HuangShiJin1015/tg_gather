# -*- coding:utf-8 -*-
# @Author: KeyH
# @Date: 2023年6月5日16:02:45

import json
import re
import typing
import time
import asyncio
import random

from telethon.errors import rpcerrorlist
from telethon.errors.common import MultiError
from tornado.web import RequestHandler
from common.const import Const
from common.logger import Logger
from common.utils import Hash
from models.joinmap import JoinMap
from models.teleclient import TeleClient, TeleClients
from services.cryptor import AesCryptor
from services.mediaprocessor import MediaProcessor
from services.parser import Parser
from services.publisher import Publisher, PublisherTask
from models.media import Media
from common.redis_util import REDIS_CLIENT

# Telegram errors
ChatAdminRequiredError = rpcerrorlist.ChatAdminRequiredError

# Request data models
TYPE_MESSAGES = "messages"                                      # 消息获取
TYPE_CHANNEL = "channel"                                        # 群基本信息获取
TYPE_USERS = "users"                                            # 用户处理，获取群用户
TYPE_ADMINS = "admins"                                          # 群管理员处理，获取群管理员
TYPE_JOIN = "join"                                              # 加入群
TYPE_LEAVE = "leave"                                            # 离开群
TYPE_SEND = "send"                                              # 发送消息
TYPE_SYNC = "sync"                                              # 同步会话列表
TYPE_SEARCH = "search"                                          # 通过用户注册的手机号来获取该用户的基本信息
TYPE_QUQUNBOT_BOT = "ququn_bot"                                 # ququn机器人返回的关键字群信息
TYPE_HAO1234_BOT = "hao1234bot"                                 # hao1234机器人返回的关键字群信息
TYPE_LOCATION_CHANNEL = "location_channel"                      # 通过给出的地理位置经纬度得到附近的群信息
TYPE_LOCATION_CHANNEL_USER = 'location_channel_user'            # 位置群成员获取
TYPE_LOCATION_CHANNEL_MESSAGES = 'location_channel_messages'    # 位置群消息获取
TYPE_LOCATION_CHANNEL_INFO = 'location_channel_info'            # 位置群详情获取
TYPE_ADDRESS_BOOK = 'address_book'                              # 通讯录联系人获取
TYPE_ADD_CONTACT = 'add_contact'                                # 添加联系人

# Request error codes
ERR_NOT_EXIST = -400        # Telegram采集目标实体不存在
ERR_CLI_NOT_FOUND = -404    # 账号对应的客户端未找到
ERR_NO_PERMISSION = -300    # Telegram接口权限不足
ERR_UNKNOWN = -200          # Telegram未知错误
ERR_REQUEST = -500          # 客户端请求错误，可能是缺少必要参数
ERR_REQUEST_TIMES = -505    # 客户端请求接口次数上限

# Number_of_requests
location_number_of_requests = 0

# 采集账号池
phones_list = []


class DataHandler(RequestHandler):
    def initialize(self, clients: TeleClients, media_processor: MediaProcessor,
                   join_map: JoinMap, publisher: Publisher):
        self.clients = clients
        self.media_processor = media_processor
        self.join_map = join_map
        self.publisher = publisher

    async def post(self):
        body = self.request.body
        if body is not None:
            body = body.decode(encoding="utf8")
            b = body.split('&')
            c = []
            for i in b:
                k = re.findall('(.*)=', i)[0]
                v = re.findall('=(.*)', i)[0]
                c.append('"' + k + '"' + ':' + ' ' + '"' + v + '"' + ', ')
            d = ''
            for j in c:
                d += j
            d = '{' + d[:-2] + '}'
            data = json.loads(d)
            # data = json.loads(body)
            Logger.debug("Receive a request, data: %s", str(data))
            type_ = data.get("type")
            result = {}
            if type_ == TYPE_MESSAGES:
                result = await self._messages_handler(data)
            elif type_ == TYPE_CHANNEL:
                result = await self._channel_handler(data)
            elif type_ == TYPE_USERS:
                result = await self._users_handler(data)
            elif type_ == TYPE_ADMINS:
                result = await self._admins_handler(data)
            elif type_ == TYPE_JOIN:
                result = await self._channel_handler(data, 1)
            elif type_ == TYPE_LEAVE:
                result = await self._channel_handler(data, 2)
            elif type_ == TYPE_SEND:
                result = await self._dialog_handler(data)
            elif type_ == TYPE_SYNC:
                result = await self._dialog_handler(data, 1)
            elif type_ == TYPE_SEARCH:
                result = await self._search(data)
            elif type_ == TYPE_QUQUNBOT_BOT:
                result = await self._ququn_bot_handler(data)
            elif type_ == TYPE_HAO1234_BOT:
                result = await self._hao1234bot_handler(data)
            elif type_ == TYPE_LOCATION_CHANNEL:
                result = await self._location_channel_handler(data)
            elif type_ == TYPE_LOCATION_CHANNEL_USER:
                result = await self._location_channel_user_handler(data)
            elif type_ == TYPE_LOCATION_CHANNEL_MESSAGES:
                result = await self._location_channel_messages_handler(data)
            elif type_ == TYPE_LOCATION_CHANNEL_INFO:
                result = await self._location_channel_info_handler(data)
            elif type_ == TYPE_ADDRESS_BOOK:
                result = await self._address_book(data)
            elif type_ == TYPE_ADD_CONTACT:
                result = await self._add_contact(data)
            else:
                Logger.debug("Invalid request data")
            self.warp_write(result)

    async def _address_book(self, data: dict):
        # 获取当前采集群所用的手机号，如果传入该手机号则用该手机号，如果没有传入，则随机用资源池的手机号
        phone = data.get('phone')
        client = self.clients.get(phone)
        result = await client.get_address_book()
        return result

    async def _add_contact(self, data: dict):
        phones = data.get("phones")
        if phones:
            client = self.clients.get()
            result = await client.add_contact(phones)
            return result

    def warp_write(self, write_obj: dict) -> None:
        # 加密数据内容
        def encrypt_data(_data) -> dict:
            Logger.debug("Encrypt response data...")
            _key = Const.crypto_key
            _iv = Hash.sha("response_iv", "aes_iv")[0:16]
            # 判断加密的数据类型
            if isinstance(_data, (list, dict)):
                # 需加密的数据为消息数据，且为一个列表
                if type(_data) == list:
                    end_data_list = []
                    for item in _data:
                        end_data = {}
                        for k, v in item.items():
                            type_list = [int, str]
                            if type(v) in type_list or v is None:
                                end_data[k] = v
                            elif type(v) == list:
                                end_data[k] = str(v)
                            else:
                                if 'user_id' in str(v.__dict__):
                                    end_data[k] = v.user_id
                                else:
                                    end_data[k] = v.channel_id
                        end_data_list.append(end_data)
                    _data = end_data_list
                # 加密数据为单条消息
                if type(_data) == dict and 'userCount' not in str(_data):
                    end_data = {}
                    for k, v in _data.items():
                        type_list = [int, str, None]
                        if type(v) in type_list or v is None:
                            end_data[k] = v
                        elif type(v) == list:
                            end_data[k] = str(v)
                        else:
                            if 'user_id' in str(v.__dict__):
                                end_data[k] = v.user_id
                            else:
                                end_data[k] = v.channel_id
                    _data = end_data
                _data = json.dumps(_data)
            else:
                _data = str(_data)
            _body = AesCryptor.encrypt(_data.encode("utf8"), key=_key, iv=_iv)
            _output = dict(iv=_iv, body=_body)
            Logger.debug("Encrypt response data complete!")
            return _output

        data = encrypt_data(write_obj)
        self.write(json.dumps(data).encode("utf8"))
        # self.write(json.dumps(dict(count=count, data=data, update=update)).encode("utf8"))

    async def _messages_handler(self, data: dict) -> typing.Union[int, list]:
        """
        处理消息获取，和旧版的变动在于，旧版只会返回最新的20条消息，如果这段时间最新消息超过20条，
        需要客户端调整offset_id，再次获取。当前版本则将这个操作放到了服务端完成，返回的结果一定是
        客户端提供的消息ID到目前为止最新的消息ID。比如：
            假设某个群最新的消息ID为 128
            旧版：
                limit = 20, o ffset_id= 0, min_id = 100
                这条参数表示，客户端的消息数据存到了ID=100那条，那么返回结果的消息ID范围为： 109 - 128
                客户端发现109 != 100，会调整参数：
                offset_id = 109, mid_id = 100, limit = 20
                再次请求一次数据，返回为 101 - 108
            当前版：
                limit = 20, offset_id = 0, min_id = 100
                服务端获取一次后发现结果ID为： 109 - 128
                会自动调整 offset_id = 109, 再次获取。所以返回的结果直接为：101-128
                无需客户端再次请求

        :param data: 
        :return: list
        """
        limit = int(data.get('limit')) or 20         # 每页消息上限
        offset_id = data.get('offset_id') or 0      # 偏移ID，用于获取历史消息
        username = data.get('channel')           # 目标群、频道、聊天
        min_id = data.get('min_id') or 0        # 返回消息的最小ID，用于更新最新消息

        # 旧版本字段配置，新版需与客户端联调。
        offset_id = data.get('min_id') or 0
        min_id = data.get('max_id') or 0

        # 获取当前采集群所用的手机号，如果传入该手机号则用该手机号，如果没有传入，则随机用资源池的手机号
        phone = data.get('phone')

        # 查看redis中是否有channel与phone的绑定关系
        channel_key = 'tg' + ':' + str(username)

        # 如果redis中存在channel和phone的对应关系，则直接取用该channel对应的手机号作为采集号
        redis_phone = await REDIS_CLIENT.get(channel_key)
        if redis_phone is not None:
            phone = redis_phone

            # 覆盖掉被ban的手机号
            ban_phones = ['+85262161655']
            if phone in ban_phones:
                # 记录该手机号已被封禁
                Logger.info("The phone number has been banned,need a new phone number to replace, phone:%s", phone)
                client = self.clients.get()
                if isinstance(client, TeleClient):
                    phone = client.phone
                    await REDIS_CLIENT.set(key=channel_key, value=phone, ex=None)
                    # 记录被禁手机号已被新手机号替换
                    Logger.info("The channel and the new phone are bound, channel:%s, phone:%s", username, phone)

            client = self.clients.get(phone)
        # 否则判断是否传入手机号
        else:
            # 如果传入手机号，则使用该手机号作为采集号，并且将该channel和该phone绑定放入redis
            if phone:
                client = self.clients.get(phone)
                if isinstance(client, TeleClient):
                    await REDIS_CLIENT.set(key=channel_key, value=phone, ex=None)
                    # 日志中记录该channel和该phone已绑定
                    Logger.info("The channel and the phone are bound, channel:%s, phone:%s", username, phone)
            else:
                client = self.clients.get()
                if isinstance(client, TeleClient):
                    phone = client.phone
                    await REDIS_CLIENT.set(key=channel_key, value=phone, ex=None)
                    # 日志中记录该channel和该phone已绑定
                    Logger.info("The channel and the phone are bound, channel:%s, phone:%s", username, phone)

        messages = list()
        Logger.info("Prepare to get message(limit:%s, channel:%s, minId:%s, offsetId:%s)...",
                    limit, username, min_id, offset_id)

        try:
            # 采集该群所用的手机号
            current_phone = client.phone
            message_entities = await client.get_messages(username=username, limit=limit, offset_id=offset_id,
                                                         min_id=min_id, current_phone=current_phone)
        except rpcerrorlist.ChatAdminRequiredError as npe:
            # 缺少权限
            Logger.error("No permission to get channel '%s' messages. message: %s", username, npe)
            return ERR_NO_PERMISSION
        except Exception as e:
            Logger.error("An error occurred while trying to get messages from '%s', message: %s", username, e)
            return ERR_UNKNOWN
        else:
            for message_entity in message_entities:

                # 格式化存储在redis中的群消息键，格式为：tg_message_to_heavy_handle/房间id_消息id
                # room_id = client.get_full_id(message_entity.to_id)
                # message_id = message_entity.id
                # room_message_key = 'tg_message_to_heavy_handle/'+str(room_id)+'_'+str(message_id)

                # 此处根据redis缓存中是存在已获取的消息进行去重
                # if await REDIS_CLIENT.get(room_message_key) is None:

                # 解析没有重复的消息
                message = await Parser.parse_message(message_entity, client, self.media_processor)
                # 将解析的消息基本信息写入日志
                Logger.info("Get a message: msgId=%s, userId=%s, channelId=%s, pubDate=%s",
                            message["originalId"], message["personCode"], message["roomCode"], message["createDate"]
                            )
                if message["originalId"] is not None:
                    messages.append(message)

                # 将处理完成的消息以格式化的形式存入redis中，键为：tg_media_handle/房间id_消息id，值为：1，并且设置有效时长为一周
                # await REDIS_CLIENT.set(room_message_key, '1', 604800)
                # # 将解析过的消息存入redis的事件记录在日志中
                # Logger.info('The message info is added to the cache, channel_id(%s), message_id(%s)',
                #             room_id, message_id)

                # else:
                #     # 该消息已重复，在日志中记录
                #     Logger.info('The message has been parsed, channel_id(%s), message_id(%s)', room_id, message_id)

            # if messages:
            #     # 获取结果列表中的最后一个消息的ID（最小ID），并计算与参数设定的差值
            #     result_min_id = messages[-1].get("originalId")
            #     delt = result_min_id - min_id

            #     # 如果消息ID最小值和参数ID最小值不是两个连续的数并且结果集不为空，则需要再次获取
            #     if delt > 1:
            #         adds = await self._messages_handler(
            #             dict(limit=limit, offset_id=result_min_id, channel=channel, min_id=min_id))
            #         if isinstance(adds, list):
            #             messages += adds
        return messages

    async def _channel_handler(self, data: dict, action: int = 0) -> typing.Union[int, dict]:
        """
        用于处理获取群的基本信息、加退群操作

        :param data: [description]
        :param action: 动作类型，默认值 `0`
        :return: [description]
        """

        # username
        username = data.get("channel")

        # 获取当前采集群所用的手机号，如果传入该手机号则用该手机号，如果没有传入，则随机用资源池的手机号
        phone = data.get('phone')

        # 查看redis中是否有channel与phone的绑定关系
        channel_key = 'tg' + ':' + str(username)

        # 如果redis中存在channel和phone的对应关系，则直接取用该channel对应的手机号作为采集号
        redis_phone = await REDIS_CLIENT.get(channel_key)
        if redis_phone is not None:
            phone = redis_phone

            # 覆盖掉被ban的手机号
            ban_phones = ['+85262161655']
            if phone in ban_phones:
                # 记录该手机号已被封禁
                Logger.info("The phone number has been banned,need a new phone number to replace, phone:%s", phone)
                client = self.clients.get()
                if isinstance(client, TeleClient):
                    phone = client.phone
                    await REDIS_CLIENT.set(key=channel_key, value=phone, ex=None)
                    # 记录被禁手机号已被新手机号替换
                    Logger.info("The channel and the new phone are bound, channel:%s, phone:%s", username, phone)

            client = self.clients.get(phone)
        # 否则判断是否传入手机号
        else:
            # 如果传入手机号，则使用该手机号作为采集号，并且将该channel和该phone绑定放入redis
            if phone:
                client = self.clients.get(phone)
                if isinstance(client, TeleClient):
                    await REDIS_CLIENT.set(key=channel_key, value=phone, ex=None)
                    # 日志中记录该channel和该phone已绑定
                    Logger.info("The channel and the phone are bound, channel:%s, phone:%s", username, phone)
            else:
                client = self.clients.get()
                if isinstance(client, TeleClient):
                    phone = client.phone
                    await REDIS_CLIENT.set(key=channel_key, value=phone, ex=None)
                    # 日志中记录该channel和该phone已绑定
                    Logger.info("The channel and the phone are bound, channel:%s, phone:%s", username, phone)

        channel = dict()
        channel_entity = None

        if username:
            try:
                # 获取群/频道信息
                if action == 0:
                    Logger.info("Get channel info..., username: %s", username)
                    # 当前用于采集信息所连接telegram的手机号
                    current_phone = client.phone
                    channel_entity = await client.get_channel(username=username, current_phone=current_phone)

                # 加入群组(订阅消息)
                elif action == 1:
                    # 如果请求提供了phone参数,表明是指定账号加入群组, 执行加群操作
                    if phone:
                        Logger.info("Prepare to join channel '%s'...", username)
                    # 如果没有提供phone参数，表明是订阅某个群的消息，执行订阅操作
                    else:
                        Logger.info("Prepare to subscribe channel '%s'...", username)
                    client = self.clients.get(phone)

                    # 如果指定了手机号或者映射里不存在此群组（即没有订阅过）,执行加群操作
                    if phone is None:
                        try:
                            channel_entity = await client.join_channel(username, current_phone=client.phone)
                            channel = {"status": 0, "channel_id": channel_entity, "msg": "ok"}
                        except Exception as e:
                            Logger.error("Account '%s' joining channel '%s' error, message: %s",
                                         client.phone, username, e)
                            channel["status"] = 2
                            channel["msg"] = "Joining or subscribing channel '%s' failed, maybe this account has " \
                                             "already in target channel." % username
                        else:
                            if not phone:
                                self.join_map.add(username, client)
                    else:
                        Logger.error("Channel '%s' has been subscribed.", username)
                        channel["status"] = 1
                elif action == 2:
                    # 离开群组/取消订阅
                    if phone:
                        Logger.info("Prepare to leave channel '%s'...", username)
                    else:
                        Logger.info("Prepare to unsubscribe channel '%s'...", username)
                        phone = self.join_map.get(username)
                    client = self.clients.get(phone)
                    if client:
                        try:
                            channel_entity = await client.leave_channel(username, current_phone=client.phone)
                            channel = {"status": 0, "channel_id": channel_entity}
                        except Exception as e:
                            Logger.error("Account '%s' leaving channel '%s' error, message: %s",
                                         client.phone, username, e)
            except Exception as e:
                Logger.error("An error occurred while processing channel '%s' actions, message: %s", username, str(e))
            else:
                if action == 0:
                    # 解析群/频道数据
                    channel = await Parser.parse_channel(channel_entity, client, self.media_processor)
                    Logger.info("Get channel: roomCode=%s, roomName=%s",
                                channel['roomCode'], channel['roomName'])

        return channel

    async def _ququn_bot_handler(self, data: dict) -> list:
        """
        用于处理ququn机器人返回的群信息

        :param data: [description]
        :return: 字典类型的数据
        """

        client = None
        result = None
        bot_type = data.get('type')
        keyword = data.get('keyword')

        if keyword:
            try:
                Logger.info("ququn_bot: Channel of '%s' by '%s'...", keyword, bot_type)
                client = self.clients.get()
                # 首先给机器人发送要搜索的关键字信息
                await client.send_bot_message(bot_type, keyword)
                # 让机器人睡5秒以返回所包含关键字的群信息
                await asyncio.sleep(5)
                # 获取该机器人返回的包含关键字信息的群
                keyword_info = await client.get_bot_messages(bot_type, limit=1)
                try:
                    result = [await Parser.parse_ququn_bot_message(msg, client, self.media_processor)
                              for msg in keyword_info]
                except Exception as e:
                    Logger.error("An error occurred while getting ququn_bot keyword info: %s", str(e))

            except Exception as e:
                Logger.error("An error occurred while getting ququn_bot keyword info: %s, current phone: %s",
                             str(e), client.phone)

        return result

    async def _hao1234bot_handler(self, data: dict) -> list:
        """
        用于处理hao1234机器人返回的群消息

        :parm data: [description]
        :return: 字典类型数据
        """

        client = None
        hao1234bot_result = None
        bot_type = data.get('type')
        keyword = data.get('keyword')

        if keyword:
            try:
                Logger.info("hao1234bot: Channel of '%s' by '%s'...", keyword, bot_type)
                client = self.clients.get()
                # 首先给机器人发送要搜索的关键字信息
                await client.send_bot_message(bot_type, keyword)
                # 让机器人睡5秒以返回所包含关键字的群信息
                await asyncio.sleep(5)
                # 获取该机器人返回的包含关键字信息的群
                keyword_info = await client.get_bot_messages(bot_type, limit=1)
                try:
                    hao1234bot_result = [await Parser.parse_hao1234bot_message(msg, client, self.media_processor)
                                         for msg in keyword_info]
                except Exception as e:
                    Logger.error("An error occurred while getting hao1234bot keyword info: %s", str(e))
            except Exception as e:
                Logger.error("An error occurred while getting hao1234bot keyword info: %s, current phone: %s",
                             str(e), client.phone)

        return hao1234bot_result

    async def _location_channel_handler(self, data) -> typing.Union[int, dict]:
        """
        用于处理地理位置获取群信息
        :param data: [description]
        :return: dict类型数据
        """
        # 接收的地点信息
        location = data.get('location')
        # 接收的位置纬度
        lat = data.get('lat')
        # 接收的位置经度s
        long = data.get('long')

        # 最终返回的结果
        result = None
        if lat and long:
            try:
                global location_number_of_requests
                # 控制用哪个手机号来模拟位置
                # phone = ['+85264395112', '+85267092660', '+85256411229', '+85259389324', '+85290639642', '+85260677135',
                #          '+85256433541', '+85256130846', '+85256101392', '+85254218911', '+85253488325', '+85256265380',
                #          '+85256214431', '+85256131943', '+85254835009', '+85256193829', '+85254839240', '+85269994531',
                #          '+85256265598', '+85292063297', '+85260923294', '+85292007185', '+85256185627', '+85256245310',
                #          '+85256128047', '+85256242173', '+85254838665', '+85256290597'
                #          ]

                # 控制用哪个手机号来模拟位置
                phone = ['+85251617973']

                if location_number_of_requests < 2:

                    Logger.info("Get channel info from '%s'...", location)
                    # 指定模拟位置的手机号去连接telegram
                    phone_client = self.clients.get(phone[location_number_of_requests])

                    # 引入InputGeoPoint类，并通过传入的经纬度初始化一个参数
                    from telethon.tl.types import InputGeoPoint
                    geo_point = InputGeoPoint(lat=lat, long=long)

                    # 得到附近群的原始数据实体
                    location_channel_entity = await phone_client.get_group_by_location(geo_point=geo_point)

                    # 每次请求完该接口请求次数就会自增1
                    location_number_of_requests += 1
                else:
                    # 如果请求次数超过资源池中的手机号个数，则会返回-505状态码，客户端请求将会休眠，并且将请求次数置零
                    location_number_of_requests = 0
                    return ERR_REQUEST_TIMES

            except Exception as e:
                Logger.error("An error occurred while get channel by location, message: %s", e)
            else:
                try:

                    # 首先解析附近群的基本信息
                    channel_by_location = await Parser.parse_nearby_group(location_channel_entity,
                                                                          phone_client, self.media_processor)

                    # 由于群的距离的原始信息与基本信息分离，因此需要单独解析
                    real_channel_info = await Parser.parse_nearyby_group_distance(location_channel_entity,
                                                                                  channel_by_location)

                    # 模拟位置的手机号
                    this_phone = {'phone': phone[location_number_of_requests - 1]}

                    # 最终客户端需要得到的数据
                    result = {'roomList': real_channel_info, 'phone': this_phone}

                    Logger.info("Get channel by location info '%s', use phone: '%s'",
                                real_channel_info, phone_client.phone)
                except Exception as e:
                    Logger.error("An error occurred while parse channel by location, message: '%s'", e)
        return result

    async def _location_channel_user_handler(self, data: dict) -> list:
        """
        用于处理位置群的成员迭代，需要传入获取该位置群的手机号、群ID、群access_hash
        :param data: [description]
        :return: 群成员列表
        """
        phone = data.get('phone')
        channel_id = data.get('channel_id')
        access_hash = data.get('access_hash')

        if channel_id:
            try:
                client = self.clients.get(phone=phone)
                user_iterator = await client.iter_location_channel_users(channel_id, access_hash)
                result = []
                try:
                    async for user_entity in user_iterator:
                        user = await Parser.parse_user(user_entity, client, self.media_processor)
                        result.append(user)
                except ChatAdminRequiredError:
                    Logger.error("Chat admin permission required for getting user list of channel '%s'", channel_id)
                except Exception as e:
                    Logger.error(
                        "An error occurred while getting users from channel '%s', message: %s", channel_id, str(e))
                return result

            except Exception as e:
                Logger.error("Iterating users of channel '%s' error, message: %s", channel_id, e)
        return []

    async def _location_channel_messages_handler(self, data: dict) -> typing.Union[int, list]:
        """
        用于获取位置群群消息
        :param data:
        :return: list
        """
        phone = data.get('phone')                   # 该位置群所用到的手机号
        channel_id = data.get('channel_id')         # 该位置群的id
        access_hash = data.get('access_hash')       # 该位置群的access_hash

        limit = data.get('limit') or 20  # 每页消息上线
        # 此处做每页消息判断，超过30会默认为30，因为一次性获取太多的消息可能会导致图片下载队列堵塞
        if limit > 30:
            limit = 30

        offset_id = data.get('min_id') or 0
        min_id = data.get('max_id') or 0

        # 用模拟位置的手机号连接telegram
        client = self.clients.get(phone)

        messages = []
        Logger.info("Prepare to get message(limit:%s, channel:%s, minId:%s, offsetId:%s)...",
                    limit, channel_id, min_id, offset_id)

        try:
            message_entities = await client.get_location_channel_messages(channel_id=channel_id,
                                                                          access_hash=access_hash, limit=limit,
                                                                          offset_id=offset_id, min_id=min_id)
        except rpcerrorlist.ChatAdminRequiredError as npe:
            # 缺少权限
            Logger.error("No permission to get channel '%s' messages. message: %s", channel_id, npe)
            return ERR_NO_PERMISSION
        except Exception as e:
            Logger.error("An error occurred while trying to get messages from '%s', message: %s", channel_id, e)
            return ERR_UNKNOWN

        else:
            for message_entity in message_entities:

                # 格式化存储在redis中的群消息键，格式为：tg_message_to_heavy_handle/房间id_消息id
                room_id = client.get_full_id(message_entity.to_id)
                message_id = message_entity.id
                room_message_key = 'tg_message_to_heavy_handle/' + str(room_id) + '_' + str(message_id)

                # 此处根据redis缓存中是存在已获取的消息进行去重
                if await REDIS_CLIENT.get(room_message_key) is None:
                    # 解析没有重复的消息
                    message = await Parser.parse_message(message_entity, client, self.media_processor)
                    # 将解析的消息基本信息写入日志
                    Logger.info("Get a message: msgId=%s, userId=%s, channelId=%s, pubDate=%s",
                                message["originalId"], message["personCode"], message["roomCode"], message["createDate"]
                                )
                    if message["originalId"] is not None:
                        messages.append(message)

                    # 将处理完成的消息以格式化的形式存入redis中，键为：tg_media_handle/房间id_消息id，值为：1，并且设置有效时长为一周
                    await REDIS_CLIENT.set(room_message_key, '1', 604800)
                    # 将解析过的消息存入redis的事件记录在日志中
                    Logger.info('The message info is added to the cache, channel_id(%s), message_id(%s)',
                                room_id, message_id)

                else:
                    # 该消息已重复，在日志中记录
                    Logger.info('The message has been parsed, channel_id(%s), message_id(%s)', room_id, message_id)
        return messages

    async def _location_channel_info_handler(self, data) -> typing.Union[int, dict]:
        """
        用户处理位置群详情
        :param data: 位置群id，对应的手机号，对应的群hash
        :return: 群详情字典
        """
        phone = data.get('phone')
        channel_id = data.get('channel_id')
        access_hash = data.get('access_hash')

        channel = dict()
        if channel_id:
            try:
                client = self.clients.get(phone=phone)
                channel_entity = await client.get_location_channel_info(channel_id, access_hash)
                channel = await Parser.parse_channel(channel_entity, client, self.media_processor)
                Logger.info("Get location channel: roomCode=%s, roomName=%s",
                            channel['roomCode'], channel['roomName'])

            except Exception as e:
                Logger.error("An error occurred while processing location channel '%s' actions, message: %s",
                             channel_id, str(e))
        return channel

    async def _search(self, data):
        phones = data.get("phones")
        gather_phone = data.get("gather_phone")
        users = []
        if phones:
            client = self.clients.get(gather_phone)
            try:
                Logger.info("Get users info by phone, the phones: '%s', gather_phone: '%s'", phones, gather_phone)
                user_entities = await client.get_user_by_phones(phones)
            except ValueError as nfe:
                Logger.error("No channel use '{}' as search, message: {}".format(phones, str(nfe)))
                return {"error": ERR_NOT_EXIST}
            except Exception as e:
                Logger.error(
                    "An error occurred while getting users from channel '{}', message: {}".format(phones, str(e)))
                return {"error": ERR_UNKNOWN}
            else:
                try:
                    i = 0
                    for user_entity in user_entities[0]:
                        user = await Parser.parse_user(user_entity, client, self.media_processor)

                        if user_entity.photo is not None:
                            head_img = Media.new(media_object=user_entity, thumb=0,
                                                 group=Const.img_profiles, client=client)
                            user['headImgUrl'] = await self.media_processor.add_task(head_img)

                        user['phone'] = user_entities[1][i]
                        users.append(user)
                        i += 1
                except MultiError:
                    Logger.error("Chat admin permission required for getting user list of channel '{}'".format(phones))
                    return {"error": ERR_NO_PERMISSION}
                except Exception as e:
                    Logger.error("An error occurred while iterating channel '{}' users, message: {}".format(phones, e))
        Logger.info("Get users info by phone finished! The results: %s", users)
        return users

    async def _users_handler(self, data: dict) -> list:
        """
        获取群成员，并将结果推送到消息队列。旧版是遍历完成后返回，但是请求时间变得非常长
        因此新版改成了异步推送

        :param data: [description]
        :return: [description]
        """
        username = data.get("channel")

        # 获取当前采集群所用的手机号，如果传入该手机号则用该手机号，如果没有传入，则随机用资源池的手机号
        phone = data.get('phone')

        # 查看redis中是否有channel与phone的绑定关系
        channel_key = 'tg' + ':' + str(username)

        # 如果redis中存在channel和phone的对应关系，则直接取用该channel对应的手机号作为采集号
        redis_phone = await REDIS_CLIENT.get(channel_key)
        if redis_phone is not None:
            phone = redis_phone

            # 覆盖掉被ban的手机号
            ban_phones = ['+85262161655']
            if phone in ban_phones:
                # 记录该手机号已被封禁
                Logger.info("The phone number has been banned,need a new phone number to replace, phone:%s", phone)
                client = self.clients.get()
                if isinstance(client, TeleClient):
                    phone = client.phone
                    await REDIS_CLIENT.set(key=channel_key, value=phone, ex=None)
                    # 记录被禁手机号已被新手机号替换
                    Logger.info("The channel and the new phone are bound, channel:%s, phone:%s", username, phone)

            client = self.clients.get(phone)
        # 否则判断是否传入手机号
        else:
            # 如果传入手机号，则使用该手机号作为采集号，并且将该channel和该phone绑定放入redis
            if phone:
                client = self.clients.get(phone)
                if isinstance(client, TeleClient):
                    await REDIS_CLIENT.set(key=channel_key, value=phone, ex=None)
                    # 日志中记录该channel和该phone已绑定
                    Logger.info("The channel and the phone are bound, channel:%s, phone:%s", username, phone)
            else:
                client = self.clients.get()
                if isinstance(client, TeleClient):
                    phone = client.phone
                    await REDIS_CLIENT.set(key=channel_key, value=phone, ex=None)
                    # 日志中记录该channel和该phone已绑定
                    Logger.info("The channel and the phone are bound, channel:%s, phone:%s", username, phone)

        if username:
            # 当前用于采集信息所连接telegram的手机号
            current_phone = client.phone
            try:
                user_iterator = await client.iter_channel_users(username, current_phone)
                # 最新版本数据放入mq进行返回，等待有缘人调试
                # task = PublisherTask(entity=user_iterator, client=client, media_processor=self.media_processor,
                #                      channel=name, task_type=PublisherTask.TYPE_USER, target_queue=Const.pub_usr_queue)
                # await self.publisher.add_task(task)

                # 获取群成员的群组id
                channel_id = await client.get_channel_id(username, current_phone)
                result = []
                try:
                    async for user_entity in user_iterator:
                        user = await Parser.parse_user(user_entity, client, self.media_processor)
                        user['channel_id'] = channel_id
                        result.append(user)
                except ChatAdminRequiredError:
                    Logger.error("Chat admin permission required for getting user list of channel '%s'", username)
                except Exception as e:
                    Logger.error(
                        "An error occurred while getting users from channel '%s', message: %s", username, str(e))
                return result

            except Exception as e:
                Logger.error("Iterating users of channel '%s' error, message: %s", username, e)
        return []

    async def _admins_handler(self, data: dict) -> list:
        """
        获取群管理员
        :param data: [description]
        :return: [description]
        """
        username = data.get("channel")

        # 获取当前采集群所用的手机号，如果传入该手机号则用该手机号，如果没有传入，则随机用资源池的手机号
        phone = data.get('phone')

        # 查看redis中是否有channel与phone的绑定关系
        channel_key = 'tg' + ':' + str(username)

        # 如果redis中存在channel和phone的对应关系，则直接取用该channel对应的手机号作为采集号
        redis_phone = await REDIS_CLIENT.get(channel_key)
        if redis_phone is not None:
            phone = redis_phone

            # 覆盖掉被ban的手机号
            ban_phones = ['+85265868027', '+85267460863', '+85262245905', '+85262253654', '+85256411229']
            if phone in ban_phones:
                # 记录该手机号已被封禁
                Logger.info("The phone number has been banned,need a new phone number to replace, phone:%s", phone)
                client = self.clients.get()
                if isinstance(client, TeleClient):
                    phone = client.phone
                    await REDIS_CLIENT.set(key=channel_key, value=phone, ex=None)
                    # 记录被禁手机号已被新手机号替换
                    Logger.info("The channel and the new phone are bound, channel:%s, phone:%s", username, phone)

            client = self.clients.get(phone)
        # 否则判断是否传入手机号
        else:
            # 如果传入手机号，则使用该手机号作为采集号，并且将该channel和该phone绑定放入redis
            if phone:
                client = self.clients.get(phone)
                if isinstance(client, TeleClient):
                    await REDIS_CLIENT.set(key=channel_key, value=phone, ex=None)
                    # 日志中记录该channel和该phone已绑定
                    Logger.info("The channel and the phone are bound, channel:%s, phone:%s", username, phone)
            else:
                client = self.clients.get()
                if isinstance(client, TeleClient):
                    phone = client.phone
                    await REDIS_CLIENT.set(key=channel_key, value=phone, ex=None)
                    # 日志中记录该channel和该phone已绑定
                    Logger.info("The channel and the phone are bound, channel:%s, phone:%s", username, phone)

        if username:
            # 当前用于采集信息所连接telegram的手机号
            current_phone = client.phone
            try:
                user_iterator = await client.get_channel_admin_user(username, current_phone)
                # 用于存放返回的管理员数据
                result = []
                try:
                    async for user_entity in user_iterator:
                        user = await Parser.parse_user(user_entity, client, self.media_processor)
                        result.append(user)
                except ChatAdminRequiredError:
                    Logger.error("Chat admin permission required for getting user list of channel '%s'", username)
                except Exception as e:
                    Logger.error(
                        "An error occurred while getting admins from channel '%s', message: %s", username, str(e))
                return result

            except Exception as e:
                Logger.error("Iterating admins of channel '%s' error, message: %s", username, e)
        return []

    async def _dialog_handler(self, data: dict, action: int = 0) -> typing.Union[int, list]:
        """
        会话处理，用于获取会话列表或发送会话

        :param data: [description]
        :param action: [description]，默认值 `0`
        :return: [description]
        """
        phone = data.get("phone")               # 账号
        content = data.get("content")           # 内容
        channel_id = data.get("channel_id")     # 目标群ID

        result = 0

        if not phone:
            return result
        else:
            client = self.clients.get(phone)
            if not client:
                return result

        if action == 0:
            # 发送消息到指定会话
            if content and channel_id:
                try:
                    sent_msg = await client.send_message(channel_id, content)
                    result = sent_msg.id
                    Logger.info("Client '%s' has sent a message(msg_id=%s, target=%s)!", phone, sent_msg.id, channel_id)
                except Exception as e:
                    Logger.error("Sending message to channel '%s' error, message: %s", channel_id, e)
        else:
            # 获取指定账号的会话列表
            try:
                dialogs = await client.get_dialogs()
                result = Parser.parse_dialogs(dialogs, client)
            except Exception as e:
                Logger.error("Listing dialogs of client '%s' error, message: %s", phone, e)
        return result


class LoginHandler(RequestHandler):
    """
    处理登录
    """

    def initialize(self, clients: TeleClients) -> None:
        self.clients = clients

    async def get(self):
        phone = None
        if "phone" in self.request.arguments.keys():
            phone = self.get_argument("phone")
            if not phone.startswith("+"):
                phone = "+" + phone
        else:
            self.write(ERR_REQUEST)
            return

        client = None
        code = None
        force_sms = False   # 是否强制使用短信验证码登录，正常情况Telegram会发送验证码到手机APP，可以更改为强制短信
        if "code" in self.request.arguments.keys():
            code = self.get_argument("code")
            # 根据手机号获取或初始化客户端对象
            client = self.clients.get(phone)
        else:
            client = TeleClient(phone=phone, proxy=Const.client_proxy)
            # 先移除资源池中旧的没有登录的这个账号对象，然后将新的添加进去
            # 这样做是为了应对重复请求验证码的情况，保证一个账号只有一个对象
            self.clients.remove(client)
            self.clients.put(client)

        if "force_sms" in self.request.arguments.keys():
            force_sms = self.get_argument("force_sms")
            if force_sms in ["1", "yes", "on", "true"]:
                force_sms = True

        if client:
            connected = await client.connect(code, sms=force_sms)
            if connected:
                # 表示登录成功
                self.write("1".encode("utf8"))
            else:
                if code:
                    # 表示登录失败
                    self.write("-1".encode("utf8"))
                else:
                    # 表示已发送登录验证码
                    self.write("0".encode("utf8"))
                    self.clients.put(client)
        else:
            self.write(json.dumps({"error": "Internal unexpact error!"}).encode("utf8"))


class PingHandler(RequestHandler):
    def get(self):
        self.write("pong".encode("utf8"))
