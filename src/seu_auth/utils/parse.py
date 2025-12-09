"""parse.py
响应解析工具模块, 提供对 SEUAuthClient 返回的 JSON 响应进行解析的函数, 与各请求方法一一对应.

Last Update: 2025-12-03
License: GPL-3.0 License
"""

import re
from enum import Enum, auto
from typing import Optional, Tuple
from urllib.parse import unquote


class GetCipherKeyStatus(Enum):
    """get_cipher_key 响应的状态枚举."""

    SUCCESS = auto()  # 成功获取公钥
    REUSE = auto()  # 复用公钥
    FAILED = auto()  # 获取失败


class CasLoginStatus(Enum):
    """casLogin 响应的登录状态枚举."""

    SUCCESS = auto()  # 登录成功
    STAGE2_REQUIRED = auto()  # 需要二次验证
    BAD_CREDENTIALS = auto()  # 账号密码错误 (无法重试解决, 应退出)
    BAD_CAPTCHA = auto()  # 验证码错误
    BAD_SMS_CODE = auto()  # 短信验证码错误
    CIPHER_ERROR = auto()  # 主要是 CHIPER_UID 相关问题
    FAILED = auto()  # 其他错误, 如网络问题等


class SendStage2CodeStatus(Enum):
    """send_stage2_code 响应的状态枚举."""

    SUCCESS = auto()  # 短信发送成功
    CIPHER_ERROR = auto()  # 主要是 CHIPER_UID 相关问题
    RATE_LIMITED = auto()  # 请求频率过高
    FAILED = auto()  # 短信发送失败


def parse_verify_tgt_resp(resp: dict) -> Tuple[bool, Optional[str]]:
    """解析 verify_tgt 请求的响应.

    Args:
        resp (dict): SEUAuthClient.verify_tgt() 方法返回的响应字典.

    Returns:
        Tuple[bool, Optional[str]]: 一个元组, 包含:
            - bool: 如果会话有效则返回 True, 否则返回 False.
            - Optional[str]: redirect URL, 如果存在则返回该 URL 字符串, 否则返回 None.
    """
    code = int(resp.get("code", 0))
    success = bool(resp.get("success"))
    info = resp.get("info", "").lower()
    redirect_url = resp.get("redirectUrl", None)
    valid = (
        200 <= code < 300
        and success
        # and "success" in info
    )
    return valid, redirect_url


def parse_need_captcha_resp(resp: dict) -> bool:
    """解析 need_captcha 请求的响应.

    Args:
        resp (dict): SEUAuthClient.need_captcha() 方法返回的响应字典.

    Returns:
        bool: 如果需要验证码则返回 True, 否则返回 False.
    """
    code = int(resp.get("code", 0))
    info = resp.get("info", "").lower()
    return not (200 <= code < 300 and "不需要" in info)


def parse_get_cipher_key_resp(resp: dict) -> Tuple[GetCipherKeyStatus, Optional[str]]:
    """解析 get_cipher_key 请求的响应.
    此处不处理 CHIPER_UID Cookie, 由 SEUAuthClient 内部自动设置.

    注意: 复用公钥的响应中不含 CHIPER_UID Cookie, 如果您没有保存上次的 CHIPER_UID,
    服务端将无法正确处理登录请求, 会导致一段时间内无法登录, 直到该公钥过期被重新生成.

    Args:
        resp (dict): SEUAuthClient.get_cipher_key() 方法返回的响应字典.

    Returns:
        Tuple[GetCipherKeyStatus,Optional[str]]: 一个元组, 包含:
            - GetCipherKeyStatus: 获取状态枚举值.
            - Optional[str]: 公钥字符串, 如果获取失败则返回 None.
    """
    code = int(resp.get("code", 0))
    success = bool(resp.get("success"))
    info = resp.get("info", "").lower()
    public_key = resp.get("publicKey", None)
    if not (
        200 <= code < 300
        and success
        # and "success" in info
        and public_key is not None
    ):
        return GetCipherKeyStatus.FAILED, None

    if "reuse" in info:
        return GetCipherKeyStatus.REUSE, public_key
    return GetCipherKeyStatus.SUCCESS, public_key


def parse_cas_login_resp(
    resp: dict,
) -> Tuple[CasLoginStatus, int, Optional[str], Optional[str]]:
    """解析 cas_login 请求的响应.

    本方法返回内容较多, 注意阅读返回值说明.

    Args:
        resp (dict): SEUAuthClient.cas_login() 方法返回的响应字典.

    Returns:
        Tuple[CasLoginStatus, int, Optional[str], Optional[str]]: 一个元组, 包含:
            - CasLoginStatus: 登录状态枚举值.
            - int: maxAge. 仅当登录成功时有效.
            - Optional[str]: tgtCookie, 未获取到则返回 None. 仅当登录成功时有效.
            - Optional[str]: redirectUrl, 未获取到则返回 None. 仅当登录成功时有效.
    """
    code = int(resp.get("code", 0))
    success = bool(resp.get("success"))
    info = resp.get("info", "").lower()
    tgt_cookie = resp.get("tgtCookie", None)

    # 1. 判断登录是否成功
    if (
        200 <= int(code) < 300
        and success
        # and "success" in info
        and tgt_cookie
    ):
        redirect_url = resp.get("redirectUrl", None)
        if redirect_url:
            redirect_url = unquote(redirect_url)
        return (
            CasLoginStatus.SUCCESS,
            resp.get("maxAge", 0),
            tgt_cookie,
            redirect_url,
        )
    # 2. 判断是否需要二次验证
    if (
        code == 502
        or bool(
            resp.get("needStage2Validation")
        )  # NOTE: Always False, I don't know why.
        or all(k in info for k in ["设备", "验证"])
    ):
        return CasLoginStatus.STAGE2_REQUIRED, 0, None, None

    # 错误原因分析
    # 3. 凭据错误
    if code == 402 or any(k in info for k in ["用户名", "密码"]):
        return CasLoginStatus.BAD_CREDENTIALS, 0, None, None
    # 4. Captcha 错误
    if (code == 4000 or code == 4001) and "验证码" in info:
        return CasLoginStatus.BAD_CAPTCHA, 0, None, None
    # 5. 短信验证码错误
    if code == 503 and "验证码" in info:
        return CasLoginStatus.BAD_SMS_CODE, 0, None, None
    # 6. CHIPER_UID 相关错误
    if any(k in info for k in ["过期", "失效", "刷新"]):
        return CasLoginStatus.CIPHER_ERROR, 0, None, None
    # 7. 其他错误
    return CasLoginStatus.FAILED, 0, None, None


def parse_send_stage2_code_resp(
    resp: dict,
) -> Tuple[SendStage2CodeStatus, Optional[str]]:
    """解析 send_stage2_code 请求的响应.

    TODO: 触发速率限制时解析等待时间并返回.

    Args:
        resp (dict): SEUAuthClient.send_stage2_code() 方法返回的响应字典.

    Returns:
        Tuple[SendStage2CodeStatus,Optional[str]]: 一个元组, 包含:
            - SendStage2CodeStatus: 发送状态枚举值.
            - Optional[str]: 发送到的手机号, 若未获取到则返回 None. 仅当请求成功时有效.
    """
    code = int(resp.get("code", 0))
    success = bool(resp.get("success"))
    info = resp.get("info", "").lower()
    if (
        200 <= code < 300
        and success
        # and "已发送" in info
    ):
        # Extract phone number from info message
        phone_num = None
        match = re.search(r"(\d{11})", info)
        if match:
            phone_num = match.group(1)
        return SendStage2CodeStatus.SUCCESS, phone_num

    if code == 5002 or any(k in info for k in ["过期", "失效", "刷新"]):
        return SendStage2CodeStatus.CIPHER_ERROR, None

    if code == 5001 or any(k in info for k in ["过多", "重试"]):
        return SendStage2CodeStatus.RATE_LIMITED, None

    return SendStage2CodeStatus.FAILED, None


def parse_cas_logout_resp(resp: dict) -> bool:
    """解析 cas_logout 请求的响应.

    Args:
        resp (dict): SEUAuthClient.cas_logout() 方法返回的响应字典.

    Returns:
        bool: 如果登出成功或未登录状态, 返回 True; 否则返回 False.
    """
    code = int(resp.get("code", 0))
    success = bool(resp.get("success"))
    info = resp.get("info", "").lower()
    return (
        200 <= code < 300
        and success
        # and "success" in info
    ) or all(k in info for k in ["not", "log"])
