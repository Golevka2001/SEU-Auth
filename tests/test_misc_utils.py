"""test_misc_utils.py
对 utils.misc 模块的单元测试
"""

import re

import pytest

from seu_auth.utils import gen_fingerprint

def test_gen_fingerprint_hex_length_and_uniqueness():
    fp1 = gen_fingerprint()
    fp2 = gen_fingerprint()

    assert isinstance(fp1, str)
    assert isinstance(fp2, str)
    assert len(fp1) == 32
    assert len(fp2) == 32
    assert re.fullmatch(r"[0-9a-f]{32}", fp1)
    assert re.fullmatch(r"[0-9a-f]{32}", fp2)
    assert fp1 != fp2  # Very low probability of collision


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
