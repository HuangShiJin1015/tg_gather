# -*- coding:utf-8 -*-
# @Author: KeyH
# @Date: 2023年6月5日16:02:59

import traceback
import typing
import re
import time

from datetime import timedelta, timezone
from telethon import types
from telethon.tl import patched

from common.const import Const
from common.logger import Logger
from common.utils import Hash
from common.redis_util import REDIS_CLIENT
from models.media import Media
from models.teleclient import TeleClient
from services.mediaprocessor import MediaProcessor
from telethon.tl.types import MessageEntityTextUrl

ChatFull = types.messages.ChatFull
Channel = types.Channel
Message = patched.Message
MessageService = patched.MessageService


class Parser:
    """
    数据解析器，数据解析在这里完成
    """
    # 媒体对象的Key列表
    MEDIA_KEYS = ["sharePicUrl", "fileUrl", "mediaUrl", "mediaPicUrl", "picUrl", "headImgUrl"]

    # 解析群/频道详情的原始数据
    @staticmethod
    async def parse_channel(chat_full: ChatFull, client: TeleClient, media_processor: MediaProcessor) -> dict:
        channel = dict(
            roomCode=None,                                  # 群/频道ID(以-100开头)
            channel_id=None,                                # 群/频道原始ID
            roomName=None,                                  # 群/频道名称(telegram不唯一，群名字)
            roomAlias=None,                                 # 群/频道username(telegram唯一)
            headImgUrl=None,                                # 群/频道头像链接
            notice=None,                                    # 群/频道介绍
            userCount=None,                                 # 群/频道成员数
            createTime=None,                                # 群/频道创建时间
            megagroup=None,                                 # 判断是群还是频道(如果是群值为True，如果是频道值为False)
        )
        if chat_full is None:
            return channel
        try:
            channel['roomName'] = chat_full.chats[0].title
            channel['roomCode'] = client.get_full_id(chat_full.chats[0])
            channel['channel_id'] = chat_full.chats[0].id
            channel['roomAlias'] = chat_full.chats[0].username
            channel['notice'] = chat_full.full_chat.about
            channel['userCount'] = chat_full.full_chat.participants_count
            channel['createTime'] = chat_full.chats[0].date.astimezone(timezone(timedelta(hours=8))).strftime(
                "%Y-%m-%d %H:%M:%S")
            channel['megagroup'] = chat_full.chats[0].megagroup

            if not isinstance(chat_full.full_chat.chat_photo, (types.PhotoEmpty, types.PhotoSizeEmpty)):
                head_img = Media.new(media_object=chat_full.full_chat, thumb=0,
                                     group=Const.img_profiles, client=client)
                channel['headImgUrl'] = await media_processor.add_task(head_img)
        except Exception as e:
            Logger.error("An error occurred while parse channel entity, message: %s", e)
        return channel

    # 解析附近的群原始信息
    @staticmethod
    async def parse_nearby_group(updates: types.Updates, client: TeleClient, media_processor: MediaProcessor) -> list:
        channel_list = []
        if updates is None:
            return channel_list
        try:
            for channel in updates.chats:
                group = dict(
                    roomName=None,           # 群名称
                    roomCode=None,           # 群ID，带-100的房间Id
                    roomAlias=None,          # 群username
                    headImgUrl=None,         # 群头像链接
                    userCount=None,          # 群成员数
                    createTime=None,         # 群创建时间
                    channelId=None,          # 群ID
                    accessHash=None,         # 用于查找群的access_hash
                    groupDistance=None,      # 附近的群距离
                    address=None,            # 位置信息
                )
                group['roomName'] = channel.title
                group['roomCode'] = client.get_full_id(channel)
                group['roomAlias'] = channel.username
                group['userCount'] = channel.participants_count
                group['createTime'] = channel.date.astimezone(timezone(timedelta(hours=8))).strftime(
                    "%Y-%m-%d %H:%M:%S")
                group['channelId'] = channel.id
                group['accessHash'] = channel.access_hash

                if not isinstance(channel.photo, (types.PhotoEmpty, types.PhotoSizeEmpty)):
                    head_img = Media.new(media_object=channel, thumb=0,
                                         group=Const.img_profiles, client=client)
                    group['headImgUrl'] = await media_processor.add_task(head_img)
                channel_list.append(group)

                # 根据channelId和accessHash来获取该群实体，通过群实体拿到位置信息
                channel_info = await client.get_channel_by_id(channel.id, channel.access_hash)
                address = channel_info.full_chat.location.address
                group['address'] = address

        except Exception as e:
            Logger.error("An error occurred while parse channel entity, message: %s", e)
        return channel_list

    @staticmethod
    async def parse_nearyby_group_distance(updates: types.Updates, channel_list: list) -> list:
        try:
            # 首先获取到附近有多少个群
            n = len(channel_list)
            # 初始化一个值，用来记录要把距离赋值给哪个群
            i = 0
            # 由于距离的原始数据在列表的最后n个，并且群信息和群距离的在各自的列表中顺序一一对应，因此可以循环赋值
            for channel in updates.updates[0].peers[-n:]:
                channel_list[i]['groupDistance'] = str(channel.distance)+'m'
                i += 1

        except Exception as e:
            Logger.error("An error occurred while parse channel entity, message: %s", e)
        return channel_list

    @staticmethod
    async def parse_user(user_entity: types.User, client: TeleClient, media_processor: MediaProcessor) -> dict:
        user = dict(
            personCode=None,    # ID
            personName=None,    # 名称
            personAlias=None,   # username
            headImgUrl=None,    # 头像
            phone=None          # 电话号码
        )

        if user_entity is None:
            return user
        try:
            user_name = ""
            if user_entity.first_name is not None:
                user_name += str(user_entity.first_name)
            if user_entity.last_name is not None:
                user_name += (" " + str(user_entity.last_name))

            # if user_entity.photo is not None:
            #     head_img = Media.new(media_object=user_entity, thumb=0, group=Const.img_profiles, client=client)
            #     user['headImgUrl'] = await media_processor.add_task(head_img)

            user['personCode'] = client.get_full_id(user_entity)
            user['personName'] = user_name.strip()
            user['personAlias'] = user_entity.username
            user['phone'] = user_entity.phone
        except Exception as e:
            # print(traceback.format_exc())
            Logger.error("An error occurred while parse user entity, message: %s", e)
        return user

    @staticmethod
    async def parse_phone_user(user_entities: types.contacts.ImportedContacts, client: TeleClient, media_processor: MediaProcessor) -> list:
        user_list = []

        if user_entities is None:
            return user_list
        try:
            for u in user_entities.users:
                user = dict(
                    personCode=None,  # ID
                    personAlias=None,  # username
                    headImgUrl=None,  # 头像
                    phone=None  # 电话号码
                )

                if u.photo is not None:
                    head_img = Media.new(media_object=u, thumb=0, group=Const.img_profiles, client=client)
                    user['headImgUrl'] = await media_processor.add_task(head_img)

                user['personCode'] = u.id
                user['personAlias'] = u.username
                user['phone'] = u.phone
                user_list.append(user)

        except Exception as e:
            Logger.error("An error occurred while parse user entity, message: %s", e)
        return user_list

    @staticmethod
    async def parse_personal_user(user_entity: types.UserFull, client: TeleClient, media_processor: MediaProcessor) -> dict:
        user = dict(
            personCode=None,    # ID
            personName=None,    # 名称
            personAlias=None,   # username
            headImgUrl=None,    # 头像
            phone=None          # 电话号码
        )
        if user_entity is None:
            return user
        try:
            user_name = ''
            if user_entity.user.first_name is not None:
                user_name += str(user_entity.user.first_name)
            if user_entity.user.last_name is not None:
                user_name += " " + str(user_entity.user.last_name)

            user['personCode'] = user_entity.user.id
            user['personName'] = user_name.strip()
            user['personAlias'] = user_entity.user.username
            user['phone'] = user_entity.user.phone

        except Exception as e:
            Logger.error("An error occurred while parse user entity, message: %s", e)
        return user

    @staticmethod
    async def parse_message(message_entity: typing.Union[MessageService, Message], client: TeleClient,
                            media_processor: MediaProcessor) -> dict:
        action_pin_message = 5
        action_change_head_photo = 4
        action_change_title = 3
        action_to_channel = 2
        action_add_users = 1
        action_del_user = 0

        message = dict(
            # assetId=None,                         # message资产ID，旧版本由数据接收端计算，新版本为了和Media绑定放到这里计算
            originalId=None,                        # telegram消息原始ID
            personCode=None,                        # 发布人ID，MessageService时表示动作发起人的ID
            roomCode=None,                          # 群ID（带-100）
            channel_id=None,                        # 群组id
            channel_name=None,                      # 群组名称
            view_count=None,                        # 浏览数
            replyToId=None,                         # 回复的消息ID
            createDate=None,                        # 发布日期
            content=None,                           # 发布内容
            shareTitle=None,                        # 分享连接标题
            shareContent=None,                      # 分享连接摘要
            shareLocation=None,                     # 分享连接地址
            sharePicUrl=None,                       # 分享连接图片
            picUrl=None,                            # 发布图片地址
            mediaPicUrl=None,                       # 发布视频封面地址
            mediaUrl=None,                          # 发布视频地址
            fileUrl=None,                           # 发布文件地址
            fileName=None,                          # 发布文件名称
            mediaSize=None,                         # 媒体文件大小
            actionType=None,                        # 仅MessageService时不为空，表示消息动作类型
            actionEntities=None,                    # 仅MessageService时不为空，表示消息影响对象
            actionFrom=None,                        # 仅MessageService时不为空，表示被动消息的执行人
            channel_username=None,                  # 消息所在群组的username
            content_type=None,                      # 消息类型
            forward_user_id=None,                   # 转发频道消息中用户的id
            forward_create_date=None,               # 抓发频道消息的消息发布时间
            forward_count=None,                     # 转发数
            forward_channel_id=None,                # 转发频道消息中频道的id(新)
            forward_channel_name=None,              # 转发频道消息中频道的name(新)
            forwardChannelName=None,                # 转发频道消息中频道的name
            forwardChannelId=None,                  # 转发频道消息中频道的id
            forwardChannelMessageId=None,           # 转发频道消息在该频道的消息id
            forwardGroupMessageUserId=None,         # 转发群消息中发送该条消息用户的id
            forwardGroupMessageUserName=None,       # 转发群消息中发送该条消息用户的username
        )
        if message_entity is None:
            return message
        try:
            # asset_id = Hash.mur(str(message_entity.id), message_entity.from_id)

            # 获取消息发送目的地
            message['roomCode'] = client.get_full_id(message_entity.to_id)
            message['channel_id'] = message_entity.chat.id
            message['channel_name'] = message_entity.chat.title
            message['view_count'] = message_entity.views
            message['channel_username'] = message_entity.chat.username

            # 获取消息基本信息
            message['originalId'] = message_entity.id                                          # 原始ID
            try:
                message['personCode'] = message_entity.from_id.user_id                             # 发送人ID
            except:
                message['personCode'] = message_entity.from_id
            # message['assetId'] = asset_id
            message['createDate'] = message_entity.date.astimezone(timezone(timedelta(hours=8))).strftime(
                "%Y-%m-%d %H:%M:%S")                                                          # 发送日期

            if isinstance(message_entity, Message):
                message['replyToId'] = message_entity.reply_to_msg_id                          # 回复的消息的原始id
                message['content'] = message_entity.message                                     # 消息正文

                # 判断是否为转发消息
                if message_entity.fwd_from is not None:
                    # 转发的消息来自群组
                    if isinstance(message_entity.fwd_from.from_id, types.PeerChannel):
                        # 转发频道消息中频道的id
                        message['forwardChannelId'] = int('-100' + str(message_entity.fwd_from.from_id.channel_id))
                        # 转发频道消息在该频道的消息id
                        message['forwardChannelMessageId'] = message_entity.fwd_from.channel_post

                        # 新频道id和name
                        message['forward_channel_id'] = message_entity.forward.chat.id
                        message['forward_channel_name'] = message_entity.forward.chat.title

                    # 转发消息来自用户
                    if isinstance(message_entity.fwd_from.from_id, types.PeerUser):
                        # 转发群消息中发送该条消息用户的id
                        message['forwardGroupMessageUserId'] = message_entity.fwd_from.from_id.user_id
                        # 转发群消息中发送该条消息用户的username
                        message['forwardGroupMessageUserName'] = message_entity.fwd_from.from_name

                    message['forward_user_id'] = message_entity.from_id.user_id
                    message['forward_create_date'] = message_entity.forward.date.astimezone(timezone(timedelta(hours=8))).strftime(
                "%Y-%m-%d %H:%M:%S")
                    message['forward_count'] = message_entity.forwards

                message_media = message_entity.media
                if message_media:
                    group = message['roomCode']
                    if isinstance(message_media, types.MessageMediaWebPage):
                        message['content_type'] = 6
                        webpage = message_media.webpage
                        if not isinstance(webpage, (types.WebPageEmpty, types.WebPagePending)):
                            message['shareTitle'] = webpage.title           # 网站标题
                            message['shareContent'] = webpage.description   # 网站摘要
                            message['shareLocation'] = webpage.url          # 网址
                            if webpage.photo:
                                media = Media.new(media_object=webpage.photo,
                                                  group=group, client=client)
                                # media.url_hash = asset_id
                                message['sharePicUrl'] = media
                    elif isinstance(message_media, (types.MessageMediaPhoto, types.Photo)):
                        message['content_type'] = 2
                        message['picUrl'] = Media.new(media_object=message_media,
                                                      group=group, client=client)
                    elif isinstance(message_media, (types.MessageMediaDocument, types.Document)):
                        media = Media.new(media_object=message_media,
                                          group=group, client=client, thumb=None)
                        if media.type == Media.TYPE_VIDEO:
                            message['content_type'] = 3
                            message['mediaUrl'] = media
                            message['mediaSize'] = media.size
                            message['mediaPicUrl'] = Media.new(media_object=message_media, group=group, client=client,
                                                               thumb=0, media_type=Media.TYPE_PHOTO)
                        else:
                            message['fileName'] = media.name
                            message['fileUrl'] = media

            elif isinstance(message_entity, MessageService):
                action = message_entity.action

                # 邀请他人或他人主动进入群组
                if isinstance(action, types.MessageActionChatAddUser):
                    # 消息操作类型（有人进群或者有人被拉进群，值：0）
                    message['actionType'] = action_add_users
                    # 进群的人
                    message['actionEntities'] = action.users
                    # 邀请人
                    message['actionFrom'] = message_entity.from_id

                # 踢出或主动退出群组
                elif isinstance(action, types.MessageActionChatDeleteUser):
                    # 消息操作类型（有人退出群聊或者有人被踢出群聊，值：1）
                    message['actionType'] = action_del_user
                    # 退群人
                    message['actionEntities'] = [action.user_id]
                    # 操作人
                    message['actionFrom'] = message_entity.from_id

                # 新建聊天群
                elif isinstance(action, types.MessageActionChannelMigrateFrom):
                    # 消息操作类型（新建聊天群，值：2）
                    message['actionType'] = action_to_channel
                    # 返回该群的title
                    message['actionEntities'] = [action.title]

                # 新建频道
                elif isinstance(action, types.MessageActionChannelCreate):
                    # 消息操作类型（新建频道，值：2）
                    message['actionType'] = action_to_channel
                    # 返回该频道的title
                    message['actionEntities'] = [action.title]

                # 群组改名
                elif isinstance(action, types.MessageActionChatEditTitle):
                    # 消息操作类型（更改群名，值：3）
                    message['actionType'] = action_change_title
                    # 新的群名
                    message['actionEntities'] = [action.title]
                    # 操作人id
                    message['actionFrom'] = message_entity.from_id

                # 群组改头像
                elif isinstance(action, types.MessageActionChatEditPhoto):
                    # 消息操作类型（改群头像，值：4）
                    message['actionType'] = action_change_head_photo
                    # 操作人id
                    message['actionFrom'] = message_entity.from_id

                # 置顶的群消息
                elif isinstance(action, types.MessageActionPinMessage):
                    # 消息操作类型（置顶群消息，值：5）
                    message['actionType'] = action_pin_message
                    # 置顶的消息id
                    message['actionEntities'] = [message_entity.reply_to_msg_id]
                    # 操作人id
                    message['actionFrom'] = message_entity.from_id

            # 将媒体对象放入媒体处理器工作队列
            for key in Parser.MEDIA_KEYS:
                if key in message.keys():
                    if isinstance(message[key], Media):
                        # message[key].url_hash = asset_id
                        message[key] = await media_processor.add_task(message[key])

        except Exception as e:
            Logger.error(
                "An error occurred while parse message entity, message: %s", e)

        return message

    @staticmethod
    async def parse_ququn_bot_message(message_entity: typing.Union[MessageService, Message], client: TeleClient,
                                      media_processor: MediaProcessor) -> dict:
        message = dict(
            originalID=None,                # telegram消息原始ID
            personCode=None,                # 发布人ID，MessageService时表示动作发起人ID
            roomCode=None,                  # 群ID
            replayToId=None,                # 回复的消息ID
            createDate=None,                # 发布日期
            content=None,                   # 发布内容
            channel_info_link=None,         # 群消息及群链接
        )
        if message_entity is None:
            return message
        try:
            # 获取消息发送目的地
            message['roomCode'] = client.get_full_id(message_entity.to_id)

            # 获取消息基本信息
            message['originalId'] = message_entity.id
            message['personCode'] = message_entity.from_id
            message['createDate'] = message_entity.date.astimezone(timezone(timedelta(hours=8))).strftime(
                '%Y-%m-%d %H:%M:%S')

            if isinstance(message_entity, Message):
                message['replyToId'] = message_entity.reply_to_msg_id   # 回复的消息的原始id
                message['content'] = message_entity.message             # 消息正文

                # res = MessageEntityTextUrl.to_dict(message_entity.entities[2])['url']
                # print(res)
                # message['grouplink'] = MessageEntityTextUrl.serialize_bytes(message_entity.entities)     # 消息链接

                # message['grouplink'] = [MessageEntityTextUrl.to_dict(message_entity.entities[i])['url']
                #                         for i in range(1, len(message_entity.entities))]

                # res = message_entity.reply_markup.rows[0].buttons[1].data
                # print(res)

                channel_info = message_entity.message
                parser_channel_info = re.findall(r'\d+\.(.*\w)', channel_info)

                for i in range(2, len(parser_channel_info)+1):
                    channel_url = MessageEntityTextUrl.to_dict(message_entity.entities[i])['url']
                    parser_channel_info[i-2] = parser_channel_info[i-2]+':'+channel_url

                message['channel_info_link'] = parser_channel_info

        except Exception as e:
            Logger.error(
                'An error occurred while parse message entity(%s), message: %s', message_entity, e)

        return message

    @staticmethod
    async def parse_hao1234bot_message(message_entity: typing.Union[MessageService, Message], client: TeleClient,
                                       media_processor: MediaProcessor) -> dict:
        message = dict(
            originalID=None,            # telegram消息原始ID
            personCode=None,            # 发布人ID，MessageService时表示动作发起人ID
            roomCode=None,              # 群ID
            replayToId=None,            # 回复的消息ID
            createDate=None,            # 发布日期
            content=None,               # 发布内容
            channel_info_link=None      # 群消息及群链接
        )
        if message_entity is None:
            return message

        # try:
        # 获取消息发送目的地
        message['roomCode'] = client.get_full_id(message_entity.to_id)

        # 获取消息基本信息
        message['originalId'] = message_entity.id
        message['personCode'] = message_entity.from_id
        message['createDate'] = message_entity.date.astimezone(timezone(timedelta(hours=8))).strftime(
            '%Y-%m-%d %H:%M:%S')

        if isinstance(message_entity, Message):
            # 回复的消息的原始id
            message['replyToId'] = message_entity.reply_to_msg_id
            # 消息正文
            message['content'] = message_entity.message

            channel_info = message_entity.message
            parser_channel_info = re.findall(r'\d+\.(.*\w)', channel_info)

            for i in range(1, len(parser_channel_info)+1):
                channel_url = MessageEntityTextUrl.to_dict(message_entity.entities[i])['url']
                parser_channel_info[i-1] = parser_channel_info[i-1]+':'+channel_url

            message['channel_info_link'] = parser_channel_info

        # except Exception as e:
        #     Logger.error(
        #         'An error occurred while parse message entity(%s), message: %s', message_entity, e)

        return message

    @staticmethod
    def parse_dialogs(dialogs: list, client: TeleClient) -> list:
        result = list()
        for dialog in dialogs:
            try:
                username = dialog.entity.username if dialog.entity else None
            except AttributeError:
                Logger.info(type(dialog.entity))
                username = None
            result.append({
                "channel_id": client.get_full_id(dialog.entity),
                "name": dialog.name,
                "username": username,
            })
        return result
