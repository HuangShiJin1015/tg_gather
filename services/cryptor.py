# -*- coding:utf-8 -*-
# @Author: HuangShiJin
# @Date: 2023年5月26日15:36:42

from binascii import a2b_hex, b2a_hex

from Crypto.Cipher import AES


class AesCryptor(object):

    @staticmethod
    def encrypt(text_bytes, key=None, iv=None, bsize=16) -> str:
        """
        使用提供的密钥`key`和偏移向量`iv`对提供的byte文本进行AES/CBC加密

        :param text_bytes: byte文本
        :param key: 加密密钥, 默认为 None
        :param iv: 偏移向量, 默认为 None
        :param bsize: 块长度, 默认为 16
        :return: 加密后的16进制加密字符串
        """
        if type(key).__name__ == "str":
            key = key.encode("utf8")
        if type(iv).__name__ == "str":
            iv = iv.encode("utf8")
        source_len = len(text_bytes)
        add = (bsize - (source_len % bsize)) % bsize
        text_bytes += b"\0" * add
        encrypted_txt = AES.new(key=key, iv=iv, mode=AES.MODE_CBC).encrypt(text_bytes)
        encrypted_hex = b2a_hex(encrypted_txt).decode("utf8")
        return encrypted_hex

    @staticmethod
    def decrypt(hex_string, key=None, iv=None) -> bytes:
        """
        使用密钥`key`和偏移向量`iv`对提供的16进制加密字符串进行解密，获取原始byte文本

        :param hex_string: 16进制加密字符串
        :param key: 加密密钥, 默认为 None
        :param iv: 偏移向量, 默认为 None
        :return: byte原始文本
        """
        if type(key).__name__ == "str":
            key = key.encode("utf8")
        if type(iv).__name__ == "str":
            iv = iv.encode("utf8")
        encrypted_bytes = a2b_hex(hex_string)
        source_bytes = AES.new(key=key, iv=iv, mode=AES.MODE_CBC).decrypt(encrypted_bytes)
        return source_bytes
