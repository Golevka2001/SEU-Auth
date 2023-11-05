"""使用seu_auth模块登录统一身份认证的一个示例：获取研究生素质讲座列表。

函数说明：
get_postgraduate_lecture_list()函数调用了seu_auth模块，登录统一身份认证平台后跳转到研究生素质讲座系统，获取讲座列表，返回登录后的session。

使用方法：
1. 配置账户信息：在`config.ini`中填入一卡通号和密码（不需要引号）；
2. 运行本文件，得到成功登录到研究生素质讲座系统的session，可用于后续在此系统中进行其他操作。

提示：
本科生账号无权限访问该应用，会在POST这一步返回403错误。

Author: Golevka2001 (https://github.com/Golevka2001)
Email: gol3vka@163.com
Date: 2023/11/03
License: GPL-3.0 License
"""

import configparser
import os
import sys

sys.path.append('..')
from seu_auth import seu_login


def get_postgraduate_lecture_list(username: str, password: str):
    """登录到研究生素质讲座系统，用于后续在此系统中进行其他操作。

    Args:
        username: 一卡通号
        password: 统一身份认证密码

    Returns:
        session: 登录到研究生素质讲座系统后的session
        lecture_list: 查询到的研究生素质讲座列表
    """
    try:
        # 登录统一身份认证平台
        service_url = 'http://ehall.seu.edu.cn/gsapp/sys/jzxxtjapp/*default/index.do'
        session, redirect_url = seu_login(username, password, service_url)
        if not session:
            raise Exception('统一身份认证平台登录失败')
        if not redirect_url:
            raise Exception('获取重定向url失败')

        # 访问研究生素质讲座系统页面
        res = session.get(redirect_url)
        if res.status_code != 200:
            raise Exception(f'访问研究生素质讲座系统失败[{res.status_code}, {res.reason}]')
        # 获取所有讲座信息
        res = session.post(
            'http://ehall.seu.edu.cn/gsapp/sys/jzxxtjapp/modules/hdyy/hdxxxs.do',
            data={
                'pageSize': 100,
                'pageNumber': 1
            })
        if res.status_code != 200:
            raise Exception(f'POST请求失败[{res.status_code}, {res.reason}]')
        lecture_list = res.json()['datas']['hdxxxs']['rows']
        print('获取讲座列表成功')
        return session, lecture_list
    except Exception as e:
        print('获取讲座列表失败，错误信息：', e)
        return None, None


if __name__ == '__main__':
    # 读取配置文件，使用时须在`config.ini`中填入一卡通号和密码
    config = configparser.ConfigParser()
    config_file_name = 'local_config.ini' if os.path.exists(
        'local_config.ini') else 'config.ini'
    config.read(config_file_name)
    username = config['ACCOUNT']['username']
    password = config['ACCOUNT']['password']
    # 获取讲座列表
    session, lecture_list = get_postgraduate_lecture_list(username, password)
    print(lecture_list)  # 为空时不一定是获取失败，可能是目前没有讲座信息，建议手动访问网页确认
