"""使用requests模拟登录旧版东南大学统一身份认证平台（https://newids.seu.edu.cn/authserver/login）

函数说明：
get_login_data()函数用于获取密钥、ticket等登录信息；
aes_encrypt()函数用于使用AES密钥加密用户密码；
seu_login()函数用于发起登陆请求，返回成功登录的session。包括了对前两个函数的调用，一般只需要导入seu_login()函数即可。

使用方法：
1. 导入seu_login()函数；
2. 调用seu_login()函数，传入一卡通号、密码，获取session；
3. 使用session访问其他页面。

Author: Golevka2001 (https://github.com/Golevka2001)
Email: gol3vka@163.com
Date: 2023/08/31
License: GPL-3.0 License
"""

import js2py
import requests
from bs4 import BeautifulSoup


def get_login_data():
    """从身份认证页面获取登录所需的ticket等，以及用于加密的密钥

    Returns:
        session: 用于后续发起登录请求的session
        key: 用于加密用户密码的密钥
        login_data: 登录所需的数据，username和password字段待填充
    """
    try:
        session = requests.Session()
        # Headers有没有都行
        # headers = {
        #     'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;'
        #               'q=0.8,application/signed-exchange;v=b3;q=0.7',
        #     'Accept-Encoding': 'gzip, deflate, br',
        #     'Accept-Language': 'en,zh-CN;q=0.9,zh;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        #     'Cache-Control': 'max-age=0',
        #     'Connection': 'keep-alive',
        #     'DNT': '1',
        #     'Host': 'newids.seu.edu.cn',
        #     'Referer': 'https://newids.seu.edu.cn/authserver/logout?service=/authserver/login',
        #     'Upgrade-Insecure-Requests': '1',
        #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
        #                   'Chrome/115.0.0.0 Safari/537.36'
        # }
        # session.headers.update(headers)
        url = 'https://newids.seu.edu.cn/authserver/login'
        res = session.get(url=url)

        if res.status_code != 200:
            raise Exception(f'[{res.status_code} {res.reason}]')

        # 使用BeautifulSoup解析html
        soup = BeautifulSoup(res.text, 'html.parser')
        # 获取隐藏的表单数据
        hidden_items = soup.select('[tabid="01"] input[type="hidden"]')
        """内容格式如下：
        [<input name="lt" type="hidden" value="LT-5893590-xxxxxx-vXLP-cas"/>,
        <input name="dllt" type="hidden" value="userNamePasswordLogin"/>,
        <input name="execution" type="hidden" value="e1s1"/>,
        <input name="_eventId" type="hidden" value="submit"/>,
        <input name="rmShown" type="hidden" value="1"/>,
        <input id="pwdDefaultEncryptSalt" type="hidden" value="iFo5xxxxxx4AhH">
        </input>]
        """
        # 密钥
        key = str(hidden_items[-1]['value'])
        # 登录信息
        login_data = {'username': '', 'password': ''}
        for item in hidden_items[:-1]:
            login_data[str(item['name'])] = str(item['value'])

        print('获取登录信息成功')
        return session, key, login_data
    except Exception as e:
        print('获取登录信息失败，错误信息：', e)
        return None, None, None


def aes_encrypt(message: str, key: str):
    """使用获取到的密钥对用户密码进行AES加密，需要调用`encrypt.js`中的`encryptAES()`函数。

    Args:
        message: 用户密码（明文）
        key: 密钥

    Returns:
        cipher_text: 加密后的用户密码（base64）
    """
    try:
        with open('./encrypt.js') as file:
            js_obj = js2py.EvalJs()
            js_obj.execute(file.read())
            cipher = js_obj.encryptAES(message, key)

            print('AES加密成功')
            return cipher
    except Exception as e:
        print('AES加密失败，错误信息', e)
        return None


def seu_login(username: str, password: str):
    """向统一身份认证平台发起登陆请求。

    Args:
        username: 一卡通号
        password: 登录密码

    Returns:
        session: 登录成功后的session
    """
    # 访问身份认证页面，获取登录信息
    print('[seu_login]')
    session, key, login_data = get_login_data()
    if not session or not key or not login_data:
        return None, None

    # 使用AES加密用户密码
    encrypt_password = aes_encrypt(password, key)
    if not encrypt_password:
        return None, None

    # 发起登陆请求
    try:
        url = 'https://newids.seu.edu.cn/authserver/login'
        # Headers目前测试依然不影响，看情况加
        # headers = {
        #     'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;'
        #               'q=0.8,application/signed-exchange;v=b3;q=0.7',
        #     'Accept-Encoding': 'gzip, deflate, br',
        #     'Accept-Language': 'en,zh-CN;q=0.9,zh;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        #     'Cache-Control': 'max-age=0',
        #     'Connection': 'keep-alive',
        #     'Content-Type': 'application/x-www-form-urlencoded',
        #     'DNT': '1',
        #     'Host': 'newids.seu.edu.cn',
        #     'Origin': 'https://newids.seu.edu.cn',
        #     'Referer': 'https://newids.seu.edu.cn/authserver/login',
        #     'Upgrade-Insecure-Requests': '1',
        #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
        #                   'Chrome/115.0.0.0 Safari/537.36'
        # }
        # session.headers.update(headers)
        login_data['username'] = username
        login_data['password'] = encrypt_password
        res = session.post(url=url, data=login_data)

        if res.status_code != 200:
            raise Exception(f'[{res.status_code} {res.reason}]')

        # 解析返回页面，判断是否登录成功
        soup = BeautifulSoup(res.text, 'html.parser')
        name_span = soup.select('.auth_username span span')
        if len(name_span) == 0:
            error_span = soup.select('#msg')[0]
            raise Exception(error_span.text.strip())

        print('认证成功，用户姓名：', name_span[0].text.strip())
        return session
    except Exception as e:
        print('认证失败，错误信息', e)
        return None


if __name__ == '__main__':
    username = '【一卡通号】'
    password = '【密码】'
    session = seu_login(username, password)
