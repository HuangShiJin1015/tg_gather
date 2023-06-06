# -*- coding:utf-8 -*-
# @Author: KeyH
# @Date: 2023年6月5日16:01:25

import os
import typing

from telethon.tl import types

from common.utils import Hash
from models import Integer
from models.teleclient import TeleClient

Entity = (types.User, types.Chat, types.Channel, types.ChatFull, types.UserFull, types.ChannelFull)
MediaObject = typing.Union[
    types.Photo, types.PhotoSize, types.MessageMediaPhoto, types.Document, types.MessageMediaDocument,
    types.Message, types.ChatFull, types.User
]

MediaPhoto = (types.Photo, types.PhotoSize, types.MessageMediaPhoto)
MediaDocument = (types.Document, types.MessageMediaDocument)


class Media:
    TYPE_PROFILE = 0
    TYPE_PHOTO = 1
    TYPE_VIDEO = 2
    TYPE_FILE = 3

    def __init__(self, media_object: MediaObject, thumb: int, media_type: int, name: str, ext: str, size: int,
                 group: str, client: TeleClient):
        """
        媒体文件下载任务对象, 封装了要下载的媒体文件的信息

        :param media_object: 媒体类所对应的Telegram内部类对象,该对象由Telegram接口提供
        :param thumb: 要下载的媒体文件的尺寸, -1 表示最大尺寸, 0 表示最小尺寸
        :param media_type: 媒体文件类型, 分为:Profile-头像; Photo-图片; Video-视频; File-文件
        :param name: 媒体文件文件名称
        :param ext: 媒体文件扩展名
        :param size: 媒体文件大小，单位Byte
        :param group: 媒体文件所在分组, 消息媒体通常为群ID, 头像为 profiles
        :param client: 获取此媒体文件对象的客户端,Telegram下载文件时要求客户端对应进行Hash校验
        """
        self.__media_object = media_object
        self.__thumb = thumb
        self.__name = name
        self.__ext = ext
        self.__type = media_type
        self.__group = group
        self.__size = size
        self.__client = client

        # 自动赋值的属性
        prefix = type(media_object).__name__ + str(self.__type)
        self.__url_hash = Hash.sha(prefix, "media_url")             # URL哈希值
        self.__iv = Hash.sha(prefix, "aes_encrypt_ivparam")[0:16]   # AES/CBC加密偏移向量
        self.__bytes = None                                         # 媒体文件字节流

    @classmethod
    def new(cls, media_object: MediaObject = None, thumb: Integer = -1, media_type: int = None, group: str = "default",
            client: TeleClient = None):
        """
        创建Media对象, 使用中不直接使用Media的__init__方法创建Media对象,而使用此方式静态的创建来自动配置某些属性
        因为某些属性是需要通过方法来计算得出

        :param media_object: 媒体类所对应的Telegram内部类对象，由Telegram接口提供, 默认为 None
        :param thumb: 要下载的媒体文件尺寸，-1表示最大尺寸，0表示最小尺寸, 默认为 -1
        :param media_type: 媒体文件类型，None表示自动检测类型, 默认为 None
        :param group: 媒体文件所在分组，消息媒体为消息对应的群组，头像为profiles, 默认为 "default"
        :param client: TeleClient客户端对象，Telegram为媒体文件对象绑定了客户端的Hash值，需要对应客户端才能下载, 默认为 None
        :return: Media实例
        """
        ext = ""        # 媒体文件拓展名
        name = None     # 媒体文件名
        size = None     # 媒体文件大小

        # 解析Document类型
        if isinstance(media_object, MediaDocument):
            name = Media.get_document_name(media_object)
            if isinstance(media_object, types.MessageMediaDocument):
                size = media_object.document.size
            else:
                size = media_object.size
            _, ext = os.path.splitext(name)

        # 如果未强制规定类型, 则自动设置媒体文件类型
        if media_type is None:
            # 如果传入的是实体对象，表明要下载的是实体的头像（如用户头像、群头像等）
            if isinstance(media_object, Entity):
                media_type = Media.TYPE_PROFILE
            # 处理图片
            elif isinstance(media_object, MediaPhoto):
                media_type = Media.TYPE_PHOTO
            else:
                # 处理视频
                if ext == ".mp4":
                    media_type = Media.TYPE_VIDEO
                # 这里一边是表情图片
                elif ext == ".jpg":
                    media_type = Media.TYPE_PHOTO
                # 处理文件
                else:
                    media_type = Media.TYPE_FILE

        # 将图片后缀统一为 .jpg
        if media_type <= Media.TYPE_PHOTO:
            ext = ".jpg"

        return cls(media_object=media_object, thumb=thumb, media_type=media_type, name=name, ext=ext, size=size,
                   group=group, client=client)

    async def download(self) -> None:
        """
        异步媒体文件数据下载
        """
        if self.type == Media.TYPE_PROFILE:
            # 下载头像
            self.bytes = await self.client.download_profile(self.media_object)
        else:
            # 下载消息文件
            self.bytes = await self.client.download_media(self.media_object, thumb=self.thumb)
        # 下载成功后，更新媒体对象的size信息
        if self.bytes:
            self.__size = len(self.bytes)

    @property
    def media_object(self):
        return self.__media_object

    @property
    def thumb(self) -> Integer:
        return self.__thumb

    @thumb.setter
    def thumb(self, thumb: Integer):
        self.__thumb = thumb

    @property
    def group(self) -> str:
        return str(self.__group)

    @group.setter
    def group(self, group: typing.Union[int, str]):
        self.__group = str(group)

    @property
    def bytes(self) -> bytes:
        return self.__bytes

    @bytes.setter
    def bytes(self, media_bytes: bytes):
        self.__bytes = media_bytes

    @property
    def iv(self) -> str:
        return self.__iv

    @property
    def client(self) -> TeleClient:
        return self.__client

    @client.setter
    def client(self, client: TeleClient):
        self.__client = client

    @property
    def name(self) -> str:
        return self.__name

    @property
    def size(self):
        return self.__size

    @property
    def type(self) -> int:
        return self.__type

    @type.setter
    def type(self, mt: int):
        self.__type = mt

    @property
    def upload_type(self) -> int:
        if self.type <= Media.TYPE_PHOTO:
            return 0
        else:
            return self.type - 1

    @property
    def url(self) -> str:
        return self.__url_hash + self.__ext

    @property
    def url_hash(self) -> str:
        return self.__url_hash

    @url_hash.setter
    def url_hash(self, url_hash: str):
        self.__url_hash = url_hash

    @staticmethod
    def get_document_name(document: types.Document) -> str:
        name = None
        if isinstance(document, types.MessageMediaDocument):
            document = document.document
        attributes = document.attributes
        for attr in attributes:
            if isinstance(attr, types.DocumentAttributeFilename):
                name = attr.file_name
            elif isinstance(attr, types.DocumentAttributeAudio):
                mime = document.mime_type
                ext = ".mp3"
                if mime:
                    ext = "." + mime.split("/")[1]
                if attr.performer and attr.title:
                    name = "{}-{}".format(attr.performer, attr.title)
                elif attr.performer:
                    name = attr.performer
                elif attr.title:
                    name = attr.title
                else:
                    name = Hash.sha("audio", "document")
                name += ext
            elif isinstance(attr, types.DocumentAttributeVideo):
                name = Hash.sha("video", "document") + ".mp4"
        return name

    def __str__(self) -> str:
        return "Media(url={}, media_object={}, type={}, size={}, name={}, group={}, client={})".format(
            self.url, type(self.__media_object).__name__, self.type, self.size, self.name, self.group,
            self.client.phone)
