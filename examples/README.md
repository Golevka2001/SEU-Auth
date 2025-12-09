# SEU-Auth 的使用示例

- 想要尽可能简单地完成登录 - 可参考 [how_to_use_auth_manager_basic.py](./how_to_use_auth_manager_basic.py)
  - 这是一个最简单的示例，可以一步完成登录并访问目标服务

- 想要减少认证环节的出现/自动化处理验证码 - 可参考 [how_to_use_auth_manager_advanced.py](./how_to_use_auth_manager_advanced.py)
  - 展示了 `SEUAuthManager` 的更多自定义选项，例如使用 OCR 处理验证码、自动获取短信验证码，以及加载 TGT Cookie 以跳过登录等
  - [ddddocr_models](./ddddocr_model/) 目录下为已经训练好的验证码识别模型，更多信息可查看 [SEU-Captcha](https://github.com/Golevka2001/SEU-Captcha)

- 如果仍无法满足需求 - 可参考 [how_to_use_auth_client.py](./how_to_use_auth_client.py)
  - 该示例展示了如何使用更底层的 `SEUAuthClient` 类，提供了对登录流程的完全控制

## How to run

在 [config.ini](./config.ini) 中配置好账号信息后，运行以下命令：

```bash
cd /path/to/SEU-Auth
uv run -m examples.how_to_use_auth_manager_basic
# or
uv run -m examples.how_to_use_auth_manager_advanced  # 还需要填写你自己的 IMAP 信息
# or
uv run -m examples.how_to_use_auth_client
```
