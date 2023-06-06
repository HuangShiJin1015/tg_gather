# -*- coding:utf-8 -*-
# @Author: KeyH
# @Date: 2023年6月5日16:09:11

import unittest

from services import AesCryptor


class ApiTest(unittest.TestCase):
    def test_decrypt(self) -> str:
        body = "1075e6c9f60bc04667a876f3a0413f10"
        key = "0b836e305ec2e5bf"
        iv = "6682632543888186"
        r = AesCryptor.decrypt(body, key, iv).strip(b"\0").decode()
        print(r)
