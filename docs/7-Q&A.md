# Q&A

## 自动化处理图形验证码的方法

可以使用 OCR 来处理，另一个库 [SEU-Captcha](https://github.com/Golevka2001/SEU-Captcha) 提供了训练好的模型，还有本地生成训练样本的方法。

自定义 `SEUAuthManager` 的 Captcha 回调即可（在 [此示例](https://github.com/Golevka2001/SEU-Auth/examples/how_to_use_auth_manager_advanced.py) 中有展示，可直接使用）。

## 自动化处理短信验证码的方法

不值得费这么大劲。

如果一定要的话，可以试试用 [SmsForwarder](https://github.com/pppscn/SmsForwarder) 将验证码短信转发到邮箱或是 webhook，然后自定义回调来获取。

## 如何触发需要图形验证码？

使用*不匹配的用户名和密码*[^1]尝试登录[^2] 4 次以上 (非确切值)， `needCaptcha` 将会返回需要验证码。

[^1]: 不存在的用户名也可以。
[^2]: `getChiperKey` + `casLogin` 记为一次登录尝试。

## 如何触发需要短信验证码？

使用一个新的 `fingerPrint`[^3] 尝试登录，并确保流程正确，其他参数无误。

[^3]: 不要求是[真实生成](https://fingerprintjs.github.io/fingerprintjs)的。

## 短信验证码的速率限制

连续 4 次请求发送验证码，每次间隔 10 秒左右，触发速率限制，要求 60 秒后重试。
没有具体测试能容忍的时间间隔，以及是否有更长的等待时间。

## 指纹起什么作用？

见 [指纹相关](https://github.com/Golevka2001/SEU-Auth/wiki/fingerprint.md)。
