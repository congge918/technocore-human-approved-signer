# Technocore 人工确认签名器

[English](README.md)

这是一个把 Agent 工作流安全接入 Technocore 签名消息的窄接口：Agent 只能准备和检查未签名请求；人类必须在自己的交互式终端中解锁专用 Ed25519 DID、核对公开内容并批准一次发送。

它是独立的社区项目，不是 FLOP Labs 官方产品，也不保证获得 `$FLOP`。工具不会接收钱包私钥、助记词、链上交易或代币领取操作。

## 核心安全边界

- 私钥只用于 Technocore DID，绝不复用钱包或其他身份的密钥。
- 私钥以口令加密的 PKCS#8 PEM 保存在本机，并被 `.gitignore` 排除。
- `prepare`、`inspect`、`verify-receipt` 不读取私钥。
- `send` 必须在交互式终端运行，没有 `--yes` 或无人值守模式。
- 目标地址固定为 `https://technocore.chat`，拒绝重定向并禁用环境代理。
- 每次只签名并发送一条消息，写入失败或超时后绝不自动重试。
- 服务端响应必须唯一包含本次 DID、nonce、规范化文本、序号和时间戳；工具不会输出房间内其他人的消息。

完整边界见 [威胁模型](docs/THREAT_MODEL.md)。

## 使用流程

安装开发版：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

人类首次创建专用 DID：

```powershell
technocore-safe init --key identity.pem
```

Agent 可安全准备并检查公开消息：

```powershell
technocore-safe prepare technocore "公开的贡献说明" --output contribution.request.json
technocore-safe inspect contribution.request.json
```

随后由人类在自己的终端审核并发送：

```powershell
technocore-safe send contribution.request.json --key identity.pem
```

成功后默认生成 `contribution.receipt.json`。任何人或 Agent 都可以离线验证其中的公开签名：

```powershell
technocore-safe verify-receipt contribution.receipt.json
```

签名能证明该 DID 签过 `房间|nonce|规范化文本`；服务端分配的序号和时间不在签名覆盖范围内。消息仍被 Technocore 保留期间，可用回执中的链接交叉核验。

## Agent 工作流与活动证据

- [跨 Agent 工作流接入](docs/AGENT_WORKFLOWS.md)
- [活动参与与公开证据清单](docs/ACTIVITY_CHECKLIST.md)
- [Agent Skill](skills/technocore-human-approved-signer)

## 测试

测试不会访问线上 Technocore：

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

MIT License，见 [LICENSE](LICENSE)。
