"""auth_manager.py
用于管理 SEU 认证流程的高级封装.

将整个登录流程 (包括异常时的状态跳转和重试) 进行封装, 提供一个简单的接口供外部调用.
能够处理大部分可能遇到的异常情况 (登录凭据有误除外).
支持自定义回调处理验证码和短信验证码, 以及自定义持久化存储方式.

使用示例:
- examples/how_to_use_auth_manager_basic.py 展示了一步完成登录的最简单用法.
- examples/how_to_use_auth_manager_advanced.py 展示了 SEUAuthManager 的完整功能,
    包括使用 OCR 处理 captcha, 自动获取短信验证码, 持久化 TGT 和指纹等.

Last updated: 2025-12-03
License: GPL-3.0 License
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional, Protocol, Tuple

import httpx

from . import SEUAuthClient
from .utils.crypto import rsa_encrypt
from .utils.misc import gen_fingerprint, hash_pub_key
from .utils.parse import (
    CasLoginStatus,
    GetCipherKeyStatus,
    SendStage2CodeStatus,
    parse_cas_login_resp,
    parse_get_cipher_key_resp,
    parse_need_captcha_resp,
    parse_send_stage2_code_resp,
    parse_verify_tgt_resp,
)

logger = logging.getLogger(__name__)

__all__ = ["SEUAuthManager", "AuthStorage"]

# ================= Enums & Context =================


class _AuthStep(Enum):
    """登录流程的各个步骤枚举."""

    INIT = auto()
    CHECK_LOCAL_SESSION = auto()
    FETCH_PUBLIC_KEY = auto()
    HANDLE_CAPTCHA = auto()
    PERFORM_LOGIN = auto()
    HANDLE_STAGE2_2FA = auto()
    SUCCESS = auto()
    FAILED = auto()


@dataclass
class _AuthContext:
    """保存单次登录流程中的临时状态"""

    username: str
    raw_password: str

    public_key: Optional[str] = None
    encrypted_password: Optional[str] = None
    captcha_code: str = ""
    sms_code: str = ""
    encrypted_sms_code: Optional[str] = None
    phone: str = ""
    service: str = ""

    step_retry_count: int = 0
    flow_retry_count: int = 0  # TODO: currently unused

    def reset_step_retry(self):
        self.step_retry_count = 0


# ================= Protocols (Interfaces) =================


class AuthStorage(Protocol):
    """持久化存储接口: 负责 TGT、指纹、公钥映射的存取"""

    async def load_tgt(self, username: str) -> Optional[str]:
        """尝试根据一卡通号加载对应的 TGT Cookie, 如果不存在或已过期则返回 None."""
        ...

    async def save_tgt(self, tgt: str, max_age: int, username: str):
        """保存 TGT Cookie 与过期时间, 与一卡通号绑定."""
        ...

    async def load_fingerprint(self) -> Optional[str]:
        """加载持久化存储的浏览器指纹."""
        ...

    async def save_fingerprint(self, fingerprint: str):
        """保存指纹."""
        ...

    async def get_cipher_uid(self, public_key_hash: str) -> Optional[str]:
        """根据公钥 Hash 获取缓存的 CHIPER_UID Cookie 值"""
        ...

    async def save_cipher_uid(self, public_key_hash: str, cipher_uid: str):
        """保存公钥 Hash 与 CHIPER_UID 的映射"""
        ...


# ================= Default Implementations =================


async def _default_captcha_callback(image_data: bytes) -> str:
    """默认 captcha 回调: 提示用户手动输入验证码"""
    path = Path("captcha_temp.jpg")
    with open(path, "wb") as f:
        f.write(image_data)
    print(f"\n[Interation] Captcha saved to {path.absolute()}")
    return await asyncio.to_thread(input, "Please enter captcha: ")


async def _default_sms_callback(phone: str) -> str:
    """默认短信验证码回调: 提示用户手动输入短信验证码"""
    print(f"\n[Interaction] SMS code sent to number ending with {phone}")
    return await asyncio.to_thread(input, "Please enter SMS code: ")


class _JsonFileAuthStorage:
    """默认存储: 使用本地 JSON 文件"""

    def __init__(self, filepath: str = "auth_session.json"):
        self.filepath = Path(filepath)
        self._data: Dict[str, Any] = {}
        self._load_from_disk()

    def _load_from_disk(self):
        if self.filepath.exists():
            try:
                self._data = json.loads(self.filepath.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}

    def _save_to_disk(self):
        self.filepath.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    async def load_tgt(self, username: str) -> Optional[str]:
        tgt_entry = self._data.get("tgt_map", {}).get(username)
        if not tgt_entry:
            return None

        expires_at = tgt_entry.get("expires_at")
        value = tgt_entry.get("value")
        if expires_at is None:
            return value
        if time.time() < float(expires_at):
            return value
        # expired
        self._data.get("tgt_map", {}).pop(username, None)
        self._save_to_disk()
        return None

    async def save_tgt(self, tgt: str, max_age: int, username: str):
        try:
            max_age_val = int(max_age) if max_age is not None else 0
        except Exception:
            max_age_val = 0

        expires_at = None
        if max_age_val > 0:
            expires_at = time.time() + max_age_val

        if "tgt_map" not in self._data:
            self._data["tgt_map"] = {}
        self._data["tgt_map"][username] = {"value": tgt, "expires_at": expires_at}
        self._save_to_disk()

    async def load_fingerprint(self) -> Optional[str]:
        return self._data.get("fingerprint")

    async def save_fingerprint(self, fingerprint: str):
        self._data["fingerprint"] = fingerprint
        self._save_to_disk()

    async def get_cipher_uid(self, public_key_hash: str) -> Optional[str]:
        return self._data.get("cipher_map", {}).get(public_key_hash)

    async def save_cipher_uid(self, public_key_hash: str, cipher_uid: str):
        if "cipher_map" not in self._data:
            self._data["cipher_map"] = {}
        self._data["cipher_map"][public_key_hash] = cipher_uid
        self._save_to_disk()


# ================= Manager Core =================


class SEUAuthManager:
    def __init__(
        self,
        username: str,
        password: str,
        *,
        captcha_callback: Optional[Callable[[bytes], Awaitable[str]]] = None,
        sms_callback: Optional[Callable[[str], Awaitable[str]]] = None,
        storage: Optional[AuthStorage] = None,
        max_step_retries: int = 3,
        fingerprint: Optional[str] = None,
        timeout: float = 10.0,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.username = username
        self.password = password

        self.captcha_callback = captcha_callback or _default_captcha_callback
        self.sms_callback = sms_callback or _default_sms_callback

        self.storage = storage or _JsonFileAuthStorage()

        self.max_step_retries = max_step_retries
        self._explicit_fingerprint = fingerprint

        # HTTP client options forwarded to the underlying SEUAuthClient
        self._client_timeout = timeout
        self._client_headers = headers or {}
        self._auth_client = SEUAuthClient(
            timeout=self._client_timeout, headers=self._client_headers
        )

        self._fingerprint: str = ""  # Fingerprint used in current session
        self._redirect_url: Optional[str] = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        await self._auth_client.close()

    async def login(
        self, force_refresh: bool = False, service: str = ""
    ) -> Tuple[Optional[httpx.AsyncClient], Optional[str]]:
        """登录并返回已登录的 httpx AsyncClient 实例.

        Args:
            force_refresh (bool, optional): 是否强制重新登录, 忽略本地持久化的会话.
            service (str, optional): 登录后跳转的目标服务 URL.

        Returns:
            Tuple[Optional[httpx.AsyncClient],Optional[str]]: 一个元组, 包含:
                - httpx.AsyncClient: 已登录的 httpx AsyncClient 实例, 可用于后续请求. 如果登录失败则返回 None.
                - Optional[str]: 登录后服务端返回的重定向 (如果有). 仅在登录成功时有效.
        """
        self._auth_client.open()
        await self._prepare_fingerprint()
        self._redirect_url = None

        if not force_refresh:
            if await self._try_resume_session(service=service):
                logger.info("Session resumed from storage.")
                return self._auth_client.client, self._redirect_url

        # Execute full login flow
        success = await self._execute_login_fsm(service=service)
        if success:
            logger.info("Login flow completed successfully.")
            return self._auth_client.client, self._redirect_url

        await self.close()
        return None, None

    async def _prepare_fingerprint(self):
        """确定当前会话使用的指纹, 并确保持久化"""
        # 1. From constructor parameter
        if self._explicit_fingerprint:
            self._fingerprint = self._explicit_fingerprint
            await self.storage.save_fingerprint(self._fingerprint)
            return

        # 2. From persistent storage
        stored = await self.storage.load_fingerprint()
        if stored:
            self._fingerprint = stored
            return

        # 3. Randomly generate
        self._fingerprint = gen_fingerprint()
        await self.storage.save_fingerprint(self._fingerprint)
        logger.debug(f"Generated new fingerprint: {self._fingerprint}")

    async def _try_resume_session(self, service: str = "") -> bool:
        """尝试加载之前持久化的 TGT 并检查有效性."""
        tgt = await self.storage.load_tgt(self.username)
        if not tgt:
            return False

        logger.debug("Verifying local TGT...")
        # Load TGT into client
        self._auth_client.load_cookies({"TGT": tgt})
        try:
            data = await self._auth_client.verify_tgt(service=service)
            valid, redirect_url = parse_verify_tgt_resp(data)
            if valid:
                self._redirect_url = redirect_url
                return True
        except Exception as e:
            logger.warning(f"Failed to verify local TGT: {e}")

        # Invalid TGT, clear it
        self._auth_client.client.cookies.delete("TGT")
        return False

    # ================= FSM Logic =================

    async def _execute_login_fsm(self, service: str = "") -> bool:
        # Initialize
        ctx = _AuthContext(
            username=self.username,
            raw_password=self.password,
            service=service,
        )
        current_step = _AuthStep.FETCH_PUBLIC_KEY

        while current_step not in (_AuthStep.SUCCESS, _AuthStep.FAILED):
            logger.debug(f"State: {current_step.name}, Retry: {ctx.step_retry_count}")

            # Check max retries
            if ctx.step_retry_count >= self.max_step_retries:
                logger.error(f"Max retries exceeded at step {current_step.name}")
                current_step = _AuthStep.FAILED
                break

            # Excute each step
            try:
                if current_step == _AuthStep.FETCH_PUBLIC_KEY:
                    current_step = await self._step_fetch_public_key(ctx)
                elif current_step == _AuthStep.HANDLE_CAPTCHA:
                    current_step = await self._step_handle_captcha(ctx)
                elif current_step == _AuthStep.PERFORM_LOGIN:
                    current_step = await self._step_perform_login(ctx)
                elif current_step == _AuthStep.HANDLE_STAGE2_2FA:
                    current_step = await self._step_handle_stage2(ctx)
                else:
                    logger.error(f"Unknown step: {current_step}")
                    current_step = _AuthStep.FAILED

            except Exception as e:
                logger.exception(f"Exception during step {current_step.name}: {e}")
                ctx.step_retry_count += 1

        return current_step == _AuthStep.SUCCESS

    # ================= Step Handlers =================

    async def _step_fetch_public_key(self, ctx: _AuthContext) -> _AuthStep:
        """步骤: 获取公钥, 并加密密码和短信验证码 (如果有的话).
        1. 请求公钥 (失败 -> 重试).
        2. 处理 `CHIPER_UID` Cookie 缺失的情况 (失败 -> 重试).
        3. 加密密码和短信验证码 (失败 -> 重试).
        4. 成功 -> 下一步, 处理验证码.
        """
        # 1. Fetch public key
        data = await self._auth_client.get_cipher_key()
        status, pub_key = parse_get_cipher_key_resp(data)

        if status is GetCipherKeyStatus.FAILED:
            # Retry from fetching public key
            ctx.step_retry_count += 1
            return _AuthStep.FETCH_PUBLIC_KEY

        ctx.public_key = pub_key
        key_hash = hash_pub_key(pub_key)

        # 2. Handle CHIPER_UID cookie
        cookies = self._auth_client.get_cookies()
        cipher_uid = cookies.get("CHIPER_UID")
        if cipher_uid:
            # 2.1. `CHIPER_UID` cookie is set, save to storage
            await self.storage.save_cipher_uid(key_hash, cipher_uid)
        else:
            # 2.2. `CHIPER_UID` missing (common when reused key is provided)
            logger.warning(
                "Missing CHIPER_UID cookie, attempting to recover from storage..."
            )
            cached_cipher_uid = await self.storage.get_cipher_uid(key_hash)
            # Recover from storage if possible
            if cached_cipher_uid:
                logger.info("Recovered CHIPER_UID from storage.")
                self._auth_client.load_cookies({"CHIPER_UID": cached_cipher_uid})
            else:
                logger.error("Failed to recover CHIPER_UID.")
                # Retry from fetching public key
                self._auth_client.client.cookies.clear()
                ctx.step_retry_count += 1
                return _AuthStep.FETCH_PUBLIC_KEY

        # 3. Encrypt password and SMS code (if any)
        logger.debug("Encrypting with key `%s`", ctx.public_key)
        ctx.encrypted_password = rsa_encrypt(ctx.raw_password, ctx.public_key)
        if ctx.sms_code:
            ctx.encrypted_sms_code = rsa_encrypt(ctx.sms_code, ctx.public_key)
        if not ctx.encrypted_password or (ctx.sms_code and not ctx.encrypted_sms_code):
            # Retry from fetching public key
            logger.error("RSA Encryption failed locally.")
            ctx.step_retry_count += 1
            return _AuthStep.FETCH_PUBLIC_KEY

        # Continue to the next step
        ctx.reset_step_retry()
        return _AuthStep.HANDLE_CAPTCHA

    async def _step_handle_captcha(self, ctx: _AuthContext) -> _AuthStep:
        """步骤: 检查并处理验证码
        1. 检查是否需要验证码 (无需 -> 下一步, 执行登录).
        2. 请求验证码 (失败 -> 重试).
        3. 调用指定的 handler 识别/输入验证码 (无效输入 -> 失败).
        4. 成功 -> 下一步, 执行登录.
        """
        # 1. Check if captcha is needed
        need_data = await self._auth_client.need_captcha()
        if not parse_need_captcha_resp(need_data):
            # Skip captcha, continue to login
            ctx.captcha_code = ""
            ctx.reset_step_retry()
            return _AuthStep.PERFORM_LOGIN

        # 2. Fetch captcha image
        img_data = await self._auth_client.get_captcha()
        if not img_data:
            # Retry fetching captcha
            logger.error("Failed to fetch captcha image.")
            ctx.step_retry_count += 1
            return _AuthStep.HANDLE_CAPTCHA

        # 3. Call external handler for captcha
        code = await self.captcha_callback(img_data)
        if not code:
            # Empty input is treated as cancellation
            logger.error("No captcha code provided.")
            return _AuthStep.FAILED

        # 4. Continue to login
        ctx.captcha_code = code
        ctx.reset_step_retry()
        return _AuthStep.PERFORM_LOGIN

    async def _step_perform_login(self, ctx: _AuthContext) -> _AuthStep:
        """步骤: 执行登录
        1. 使用所有准备好的参数发起登录请求.
        2. 根据响应结果决定下一步:
            - 成功 -> 持久化 TGT, 结束流程.
            - 需要二次验证 -> 继续处理二次验证.
            - 验证码错误 -> 重试验证码处理.
            - 短信验证码错误 -> 重试二次验证处理.
            - 公钥错误 -> 重试获取公钥.
            - 凭据错误 -> 结束流程失败.
            - 其他错误 -> 重试登录.
        """
        # 1. All parameters are ready, perform login
        resp = await self._auth_client.cas_login(
            username=ctx.username,
            encrypted_password=ctx.encrypted_password,
            service=ctx.service,
            captcha=ctx.captcha_code,
            fingerprint=self._fingerprint,
            encrypted_mobile_verify_code=ctx.encrypted_sms_code,
        )

        status, max_age, tgt, redirect_url = parse_cas_login_resp(resp)

        if status == CasLoginStatus.SUCCESS:
            # Successful login, persist TGT
            if tgt:
                await self.storage.save_tgt(tgt, max_age, ctx.username)
            self._redirect_url = redirect_url
            return _AuthStep.SUCCESS
        elif status == CasLoginStatus.STAGE2_REQUIRED:
            # Continue to handle 2FA
            ctx.reset_step_retry()
            return _AuthStep.HANDLE_STAGE2_2FA
        elif status == CasLoginStatus.BAD_CAPTCHA:
            # Retry from fetching captcha (don't just retry the captcha handler)
            logger.warning("Incorrect captcha.")
            ctx.captcha_code = ""
            return _AuthStep.HANDLE_CAPTCHA
        elif status == CasLoginStatus.BAD_SMS_CODE:
            # Retry from sending SMS code
            logger.warning("Incorrect SMS code.")
            ctx.sms_code = ""
            ctx.encrypted_sms_code = ""
            return _AuthStep.HANDLE_STAGE2_2FA
        elif status == CasLoginStatus.CIPHER_ERROR:
            # Retry from fetching public key
            logger.error("Cipher error during login.")
            self._auth_client.client.cookies.clear()
            return _AuthStep.FETCH_PUBLIC_KEY
        elif status == CasLoginStatus.BAD_CREDENTIALS:
            # Invalid username/password
            logger.error("Invalid username or password.")
            return _AuthStep.FAILED
        else:
            # Other errors, retry from login
            logger.error(f"Unknown login error: {resp}")
            ctx.step_retry_count += 1
            return _AuthStep.PERFORM_LOGIN

    async def _step_handle_stage2(self, ctx: _AuthContext) -> _AuthStep:
        """步骤: 处理需要二次验证的情况.
        1. 请求发送短信验证码.
        2. 调用指定的 handler 获取短信验证码 (无效输入 -> 失败).
        3. 成功 -> 获取公钥.
        """
        # 1. Trigger sending SMS code
        send_resp = await self._auth_client.send_stage2_code(ctx.username)
        status, phone = parse_send_stage2_code_resp(send_resp)

        if status is SendStage2CodeStatus.CIPHER_ERROR:
            # Retry from fetching public key
            logger.error("Cipher error when sending SMS code.")
            self._auth_client.client.cookies.clear()
            ctx.step_retry_count += 1
            return _AuthStep.FETCH_PUBLIC_KEY
        elif status is SendStage2CodeStatus.RATE_LIMITED:
            # Retry sending stage 2 code after 70 seconds
            delay = 70  # TODO: parse wait time from response in future
            logger.error("SMS code request rate limited, sleeping %d seconds.", delay)
            ctx.step_retry_count += 1
            await asyncio.sleep(delay)
            return _AuthStep.HANDLE_STAGE2_2FA
        elif status is not SendStage2CodeStatus.SUCCESS:
            # Retry sending stage 2 code
            logger.error("Failed to send SMS code.")
            ctx.step_retry_count += 1
            return _AuthStep.HANDLE_STAGE2_2FA

        ctx.phone = phone or ctx.phone

        # 2. Call external handler for SMS code
        sms_code = await self.sms_callback(ctx.phone)
        if not sms_code:
            # Empty input is treated as cancellation
            logger.error("No SMS code provided.")
            return _AuthStep.FAILED

        ctx.sms_code = sms_code

        # 3. New public key is needed, so retry from fetching it
        ctx.reset_step_retry()
        return _AuthStep.FETCH_PUBLIC_KEY

    def get_redirect_url(self) -> Optional[str]:
        """获取登录完成后服务端返回的 redirectUrl (如果有)."""
        return self._redirect_url
