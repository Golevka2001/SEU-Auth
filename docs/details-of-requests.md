# 认证流程请求细节

本文档提供了 [认证流程概述](https://github.com/Golevka2001/SEU-Auth/wiki/overview-of-auth-process.md) 中提到的各请求的详细信息，包括参数说明、请求示例、响应示例以及注意事项。

## 相关请求详情

若您还不清楚下面每节的标题是什么，可先阅读 [认证流程概述](https://github.com/Golevka2001/SEU-Auth/wiki/overview-of-auth-process.md#主要步骤)。
避免重复，下面不再介绍各请求在认证流程中的作用。

注：下述请求示例中的 Headers 有省略，仅保留了我认为重要的部分，具体可自行抓包查看。

### verifyTGT

- Method: `POST`
- Endpoint: `verifyTGT`
- Headers: 无特殊要求
- Body: `{ "service": "<登录后要访问的服务地址>" }`

在浏览器中，通常是第一个请求。
但在脚本中，除非持久化 Cookie，否则没有必要在一开始发送此请求，建议作为成功登录后的验证请求。

<details>
<summary>请求示例</summary>

```shell
curl --request POST \
  --url https://auth.seu.edu.cn/auth/casback/verifyTgt \
  --header 'Accept: application/json' \
  --header 'Content-Type: application/json' \
  --header 'Origin: https://auth.seu.edu.cn' \
  --header 'Referer: https://auth.seu.edu.cn/dist/' \
  --header 'User-Agent: Mozilla/5.0...' \
  --data '{"service":"http://ehall.seu.edu.cn/login?service=https://ehall.seu.edu.cn/new/index.html"}'
```

如果非首次请求，应该会有下面这样的 Cookie：

```shell
  --header 'Cookie: CHIPER_UID=AGENTMD5_6235c...; TGT=eyJhb...' \
```

</details>

<details>
<summary>响应示例</summary>

1. 成功，无需重复认证

    ```json
    {
        "code": 200,
        "info": "verify tgt success",
        "success": true,
        "stCookie": null,
        "redirectUrl": null
    }
    ```

2. 成功，且有重定向链接

    ```json
    {
        "code": 201,
        "info": "CasLoginByCookieRequest Success",
        "success": true,
        "stCookie": null,
        "redirectUrl": "http://ehall.seu.edu.cn/login?service=https://ehall.seu.edu.cn/new/index.html&ticket=ST-23854..."
    }
    ```

3. TGT 无效

    ```json
    {
        "code": 400,
        "info": "verify tgt Failed. tgt is not vaild",
        "success": false,
        "stCookie": null,
        "redirectUrl": null
    }
    ```

4. Cookies 中未包含 TGT

    ```json
    {
        "code": 400,
        "info": "user not login",
        "success": false,
        "stCookie": null,
        "redirectUrl": null
    }
    ```

</details>

### needCaptcha

- Method: `GET`
- Endpoint: `needCaptcha`
- Headers: 无特殊要求

必须在 casLogin 前执行，

- 如返回需要验证码，则要 getCaptcha 获取验证码图片，并将结果传入 casLogin 的 `captcha` 参数。
- 若不需要验证码，则跳过 getCaptcha，casLogin 中 `captcha=""` 即可。

<details>
<summary>请求示例</summary>

```shell
curl --request GET \
  --url https://auth.seu.edu.cn/auth/casback/needCaptcha \
  --header 'Accept: */*' \
  --header 'Content-Type: application/json' \
  --header 'Referer: https://auth.seu.edu.cn/dist/' \
  --header 'User-Agent: Mozilla/5.0...'
```

</details>

<details>
<summary>响应示例</summary>

1. 不需要验证码

    ```json
    {
        "tgtCookie": null,
        "redirectUrl": null,
        "code": 200,
        "info": "不需要验证码",
        "success": true,
        "maxAge": 0,
        "needStage2Validation": false
    }
    ```

2. 需要验证码

    ```json
    {
        "tgtCookie": null,
        "redirectUrl": null,
        "code": 4000,
        "info": "需要验证码",
        "success": true,
        "maxAge": 0,
        "needStage2Validation": false
    }
    ```

</details>

### getCaptcha

- Method: `GET`
- Endpoint: `getCaptcha`
- Headers: `Accept: */*`

返回的是一张验证码图片的**二进制数据**。

关于使用 OCR 处理验证码，可以看看 [SEU-Captcha](https://github.com/Golevka2001/SEU-Captcha)，识别准确率在 80% ~ 90%（这验证码有时候我人眼也分不清 :sweat_smile:）。

<details>
<summary>请求示例</summary>

```shell
curl --request GET \
  --url https://auth.seu.edu.cn/auth/casback/getCaptcha \
  --header 'Accept: */*' \
  --header 'Referer: https://auth.seu.edu.cn/dist/' \
  --header 'User-Agent: Mozilla/5.0...'
```

</details>

### getChiperKey

- Method: `POST`
- Endpoint: `getChiperKey`
- Headers: 无特殊要求
- Body: `{}`（空 JSON 对象）

*:warning: 不知道他们是否会修正拼写错误，本端点或许存在较大的过时风险。*

返回的是 RSA 公钥 **PEM 头部之间的数据**，并且是 **Base64URL** 编码的。
根据要使用的加密库，可能需要转为标准的 Base64，再补充上 PEM 头尾。

注意：该请求会设置 `CHIPER_UID` Cookie，在后续请求中（尤其是 `casLogin` 和 `sendStage2Code`）必须携带，否则会返回登录态失效/过期的错误。

如果需要二次认证，会再次发送该请求，获取新的公钥和 `CHIPER_UID`。

> [!CAUTION]
> 存在复用公钥的情况：当上次请求的公钥**未被使用且未过期**时，再次请求会返回相同的公钥并提示 reuse（见下方响应示例）。
> 复用公钥的响应中不含 `CHIPER_UID` Cookie，也就是说如果您没有保存上次的 `CHIPER_UID`，服务端将无法正确处理登录请求，会导致**一段时间内无法登录**，直到该*公钥过期*被重新生成.

<details>
<summary>请求示例</summary>

```shell
curl --request POST \
  --url https://auth.seu.edu.cn/auth/casback/getChiperKey \
  --header 'Accept: application/json' \
  --header 'Content-Type: application/json' \
  --header 'Origin: https://auth.seu.edu.cn' \
  --header 'Referer: https://auth.seu.edu.cn/dist/' \
  --header 'User-Agent: Mozilla/5.0...'
  --data '{}'
```

</details>

<details>
<summary>响应示例</summary>

1. 成功获取公钥

    ```json
    {
        "code": 200,
        "info": "get public key success",
        "success": true,
        "publicKey": "MIGfMA0GCSqGSI..."
    }
    ```

    且 Headers 中会有这样的 Set-Cookie：`CHIPER_UID=AGENTMD5_fa84c...`

2. 成功获取公钥，但为复用公钥

    ```json
    {
        "code": 200,
        "info": "get reuse public key success",
        "success": true,
        "publicKey": "MIGfM..."
    }
    ```

    该响应中不含 Set-Cookie。

</details>

### casLogin

- Method: `POST`
- Endpoint: `casLogin`
- Headers: 必须携带 `CHIPER_UID` Cookie
- Body:

    ```json
    {
        "service": "<登录后跳转的服务地址>",  // 不需要可留空
        "username": "<一卡通号>",  // 必须
        "password": "<加密的密码>",  // 必须，加密相关内容见后续文档
        "captcha": "<图片验证码>",  // 不需要可留空
        "rememberMe": true,  // 没测试有没有用
        "loginType": "account",  //没用
        "wxBinded": false,  // 没用
        "mobilePhoneNum": "",  // 没用
        "mobileVerifyCode": "<加密的短信验证码>",  // 首次登录不需要该字段，二次认证时必须
        "fingerPrint": "<设备指纹>"  // 可以从真实请求中复制，或者生成一个，其实随便填一串十六进制字符也无所谓，记得持久化
    }
    ```

填好上述参数后，即可发送登录请求，可能会被要求二次认证（和 `fingerPrint` 有较大关系）。
二次验证时，需要请求发送短信验证码，并再次获取公钥，加密密码和短信验证码，更新 Body 再次发送该请求。

`fingerPrint` 为 [fingerprintjs](https://github.com/fingerprintjs/fingerprintjs) 生成的设备指纹，你可以从浏览器真实请求中复制，或者从[在线演示](https://fingerprintjs.github.io/fingerprintjs/) 获得。
目前没发现有什么严格的限制，随便填一串十六进制字符也无所谓，总之记得持久化，应该能够减少二次认证的概率。

注：若第一次被登录需要 captcha，又触发了二次认证，那么第二次登录请求中的 `captcha` 留空即可（截至本文最后更新时有效）。

<details>
<summary>请求示例</summary>

```shell
curl --request POST \
  --url https://auth.seu.edu.cn/auth/casback/casLogin \
  --header 'Accept: application/json' \
  --header 'Content-Type: application/json' \
  --header 'Cookie: CHIPER_UID=AGENTMD5_6235c...' \
  --header 'Origin: https://auth.seu.edu.cn' \
  --header 'Referer: https://auth.seu.edu.cn/dist/' \
  --header 'User-Agent: Mozilla/5.0...' \
  --data '{
 "service": "",
 "username": "123456789",
 "password": "KmNU7...",
 "captcha": "abcd",
 "rememberMe": true,
 "loginType": "account",
 "wxBinded": false,
 "mobilePhoneNum": "",
 "fingerPrint": "5a663..."
}'
```

如果是二次认证，Body 中还需要包含 `mobileVerifyCode` 参数，即短信验证码的加密结果。

</details>

<details>
<summary>响应示例</summary>

1. 成功

    ```json
    {
        "tgtCookie": "eyJhb...",
        "redirectUrl": null,
        "code": 200,
        "info": "Authentication Success(no service provided)",
        "success": true,
        "maxAge": -1,
        "needStage2Validation": false
    }
    ```

2. 成功，有重定向链接

    ```json
    {
        "tgtCookie": "eyJhb...",
        "redirectUrl": "http%3A%2F%2Fehall.seu.edu.cn%2Flogin%3Fservice%3Dhttps%3A%2F%2Fehall.seu.edu.cn%2Fnew%2Findex.html%26ticket%3DST-31300...",
        "code": 201,
        "info": "Authentication Success(with service provided)",
        "success": true,
        "maxAge": -1,
        "needStage2Validation": false
    }
    ```

3. 需要二次认证

    ```json
    {
        "tgtCookie": null,
        "redirectUrl": null,
        "code": 502,
        "info": "非可信设备，需要二次验证",
        "success": false,
        "maxAge": 0,
        "needStage2Validation": false
    }
    ```

4. 凭据错误

    ```json
    {
        "tgtCookie": null,
        "redirectUrl": null,
        "code": 402,
        "info": "用户名或密码错误",
        "success": false,
        "maxAge": 0,
        "needStage2Validation": false
    }
    ```

    ```json
    {
        "tgtCookie": null,
        "redirectUrl": null,
        "code": 500,
        "info": "用户名含有非法字符",
        "success": false,
        "maxAge": 0,
        "needStage2Validation": false
    }
    ```

    ```json
    {
        "tgtCookie": null,
        "redirectUrl": null,
        "code": 500,
        "info": "登录者用户名为空，禁止登录",
        "success": false,
        "maxAge": 0,
        "needStage2Validation": false
    }
    ```

5. Captcha 未提供或错误

    ```json
    {
        "tgtCookie": null,
        "redirectUrl": null,
        "code": 4000,
        "info": "未填写验证码",
        "success": false,
        "maxAge": 0,
        "needStage2Validation": false
    }
    ```

    ```json
    {
        "tgtCookie": null,
        "redirectUrl": null,
        "code": 4001,
        "info": "验证码错误",
        "success": false,
        "maxAge": 0,
        "needStage2Validation": false
    }
    ```

6. 短信验证码错误

    ```json
    {
        "tgtCookie": null,
        "redirectUrl": null,
        "code": 503,
        "info": "验证码错误",
        "success": false,
        "maxAge": 0,
        "needStage2Validation": false
    }
    ```

7. `CHIPER_UID` 缺失或无效

    ```json
    {
        "tgtCookie": null,
        "redirectUrl": null,
        "code": 500,
        "info": "访问速度过快，请重新刷新页面",
        "success": false,
        "maxAge": 0,
        "needStage2Validation": false
    }
    ```

    ```json
    {
        "tgtCookie": null,
        "redirectUrl": null,
        "code": 500,
        "info": "登陆态已过期，请刷新页面重新登陆",
        "success": false,
        "maxAge": 0,
        "needStage2Validation": false
    }
    ```

</details>

### sendStage2Code

- Method: `POST`
- Endpoint: `sendStage2Code`
- Headers: 必须携带 `CHIPER_UID` Cookie
- Body: `{ "userId": "<一卡通号>" }`

触发发送短信验证码到用户绑定的手机号，与 `casLogin` 中的 `mobilePhoneNum` 无关。

<details>
<summary>请求示例</summary>

```shell
curl --request POST \
  --url https://auth.seu.edu.cn/auth/casback/sendStage2Code \
  --header 'Accept: application/json' \
  --header 'Content-Type: application/json' \
  --header 'Cookie: CHIPER_UID=AGENTMD5_814cd561984b4ed29c1501af1ea7cbd9' \
  --header 'Origin: https://auth.seu.edu.cn' \
  --header 'Referer: https://auth.seu.edu.cn/dist/' \
  --header 'User-Agent: Mozilla/5.0...' \
  --data '{
 "userId": "123456789"
}'
```

</details>

<details>
<summary>响应示例</summary>

1. 成功

    ```json
    {
        "code": 200,
        "info": "验证码已发送 18812345678，5分钟有效",
        "success": true
    }
    ```

2. 速率限制

    ```json
    {
        "code": 5001,
        "info": "短时间内发送验证码次数过多，请等候60秒再重试",
        "success": false
    }
    ```

3. `CHIPER_UID` 缺失或无效

    ```json
    {
        "code": 5002,
        "info": "登录态失效，请刷新页面重新登录",
        "success": false
    }
    ```

</details>

### casLogout

- Method: `POST`
- Endpoint: `casLogout`
- Headers: 必须携带 `TGT` Cookie
- Body: `{}`

发送该请求即可登出当前会话，`TGT` 应该会被服务端删除。

<details>
<summary>请求示例</summary>

```shell
curl --request POST \
  --url https://auth.seu.edu.cn/auth/casback/casLogout \
  --header 'Accept: application/json' \
  --header 'Content-Type: application/json' \
  --header 'Cookie: CHIPER_UID=AGENTMD5_e92ed...;TGT=eyJhb...' \
  --header 'Origin: https://auth.seu.edu.cn' \
  --header 'Referer: https://auth.seu.edu.cn/dist/' \
  --header 'User-Agent: Mozilla/5.0...' \
  --data '{}'
```

</details>

<details>
<summary>响应示例</summary>

1. 成功

    ```json
    {
        "code": 200,
        "info": "CASLogout Success",
        "success": true
    }
    ```

2. 未登录

    ```json
    {
        "code": 400,
        "info": "user not login",
        "success": false
    }
    ```

</details>
