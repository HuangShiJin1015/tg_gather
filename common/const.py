# -*- coding:utf-8 -*-
# @Author: KeyH
# @Date: 2023年6月5日15:53:10


import os
import typing

from socks import SOCKS5


class _PropertiesReader:
    def __init__(self, path: str):
        """
        配置文件读取与解析

        :param path: 配置文件路径
        """
        file = open(path, "r", encoding="utf8", errors="ignore")
        self.__dict = dict()
        line = file.readline()
        while line:
            line = line.strip()
            if not line or line.startswith("#"):
                line = file.readline()
                continue
            key, val = line.split("=")
            key = key.strip()
            val = val.strip()
            self.__dict[key] = val
            line = file.readline()

    def get_int(self, key) -> int:
        return int(self.__dict[key])

    def get_str(self, key) -> str:
        return self.__dict[key]

    def get_list(self, key) -> list:
        return self.__dict[key].split(",")

    def get_bool(self, key) -> bool:
        if self.__dict[key] in ["true", "ok", "on", "1"]:
            return True
        return False


class _Const:
    class ConstError(TypeError):
        pass

    def __init__(self):

        self.__project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.pardir)
        self.__properties = _PropertiesReader(self.__project_root + "/config.properties")

    @property
    def project_root(self) -> str:
        return self.__project_root

    @property
    def session_folder(self) -> str:
        return self.project_root + "/sessions/"

    @property
    def crypto_key(self) -> str:
        return self.__properties.get_str("crypto_key")

    @property
    def img_profiles(self) -> str:
        return "profiles"

    @property
    def server_path(self) -> str:
        return self.__properties.get_str("server_path")

    @property
    def server_port(self) -> int:
        return self.__properties.get_int("server_port")

    @property
    def server_debug(self) -> bool:
        return self.__properties.get_bool("server_debug")

    @property
    def api_id(self) -> int:
        return self.__properties.get_int("api_id")

    @property
    def api_hash(self) -> str:
        return self.__properties.get_str("api_hash")

    @property
    def client_proxy(self) -> typing.Union[tuple, None]:
        is_on = self.__properties.get_bool("cli_use_proxy")
        if is_on:
            ip = self.__properties.get_str("cli_proxy_ip")
            port = self.__properties.get_int("cli_proxy_port")
            return SOCKS5, ip, port
        else:
            return None

    @property
    def client_phones(self) -> list:
        return self.__properties.get_list("cli_phones")

    @property
    def mp_upload_server(self) -> str:
        return self.__properties.get_str("mp_upload_server")

    @property
    def mp_upload_chunk_size(self) -> int:
        return self.__properties.get_int("mp_upload_chunk_size")

    @property
    def mp_upload_retry(self) -> int:
        return self.__properties.get_int("mp_upload_retry")

    @property
    def mp_download_size_limit(self) -> int:
        size = self.__properties.get_str("mp_download_size_limit")
        size = size.upper()
        size_num = int(size[: len(size) - 1])
        if size_num <= 0:
            return 0
        size_unit = size[len(size) - 1]
        if size_unit == "B":
            return size_num
        elif size_unit == "K":
            return size_num * 1024
        elif size_unit == "M":
            return size_num * 1024 * 1024
        elif size_unit == "G":
            return size_num * 1024 * 1024 * 1024
        else:
            return size_num * 1024

    @property
    def mp_download_concurrency(self) -> int:
        return self.__properties.get_int("mp_download_concurrency")

    @property
    def pub_url(self) -> str:
        return self.__properties.get_str("pub_url")

    @property
    def pub_msg_queue(self) -> str:
        return self.__properties.get_str("pub_msg_queue")

    @property
    def pub_usr_queue(self) -> str:
        return self.__properties.get_str("pub_usr_queue")

    @property
    def pub_concurrency(self) -> int:
        return self.__properties.get_int("pub_concurrency")

    @property
    def log_format(self) -> str:
        return self.__properties.get_str("log_format")


Const = _Const()
