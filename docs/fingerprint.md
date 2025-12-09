# 指纹相关

前端使用 [fingerprintjs](https://github.com/fingerprintjs/fingerprintjs) 生成客户端指纹，服务端根据该指纹判断是否为“熟悉的设备”，从而决定**是否需要二次认证**。
如果留空，基本每次都会被要求进行二次认证。

目前来看，没有什么复杂的校验逻辑，也不要求指纹格式与生成的一致，只要传入一个通过身份验证的指纹即可避免二次认证（大部分情况下）。

`SEUAuthManager` 在用户没有提供指纹时会随机生成一个（下面的 3），并支持持久化以复用。

## 怎么获取一个指纹？

1. 【守序】 浏览器访问[认证页面](https://auth.seu.edu.cn/dist/#/dist/main/login)，打开 dev tools，登录成功后找到 `casLogin` 请求，复制 payload 中的 `fingerPrint`。
2. 【中立】 访问 fingerprintjs 的[在线演示](https://fingerprintjs.github.io/fingerprintjs)，就能看到当前的浏览器指纹。
3. 【混乱】 `secrets.token_hex(16)` 生成一个 32 字符的 HEX 字符串。
4. 【混乱】 随便输一串。
