# -*- coding:utf-8 -*-
# @Author: KeyH
# @Date: 2023年6月5日16:01:34


import re
import typing
import random

# from tornado.queues import Queue as AsyncQueue
from telethon import TelegramClient, events, functions, sessions, types
from telethon import utils as teleutils
from telethon.tl.custom.message import Message
from telethon.tl.functions.contacts import DeleteContactsRequest, ImportContactsRequest
from telethon.tl.functions.users import GetFullUserRequest

from common.const import Const
from common.logger import Logger
from models import String
from common.redis_util import REDIS_CLIENT

Entities = typing.Union[types.Channel, types.User, types.Chat,
                        types.PeerChannel, types.PeerUser, types.PeerChat]
ChannelTypes = typing.Union[types.Channel, types.InputChannel, types.InputPeerChannel]

JoinChannelRequest = functions.channels.JoinChannelRequest
LeaveChannelRequest = functions.channels.LeaveChannelRequest
ImportChatInviteRequest = functions.messages.ImportChatInviteRequest
SQLiteSession = sessions.SQLiteSession


class TeleClient:
    def __init__(self, phone: str = None, proxy: typing.Tuple[int, str, int] = None, new_msg_cbk: typing.Any = None):
        """
        TelegramClient包装对象

        :param phone: 手机号, 默认为 None
        :param proxy: SOCKS5代理, 默认为 None
        :param new_msg_cbk: 新消息事件回调, 默认为 None
        """
        if phone:
            phone = "+" + re.sub(r"\D", "", phone)  # 去除非手机号中的非数字符号，标准化手机号格式为 `+12345`
        self.__phone = phone
        self.__proxy = proxy
        self.__new_msg_cbk = new_msg_cbk

        self.__connected = False    # 表示是否连接到Telegram服务器
        # telethon原生客户端对象
        if phone:
            self.__client = TelegramClient(SQLiteSession(Const.session_folder + phone), Const.api_id, Const.api_hash,
                                           proxy=proxy, base_logger='only_error')

    async def connect(self, code: String = None, sms: bool = False) -> bool:
        """
        连接客户端到Telegram服务器，并进行登陆验证。
        发起连接请求时，先校验账号是否已经有登录认证，如果没有登录认证且登录验证码参数`code`值为None时，会发出登录验证码请求来获取验证码
        如果登录验证码参数`code`值不为None，则进行登录操作并记录认证许可

        :param code: 登陆验证码, 默认为 None
        :return: 连接是否成功，此状态会标记到`connected`属性中
        """
        if self.__phone:
            try:
                # 先建立连接
                if not self.__client.is_connected():
                    await self.__client.connect()

                # 如果账号没有登录认证
                if not await self.__client.is_user_authorized():
                    # 如果有验证码参数，进行登录
                    if code:
                        await self.__client.sign_in(self.__phone, code)
                        self.__connected = True
                    # 如果没有验证码参数，发送验证码
                    else:
                        await self.__client.send_code_request(self.__phone, force_sms=sms)
                else:
                    self.__connected = True

                # 如果登陆成功，注册新消息事件监听（目前没有订阅的需求，所以暂时注释掉了）
                if self.__connected and self.__new_msg_cbk:
                    # Logger.debug("Regist new message event...")
                    # self.__client.add_event_handler(self.__new_msg_cbk, events.NewMessage)
                    pass
            except Exception as e:
                if self.__client.is_connected():
                    self.__client.disconnect()
                Logger.error("Connecting to telegram server error, message: %s", e)
        return self.connected

    async def get_channel_type(self, channel: typing.Union[str, int], current_phone) -> typing.Union[None, ChannelTypes]:
        """
        根据ID或username获取 Channel, InputChannel, InputPeerChannel对象以防止username重复导致获取群信息出错的问题

        :param channel: 群组username
        :param current_phone: 当前连接telegram所用到的手机号
        :return: 包含有access_hash和channel_id的对象，能保证群组的唯一性
        """

        input_channel = None
        if not channel:
            return input_channel
        # 记录当前获取群信息的手机号，并且将群名称+手机号作为查找或者存储redis的键
        current_phone_channel_key = 'tg_input_channel_handle:' + str(channel) + '->' + str(current_phone)
        # 判断redis中是否存在当前手机号的群实体
        if await REDIS_CLIENT.get(current_phone_channel_key) is None:
            try:
                input_entity = await self.__client.get_input_entity(channel)
            except ValueError:
                # channel名字解析错误
                pass
            except Exception as e:
                # 其他未知错误
                Logger.error("Trying to get channel type of entity '%s' error, message: %s，phone: %s", channel,
                             e, self.__phone)
            else:
                if not isinstance(input_entity, (types.InputPeerChannel, types.InputChannel, types.Channel)):
                    if isinstance(channel, str):

                        try:
                            entity = await self.client.get_entity(channel)
                        except ValueError:
                            pass
                        except Exception as e:
                            Logger.error(
                                "Trying to get channel type of entity '%s' error, message: %s", channel, e)
                        else:
                            if isinstance(entity, types.Channel):
                                input_channel = teleutils.get_input_channel(entity)
                else:
                    input_channel = input_entity

                if not input_channel:
                    Logger.error("Can not get channel type of entity '%s(typeName: %s)', maybe it's not a channel.",
                                 channel, type(entity).__name__)
                else:
                    Logger.debug("Get a channel type '%s' of '%s'", input_channel, channel)
                # 将得到的InputPeerChannel实体类转换为string类型存入redis缓存中
                str_input_channel = str(input_channel.channel_id)+','+str(input_channel.access_hash)
                await REDIS_CLIENT.set(key=current_phone_channel_key, value=str_input_channel, ex=None)
                # 在日志中记录该群的实体信息
                Logger.info("The phone number gets the group's entity for the first time, the phone:%s, the channel:%s",
                            current_phone, channel)
        else:
            # 该手机号已经获取过该群的群实体，将redis中的群实体取出并把string类型转换为InputPeerChannel类型
            str_input_channel = await REDIS_CLIENT.get(current_phone_channel_key)
            # 引入InputPeerChannel类型
            from telethon.tl.types import InputPeerChannel
            # 处理input_channel
            channel_id = int(str_input_channel.split(',')[0])
            access_hash = int(str_input_channel.split(',')[1])
            input_channel = InputPeerChannel(channel_id, access_hash)
            # 在日志中记录是从redis缓存中获取到的群实体
            Logger.info("This phone number has already obtained the entities of the group, the phone:%s, "
                        "the channel:%s", current_phone, channel)
        return input_channel

    # 通过地理位置获取周边的群组
    async def get_group_by_location(self, geo_point: types.InputGeoPoint) -> types.Updates:
        """
        通过传入的地理位置经纬度来获取附近群的原始数据
        :param geo_point: 经纬度
        :return: 详细位置附近群的原始信息
        """
        result = None
        if geo_point:
            result = await self.__client(functions.contacts.GetLocatedRequest(geo_point=geo_point))
        return result

    # 获取TG群/频道详情
    async def get_channel(self, username: str = None, current_phone: str = None) -> types.ChatFull:
        """
        获取Telegram群或者频道的详细信息

        :param username: 目标群/频道的username
        :param current_phone: 当前用于采集信息所连接telegram的手机号
        :return: ChatFull原生对象
        """

        input_channel = await self.get_channel_type(username, current_phone)

        result = None
        if input_channel:
            result = await self.__client(functions.channels.GetFullChannelRequest(channel=input_channel))
        return result

    # 通过channel_id和access_hash来获取群/频道信息
    async def get_channel_by_id(self, channel_id: int, access_hash: int) -> types.ChatFull:
        """
        通过系统中的channel_id来获取群/频道的信息

        :param channel_id: 系统中群/频道的id
        :param access_hash: 群/频道的access_hash
        :return: ChatFull原生对象
        """
        input_channel = types.InputPeerChannel(channel_id, access_hash)
        # print(input_channel)

        result = None
        if input_channel:
            result = await self.__client(functions.channels.GetFullChannelRequest(channel=input_channel))
        return result

    async def get_more_channel(self, more_username: list, channels_id: list = None) -> types.ChatFull:
        """
        获取多个Channel原始数据

        :param more_username: 目标多个Channel的名称
        :param channels_id: 目标多个Channel的id，默认值None
        """

        result = None
        if more_username:
            result = await self.__client(functions.channels.GetChannelsRequest(id=more_username))
        return result

    # 获取群成员的群组id
    async def get_channel_id(self, username: str, current_phone: str):
        """
        获取群成员的群组id
        :param username: 目标群username
        :param channel_id: 目标群ID，默认值 `None`
        :param current_phone: 当前用于采集信息所连接telegram的手机号
        :return: 群组id（str）
        """
        input_channel = await self.get_channel_type(username, current_phone)
        channel_id = ''
        if input_channel:
            channel = await self.__client(functions.channels.GetFullChannelRequest(channel=input_channel))
            channel_id = channel.full_chat.id
        return channel_id

    # 获取指定群名称的群成员
    async def iter_channel_users(self, username: str, current_phone: str):
        """
        迭代群成员

        :param username: 目标群username
        :param channel_id: 目标群ID，默认值 `None`
        :param current_phone: 当前用于采集信息所连接telegram的手机号
        :return: 异步生成器
        """
        input_channel = await self.get_channel_type(username, current_phone)
        iterator = None
        if input_channel:
            flag = None
            channel = await self.__client(functions.channels.GetFullChannelRequest(channel=input_channel))
            user_count = channel.full_chat.participants_count
            if user_count < 5000:
                flag = False
            else:
                flag = True
            iterator = self.__client.iter_participants(input_channel, aggressive=flag)
        return iterator

    # 获取位置群的群成员（通过群id和群assess_hash获取）
    async def iter_location_channel_users(self, channel_id: int, access_hash: int):
        """
        迭代位置群成员

        :param channel_id: 位置群的id
        :param access_hash: 位置群的access_hash
        :return: 异步生成器
        """
        input_channel = types.InputPeerChannel(channel_id, access_hash)
        iterator = None
        if input_channel:
            iterator = self.__client.iter_participants(input_channel)
        return iterator

    # 获取位置群群消息（通过群id和群assess_hash获取）
    async def get_location_channel_messages(self, channel_id: int, access_hash: int, limit: int = 20,
                                            offset_id: int = 0, min_id: int = 0, max_id: int = 0) -> list:

        input_channel = types.InputPeerChannel(channel_id, access_hash)
        messages = []
        if input_channel:
            messages = await self.__client.get_messages(input_channel, limit=limit, offset_id=offset_id, min_id=min_id,
                                                        max_id=max_id)
        return messages

    # 获取位置群详情（通过群id和群assess_hash获取）
    async def get_location_channel_info(self, channel_id: int, access_hash: int):
        """
        获取位置群详情
        :param channel_id: 位置群的id
        :param access_hash: 位置群的access_hash
        :return: ChatFull原生对象
        """
        input_channel = types.InputPeerChannel(channel_id, access_hash)
        result = None
        if input_channel:
            result = await self.__client(functions.channels.GetFullChannelRequest(channel=input_channel))
        return result

    async def get_personal_user(self, username: str):
        """
        通过用户的username获取到用户的详细信息

        :param username: 目标用户
        return 用户信息对象
        """
        user_info = None
        if username:
            user_info = await self.__client(GetFullUserRequest(username))
        return user_info

    # 获取群消息
    async def get_messages(self, username: str, current_phone: str, limit: int = 20,
                           offset_id: int = 0, min_id: int = 0, max_id: int = 0) -> list:
        input_channel = await self.get_channel_type(username, current_phone)
        messages = []
        if input_channel:
            messages = await self.__client.get_messages(input_channel, limit=limit, offset_id=offset_id, min_id=min_id,
                                                        max_id=max_id)
        return messages

    # 获取机器人返回的消息（用于处理机器人接口的相关操作）
    async def get_bot_messages(self, bot_name: str, limit: int = 1, offset_id: int = 0,
                               min_id: int = 0, max_id: int = 0,) -> list:
        target_bot = await self.__client.get_input_entity(bot_name)
        messages = []
        if target_bot:
            messages = await self.__client.get_messages(target_bot, limit=limit, offset_id=offset_id, min_id=min_id,
                                                        max_id=max_id)

        # from telethon.tl.types import KeyboardButtonCallback
        # res = KeyboardButtonCallback(text='下一页', data='aa')
        # messages.append(res)
        return messages

    # 给机器人发送消息（用于处理机器人接口的相关操作）
    async def send_bot_message(self, bot_name: str, message: str) -> Message:
        """
        发送关键字给机器人，成功返回消息原生对象，失败返回None

        :param bot_name: 机器人的username
        :param message: 关键字
        :return: 消息原生对象
        """
        if bot_name:
            target_bot = await self.__client.get_input_entity(bot_name)
            sent_msg = await self.__client(functions.messages.SendMessageRequest(peer=target_bot, message=message))
            return sent_msg

    # 虚实对应（通过手机号查找用户）
    async def get_user_by_phones(self, phone: typing.Union[str, typing.List[str]]) -> typing.Optional[typing.List[types.User]]:
        if not isinstance(phone, list):
            phone = [phone]
        contacts = []
        for p in phone:
            input_contact = types.InputPhoneContact(client_id=random.randrange(-2**63, 2**63), phone=p, first_name=p, last_name="")
            contacts.append(input_contact)
        rtn = await self.client(ImportContactsRequest(contacts))

        if rtn:
            user_ids = []
            user_phones = []
            for user in rtn.users:
                user_ids.append(user.id)
                user_phones.append(user.phone)
            rtn = await self.client(DeleteContactsRequest(user_ids))
            if rtn:
                print(rtn)
                return [rtn.users, user_phones]
            else:
                return None
        else:
            return None

    # 添加联系人
    async def add_contact(self, phone: typing.Union[str, typing.List[str]]) -> typing.Optional[typing.List[types.User]]:
        if not isinstance(phone, list):
            phone = [phone]
        contacts = []
        for p in phone:
            result = await self.__client(functions.contacts.AddContactRequest(
                id=1218234368,
                first_name='name',
                last_name='test',
                phone=p
            ))
            contacts.append(result)
        print(contacts)
        return contacts

    # 获取通讯录用户
    async def get_address_book(self):
        result = await self.__client(functions.contacts.GetContactsRequest(hash=0))
        print(result)


    async def get_channel_admin_user(self, username: str, current_phone: str, channel_id: int = None):
        """
        获取群管理员成员

        :param username: 目标群username
        :param current_phone: 当前用于采集信息所连接telegram的手机号
        :param channel_id: 目标群ID，默认为None
        :return 异步生成器
        """
        input_channel = await self.get_channel_type(username, current_phone) or await \
            self.get_channel_type(channel_id, current_phone)
        iterator = None
        if input_channel:
            from telethon.tl.types import ChannelParticipantsAdmins
            iterator = self.__client.iter_participants(input_channel, filter=ChannelParticipantsAdmins())
        return iterator

    async def join_channel(self, username: str, current_phone: str, channel_id: int = None) -> int:
        """
        加群，成功返回群ID，失败返回None

        :param username: username
        :param current_phone: 当前用于采集信息所连接telegram的手机号
        :param channel_id: channel_id，默认值 `None`
        :return: channel_id
        """
        input_channel = await self.get_channel_type(username, current_phone) or await \
            self.get_channel_type(channel_id, current_phone)
        # updates = await self.__client(ImportChatInviteRequest(channel)) if is_private else await self.__client(
        #     JoinChannelRequest(channel))
        if input_channel:
            updates = await self.__client(JoinChannelRequest(input_channel))
            return self.get_full_id(updates.chats[0])
        return None

    async def leave_channel(self, username: str, current_phone: str, channel_id: int = None) -> int:
        input_channel = await self.get_channel_type(username, current_phone) or await \
            self.get_channel_type(channel_id, current_phone)
        if input_channel:
            updates = await self.__client(LeaveChannelRequest(channel=input_channel))
            return self.get_full_id(updates.chats[0])
        return None

    async def send_message(self, channel: typing.Union[str, int], current_phone: str, message: str) -> Message:
        """
        发送群消息，成功返回本条消息的原生对象，失败返回None

        :param channel: 目标群ID
        :param current_phone: 当前用于采集信息所连接telegram的手机号
        :param message: 消息内文本
        :return: MessageEntity
        """
        target_channel = await self.get_channel_type(channel, current_phone)
        sent_msg = await self.__client.send_message(target_channel, message=message)
        return sent_msg

    async def get_dialogs(self) -> list:
        """
        获取会话列表

        :return: [description]
        """
        dialogs = await self.__client.get_dialogs()
        return dialogs

    async def download_media(self, media, thumb: typing.Union[int, types.PhotoSize, None] = -1):
        return await self.__client.download_media(media, thumb=thumb, file=bytes)

    async def download_profile(self, entity: typing.Union[types.User, types.ChannelFull]):
        return await self.__client.download_profile_photo(entity=entity, download_big=False, file=bytes)

    def get_full_id(self, entity: Entities) -> int:
        """
        获取全ID，Telegram规定，群ID以 -100开头

        :param entity: [description]
        :return: [description]
        """
        if isinstance(entity, types.User):
            return entity.id
        elif isinstance(entity, types.Channel):
            return int("-100" + str(entity.id))
        elif isinstance(entity, types.Chat):
            return -entity.id
        elif isinstance(entity, types.PeerUser):
            return entity.user_id
        elif isinstance(entity, types.PeerChannel):
            return int("-100" + str(entity.channel_id))
        elif isinstance(entity, types.PeerChat):
            return -entity.chat_id

    @property
    def phone(self) -> str:
        return self.__phone

    @phone.setter
    def phone(self, phone: str) -> None:
        if phone:
            phone = "+" + re.sub(r"\D", "", phone)
        self.__phone = phone
        self.__client = TelegramClient(Const.session_folder + phone, Const.api_id, Const.api_hash,
                                       proxy=self.__proxy, base_logger='only_error')
        self.__client.add_event_handler(self.__new_msg_cbk)

    @property
    def proxy(self) -> typing.Tuple[int, str, int]:
        return self.__proxy

    @proxy.setter
    def proxy(self, proxy: typing.Tuple[int, str, int]) -> None:
        self.__proxy = proxy
        self.__client = TelegramClient(self.__phone, Const.api_id, Const.api_hash,
                                       proxy=proxy, base_logger='only_error')
        self.__client.add_event_handler(self.__new_msg_cbk)

    @property
    def client(self) -> TelegramClient:
        return self.__client

    @client.setter
    def client(self, client: TelegramClient):
        self.__client = client
        self.__connected = client.is_connected()

    @property
    def connected(self) -> bool:
        return self.__connected


class TeleClients:
    def __init__(self, phones: typing.List[str]):
        """
        资源池

        :param phones: 初始化手机号
        """
        self.__phones = phones

        self.__clients = dict()     # 存储 手机号 -> TeleClient 映射
        self.__initialized = False  # 是否已经初始化
        self.__idx = 0              # 下一个TeleClient对象索引，用于获取一个客户端对象

    async def initialize(self, callback=None):
        if not self.__initialized:
            Logger.info("Initializing client pool...")
            for phone in self.__phones:
                client = TeleClient(phone=phone, proxy=Const.client_proxy, new_msg_cbk=callback)
                connected = await client.connect()
                if connected:
                    Logger.info(str('[init]-[账号成功初始化]-[{}]'.format(phone)))
                    self.put(client)
                else:
                    Logger.error(str('[init]-[账号初始化失败]-[{}]'.format(phone)))
            self.__initialized = True
            Logger.info("Client pool has been initialized, total: %s", len(self.__clients))

    def get(self, phone: str = None) -> typing.Union[None, TeleClient]:
        """
        从账号资源池中获取采集账号。如果`phone`为`None`, 则会从资源池中自动获取一个有效的采集资源；
        如果`phone`参数指定，则会尝试从资源池中获取指定的资源。获取失败时返回`None`

        :param phone: 手机号, 默认为 None
        :return: 采集账号对象
        """
        global client
        if not phone:
            for _ in range(len(self.__clients)):
                key = list(self.__clients.keys())[self.idx]
                self.idx += 1
                client = self.__clients.get(key)
                if client.connected:
                    break
        else:
            client = self.__clients.get(phone)
            if client is None:
                Logger.error(str('[账号不存在]-[{}]'.format(phone)))
                # 记录账号异常，并存入redis传入预警平台
                REDIS_CLIENT.hset(key='telegram_phone_error', field=phone, value='账号session失效或异常')

        return client

    def put(self, client: TeleClient):
        if client.phone not in self.__clients.keys():
            self.__clients[client.phone] = client

    def remove(self, client: TeleClient):
        if client.phone in self.__clients.keys():
            del self.__clients[client.phone]

    @property
    def idx(self) -> int:
        return self.__idx

    @idx.setter
    def idx(self, i: int):
        self.__idx = i % len(self.__clients)
