# X Auto-Reply Bot

自动监听 X (Twitter) 上的 @提及，并使用 AI (Claude) 生成智能回复。

## 功能

- 定时轮询检测新的 @提及
- 使用 Claude API 根据推文内容生成上下文相关的回复
- 自动发送回复
- 断点续传：记录已处理的推文 ID，重启后不会重复回复

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API 密钥：

- **X API 密钥**：在 [X Developer Portal](https://developer.x.com/) 申请
- **Anthropic API 密钥**：在 [Anthropic Console](https://console.anthropic.com/) 获取

### 3. 运行

```bash
python bot.py
```

## 项目结构

```
bot.py              # 主程序入口，轮询 + 回复逻辑
x_client.py         # X API v2 客户端封装
reply_generator.py  # AI 回复生成器
.env.example        # 环境变量模板
requirements.txt    # Python 依赖
```

## 配置项

| 环境变量 | 说明 |
|---------|------|
| `X_API_KEY` | X API Key |
| `X_API_SECRET` | X API Secret |
| `X_ACCESS_TOKEN` | X Access Token |
| `X_ACCESS_TOKEN_SECRET` | X Access Token Secret |
| `X_BEARER_TOKEN` | X Bearer Token |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 |
| `POLL_INTERVAL_SECONDS` | 轮询间隔（秒），默认 60 |
| `REPLY_PROMPT` | 自定义回复风格的 system prompt |
