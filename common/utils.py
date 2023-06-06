# -*- coding:utf-8 -*-
# @Author: KeyH
# @Date: 2023年6月5日15:58:51

import datetime
import hashlib
import random

import mmh3


class Hash(object):

    @staticmethod
    def _get_string(prefix: str, suffix: str, rand: bool) -> str:
        if rand:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " CST"
            rnd = random.randint(1000000, 9999999)
            string = "{}-{}-{}-{}".format(prefix, now, rnd, suffix)
        else:
            string = "{}-{}".format(prefix, suffix)
        return string

    @staticmethod
    def sha(prefix: str = "sha1", suffix: str = "hash", rand: bool = True) -> str:
        """
        SHA1 Hash算法

        :param prefix: 前缀，默认值 `"sha1"`
        :param suffix: 后缀，默认值 `"hash"`
        :param rand: 是否启用随机，启用随机后，会用再前缀和后缀间接入时间戳和随机数，默认值 `True`
        :return: SHA1 Hash结果
        """
        sha1 = hashlib.sha1()
        string = Hash._get_string(prefix, suffix, rand)
        sha1.update(string.encode('utf-8'))
        hash_code = sha1.hexdigest()
        return hash_code

    @staticmethod
    def mur(prefix: str = "murmur", suffix: str = "hash", rand: bool = True) -> str:
        """
        MurMurHash3 Hash算法

        :param prefix: 前缀，默认值 `"murmur"`
        :param suffix: 后缀，默认值 `"hash"`
        :param rand: 是否启用随机，默认值 `True`
        :return: MurMurHash3 Hash结果
        """
        string = Hash._get_string(prefix, suffix, rand)
        return str(mmh3.hash64(string)[0])
