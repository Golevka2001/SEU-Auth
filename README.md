# SEU-Auth

[东南大学身份认证](https://auth.seu.edu.cn/dist/#/dist/main/login)的逆向、模拟登录，可用于其他自动化脚本的身份认证过程。

- 提供简洁的方法一步完成登录，以及对关键请求的统一封装。
- 完整使用示例与文档。
- 关于身份认证系统的文档（包括请求流程与细节说明）。

**:heavy_exclamation_mark: 控制访问资源的频率在合理范围内；保管好登录凭据；不要用于撞库、攻击等非法用途。**

## :calendar: Latest Changes

> 认证系统可能不时更新，本项目无法保证一直可用，注意关注最后更新时间。

- 2025-12-03: 重构项目及文档，增加完整的异常处理和重试逻辑。能够处理当前认证系统的**短信验证**和**浏览器指纹**。

## :notebook: Documentation

[Wiki](https://github.com/Golevka2001/SEU-Auth/wiki) 中提供了更详细的文档，包括对认证系统的说明以及本项目的使用帮助。

## :rocket: Getting Started

从 [Releases](https://github.com/Golevka2001/SEU-Auth/releases) 下载 `seu_auth-x.x.x-py3-none-any.whl`

```bash
uv add ./seu_auth-x.x.x-py3-none-any.whl
```

### Basic Usage

```python
from seu_auth import SEUAuthManager

# 初始化
manager = SEUAuthManager(
    username="<一卡通号>",
    password="<密码>",
)
# 一步完成登录
async with manager:
    httpx_client, redirect_url = await manager.login(service="<目标服务 URL>")
    # 登录成功后访问目标服务
    if httpx_client is not None and redirect_url is not None:
        response = await httpx_client.get(redirect_url)
```

[这里是一个完整、可运行的简单示例](./examples/how_to_use_auth_manager_basic.py)，如果没有什么复杂需求，完全可以在该示例基础上简单修改，实现一些自动化脚本。

### Advanced Usage

#### SEUAuthManager

`SEUAuthManager` 类还提供了很多自定义选项（例如，自定义验证码回调、持久化等），可以实现**使用 OCR 处理验证码**、恢复会话以**跳过登录**等功能。

[这里是另一个示例](./examples/how_to_use_auth_manager_advanced.py)，展示了复杂一些的用法，配置了 OCR，自动获取短信验证码，以及加载 TGT Cookie 以跳过登录等。

#### SEUAuthClient

`SEUAuthClient` 是比较底层的对各关键请求的封装，除非*您想完全自己控制每个步骤，或者有其它更复杂的需求*，否则用 `SEUAuthClient` 就足够了。
如果一定要用的话，记得配合 [utils/parse.py](./src/seu_auth/utils/parse.py) 使用，将响应中的必要信息解析出来。

当然，[这里也提供了一个相应的示例](./examples/how_to_use_auth_client.py)，另外 [SEUAuthManager](./src/seu_auth/auth_manager.py) 本身也可以当做它的示例。

## :hammer_and_wrench: Development & Contribution

### Setup

```bash
git clone git@github.com:Golevka2001/SEU-Auth.git && cd SEU-Auth
uv sync --dev
```

### Dir Structure

```text
.
├── docs/                   # Wiki 中的内容
├── examples/               # 使用示例, 具体见 examples/README.md
├── src/
│   └── seu_auth/
│       ├── auth_client.py  # SEUAuthClient 实现
│       ├── auth_manager.py # SEUAuthManager 实现
│       └── utils/          # 工具函数
└── tests/                  # 测试代码
```

### Test & Build

```bash
# test
uv run pytest -v
# build
uv build
```

### Contribution

认证系统系统可能会不时更新，我也不会经常检查项目状态，如果发现问题，欢迎提交 issue 或 PR。
