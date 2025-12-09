"""SEUAuthClient 的完整使用示例, 演示如何成功通过认证并访问需要登录的服务 (本示例中为 ehall).

do_login() 方法演示了如何使用 SEUAuthClient 完成一次完整的登录流程, 包括处理验证码和二次验证短信等步骤.
main() 方法主要是完成开始前的准备工作, 以及演示登录成功后可以用来做什么.

SEUAuthClient 对一次完整认证流程中的各个关键步骤都提供了单独的方法, 也就是说需要用户手动调用各个步骤来完成认证.
适用于对认证流程有较高自定义需求, 且熟悉该流程的使用者.
否则建议使用更高层封装的 SEUAuthManager, 将认证流程自动化.

Last updated: 2025-12-03
License: GPL-3.0 License
"""

import asyncio
import configparser
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from rich.logging import RichHandler

from seu_auth import SEUAuthClient
from seu_auth.utils.crypto import rsa_encrypt
from seu_auth.utils.parse import (
    CasLoginStatus,
    GetCipherKeyStatus,
    SendStage2CodeStatus,
    parse_cas_login_resp,
    parse_cas_logout_resp,
    parse_get_cipher_key_resp,
    parse_need_captcha_resp,
    parse_send_stage2_code_resp,
    parse_verify_tgt_resp,
)

logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logging.getLogger("seu_auth").setLevel(logging.DEBUG)


EXAMPLE_DIR = Path(__file__).parent


async def prepare_credentials(client: SEUAuthClient, raw_password: str) -> str:
    """获取公钥并加密密码."""
    # 2.1.1. 获取公钥
    data = await client.get_cipher_key()
    status, public_key = parse_get_cipher_key_resp(data)
    if status is GetCipherKeyStatus.FAILED:
        raise RuntimeError("Failed to get public key.")
    elif status is GetCipherKeyStatus.REUSE:
        # 如果出现复用公钥的情况, 由于没有 CHIPER_UID cookie, 目前不好处理, 报错退出
        raise RuntimeError("Received reused public key.")
    # 2.1.2. 加密密码
    enc_pwd = rsa_encrypt(raw_password, public_key)
    if not enc_pwd:
        raise RuntimeError("rsa_encrypt failed")
    return enc_pwd


async def prepare_captcha(client: SEUAuthClient) -> Optional[str]:
    """检查是否需要验证码, 如需要则获取验证码图片并处理, 本示例中为提示用户手动输入, 也可以集成 OCR 自动识别."""
    # 2.2.1. 检查是否需要验证码
    data = await client.need_captcha()
    need = parse_need_captcha_resp(data)
    if not need:
        return None

    # 2.2.2. 获取验证码图片, 保存到本地文件
    captcha_img = await client.get_captcha()
    path = Path("captcha_temp.jpg")
    try:
        with open(path, "wb") as f:
            f.write(captcha_img)
        print(f"Captcha saved to {path}. Please open and read it.")
    except Exception:
        print("Failed to write captcha image; continuing with manual input.")

    # 2.2.3. 提示用户输入验证码
    captcha = await asyncio.to_thread(input, "Enter captcha text: ")
    return captcha.strip()


async def do_login(
    username: str,
    raw_password: str,
    service: str = "",
    fingerprint: str = "",
) -> Tuple[bool, int, Optional[str], Optional[str], SEUAuthClient]:
    # 1. 初始化 SEUAuthClient 实例
    # 可以根据需要自定义 headers, timeout 等参数
    custom_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "Sec-Ch-Ua": '"Chromium";v="142", "Google Chrome";v="142", ";Not A Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    }
    auth_client = SEUAuthClient(timeout=5.0, headers=custom_headers)
    auth_client.open()

    # 2. 手动调用各个步骤完成登录流程
    # 其中的一些任务可以并行执行, 比如 "获取公钥并加密密码" 和 "检查是否需要验证码, 获取并处理验证码图片", 但如果考虑错误处理的话会比较复杂
    # 2.1. 加密密码: 获取公钥, 并加密用户密码
    cred_task = asyncio.create_task(prepare_credentials(auth_client, raw_password))
    # 2.2. 处理 captcha: 检查是否需要验证码, 如需要则获取验证码图片并提示用户输入 (和上一步并行, 但如果需要验证码的话, 不管手动输入还是 OCR, 最后都应该阻塞住)
    captcha_task = asyncio.create_task(prepare_captcha(auth_client))
    enc_pwd, captcha = await asyncio.gather(cred_task, captcha_task)

    # 2.3. 执行登录
    data = await auth_client.cas_login(
        username=username,
        encrypted_password=enc_pwd,
        service=service,
        captcha=captcha or "",
        fingerprint=fingerprint,
    )
    status, max_age, tgt, redirect_url = parse_cas_login_resp(data)

    # 3. 成功登录, 再验证一次
    if status is CasLoginStatus.SUCCESS:
        data = await auth_client.verify_tgt(service=service)
        verify_success = parse_verify_tgt_resp(data)
        if not verify_success:
            raise RuntimeError("verify_tgt failed after login")
        return True, max_age, tgt, redirect_url, auth_client

    # 4. 进行二次验证 (如果需要的话)
    if status is CasLoginStatus.STAGE2_REQUIRED:
        # 4.1. 发送二次验证短信
        data = await auth_client.send_stage2_code(username=username)
        status, phone = parse_send_stage2_code_resp(data)
        if status is not SendStage2CodeStatus.SUCCESS:
            raise RuntimeError("Failed to send stage 2 code.")

        # 4.2. 提示用户输入短信验证码
        sms_code = await asyncio.to_thread(
            input, f"Enter the SMS code sent to {phone}: "
        )
        sms_code = sms_code.strip()

        # 4.3. 再次获取公钥
        data = await auth_client.get_cipher_key()
        cipher_key_status, public_key = parse_get_cipher_key_resp(data)
        if cipher_key_status is GetCipherKeyStatus.FAILED:
            raise RuntimeError("Failed to get public key.")
        elif cipher_key_status is GetCipherKeyStatus.REUSE:
            raise RuntimeError("Received reused public key.")

        # 4.4. 加密密码和短信验证码
        enc_pwd = rsa_encrypt(raw_password, public_key)
        enc_sms = rsa_encrypt(sms_code, public_key)
        if not enc_pwd or not enc_sms:
            raise RuntimeError("rsa_encrypt failed")

        # 4.5. 再次发起登录请求, 附加短信验证码
        data = await auth_client.cas_login(
            username=username,
            encrypted_password=enc_pwd,
            service=service,
            captcha="",
            encrypted_mobile_verify_code=enc_sms,
            fingerprint=fingerprint,
        )
        stage2_status, max_age, tgt, redirect_url = parse_cas_login_resp(data)
        if stage2_status is not CasLoginStatus.SUCCESS:
            print("Stage 2 login failed, status:", stage2_status)
            return False, max_age, tgt, redirect_url, auth_client

        # 5. 成功登录, 再验证一次
        data = await auth_client.verify_tgt(service=service)
        verify_success = parse_verify_tgt_resp(data)
        if not verify_success:
            raise RuntimeError("verify_tgt failed after login")
        return (
            stage2_status is CasLoginStatus.SUCCESS,
            max_age,
            tgt,
            redirect_url,
            auth_client,
        )
    elif status is CasLoginStatus.BAD_CREDENTIALS:
        # 账号密码错误, 应该结束流程, 提示用户检查账号密码
        pass
    elif status is CasLoginStatus.BAD_CAPTCHA:
        # 图片验证码错误, 可以从 getCaptcha 重新开始
        pass
    elif status is CasLoginStatus.BAD_SMS_CODE:
        # 短信验证码错误, 可以从 sendStage2Code 重新开始
        pass
    elif status is CasLoginStatus.CIPHER_ERROR:
        # CHIPER_UID 相关错误, 需要重新获取公钥, 但如果是复用公钥, 缺失 CHIPER_UID Cookie 的话, 可能无法解决
        pass
    else:
        # 其他错误, 可以尝试重新发送当前 casLogin 请求
        pass
    return False, max_age, tgt, redirect_url, auth_client


async def main():
    # 从 local_config.ini 或 config.ini 读取账号密码
    config = configparser.ConfigParser()
    config_file_name = (
        EXAMPLE_DIR / "local_config.ini"
        if (EXAMPLE_DIR / "local_config.ini").exists()
        else EXAMPLE_DIR / "config.ini"
    )
    config.read(config_file_name)
    username = config["ACCOUNT"]["username"].strip()
    password = config["ACCOUNT"]["password"].strip()
    fingerprint = config["ACCOUNT"].get("fingerprint", "").strip()
    if not username or not password:
        raise ValueError("username/password is required")

    # 目标服务 URL, 这里以 ehall 为例
    service = (
        "http://ehall.seu.edu.cn/login?service=https://ehall.seu.edu.cn/new/index.html"
    )

    # 执行完整登录流程, 会返回完成登录的 SEUAuthClient 实例, 可复用其 client 进行后续请求
    login_success, max_age, tgt, redirect_url, httpx_client = await do_login(
        username=username,
        raw_password=password,
        service=service,
        fingerprint=fingerprint,
    )

    # 打印登录结果
    if not login_success:
        print("Login failed.")
        await httpx_client.close()
        return
    print(f"Login successful! TGT cookie: {tgt}, max_age: {max_age}")

    # 如果成功登录, 可以考虑持久化 TGT Cookie 以及浏览器指纹, 以便在下次登录时复用.

    # 访问重定向 URL (如果有的话)
    if redirect_url:
        resp = await httpx_client.client.get(redirect_url)
        print(f"Accessed redirect URL, response status: {resp.status_code}")

    # 复用 client 进行后续请求
    # 例如: 获取 ehall 用户信息
    resp = await httpx_client.client.get(
        url=f"https://ehall.seu.edu.cn/jsonp/userDesktopInfo.json?type=&_={int(datetime.now().timestamp())}"
    )
    print(resp.json())

    # 登出
    data = await httpx_client.cas_logout()
    logout_success = parse_cas_logout_resp(data)
    if logout_success:
        print("Logged out successfully.")
    else:
        print("Logout failed.")

    # 显式关闭 client 如果不再需要
    await httpx_client.close()


if __name__ == "__main__":
    asyncio.run(main())
