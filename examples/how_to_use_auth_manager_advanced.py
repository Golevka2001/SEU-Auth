import asyncio
import configparser
import email
import imaplib
import logging
import re
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path

from ddddocr import DdddOcr
from PIL import Image
from rich.logging import RichHandler

from seu_auth import SEUAuthManager

logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logging.getLogger("seu_auth").setLevel(logging.DEBUG)

EXAMPLE_DIR = Path(__file__).parent

# 初始化 ORC 模块, 用于图片验证码识别
ocr = DdddOcr(
    import_onnx_path=str(EXAMPLE_DIR / "ddddocr_model/model.onnx"),
    charsets_path=str(EXAMPLE_DIR / "ddddocr_model/charsets.json"),
    show_ad=False,
)


async def custom_captcha_cb(image_data: bytes) -> str:
    """自定义 captcha 回调: 使用 ddddocr 进行验证码识别."""
    img = Image.open(BytesIO(image_data))
    result = ocr.classification(img)

    # 暂存
    calc_hash = hash(img.tobytes())
    img.save(EXAMPLE_DIR / f"local_cache/{result}_{calc_hash}.jpg")  # 不管对错

    print(f"DDDDOCR 识别结果: {result}")
    return result


async def custom_sms_cb(phone: str) -> str:
    """自定义短信回调: 从邮箱中读取 (已配置好短信转发规则)."""
    start_time = time.time()
    print(f"Waiting for SMS code")

    # 连接并登录邮箱
    mail = imaplib.IMAP4_SSL("<您的邮箱 IMAP 服务器地址>")
    mail.login("<您的邮箱地址>", "<您的邮箱密码或授权码>")
    status, messages = mail.select("INBOX")
    if status != "OK":
        raise RuntimeError("Failed to select mailbox")

    sms_code = None
    while (
        time.time() - start_time < 60 * 4
    ):  # 最多等待 4 分钟, 验证码有效时间一般为 5 分钟
        status, mail_ids = mail.search(
            None,
            '(ON "{}" FROM "<短信转发邮箱地址>")'.format(
                time.strftime("%d-%b-%Y", time.localtime(start_time))
            ),
        )
        mail_ids = mail_ids[0].split()
        mail_ids.reverse()  # 从最新的邮件开始检查
        for mail_id in mail_ids:
            result, msg_data = mail.fetch(mail_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            email_date = email.utils.parsedate_to_datetime(msg["Date"])
            if email_date.timestamp() < start_time:
                continue  # 邮件时间早于开始时间，跳过
            # 解码
            decoded_parts = email.header.decode_header(msg["Subject"])
            subject = ""
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    subject += part.decode(encoding or "utf-8", errors="ignore")
                else:
                    subject += part
            # 假设已经配置好邮件主题为 "【SEU】<6 位验证码>"
            match = re.search(r"【东南大学】(\d{6})", subject)
            if match:
                sms_code = match.group(1)
                print(f"Retrieved SMS code from email subject: {sms_code}")
                break
        if sms_code:
            break
        print("SMS code not found yet, waiting for 5 seconds before retrying...")
        await asyncio.sleep(5)

    mail.logout()
    if not sms_code:
        raise TimeoutError("Failed to retrieve SMS code from email within time limit.")
    return sms_code


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
    if not username or not password:
        raise ValueError("username/password is required")

    # 自定义请求头
    custom_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "Sec-Ch-Ua": '"Chromium";v="142", "Google Chrome";v="142", ";Not A Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    }

    # 目标服务 URL, 这里以 ehall 为例
    service = (
        "http://ehall.seu.edu.cn/login?service=https://ehall.seu.edu.cn/new/index.html"
    )

    manager = SEUAuthManager(
        username=username,
        password=password,
        captcha_callback=custom_captcha_cb,  # 自定义验证码回调: OCR
        sms_callback=custom_sms_cb,  # 自定义短信回调: 邮箱读取
        max_step_retries=2,  # 每个步骤最多重试 2 次
        timeout=5.0,
        headers=custom_headers,
    )

    try:
        async with manager:
            # 执行登录
            httpx_client, redirect_url = await manager.login(
                force_refresh=True,  # 当不启用 force_refresh 时会尝试使用缓存的 TGT 进行快速登录
                service=service,
            )

            # 判断是否成功登录
            if httpx_client is None:
                raise RuntimeError("Login failed")

            # 访问重定向 URL (如果有的话)
            if redirect_url:
                resp = await httpx_client.get(redirect_url)
                print(f"Accessed redirect URL, response status: {resp.status_code}")

            # 复用 client 进行后续请求
            # 例如: 获取 ehall 用户信息
            resp = await httpx_client.get(
                url=f"https://ehall.seu.edu.cn/jsonp/userDesktopInfo.json?type=&_={int(datetime.now().timestamp())}"
            )
            print(resp.json())

    except Exception as e:
        print(f"Login failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
