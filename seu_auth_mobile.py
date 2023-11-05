"""使用requests模拟登录东南大学移动端身份认证平台（ids_mobile）

函数说明：
get_user_info()函数用于获取已登录用户的身份信息（用于检查是否成功登录）；
seu_login()函数用于发起登陆请求，返回成功登录的session。包括了对前一个函数的调用，一般只需要导入seu_login()函数即可。

使用方法：
1. 导入seu_login()函数；
2. 调用seu_login()函数，传入一卡通号、密码，获取session；
3. 使用session访问其他移动端应用。

Author: Golevka2001 (https://github.com/Golevka2001)
Email: gol3vka@163.com
Date: 2023/11/05
License: GPL-3.0 License
"""

import json

import requests


def get_user_info(session: requests.Session):
    """获取已登录用户的身份信息（用于检查是否成功登录）。

    Args:
        session: 成功登录移动端身份认证平台后的session

    Returns:
        user_info: 用户身份信息
    """
    try:
        url = 'http://mobile4.seu.edu.cn/_ids_mobile/loginedUser15'
        # Headers和登录时的一致，同样有没有都行

        res = session.post(url)  # POST但不需要data
        if res.status_code != 200:
            raise Exception(f'[{res.status_code}, {res.reason}]')

        if res.json()['result'] != '1' or res.json()['data'] is None:
            raise Exception('返回数据异常')

        return res.json()['data']
    except Exception as e:
        print('获取用户信息失败，错误信息：', e)
        return None


def seu_login(username: str, password: str):
    """向移动端身份认证平台发起登陆请求（注：用户名/密码错误对应的状态码是：401, Unauthorized）

    Args:
        username: 一卡通号
        password: 登录密码

    Returns:
        session: 登录成功后的session
    """
    try:
        session = requests.Session()
        # Headers有没有都行
        # headers = {
        #     'Connection': 'Keep-Alive',
        #     'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        #     'Host': 'mobile4.seu.edu.cn',
        #     'User-Agent': 'Mozilla/5.0 (Linux; Android 13; Pixel 5 Build/TQ3A.230605.012; wv) AppleWebKit/537.36 (KHTML, like Gecko) '
        #                   'Version/4.0 Chrome/113.0.5672.131 Mobile Safari/537.36 iPortal/41',
        # }
        # session.headers.update(headers)
        url = 'http://mobile4.seu.edu.cn/_ids_mobile/login18_9'
        login_data = {
            'apnsKey': '',
            'appName': 'teacher',  # 不知道为啥是teacher
            'code': '2',
            'deviceName': '',  # 设备名称，如`Pixel+5`，可不填
            'name': '',  # 同上
            'password': password,  # NOTE：明文传输的密码哦
            'serialNo': '',  # 设备序列号，可不填
            'type': '0',
            'username': username,
        }

        res = session.post(url, data=login_data)  # 响应体为空
        if res.status_code != 200:
            raise Exception(f'[{res.status_code}, {res.reason}]')

        # 手动更新sso-cookies，用于后续访问其他应用
        sso_cookies = json.loads(res.headers['ssoCookie'])  # str -> dict
        for cookie in sso_cookies:
            session.cookies.set(cookie['cookieName'], cookie['cookieValue'])

        res = get_user_info(session)
        if res is not None:
            if res['uxid'] != username:
                raise Exception('返回数据异常')
            print('认证成功，用户姓名：', res['username'])
        return session
    except Exception as e:
        print('登陆失败，错误信息：', e)
        return None


if __name__ == '__main__':
    username = '【一卡通号】'
    password = '【密码】'
    session = seu_login(username, password)
