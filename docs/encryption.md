# 加密相关

## 流程图

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant Server as CAS服务端
    participant KeyStore as 密钥存储
    participant AuthDB as 认证数据库
    
    Client->>Server: 请求公钥
    activate Server
    Server->>KeyStore: 生成 RSA 密钥对
    activate KeyStore
    KeyStore-->>Server: 公钥 + UID
    deactivate KeyStore
    Server-->>Client: 返回公钥和 UID
    deactivate Server
    
    Client->>Client: 公钥加密凭据
    Client->>Server: 发送加密内容 + UID
    activate Server
    Server->>KeyStore: 根据 UID 获取对应私钥
    activate KeyStore
    KeyStore-->>Server: 返回私钥
    deactivate KeyStore
    Server->>Server: 私钥解密内容
    Server->>AuthDB: 验证用户凭据
    activate AuthDB
    AuthDB-->>Server: 返回验证结果
    deactivate AuthDB
    Server-->>Client: 返回验证结果
    deactivate Server
```

## 使用的算法/库

- RSA
- PKCS#1 v1.5 填充
- 公钥为 PEM 格式，但不含头尾标识行，且为 Base64URL 编码
- 前端使用 [JSEncrypt](https://github.com/travist/jsencrypt)
- 本项目使用 [PyCryptodome](https://github.com/Legrandin/pycryptodome)
