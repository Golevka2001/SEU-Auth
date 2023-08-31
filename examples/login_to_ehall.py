"""使用seu_auth模块登录统一身份认证的一个示例：登录网上办事服务大厅。

函数说明：
login_to_ehall()函数调用了seu_auth模块，登录统一身份认证平台后跳转到网上办事服务大厅，获取用户信息并与传入的一卡通号核对，返回登录后的session。

使用方法：
1. 配置账户信息：将`config.ini`重命名为`local_config.ini`，并填入一卡通号和密码（不需要引号）；
2. 运行本文件，得到成功登录到网上办事服务大厅的session，可用于继续访问网上办事服务大厅的其他应用。

Author: Golevka2001 (https://github.com/Golevka2001)
Email: gol3vka@163.com
Date: 2023/08/27
License: GPL-3.0 License
"""

import configparser

from seu_auth import seu_login


def login_to_ehall(username, password):
    """登录到网上办事服务大厅，用于后续访问网上办事服务大厅的其他应用。

    Args:
        username: 一卡通号
        password: 统一身份认证密码

    Returns:
        session: 登录到网上办事服务大厅后的session
    """
    try:
        # 登录统一身份认证平台
        service_url = 'http://ehall.seu.edu.cn/login?service=http://ehall.seu.edu.cn/new/index.html'
        session, redirect_url = seu_login(username, password, service_url)
        if not session:
            raise Exception('Login failed')

        # 更新Headers。UA必填，其他目前无所谓
        session.headers = {
            # 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;'
            #           'q=0.8,application/signed-exchange;v=b3;q=0.7',
            # 'Accept-Encoding': 'gzip, deflate',
            # 'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            # 'Connection': 'keep-alive',
            # 'DNT': '1',
            # 'Host': 'ehall.seu.edu.cn',
            # 'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/115.0.0.0 Safari/537.36'
        }

        # 访问网上办事服务大厅首页
        res = session.get(redirect_url)
        if res.status_code != 200:
            raise Exception('Cannot access ehall page')

        # 获取用户身份信息，检查是否登录成功
        user_info_url = 'http://ehall.seu.edu.cn/jsonp/userDesktopInfo.json?type=&_=1693121329211'
        res = session.get(user_info_url)
        if res.status_code != 200:
            raise Exception('Cannot get user information')
        if 'userId' in res.json():
            if res.json()['userId'] == username:
                print('Successfully login to ehall, name:', res.json()['userName'])
            else:
                raise Exception('Id not match')
        else:
            raise Exception('Cannot get user information')
        return session
    except Exception as e:
        print('Failed to login to ehall, info:', e)
        return None


if __name__ == '__main__':
    # 读取配置文件，使用时将`config.ini`重命名为`local_config.ini`，并填入一卡通号和密码
    config = configparser.ConfigParser()
    config.read('local_config.ini')
    username = config['ACCOUNT']['username']
    password = config['ACCOUNT']['password']
    # 登录到网上办事服务大厅（会打印姓名用于核对账户信息，如不需要可注释掉）
    session = login_to_ehall(username, password)
