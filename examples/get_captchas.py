"""使用seu_auth模块登录统一身份认证的一个示例：获取验证码图片（研究生素质讲座系统、本科生选课系统）。

函数说明：
login_postgraduate_lecture_system()函数调用了seu_auth模块，登录统一身份认证平台后跳转到研究生素质讲座系统，返回登录后的session。
get_captcha_in_postgraduate_lecture_system()函数获取一张研究生素质讲座系统中的验证码图片。
get_captcha_in_undergraduate_course_system()函数获取一张本科生选课系统中的验证码图片。

使用方法：
1. 配置账户信息：在`config.ini`中填入一卡通号和密码（不需要引号）；
2. 运行本文件，依次得到研究生素质讲座系统中使用的验证码，还有本科生选课系统中的验证码。

提示：
本科生账号无权限访问研究生素质讲座应用，会在POST这一步返回403错误。

Author: Golevka2001 (https://github.com/Golevka2001)
Email: gol3vka@163.com
Date: 2023/11/03
License: GPL-3.0 License
"""

import base64
import configparser
import os
import sys
import time
from io import BytesIO

import matplotlib.pyplot as plt
import requests
from PIL import Image

sys.path.append('..')
from seu_auth import seu_login


def login_postgraduate_lecture_system(username: str, password: str):
    """登录到研究生素质讲座系统，用于后续在此系统中进行其他操作。

    Args:
        username: 一卡通号
        password: 统一身份认证密码

    Returns:
        session: 登录到研究生素质讲座系统后的session
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
        res = session.get(url=redirect_url, verify=False)
        if res.status_code != 200:
            raise Exception(f'访问研究生素质讲座系统失败[{res.status_code}, {res.reason}]')
        print('登录研究生素质讲座系统成功')
        return session
    except Exception as e:
        print('登录研究生素质讲座系统失败，错误信息：', e)
        return None


def get_captcha_in_postgraduate_lecture_system(session):
    """获取研究生素质讲座系统中的验证码图片。

    Args:
        session: 登录到研究生素质讲座系统后的session

    Returns:
        img: 验证码图片
    """
    try:
        res = session.post(
            url=f'https://ehall.seu.edu.cn/gsapp/sys/jzxxtjapp/hdyy/vcode.do?_={int(time.time() * 1000)}')
        if res.status_code != 200:
            raise Exception(f'POST请求失败[{res.status_code}, {res.reason}]')
        img = base64.b64decode(res.json()['result'].split(',')[1])
        print('获取验证码成功')
        return img
    except Exception as e:
        print('获取验证码失败，错误信息：', e)
        return None


def get_captcha_in_undergraduate_course_system():
    """获取本科生选课系统中的验证码图片。（注：这个无需登录）

    Returns:
        img: 验证码图片
    """
    try:
        res = requests.post(
            url='https://newxk.urp.seu.edu.cn/xsxk/auth/captcha', verify=False)
        if res.status_code != 200:
            raise Exception(f'POST请求失败[{res.status_code}, {res.reason}]')
        img = base64.b64decode(res.json()['data']['captcha'].split(',')[1])
        print('获取验证码成功')
        return img
    except Exception as e:
        print('获取验证码失败，错误信息：', e)
        return None


if __name__ == '__main__':
    # 读取配置文件，使用时须在`config.ini`中填入一卡通号和密码
    config = configparser.ConfigParser()
    config_file_name = 'local_config.ini' if os.path.exists(
        'local_config.ini') else 'config.ini'
    config.read(config_file_name)
    username = config['ACCOUNT']['username']
    password = config['ACCOUNT']['password']

    # 登录研究生素质讲座系统
    session = login_postgraduate_lecture_system(username, password)
    # 获取验证码
    img = get_captcha_in_postgraduate_lecture_system(session)
    # 显示
    img = Image.open(BytesIO(img))
    plt.imshow(img)
    plt.axis('off')
    plt.show()

    # 获取本科生选课系统验证码
    img = get_captcha_in_undergraduate_course_system()
    # 显示
    img = Image.open(BytesIO(img))
    plt.imshow(img)
    plt.axis('off')
    plt.show()
