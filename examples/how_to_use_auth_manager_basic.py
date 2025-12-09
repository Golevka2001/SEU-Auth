"""SEUAuthManager 的简单使用示例, 一步完成认证并访问需要登录的服务 (本示例中为 ehall).

Last updated: 2025-12-03
License: GPL-3.0 License
"""

import asyncio
import configparser
import logging
import sys
from datetime import datetime
from pathlib import Path

from rich.logging import RichHandler

sys.path.append("..")

from seu_auth import SEUAuthManager

logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logging.getLogger("seu_auth").setLevel(logging.DEBUG)


EXAMPLE_DIR = Path(__file__).parent


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
    # 目标服务 URL, 这里以 ehall 为例
    service = (
        "http://ehall.seu.edu.cn/login?service=https://ehall.seu.edu.cn/new/index.html"
    )

    # 初始化 SEUAuthManager 实例
    manager = SEUAuthManager(
        username=username,
        password=password,
        # fingerprint=fingerprint,  # 不传入时会自动生成
    )

    try:
        # 使用 async context 确保 client 正确关闭
        async with manager:
            httpx_client, redirect_url = await manager.login(
                force_refresh=True, service=service
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

            # 退出 async with 块时，client 会被关闭
    except RuntimeError as e:
        print(f"Login failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
