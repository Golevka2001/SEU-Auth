"""使用requests模拟登录新版东南大学统一身份认证平台（https://auth.seu.edu.cn/dist/#/dist/main/login）

函数说明：
init_ocr()函数用于初始化OCR识别器（处理验证码）；
new_session()函数用于创建一个具有必要headers的seesion；
is_captcha_required()函数用于在登录前检查是否需要验证码；
solve_captcha()函数用于获取并OCR识别验证码（也可选手动输入）；
get_pub_key()函数用于获取RSA公钥；
rsa_encrypt()函数用于使用RSA公钥加密用户密码；
seu_login()函数用于发起登录请求，返回成功登录的session和包含了ticket的重定向url。包括了对前两个函数的调用，一般只需要导入seu_login()函数即可。

使用方法：
1. 导入seu_login()函数；
2. 调用seu_login()函数，传入一卡通号、密码、后续所要访问的服务url（可选）、session（可选）、OCR识别器（可选）、是否手动输入验证码（可选）；
3. 使用session访问重定向url，执行后续操作。

Author: Golevka2001 (https://github.com/Golevka2001)
Email: gol3vka@163.com
Date: 2023/08/20
Last Update: 2024/12/30
License: GPL-3.0 License
"""

import base64
import json
from datetime import datetime
from io import BytesIO
from urllib.parse import unquote

import ddddocr
import requests
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from PIL import Image


def init_ocr():
    """初始化OCR识别器。

    Returns:
        ocr: DdddOcr对象
    """
    ocr = ddddocr.DdddOcr()
    ocr.set_ranges(1)
    return ocr


def new_session():
    """创建一个设置好所需headers的新session。

    Returns:
        session: 新的session
    """
    session = requests.Session()
    # Headers中的Content-Type、UA必填；
    # Host、Origin、Referer在后续访问其他服务时大多需要填，内容自己去抓包看；
    # 经测试，以下headers中注释掉的字段均不影响身份认证的登录过程，但访问其他服务时需要自行抓包填写。
    headers = {
        # 'Accept': 'application/json',
        # 'Accept-Encoding': 'gzip, deflate, br',
        # 'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        # 'Connection': 'keep-alive',
        'Content-Type':
        'application/json',
        # 'Host': 'auth.seu.edu.cn',
        # 'Origin': 'https://auth.seu.edu.cn',
        # 'Referer': 'https://auth.seu.edu.cn/dist/',
        'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/115.0.0.0 Safari/537.36'
    }
    session.headers.update(headers)
    return session


def is_captcha_required(session):
    """检查是否需要验证码。

    Args:
        session: 创建好的session

    Returns:
        bool: 是否需要验证码
    """
    url = 'https://auth.seu.edu.cn/auth/casback/needCaptcha'

    res = session.get(url=url, verify=False)
    if res.status_code != 200:
        raise Exception(f'[{res.status_code}, {res.reason}]')
    return res.json()['code'] == 4000 and '不需要' not in res.json()['info']


def solve_captcha(session, ocr=None, manual=False):
    """获取并自动/手动识别验证码。

    Args:
        session: 创建好的session
        ocr: OCR识别器
        manual: 是否手动输入验证码

    Returns:
        str: 验证码结果
    """
    try:
        url = 'https://auth.seu.edu.cn/auth/casback/getCaptcha'

        res = session.get(url=url, verify=False)
        if res.status_code != 200:
            raise Exception(f'[{res.status_code}, {res.reason}]')
        print('获取验证码成功')
        img = Image.open(BytesIO(res.content))

        # 手动输入
        if manual:
            img.show()
            result = ''
            # NOTE: 目前为4位纯字母，如有变动请修改
            while len(result) != 4 or not result.isalpha():
                result = input('请输入验证码：')
        # OCR识别
        else:
            if not ocr:
                ocr = init_ocr()
            result = ''
            # NOTE: 同上
            while len(result) != 4 or not result.isalpha():
                result = ocr.classification(img, probability=True)
                s = ''
                for i in result['probability']:
                    s += result['charsets'][i.index(max(i))]
                result = s
            print('验证码识别结果：', result)
        return result
    except Exception as e:
        print('获取/识别验证码失败，错误信息：', e)
        return None


def get_pub_key(session):
    """从服务器请求RSA公钥并保存cookie（使用session就不需要另外保存cookie）。
    RSA公钥是变化的，并且应该和cookie有关联，每次登录前需要重新获取。

    Args:
        session: 创建好的session

    Returns:
        pub_key: RSA公钥
    """
    try:
        url = 'https://auth.seu.edu.cn/auth/casback/getChiperKey'

        res = session.post(url=url, verify=False)
        if res.status_code != 200:
            raise Exception(f'[{res.status_code}, {res.reason}]')

        pub_key = res.json()['publicKey']
        print('获取RSA公钥成功')
        return pub_key
    except Exception as e:
        print('获取RSA公钥失败，错误信息', e)
        return None


def rsa_encrypt(message: str, pub_key: str):
    """使用服务器返回的公钥对用户密码进行RSA加密。

    Args:
        message: 用户密码（明文）
        pub_key: 服务器提供的公钥

    Returns:
        cipher_text: 加密后的用户密码（base64）
    """
    try:
        pub_key = pub_key.replace('-', '+').replace('_',
                                                    '/')  # base64url -> base64
        pub_key = '-----BEGIN PUBLIC KEY-----\n' + pub_key + '\n-----END PUBLIC KEY-----'
        rsa_key = RSA.importKey(pub_key)
        cipher = PKCS1_v1_5.new(rsa_key)
        cipher_text = base64.b64encode(cipher.encrypt(
            message.encode()))  # base64

        print('RSA加密成功')
        return cipher_text.decode()
    except Exception as e:
        print('RSA加密失败，错误信息：', e)
        return None


def seu_login(username: str,
              password: str,
              service_url: str = '',
              session=None,
              ocr=None,
              manual_captcha=False):
    """向统一身份认证平台发起登录请求。

    Args:
        username: 一卡通号
        password: 用户密码（明文）
        service_url: 所要访问服务的url，如`http://ehall.seu.edu.cn`
        session: 登录前的session，若未提供则新建
        ocr: OCR识别器，若未提供且未指定手动输入验证码则新建
        manual_captcha: 是否手动输入验证码，默认使用OCR识别

    Returns:
        session: 成功通过身份认证的session，用于后续访问其他服务
        redirect_url: 登录后重定向到所要访问的服务的url
    """
    print('[seu_login]')
    session = new_session() if not session else session
    ocr = init_ocr() if not ocr and not manual_captcha else ocr
    captcha_required = True
    captcha_correct = False

    while captcha_required and not captcha_correct:
        # 获取、识别验证码
        captcha_required = is_captcha_required(session)
        captcha_result = solve_captcha(
            session, ocr, manual_captcha) if captcha_required else ''

        # 获取RSA公钥
        pub_key = get_pub_key(session)
        if not pub_key:
            return None, None

        # 使用服务器返回的RSA公钥加密用户密码
        encrypted_password = rsa_encrypt(password, pub_key)
        if not encrypted_password:
            return None, None

        # 发起登录请求
        try:
            url = 'https://auth.seu.edu.cn/auth/casback/casLogin'
            data = {
                'captcha': captcha_result,
                'loginType': 'account',
                'mobilePhoneNum': '',
                'mobileVerifyCode': '',
                'password': encrypted_password,
                'rememberMe': False,
                'service': service_url,
                'username': username,
                'wxBinded': False,
            }

            res = session.post(url=url, data=json.dumps(data), verify=False)
            if res.status_code != 200:
                raise Exception(f'[{res.status_code}, {res.reason}]')

            # 处理验证码错误
            if not res.json()['success'] and '验证码' in res.json()['info']:
                print('验证码错误，重试')
                continue

            # 其他错误
            if not res.json()['success']:
                raise Exception(res.json()['info'])

            print('认证成功')

            # 未指定服务，无需重定向，直接返回session
            if res.json()['redirectUrl'] is None:
                return session, None

            # 指定服务，返回重定向url（含ticket）
            redirect_url = unquote(res.json()['redirectUrl'])
            return session, redirect_url
        except Exception as e:
            print('认证失败，错误信息：', e)
            return None, None


def seu_logout(session):
    """退出登录

    Args:
        session: 登录成功后的session
    """
    try:
        url = 'https://auth.seu.edu.cn/auth/casback/casLogout'
        res = session.post(url=url, verify=False)
        if res.status_code != 200 or not res.json()['success']:
            raise Exception(f'[{res.status_code}, {res.reason}]')
        print('退出登录成功')
    except Exception as e:
        print('退出登录失败，错误信息：', e)


if __name__ == '__main__':
    username = '【一卡通号】'
    password = '【密码】'

    # 测试：登录网上办事服务大厅
    session = new_session()
    ocr = init_ocr()
    service_url = 'http://ehall.seu.edu.cn/login?service=http://ehall.seu.edu.cn/new/index.html'
    session, redirect_url = seu_login(username,
                                      password,
                                      service_url,
                                      ocr=ocr,
                                      manual_captcha=False)
    if not session:
        exit(1)

    # 登录成功后获取用户信息
    if redirect_url:
        print(redirect_url)
        session.get(url=redirect_url, verify=False)
        res = session.get(
            url=
            f'http://ehall.seu.edu.cn/jsonp/userDesktopInfo.json?type=&_={int(datetime.now().timestamp())}',
            verify=False)
        print(res.json())

    # 退出登录
    seu_logout(session)
