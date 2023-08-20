# SEU-Login
东南大学新版身份认证页面的逆向，模拟登录，可用于其他自动化脚本的身份认证过程。

在 [`login.py`](./login.py) 中实现了模拟登录[新版身份认证系统](https://auth.seu.edu.cn/dist/#/dist/main/login)，流程如下：

1. 函数 `get_pub_key()` 从服务器请求 RSA 公钥，以及存储与公钥相匹配的 cookie；
2. 函数 `rsa_encrypt()` 对用户密码进行 RSA 加密；
3. 函数 `login()` 中调用以上两个函数，向服务器发送用户名（一卡通号）、加密后的密码，以及先前获取到的cookie，模拟登录。

web 请求使用到 `requests` 库，RSA 加密使用到 `pycryptodome` 库。
