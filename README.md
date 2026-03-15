# Stock Strategy Assistant

AI 驱动的股票策略助手 — 集成实时信息搜索、技术分析、策略管理和智能建议。

## 核心功能

- **实时信息聚合**：通过 Claude Web Search 自动搜索最新新闻、市场动态、分析师评级
- **技术面分析**：RSI、MACD、布林带、均线系统等技术指标自动计算
- **策略引擎**：以 YAML 文件定义策略规则，支持自由创建、修改、切换策略
- **AI 综合分析**：Claude 结合数据、新闻、策略信号生成结构化分析报告和操作建议
- **每日自动报告**：通过 crontab 定时生成分析报告，每天查看最新状况
- **交互式对话**：针对分析结果进行追问和深入讨论
- **决策权在你**：所有建议仅供参考，最终操作由你决定

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入 Anthropic API 密钥（从 [Anthropic Console](https://console.anthropic.com/) 获取）。

### 3. 使用

```bash
# 快速查看股票行情
python stock_assistant.py watch AAPL MSFT NVDA

# 创建策略
python stock_assistant.py strategy create my_tech AAPL,MSFT,NVDA --style balanced

# 评估策略信号
python stock_assistant.py strategy eval my_tech

# 对单只股票进行完整分析（含新闻搜索 + AI 分析）
python stock_assistant.py analyze AAPL --strategy my_tech

# 生成每日报告
python stock_assistant.py report

# 交互式分析对话
python stock_assistant.py chat --symbol AAPL
```

## 命令一览

| 命令 | 说明 |
|------|------|
| `watch <symbols...>` | 快速查看多只股票的关键指标 |
| `analyze <symbol> [-s strategy]` | 对单只股票进行完整 AI 分析 |
| `report [-s strategy]` | 生成每日分析报告（所有策略或指定策略） |
| `strategy list` | 列出所有策略 |
| `strategy create <name> <symbols> [--style]` | 创建新策略 |
| `strategy show <name>` | 查看策略详情 |
| `strategy eval <name>` | 评估策略对应股票的信号 |
| `chat [--symbol]` | 交互式分析对话 |

## 策略系统

策略以 YAML 文件存储在 `strategies/` 目录下，你可以随时手动编辑。

### 支持的规则类型

| 规则 | 说明 | 可配参数 |
|------|------|----------|
| `rsi` | RSI 超买超卖 | `oversold`, `overbought` |
| `ma_cross` | 均线交叉 | `fast` (如 ma5), `slow` (如 ma20) |
| `price_vs_ma` | 价格偏离均线 | `ma`, `threshold` (百分比) |
| `macd` | MACD 信号 | — |
| `bollinger` | 布林带位置 | — |
| `volume` | 成交量异动 | `high_ratio`, `low_ratio` |
| `pe_ratio` | 市盈率估值 | `low`, `high` |

### 策略风格

- `conservative`：保守型，阈值宽松，仓位小，止损紧
- `balanced`：均衡型，标准参数
- `aggressive`：激进型，阈值敏感，仓位大

### 自定义策略示例

```yaml
name: My Custom Strategy
symbols:
  - AAPL
  - TSLA
style: balanced
rules:
  - type: rsi
    name: RSI Check
    oversold: 28
    overbought: 72
  - type: macd
    name: MACD Trend
  - type: pe_ratio
    name: Valuation
    low: 12
    high: 35
risk_management:
  max_position_pct: 20
  stop_loss_pct: 8
  take_profit_pct: 25
  max_total_exposure_pct: 80
notes: My personal strategy notes here.
```

## 每日自动报告

使用 crontab 设置每日定时生成报告：

```bash
# 编辑 crontab
crontab -e

# 每个工作日晚 9 点生成报告
0 21 * * 1-5 cd /path/to/project && python stock_assistant.py report >> /var/log/stock_report.log 2>&1
```

报告保存在 `reports/` 目录下，为 Markdown 格式，方便阅读。

参考 `crontab_example.txt` 获取更多定时任务配置示例。

## 项目结构

```
stock_assistant.py   # CLI 主入口
market_data.py       # 市场数据获取（yfinance）
news_fetcher.py      # 新闻和信息搜索（Claude Web Search）
strategy.py          # 策略引擎（YAML 配置）
analyzer.py          # AI 综合分析（Claude）
daily_report.py      # 每日报告生成
strategies/          # 策略 YAML 文件目录
reports/             # 生成的报告目录
bot.py               # X 自动回复 Bot（独立功能）
x_client.py          # X API 客户端
reply_generator.py   # X 回复生成器
```

## 支持的市场

通过 yfinance 支持全球主要市场：

- **美股**: `AAPL`, `MSFT`, `GOOGL`, `NVDA` 等
- **A股**: `600519.SS`（上证）, `000858.SZ`（深证）
- **港股**: `0700.HK`, `9988.HK` 等
- **其他**: 日股、欧股等 yfinance 支持的市场

## 环境变量

| 环境变量 | 必需 | 说明 |
|---------|------|------|
| `ANTHROPIC_API_KEY` | 是 | Anthropic API 密钥（用于 AI 分析和新闻搜索） |
| `X_API_KEY` | 否 | X API Key（仅 X Bot 功能需要） |
| `X_API_SECRET` | 否 | X API Secret |
| `X_ACCESS_TOKEN` | 否 | X Access Token |
| `X_ACCESS_TOKEN_SECRET` | 否 | X Access Token Secret |
| `X_BEARER_TOKEN` | 否 | X Bearer Token |
