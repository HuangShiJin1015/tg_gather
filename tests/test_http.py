import json
import requests
import datetime

from common.const import Const
from services.cryptor import AesCryptor

URL = 'http://localhost:8088/teleclient'


# URL = 'http://198.11.176.126:8280/teleclient'

# PHONE = '+85251617973'


def main():
    # test_get_message()
    # test_get_dialog()
    # test_get_users()
    # test_get_admins()
    # test_search()
    # test_get_channel()
    # test_get_channel_by_bot()
    # test_get_channel_by_location()
    # test_get_location_channel_user()
    # test_get_location_channel_message()
    # test_get_location_channel_info()
    # test_get_ququn_bot_messages()
    # test_get_address_book()
    test_add_contact()


def test_add_contact():
    res = requests.post(URL, json={
        "type": "add_contact",
        "phones": ['+85252671253', ]
    })
    print(res)


def test_get_address_book():
    res = requests.post(URL, json={
        "type": "address_book",
        "phone": "+85251377034"
    })
    # list_ = json.loads(_decrypto(res.json()))
    print(res)


def test_search():
    res = requests.post(URL, json={
        "type": "search",
        "gather_phone": "https://t.me/Kn1ght_Dark",

        # +85265868027, +85254947396, 85295192756, 85297101842, +85262245905, +85262253654(这6个采集号出问题)

        # "phones": ['85296859406', '85251377034', '85295192756'],

        # "phones": ['8616603828752']

        # "phones": ['85251617973', '85251110757', '8618236575876', '8618600908764', '85256215802', '85261501587',
        #            '85251171735']

        # "phones": ['85261501587', '85267460863', '85254494723', '85262245905', '85262253654']

        # "phones": ['8615042224900']

        # "phones": ['85251654091', '85252671253', '85256247034', '85256215802', '85267360276', '85267097436',
        #            '85266792352', '85259803115', '85265868027', '85254947396']

    })

    list_ = json.loads(_decrypto(res.json()))

    print(list_)
    for item in list_:
        print(item)


def test_get_channel():
    res = requests.post(URL, json={
        "type": "channel",
        "channel": 'a4papernow',
        "phone": "+85262161655"
    })
    s = _decrypto(res.json())
    list_ = json.loads(_decrypto(res.json()))
    print(list_)


def test_get_dialog():
    res = requests.post(URL, json={
        "type": "sync",
        # "phone": '+8617079600153'
        "phone": '+639568014449'
        # "phone": PHONE
    })
    print(_decrypto(res.json()))
    list_ = json.loads(_decrypto(res.json()))
    for item in list_:
        print(item)


def test_get_message():
    res = requests.post(URL, json={
        "type": "messages",
        "channel": 'a4papernow',
        "limit": 10,
        # "max_id": 0,
        # "min_id": 0,
        # "phone": "+85251617973",
    })
    data = json.loads(_decrypto(res.json()))
    print(json.dumps(data, ensure_ascii=False))
    for data in data:
        print(data)


def test_get_users():
    res = requests.post(URL, json={
        "type": "users",
        "channel": 'https://t.me/a4papernow',
        # "phone": '+85251357794'
    })
    data = json.loads(_decrypto(res.json()))
    print(json.dumps(data, ensure_ascii=False))
    for d in data:
        print(d)

def test_get_admins():
    res = requests.post(URL, json={
        "type": "admins",
        "channel": "TelethonChat",
        "phone": ""
    })
    data = json.loads(_decrypto(res.json()))
    print(json.dumps(data, ensure_ascii=False))
    for d in data:
        print(d)


def test_get_channel_by_bot():
    res = requests.post(URL, json={
        "type": "hao1234bot",
        "keyword": "新闻"
    })
    data = json.loads(_decrypto(res.json()))
    print(data)


def test_get_channel_by_location():
    res = requests.post(URL, json={
        'type': 'location_channel',
        'location': '腾讯滨海大厦',
        'lat': 22.5226305,
        'long': 113.9330568,
    })
    data = json.loads(_decrypto(res.json()))
    # json_data = json.dumps(data, ensure_ascii=False)
    # print(type(data))
    # print(type(json_data))
    # print(json_data)
    print(data)
    for i in data['roomList']:
        print(i)


def test_get_location_channel_user():
    res = requests.post(URL, json={
        'type': 'location_channel_user',
        'phone': '+85251617973',
        'channel_id': 1222208287,
        'access_hash': -3115476045399947993
    })
    data = json.loads(_decrypto(res.json()))
    print(json.dumps(data, ensure_ascii=False))
    for data in data:
        print(data)


def test_get_location_channel_message():
    res = requests.post(URL, json={
        'type': 'location_channel_messages',
        'phone': '+85251654091',
        'channel_id': 1425192136,
        'access_hash': 3562652297468182767,
        'limit': 10,
        'min_id': 0
    })
    data = json.loads(_decrypto(res.json()))
    # print(json.dumps(datas, ensure_ascii=False))
    print(data)
    for data in data:
        print(data)


def test_get_location_channel_info():
    res = requests.post(URL, json={
        'type': 'location_channel_info',
        'phone': '+85295192756',
        'channel_id': 1173752118,
        'access_hash': 5661466759557601903
    })
    data = json.loads(_decrypto(res.json()))
    print(data)


def test_get_ququn_bot_messages():
    res = requests.post(URL, json={
        'type': 'ququn_bot',
        'keyword': '香港',
    })
    data = json.loads(_decrypto(res.json()))
    print(data)


def _decrypto(data: dict):
    data = AesCryptor.decrypt(
        data.get("body"), Const.crypto_key, data.get("iv")).decode("utf8")
    data = data.strip(b'\x00'.decode())
    return data


if __name__ == '__main__':
    main()
