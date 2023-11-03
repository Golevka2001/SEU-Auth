"""使用seu_auth模块登录统一身份认证的一个示例：登录第二课堂。

函数说明：
get_dekt_user_id()函数调用了seu_auth模块，登录统一身份认证平台后跳转到第二课堂，获取用户id。

使用方法：
1. 配置账户信息：在`config.ini`中填入一卡通号和密码（不需要引号）；
2. 运行本文件，即可获取第二课堂用户id，此id在后续访问第二课堂其他服务时大多需要通过`http://dekt.seu.edu.cn/xxx?.me=xxx`的方式传入。

Author: Golevka2001 (https://github.com/Golevka2001)
Email: gol3vka@163.com
Date: 2023/08/27
License: GPL-3.0 License
"""
import sys

sys.path.append('..')

import configparser
import os

from bs4 import BeautifulSoup

from seu_auth import seu_login


def get_dekt_user_id(username, password):
    """获取第二课堂用户id，用于后续访问第二课堂其他服务。

    Args:
        username: 一卡通号
        password: 统一身份认证密码

    Returns:
        session: 登录到第二课堂后的session
        user_id: 第二课堂用户id（似乎是固定的）
    """
    print('[login_to_dekt]')
    try:
        # 登录统一身份认证平台
        service_url = 'http://dekt.seu.edu.cn/zhtw/'
        session, redirect_url = seu_login(username, password, service_url)
        if not session:
            raise Exception('统一身份认证平台登录失败')
        if not redirect_url:
            raise Exception('获取重定向url失败')

        # 更新Headers。UA必填，其他目前无所谓
        session.headers = {
            # 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;'
            #           'q=0.8,application/signed-exchange;v=b3;q=0.7',
            # 'Accept-Encoding': 'gzip, deflate',
            # 'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            # 'Connection': 'keep-alive',
            # 'DNT': '1',
            # 'Host': 'dekt.seu.edu.cn',
            # 'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/115.0.0.0 Safari/537.36'
        }

        # 访问第二课堂页面，获取用户id
        res = session.get(redirect_url)
        if res.status_code != 200:
            raise Exception(f'访问第二课堂失败[{res.status_code}, {res.reason}]')

        # 使用BeautifulSoup解析html
        soup = BeautifulSoup(res.text, 'html.parser')
        if not soup.title:
            raise Exception('BeautifulSoup解析失败')
        user_id = soup.title['data-m']
        if not user_id:
            raise Exception('BeautifulSoup解析失败')
        # # 或者使用正则表达式（需要在文件头添加import re）
        # pattern = r'<title.*?data-m="(.*?)".*?>'
        # match = re.search(pattern, res.text)
        # if match:
        #     user_id = match.group(1)
        # else:
        #     raise Exception('正则解析失败')
        print('登录第二课堂成功，用户ID：', user_id)
        return session, user_id
    except Exception as e:
        print('登录第二课堂失败，错误信息：', e)
        return None, None


if __name__ == '__main__':
    # 读取配置文件，使用时须在`config.ini`中填入一卡通号和密码
    config = configparser.ConfigParser()
    config_file_name = 'local_config.ini' if os.path.exists('local_config.ini') else 'config.ini'
    config.read(config_file_name)
    username = config['ACCOUNT']['username']
    password = config['ACCOUNT']['password']
    # 获取第二课堂用户id
    session, user_id = get_dekt_user_id(username, password)
    print(user_id)
