# -*- coding:utf-8 -*-
# @Author: KeyH
# @Date: 2023年6月5日16:11:31


import json
import unittest

import requests

from common.const import Const
from services.cryptor import AesCryptor


class HandlersTest(unittest.TestCase):
    def test_messages(self):
        username = "acgcn"
        data = dict(type="messages", channel=username, limit=5, offset_id=24, min_id=21)
        json_data = self._request(data)
        self._decrypto(json_data)

    def test_channel(self):
        username = "acgcn"
        data = dict(type="channel", channel=username)
        json_data = self._request(data)
        self._decrypto(json_data)

    def test_users(self):
        username = "acgcn"
        data = dict(type="users", channel=username)
        json_data = self._request(data)
        self._decrypto(json_data)

    def test_join(self):
        # TODO
        pass

    def test_leave(self):
        # TODO
        pass

    def _request(self, data: dict) -> str:
        url = "http://localhost:8081/teleclient"
        response = requests.post(url, json=data, headers={"Content-Type": "application/json;charset=UTF-8"})
        return response.json()

    def _decrypto(self, data: dict):
        data = AesCryptor.decrypt(data.get("body"), Const.crypto_key, data.get("iv")).decode("utf8")
        print(json.loads(data.strip(b'\x00'.decode())))
