"""auth_client.py
SEU 身份认证客户端基础设施模块.

SEUAuthClient 类封装了与 SEU 认证服务器的 HTTP 通信细节, 提供基础的异步请求方法.
可配合 utils/parse.py 中对应的响应解析函数使用.
适用于构建自定义认证流程或集成到更复杂的系统中, 否则建议使用更高层封装的 SEUAuthManager.

使用示例:
- examples/how_to_use_auth_client.py 展示了使用 SEUAuthClient 进行手动认证的完整流程.

Last updated: 2025-12-03
License: GPL-3.0 License
"""

import logging
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)

__all__ = ["SEUAuthClient"]


class SEUAuthClient:
    """认证客户端, 基础设施, 负责与 SEU 认证服务器进行 HTTP 通信.

    - 将完整认证流程中的各个请求封装为异步方法, 隐藏 URL 和参数构造细节.
    - 每个方法返回服务器响应的完整 JSON 字典, 可配合 utils/parse.py 使用.
    - 内部持有 httpx.AsyncClient, 管理会话和 CookieJar.
    - 不处理持久化, 重试, 回调等逻辑, 仅提供基础请求接口.
    """

    BASE_URL = "https://auth.seu.edu.cn/auth/casback/"
    ORIGIN = "https://auth.seu.edu.cn/"
    REFERER = "https://auth.seu.edu.cn/dist/"
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        timeout: float = 10.0,
        headers: Optional[Dict[str, str]] = None,
    ):
        """初始化 SEUAuthClient 实例.

        Args:
            timeout (float, optional): HTTP 请求超时时间.
            headers (Optional[Dict[str, str]], optional): 初始化 httpx 客户端时使用的自定义请求头,
                会与默认请求头合并, 覆盖默认值. 除非必要, 不建议包含 "Origin", "Referer".
        """
        self.logger = logger

        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._headers = headers or {}

    async def __aenter__(self):
        self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def open(self):
        """初始化 HTTP 客户端"""
        if self._client is None:
            self.logger.debug("Initializing httpx AsyncClient")
            self._client = httpx.AsyncClient(
                headers={
                    "Accept": "*/*",
                    "Content-Type": "application/json",
                    "Origin": self.ORIGIN,
                    "Referer": self.REFERER,
                    "User-Agent": self.DEFAULT_USER_AGENT,
                },
                timeout=self.timeout,
                follow_redirects=True,
            )
            self._client.headers.update(self._headers)

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client:
            self.logger.debug("Closing httpx AsyncClient")
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError(
                "Client is not open. Call open() or use async context manager."
            )
        return self._client

    # ========== Cookie 管理接口 ==========

    def get_cookies(self) -> Dict[str, str]:
        """导出当前 Cookie 字典"""
        return dict(self.client.cookies)

    def load_cookies(self, cookies: Dict[str, str]):
        """加载 Cookie 到当前会话"""
        self.client.cookies.update(cookies)

    def get_tgt(self) -> Optional[str]:
        """获取当前会话的 TGT Cookie 值"""
        return self.client.cookies.get("TGT")

    # ========== 基础请求封装 ==========

    async def _post(
        self, endpoint: str, json_data: Dict = None, **kwargs
    ) -> Dict[str, Any]:
        url = urljoin(self.BASE_URL, endpoint)
        self.logger.debug(
            "POST %s json=%s cookies=%s", url, json_data, self.get_cookies()
        )
        resp = await self.client.post(url, json=json_data or {}, **kwargs)
        resp.raise_for_status()
        self.logger.debug("Response: %s", resp.text)
        return resp.json()

    async def _get(self, endpoint: str, **kwargs) -> Any:
        url = urljoin(self.BASE_URL, endpoint)
        self.logger.debug("GET %s cookies=%s", url, self.get_cookies())
        resp = await self.client.get(url, **kwargs)
        resp.raise_for_status()
        # Detect response type
        if "application/json" in resp.headers.get("Content-Type", ""):
            self.logger.debug("Response: %s", resp.text)
            return resp.json()
        self.logger.debug("Response: <binary data>")
        return resp.content

    # ========== 认证相关请求封装 ==========

    async def verify_tgt(
        self, tgt: Optional[str] = None, service: Optional[str] = None
    ) -> Dict[str, Any]:
        """验证会话是否有效. 通常是浏览器访问时的第一个请求, 检查的是 Cookies 中的 TGT 值.

        Args:
            tgt (Optional[str], optional): 可选, 根据是否传入该参数有以下两种行为:
                - tgt=None, 使用当前客户端的 Cookies 验证 (通常用于在登录完成后验证登录状态).
                - tgt=str, 验证传入的 TGT 值, 不修改当前客户端的 Cookies (作为工具函数使用).
            service (Optional[str], optional): 可选, 指定跳转的服务地址.

        Returns:
            Dict[str, Any]: 服务器响应的完整 JSON 字典.

        响应示例:
        1. 已登录, 无需重复认证:
        {
            "code": 200,
            "info": "verify tgt success",
            "success": true,
            "stCookie": null,
            "redirectUrl": null
        }
        2. TGT 无效:
        {
            "code": 400,
            "info": "verify tgt Failed. tgt is not vaild",
            "success": false,
            "stCookie": null,
            "redirectUrl": null
        }
        3. Cookies 中未包含 TGT:
        {
            "code": 400,
            "info": "user not login",
            "success": false,
            "stCookie": null,
            "redirectUrl": null
        }
        """
        payload = {}
        if service is not None:
            payload["service"] = service

        if tgt is None:
            # Verify current session
            data = await self._post("verifyTgt", json_data=payload)
        else:
            # Verify provided TGT (do not mutate caller cookies)
            current_cookies = self.get_cookies()
            try:
                self._client.cookies.set("TGT", tgt)
                data = await self._post("verifyTgt", json_data=payload)
            finally:
                # Restore original cookies
                self._client.cookies.clear()
                self._client.cookies.update(current_cookies)
        # success = int(data.get("code", 0)) == 200 and bool(data.get("success"))
        return data

    async def need_captcha(self) -> Dict[str, Any]:
        """判断当前认证会话是否需要验证码.

        Raises:
            httpx.HTTPStatusError: 如果请求失败或返回非 2xx 状态码.

        Returns:
            Tuple[bool,Dict[str,Any]]: 一个元组, 包含:
                - bool: 如果需要验证码则返回 True; 否则返回 False.
                - Dict[str, Any]: 服务器响应的完整 JSON 字典.

        响应示例:
        1. 不需要验证码, 可跳过 getCaptcha 且 casLogin 中不需要提供 captcha 参数:
        {
            "tgtCookie": null,
            "redirectUrl": null,
            "code": 200,
            "info": "不需要验证码",
            "success": true,
            "maxAge": 0,
            "needStage2Validation": false
        }
        2. 需要验证码, 必须调用 getCaptcha 获取验证码图片, 并在 casLogin 中提供 captcha 参数:
        {
            "tgtCookie": null,
            "redirectUrl": null,
            "code": 4000,
            "info": "需要验证码",
            "success": true,
            "maxAge": 0,
            "needStage2Validation": false
        }
        """

        data = await self._get("needCaptcha", headers={"Accept": "*/*"})
        # need = not (
        #     int(data.get("code", 0)) == 200 and "不需要" in data.get("info", "")
        # )
        return data

    async def get_captcha(self) -> bytes:
        """获取验证码图片的二进制数据.

        Raises:
            httpx.HTTPStatusError: 如果请求失败或返回非 2xx 状态码.

        Returns:
            bytes: 响应, 即图片验证码的二进制数据.
        """
        return await self._get("getCaptcha", headers={"Accept": "*/*"})

    async def get_cipher_key(self) -> Dict[str, Any]:
        """获取加密公钥 (注意：此请求会自动设置 CHIPER_UID Cookie).

        CHIPER_UID Cookie 在后续请求中 (尤其是 casLogin) 必须携带, 否则会返回 "登录态失效/过期" 错误.
        // Typo: cipher 全被写成 chiper 了, 不知道他们以后会不会改回来.

        Raises:
            httpx.HTTPStatusError: 如果请求失败或返回非 2xx 状态码

        Returns:
            Dict[str,Any]: 服务器响应的完整 JSON 字典.

        响应示例:
        1. 成功获取公钥:
        {
            "code": 200,
            "info": "get public key success",
            "success": true,
            "publicKey": "MIGfMA0GCSqGSI..."
        }
        """
        payload = {}
        data = await self._post("getChiperKey", json_data=payload)
        return data

    async def cas_login(
        self,
        username: str,
        encrypted_password: str,
        service: str = "",
        captcha: str = "",
        fingerprint: str = "",
        encrypted_mobile_verify_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """发起登录请求.

        Args:
            username (str): 一卡通号.
            encrypted_password (str): RSA 加密后的密码.
            service (str, optional): 登录后跳转的服务地址, 默认为空字符串.
            captcha (str, optional): 图片验证码结果, 只有 needCaptcha 返回需要验证码时才需提供.
            fingerprint (str, optional): 浏览器指纹.
            encrypted_mobile_verify_code (Optional[str], optional): RSA 加密后的短信验证码, 只有需要二次验证时才需提供.

        Raises:
            httpx.HTTPStatusError: 如果请求失败或返回非 2xx 状态码

        Returns:
            Dict[str, Any]: 服务器响应的完整 JSON 字典.

        响应示例:
        1. 登录成功, 返回 TGT Cookie 和跳转 URL:
        {
            "tgtCookie": "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ...",
            "redirectUrl": null,
            "code": 200,
            "info": "Authentication Success(no service provided)",
            "success": true,
            "maxAge": -1,
            "needStage2Validation": false
        }
        2. 需要二次短信验证, 通常与 fingerPrint 有关:
        {
            "tgtCookie": null,
            "redirectUrl": null,
            "code": 502,
            "info": "非可信设备，需要二次验证",
            "success": false,
            "maxAge": 0,
            "needStage2Validation": false  // 注意: 这里是 false, 要从 code 和 info 判断
        }
        3. 其他登录失败情况, 比如密码错误, 验证码错误, 登录态过期等...
        """
        payload = {
            "service": service,
            "username": username,
            "password": encrypted_password,
            "captcha": captcha,
            "rememberMe": True,
            "loginType": "account",
            "wxBinded": False,
            "mobilePhoneNum": "",
            "fingerPrint": fingerprint,
        }

        # Only include mobileVerifyCode if provided
        if encrypted_mobile_verify_code:
            payload["mobileVerifyCode"] = encrypted_mobile_verify_code

        return await self._post("casLogin", json_data=payload)

    async def send_stage2_code(self, username: str) -> Dict[str, Any]:
        """触发二次验证短信发送.

        Args:
            username (str): 一卡通号.

        Raises:
            httpx.HTTPStatusError: 如果请求失败或返回非 2xx 状态码

        Returns:
            Dict[str, Any]: 服务器响应的完整 JSON 字典.

        响应示例:
        1. 成功发送短信验证码
        {
            "code": 200,
            "info": "验证码已发送 12345678910，5分钟有效",
            "success": true
        }
        2. 未携带 CHIPER_UID Cookie 或已过期
        {
            "code": 5002,
            "info": "登录态失效，请刷新页面重新登录",
            "success": false
        }
        """
        # # Use regex to extract phone number from info message
        # phone_num = None
        # info = resp.get("info", "")
        # match = re.search(r"(\d{11})", info)
        # if match:
        #     phone_num = match.group(1)
        return await self._post("sendStage2Code", json_data={"userId": username})

    async def cas_logout(self) -> Dict[str, Any]:
        """执行登出请求.

        Raises:
            httpx.HTTPStatusError: 如果请求失败或返回非 2xx 状态码

        Returns:
            Dict[str,Any]: 服务器响应的完整 JSON 字典.

        响应示例:
        1. 成功登出:
        {
            "code": 200,
            "info": "CASLogout Success",
            "success": true
        }
        2. 未登录或 TGT 无效:
        {
            "code": 400,
            "info": "user not login",
            "success": false
        }
        """
        # if int(resp.get("code", 0)) == 200 and bool(resp.get("success")) is True:
        #     return True
        # if all(keyword in resp.get("info", "").lower() for keyword in ["not", "login"]):
        #     # Not logged in is also considered success
        #     return True
        return await self._post("casLogout", json_data={})
