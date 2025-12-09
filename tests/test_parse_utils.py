"""test_parse_utils.py
对 utils.parse 模块的单元测试
"""

import pytest

from seu_auth.utils import (
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


class TestParseVerifyTgtResp:
    def test_when_session_valid_with_redirect(self):
        """场景：有效会话且包含重定向 URL"""
        resp = {
            "code": 201,
            "info": "CasLoginByCookieRequest Success",
            "success": True,
            "stCookie": None,
            "redirectUrl": "http://ehall.seu.edu.cn/login?service=https://ehall.seu.edu.cn/new/index.html&ticket=ST-23854...",
        }
        valid, redirect_url = parse_verify_tgt_resp(resp)
        assert valid is True
        assert (
            redirect_url
            == "http://ehall.seu.edu.cn/login?service=https://ehall.seu.edu.cn/new/index.html&ticket=ST-23854..."
        )

    def test_when_session_valid_without_redirect(self):
        """场景：有效会话且无重定向 URL"""
        resp = {
            "code": 200,
            "info": "verify tgt success",
            "success": True,
            "stCookie": None,
            "redirectUrl": None,
        }
        valid, redirect_url = parse_verify_tgt_resp(resp)
        assert valid is True
        assert redirect_url is None

    def test_when_not_logged_in(self):
        """场景：未登录状态"""
        resp = {
            "code": 400,
            "info": "user not login",
            "success": False,
            "stCookie": None,
            "redirectUrl": None,
        }
        valid, redirect_url = parse_verify_tgt_resp(resp)
        assert valid is False
        assert redirect_url is None

    def test_when_verify_failed(self):
        """场景：success 字段为 False"""
        resp = {
            "code": 400,
            "info": "verify tgt Failed. tgt is not vaild",
            "success": False,
            "stCookie": None,
            "redirectUrl": None,
        }
        valid, redirect_url = parse_verify_tgt_resp(resp)
        assert valid is False
        assert redirect_url is None

    def test_when_fields_missing(self):
        """场景：缺少字段视为无效会话"""
        resp = {}
        valid, redirect_url = parse_verify_tgt_resp(resp)
        assert valid is False
        assert redirect_url is None


class TestParseNeedCaptchaResp:
    """parse_need_captcha_resp 的测试用例"""

    def test_when_captcha_required(self):
        """场景：需要验证码"""
        resp = {
            "tgtCookie": None,
            "redirectUrl": None,
            "code": 4000,
            "info": "需要验证码",
            "success": True,
            "maxAge": 0,
            "needStage2Validation": False,
        }
        result = parse_need_captcha_resp(resp)
        assert result is True

    def test_when_captcha_not_required(self):
        """场景：不需要验证码"""
        resp = {
            "tgtCookie": None,
            "redirectUrl": None,
            "code": 200,
            "info": "不需要验证码",
            "success": True,
            "maxAge": 0,
            "needStage2Validation": False,
        }
        result = parse_need_captcha_resp(resp)
        assert result is False

    def test_when_captcha_field_missing(self):
        """场景：缺少字段视为需要验证码"""
        resp = {}
        result = parse_need_captcha_resp(resp)
        assert result is True


class TestParseGetCipherKeyResp:
    """parse_get_cipher_key_resp 的测试用例"""

    def test_when_new_key_retrieved(self):
        """场景：成功获取新公钥"""
        resp = {
            "code": 200,
            "info": "get public key success",
            "success": True,
            "publicKey": "MIGfM...",
        }
        status, public_key = parse_get_cipher_key_resp(resp)
        assert status is GetCipherKeyStatus.SUCCESS
        assert public_key == "MIGfM..."

    def test_when_reused_key_retrieved(self):
        """场景：成功获取复用公钥"""
        resp = {
            "code": 200,
            "info": "get reuse public key success",
            "success": True,
            "publicKey": "MIGfM...",
        }
        status, public_key = parse_get_cipher_key_resp(resp)
        assert status is GetCipherKeyStatus.REUSE
        assert public_key == "MIGfM..."

    def test_when_invalid_code_returns_none(self):
        """场景：响应码无效返回 None"""
        resp = {
            "code": 400,
            "info": "agent not recogonized",
            "success": False,
            "publicKey": None,
        }
        status, public_key = parse_get_cipher_key_resp(resp)
        assert status is GetCipherKeyStatus.FAILED

    def test_when_cipher_key_fields_missing(self):
        """场景：缺少字段"""
        resp = {}
        status, public_key = parse_get_cipher_key_resp(resp)
        assert status is GetCipherKeyStatus.FAILED


class TestParseCasLoginResp:
    """parse_cas_login_resp 的测试用例"""

    def test_when_login_success_without_redirect(self):
        """场景：登录成功且无重定向 URL"""
        resp = {
            "tgtCookie": "eyJhb...",
            "redirectUrl": None,
            "code": 200,
            "info": "Authentication Success(no service provided)",
            "success": True,
            "maxAge": -1,
            "needStage2Validation": False,
        }
        status, max_age, tgt, redirect_url = parse_cas_login_resp(resp)
        assert status is CasLoginStatus.SUCCESS
        assert max_age == -1
        assert tgt == "eyJhb..."
        assert redirect_url == None

    def test_when_login_success_with_redirect(self):
        """场景：登录成功且有重定向 URL"""
        resp = {
            "tgtCookie": "eyJhb...",
            "redirectUrl": "http%3A%2F%2Fehall.seu.edu.cn%2Flogin%3Fservice%3Dhttps%3A%2F%2Fehall.seu.edu.cn%2Fnew%2Findex.html%26ticket%3DST-31300...",
            "code": 200,
            "info": "Authentication and get st Success",
            "success": True,
            "maxAge": -1,
            "needStage2Validation": False,
        }
        status, max_age, tgt, redirect_url = parse_cas_login_resp(resp)
        assert status is CasLoginStatus.SUCCESS
        assert max_age == -1
        assert tgt == "eyJhb..."
        assert (
            redirect_url
            == "http://ehall.seu.edu.cn/login?service=https://ehall.seu.edu.cn/new/index.html&ticket=ST-31300..."
        )

    def test_when_stage2_validation_required(self):
        """场景：登录需要二次验证"""
        resp = {
            "tgtCookie": None,
            "redirectUrl": None,
            "code": 502,
            "info": "非可信设备，需要二次验证",
            "success": False,
            "maxAge": 0,
            "needStage2Validation": False,
        }
        status, max_age, tgt, redirect_url = parse_cas_login_resp(resp)
        assert status is CasLoginStatus.STAGE2_REQUIRED

    def test_when_credentials_invalid(self):
        """场景：登录失败（凭证错误）"""
        resp = {
            "tgtCookie": None,
            "redirectUrl": None,
            "code": 402,
            "info": "用户名或密码错误",
            "success": False,
            "maxAge": 0,
            "needStage2Validation": False,
        }
        status, max_age, tgt, redirect_url = parse_cas_login_resp(resp)
        assert status is CasLoginStatus.BAD_CREDENTIALS

    def test_when_credentials_invalid2(self):
        """场景：登录失败（凭证错误）"""
        resp = {
            "tgtCookie": None,
            "redirectUrl": None,
            "code": 500,
            "info": "登录者用户名为空，禁止登录",
            "success": False,
            "maxAge": 0,
            "needStage2Validation": False,
        }
        status, max_age, tgt, redirect_url = parse_cas_login_resp(resp)
        assert status is CasLoginStatus.BAD_CREDENTIALS

    def test_when_captcha_missing(self):
        """场景：登录失败（未提供验证码）"""
        resp = {
            "tgtCookie": None,
            "redirectUrl": None,
            "code": 4000,
            "info": "未填写验证码",
            "success": False,
            "maxAge": 0,
            "needStage2Validation": False,
        }
        status, max_age, tgt, redirect_url = parse_cas_login_resp(resp)
        assert status is CasLoginStatus.BAD_CAPTCHA

    def test_when_captcha_incorrect(self):
        """场景：登录失败（验证码错误）"""
        resp = {
            "tgtCookie": None,
            "redirectUrl": None,
            "code": 4001,
            "info": "验证码错误",
            "success": False,
            "maxAge": 0,
            "needStage2Validation": False,
        }
        status, max_age, tgt, redirect_url = parse_cas_login_resp(resp)
        assert status is CasLoginStatus.BAD_CAPTCHA

    def test_when_sms_code_incorrect(self):
        """场景：登录失败（短信验证码错误）"""
        resp = {
            "tgtCookie": None,
            "redirectUrl": None,
            "code": 503,
            "info": "验证码错误",
            "success": False,
            "maxAge": 0,
            "needStage2Validation": False,
        }
        status, max_age, tgt, redirect_url = parse_cas_login_resp(resp)
        assert status is CasLoginStatus.BAD_SMS_CODE

    def test_when_cipher_uid_invalid(self):
        """场景：登录失败（CHIPER_UID 无效或未携带）"""
        resp = {
            "tgtCookie": None,
            "redirectUrl": None,
            "code": 500,
            "info": "访问速度过快，请重新刷新页面",
            "success": False,
            "maxAge": 0,
            "needStage2Validation": False,
        }
        status, max_age, tgt, redirect_url = parse_cas_login_resp(resp)
        assert status is CasLoginStatus.CIPHER_ERROR

    def test_when_cipher_uid_invalid2(self):
        """场景：登录失败（CHIPER_UID 无效或未携带）"""
        resp = {
            "tgtCookie": None,
            "redirectUrl": None,
            "code": 500,
            "info": "登陆态已过期，请刷新页面重新登陆",
            "success": False,
            "maxAge": 0,
            "needStage2Validation": False,
        }
        status, max_age, tgt, redirect_url = parse_cas_login_resp(resp)
        assert status is CasLoginStatus.CIPHER_ERROR

    def test_when_login_fields_missing(self):
        """场景：缺少字段"""
        resp = {}
        status, max_age, tgt, redirect_url = parse_cas_login_resp(resp)
        assert status is CasLoginStatus.FAILED


class TestParseSendStage2CodeResp:
    """parse_send_stage2_code_resp 的测试用例"""

    def test_when_stage2_code_sent(self):
        """场景：验证码发送成功"""
        resp = {
            "code": 200,
            "info": "验证码已发送 18812345678，5分钟有效",
            "success": True,
        }
        status, phone = parse_send_stage2_code_resp(resp)
        assert status is SendStage2CodeStatus.SUCCESS
        assert phone == "18812345678"

    def test_when_chiper_uid_invalid(self):
        """场景：CHIPER_UID 无效或未携带导致发送失败"""
        resp = {
            "code": 5002,
            "info": "登录态失效，请刷新页面重新登录",
            "success": False,
        }
        status, phone = parse_send_stage2_code_resp(resp)
        assert status is SendStage2CodeStatus.CIPHER_ERROR

    def test_when_rate_limited(self):
        """场景：请求频率过高导致发送失败"""
        resp = {
            "code": 5001,
            "info": "短时间内发送验证码次数过多，请等候60秒再重试",
            "success": False,
        }
        status, phone = parse_send_stage2_code_resp(resp)
        assert status is SendStage2CodeStatus.RATE_LIMITED

    def test_when_stage2_response_fields_missing(self):
        """场景：缺少字段"""
        resp = {}
        status, phone = parse_send_stage2_code_resp(resp)
        assert status is SendStage2CodeStatus.FAILED


class TestParseCasLogoutResp:
    """parse_cas_logout_resp 的测试用例"""

    def test_when_logout_successful(self):
        """场景：登出成功"""
        resp = {
            "code": 200,
            "info": "CASLogout Success",
            "success": True,
        }
        result = parse_cas_logout_resp(resp)
        assert result is True

    def test_when_logout_not_logged_in_treated_success(self):
        """场景：未登录状态视为成功"""
        resp = {
            "code": 400,
            "info": "user not login",
            "success": False,
        }
        result = parse_cas_logout_resp(resp)
        assert result is True

    def test_when_logout_fields_missing(self):
        """场景：登出失败（缺少字段）"""
        resp = {}
        result = parse_cas_logout_resp(resp)
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
