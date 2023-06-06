# -*- coding:utf-8 -*-
# @Author: KeyH
# @Date: 2023年6月5日16:02:52

import asyncio
import time
import urllib.parse
import os

from tornado import gen
from tornado.httpclient import AsyncHTTPClient
from tornado.queues import Queue as AsyncQueue

from common.const import Const
from common.logger import Logger
from models import String
from models.media import Media

request_header = {
    "Content-type": "application/x-www-form-urlencoded",
    "Connection": "keep-alive"
}


class MediaProcessor(object):
    def __init__(self, server: str = None, chunk_size: int = 65536, size_limit: int = 40, retry: int = 5,
                 concurrency: int = 1):
        """
        媒体文件处理器

        :param server: 媒体文件存储服务器，默认值 `None`
        :param chunk_size: 上传分片大小（Byte），默认值 `65536`
        :param size_limit: 上传媒体文件大小限制，默认值 `40`
        :param retry: 重试次数，默认值 `5`
        :param concurrency: 下载并发数，默认值 `1`
        """
        self.__server = server
        self.__chunk_size = chunk_size
        self.__size_limit = size_limit
        self.__retry = retry if retry is not None else 5
        self.__concurrency = concurrency

        self.__slow_download_queue = AsyncQueue()   # 慢速下载队列，用于下载大文件
        self.__fast_download_queue = AsyncQueue()   # 快速下载队列，用于下载小文件
        self.__upload_queue = AsyncQueue()          # 上传任务队列
        self.__http = AsyncHTTPClient()             # 异步HTTP客户端

    async def start(self):
        Logger.info("Starting mediaprocessor...")
        workers = [self.downloader(self.__fast_download_queue) for _ in range(self.__concurrency)]
        workers.append(self.downloader(self.__slow_download_queue))
        workers.append(self.uploader())
        await gen.multi(workers)

    async def add_task(self, media: Media = None) -> String:
        """
        添加下载任务

        :param media: 媒体对象，默认值 `None`
        :return: 媒体对象URL
        """
        if media is None:
            return None
        try:
            # 文件大小小于5M或者类型为图片时，任务放入快速下载队列，否则放入慢速下载队列。
            # 防止因为大文件下载过慢影响小文件的响应速度
            # if media.type <= Media.TYPE_PHOTO or (media.size and media.size < 5 * 1024 * 1024):

            # 改为只下图片
            if media.type <= Media.TYPE_PHOTO:
                await self.__fast_download_queue.put(media)
                Logger.info("Add a fast media download task(%s), %s tasks waiting...", media, self.__fast_download_queue.qsize())
                # 此处用于判断任务队列中剩余的任务数，如果任务数超过500，则会调用重启该进程脚本将程序重启
                if self.__fast_download_queue.qsize() > 10000:
                    Logger.info("Too many tasks backlogs, restart the process!")
                    os.system('python /home/telegram-client/services/restart_procedure.py')
            else:
                Logger.info('媒体文件不是图片，不下载------文件类型为{}'.format(media))
                return None

            # else:
            #     await self.__slow_download_queue.put(media)
            #     Logger.info("Add a slow media download task(%s), %s tasks waiting...",
            #                 media, self.__slow_download_queue.qsize())
            return media.group + "/" + media.url
        except Exception as err:
            Logger.error("An error occurred while add a media download task, message: %s", err)

    async def downloader(self, download_queue: AsyncQueue):
        """
        下载器

        :param download_queue: 待下载任务队列
        """
        Logger.info("Download coroutine start...")

        # 异步迭代，当队列中没有任务的时候，协程会让步，当有任务的时候，协程会被唤醒，类似于多线程的阻塞队列`BlockingQueue`
        async for media in download_queue:
            Logger.info(
                "Prepare to download media(%s), left: %s...", media, download_queue.qsize())
            # 必须是合法的媒体对象才能作为下载器的任务
            if not isinstance(media, Media):
                Logger.warning("Illegal download task(%s), will skip.", media)
                download_queue.task_done()
                continue
            try:
                size_limit = Const.mp_download_size_limit
                if size_limit > 0 and media.size:
                    if media.size > size_limit * 1024 * 1024:
                        Logger.info("Donwload task(%s) is too large, will skip.", media)
                        continue
                # 下载媒体文件并计时
                _time_start = time.time()
                await media.download()

                # DEBUG模式下，将媒体文件写入本地文件系统方便检查正确性
                if Const.server_debug:
                    open(Const.project_root + "/test_files/" + media.url, "wb+").write(media.bytes)
                    Logger.debug("Media file was saved at __root__/test_files/%s", media.url)
                _time_end = time.time()

                # 添加上传任务到上传器队列
                if media.bytes and media.size <= Const.mp_download_size_limit:
                    await self.__upload_queue.put(media)
                else:
                    Logger.warning("Download task(%s) may not correct, media object: %s",
                                   media, media.media_object.stringify())

                _time = round(_time_end - _time_start, 2)
                Logger.info("Download task(%s) finished, total cost %s seconds.", media, _time)
            except Exception as e:
                Logger.error("An error occurred while process a download task(%s), message:%s", media, e)
            finally:
                # 异步队列必须调用此方法，以通知任务完成
                download_queue.task_done()

    async def uploader(self):
        """
        上传器
        """
        Logger.info("Upload coroutine start...")
        async for media in self.__upload_queue:
            Logger.info("Prepare to upload media(%s), left: %s", media, self.__upload_queue.qsize())

            data = {
                "content": None,
                "fileName": media.url,
                "mediaType": media.upload_type,
                "process": None,
                "groupId": media.group,
                "project": "telegram"
            }

            try:
                process = 0
                is_success = False
                for chunk in self._chunks(media):
                    data["content"] = chunk
                    data["process"] = process
                    is_success = await self._request_server(urllib.parse.urlencode(data))
                    if is_success:
                        Logger.debug("Upload media(size:%s) chunk(process:%s, size:%s) success!",
                                    len(media.bytes), process, len(chunk))
                        process += 1
                    else:
                        Logger.debug("Upload media(size:%s) chunk(process:%s, size:%s) failed.",
                                    len(media.bytes), process, len(chunk))
                        break
                if is_success:
                    Logger.info("Upload media(%s) complete!", media)
                else:
                    Logger.error("Upload media(%s) failed.", media)
                del media
            except Exception as e:
                Logger.error("图片上传失败(%s), message:%s", media, e)
            finally:
                self.__upload_queue.task_done()

    async def _request_server(self, data: dict) -> bool:
        """
        向存储服务器发送HTTP请求

        :param data: 数据
        :return: [description]
        """
        retry = self.__retry
        is_success = False
        while retry > 0:
            try:
                await self.__http.fetch(self.__server, method="POST", body=data, headers=request_header)
                retry = 0
                is_success = True
            except Exception as e:
                Logger.error(
                    "An error occurred while uploading data, message: %s, left retry %s times.", e, retry)
                retry -= 1
                await asyncio.sleep(1)
        return is_success

    def _chunks(self, media: Media) -> str:
        """
        数据分片

        :param media: [description]
        :return: [description]
        :yield: [description]
        """
        data = media.bytes
        ck_count = int(len(data) / self.__chunk_size)
        ck_count = ck_count + 1 if len(data) % self.__chunk_size != 0 else ck_count

        Logger.debug("Slice data(size: %s) to %s shards.", len(data), ck_count)

        for i in range(ck_count):
            start = i * self.__chunk_size
            end = (i + 1) * self.__chunk_size
            chunk = data[start: end]
            yield chunk.hex()   # 重要，一定要将bytes转换为16进制字符串再发送。HTTP是基于字符串的协议，不是二进制协议
