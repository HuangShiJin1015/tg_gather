"""
添加采集资源
1.下载客户端(桌面版or手机版)
2.根据手机号登录
3.调用此方法进行程序登录验证，生成session文件
"""

import requests


def main():
    phone_num = '639568014449'

    # 发送添加账号请求
    requests.get('http://127.0.0.1:8088/teleclient/login', params={
        'phone': '+' + phone_num
    })

    # 发送验证码验证请求
    code = input("请输入验证码：")
    requests.get('http://127.0.0.1:8088/teleclient/login', params={
        'phone': '+' + phone_num,
        'code': code
    })


if __name__ == "__main__":
    main()
