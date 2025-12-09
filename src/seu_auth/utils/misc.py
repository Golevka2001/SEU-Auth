"""misc.py
其他辅助函数.

Last Update: 2025-12-03
License: GPL-3.0 License
"""

import hashlib
import secrets


def hash_pub_key(key: str) -> str:
    """计算公钥 Hash 用于 Map 索引"""
    clean = key.replace("\n", "").replace(" ", "").replace("\r", "")
    return hashlib.md5(clean.encode()).hexdigest()


def gen_fingerprint() -> str:
    """生成随机指纹"""
    return secrets.token_hex(16)
