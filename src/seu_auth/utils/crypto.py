"""crypto.py
加密工具模块, 提供 RSA 加密功能.

Last Update: 2025-12-03
License: GPL-3.0 License
"""

import base64
import logging
from typing import Optional

from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

logger = logging.getLogger(__name__)


def rsa_encrypt(message: str, pub_key: str) -> Optional[str]:
    """使用 RSA 公钥加密消息, 在本项目中主要用于加密用户密码和短信验证码.

    网页端使用 [JSEncrypt](https://github.com/travist/jsencrypt) 进行 RSA 相关操作.
    使用 PKCS#1 v1.5 填充模式, 对加密后的数据进行 Base64 编码.

    Args:
        message (str): 要加密的消息 (UTF-8 字符串).
        pub_key (str): RSA 公钥 (Base64/Base64URL 编码均可, PEM 格式, 含不含头尾标记均可).

    Returns:
        Optional[str]: 加密后消息的 Base64 编码, 如果加密失败则返回 None.
    """
    try:
        # Normalize the PEM public key
        pem_key = _normalize_pem_public_key(pub_key)
        rsa_key = RSA.import_key(pem_key)

        # Check message size
        key_size = rsa_key.size_in_bytes()
        message_bytes = message.encode("utf-8")
        max_message_size = key_size - 11  # PKCS#1 v1.5 padding overhead
        if len(message_bytes) > max_message_size:
            raise ValueError(
                f"Message is too long: {len(message_bytes)} bytes, "
                f"max {max_message_size} bytes"
            )

        # Encrypt
        cipher = PKCS1_v1_5.new(rsa_key)
        ciphertext = cipher.encrypt(message_bytes)

        return base64.b64encode(ciphertext).decode("utf-8")
    except Exception as e:
        logger.error(f"RSA encryption failed: {e}")
        return None


def _normalize_pem_public_key(pub_key: str) -> str:
    """规范化 PEM 格式的公钥字符串, 包括 Base64URL 到 Base64 的转换, 以及添加头尾标记.

    如果公钥已经是规范的 PEM 格式, 则不会重复添加头尾标记.

    Args:
        pub_key (str): RSA 公钥的 Base64/Base64URL 编码字符串 (PEM 格式, 可不含头尾标记).

    Returns:
        str: 规范化后的 PEM 格式公钥字符串.
    """
    pub_key = pub_key.strip()

    # Base64URL to Base64 ('-' -> '+', '_' -> '/')
    pub_key_base64 = pub_key.replace("-", "+").replace("_", "/")

    # Reconstruct the PEM formatted public key
    beginning = "-----BEGIN PUBLIC KEY-----"
    ending = "-----END PUBLIC KEY-----"
    pem_key = pub_key_base64
    if not pub_key_base64.startswith(beginning):
        pem_key = f"{beginning}\n{pem_key}"
    if not pub_key_base64.endswith(ending):
        pem_key = f"{pem_key}\n{ending}"

    return pem_key
