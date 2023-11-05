"""使用seu_auth_mobile模块登录移动端身份认证的一个示例：查询东大信息化中的东豆余额。

函数说明：
query_seu_points()函数调用了seu_auth_mobile模块，登录移动端身份认证平台后查询所登录账户的东豆余额，返回登录后的session和东豆余额。

使用方法：
1. 配置账户信息：在`config.ini`中填入一卡通号和密码（不需要引号）；
2. 运行本文件，将在控制台打印所登录账户的东豆余额。

Author: Golevka2001 (https://github.com/Golevka2001)
Email: gol3vka@163.com
Date: 2023/11/05
License: GPL-3.0 License
"""

import configparser
import os
import sys

sys.path.append('..')
from seu_auth_mobile import seu_login


def query_seu_points(username: str, password: str):
    """查询东大信息化中的东豆余额。

    Args:
        username: 一卡通号
        password: 统一身份认证密码

    Returns:
        session: 成功登录移动端身份认证平台后的session
        user_points: 查询到的东豆余额
    """
    try:
        # 登录移动端身份认证平台
        session = seu_login(username, password)
        if not session:
            raise Exception('移动端身份认证平台登录失败')
        # 查询东豆余额
        url = (
            'http://apoint.seu.edu.cn/_web/_customizes/seu/point/api/findUserPoint.rst?'
            '_p=YXM9MiZwPTEmbT1OJg__'
            '&act=1'
            f'&loginName={username}')

        res = session.get(url)
        if res.status_code != 200:
            raise Exception(f'[{res.status_code}, {res.reason}]')

        user_points = res.json()['result']['data']['score']
        return session, user_points
    except Exception as e:
        print('东豆余额查询失败，错误信息：', e)
        return None, None


if __name__ == '__main__':
    # 读取配置文件，使用时须在`config.ini`中填入一卡通号和密码
    config = configparser.ConfigParser()
    config_file_name = 'local_config.ini' if os.path.exists(
        'local_config.ini') else 'config.ini'
    config.read(config_file_name)
    username = config['ACCOUNT']['username']
    password = config['ACCOUNT']['password']
    # 获取东豆余额
    session, user_points = query_seu_points(username, password)
    print(user_points)
