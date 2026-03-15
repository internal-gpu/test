# Stock Strategy Assistant

AI 驱动的股票策略助手 — 集成实时信息搜索、技术分析、策略管理和智能建议。

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit Dashboard                     │
│  Dashboard │ Stock Analysis │ Strategy Manager │ AI & Chat  │
├─────────────────────────────────────────────────────────────┤
│                       Core Engine                           │
│  MarketData │ NewsFetcher │ Strategy Engine │ AI Analyzer   │
├─────────────────────────────────────────────────────────────┤
│                      Data Sources                           │
│        yfinance │ Claude Web Search │ YAML Configs          │
└─────────────────────────────────────────────────────────────┘
```

**Core Engine** (Python): 数据获取、技术指标计算、策略逻辑、信号生成、AI 分析
**Dashboard** (Streamlit): 可视化界面，K线图、指标图、策略管理、AI 对话
**Notification** (planned): Bot / 邮件推送每日报告

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

### 3. 启动 Dashboard

```bash
streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`。

### 4. CLI 模式（可选）

```bash
# 快速看盘
python stock_assistant.py watch AAPL MSFT NVDA

# 创建策略
python stock_assistant.py strategy create my_tech AAPL,MSFT,NVDA --style balanced

# 完整 AI 分析
python stock_assistant.py analyze AAPL --strategy my_tech

# 生成每日报告
python stock_assistant.py report
```

## Dashboard 页面

### Dashboard
- 选择策略后显示所有跟踪股票的概览表（价格、涨跌幅、RSI、成交量比）
- 每只股票的策略信号汇总（买入/卖出/持有信号数量 + 详细规则触发情况）

### Stock Analysis
- 输入任意股票代码，选择时间范围
- 关键指标面板（价格、RSI、P/E、市值、成交量比）
- 交互式 K线图 + 均线 + 布林带 + 成交量 + RSI + MACD（Plotly）
- 技术指标详情展开

### Strategy Manager
- 查看所有策略详情
- 创建新策略（选风格自动生成规则模板）
- 可视化编辑策略：修改股票列表、增删规则、调参数、设风险管理
- 所有改动保存到 YAML 文件

### AI Analysis
- 选股票 + 策略，一键运行完整 AI 分析
- 自动获取数据 → 计算指标 → 搜索新闻 → Claude 生成综合分析报告
- 报告包含：多空判断、技术面、消息面、操作建议（含价格/仓位/止损止盈）

### Chat
- 与 AI 助手对话，讨论投资策略和股票分析
- 自动加载最近一次分析结果作为上下文
- 支持多轮连续对话

## CLI 命令

| 命令 | 说明 |
|------|------|
| `watch <symbols...>` | 快速查看多只股票的关键指标 |
| `analyze <symbol> [-s strategy]` | 对单只股票进行完整 AI 分析 |
| `report [-s strategy]` | 生成每日分析报告 |
| `strategy list` | 列出所有策略 |
| `strategy create <name> <symbols> [--style]` | 创建新策略 |
| `strategy show <name>` | 查看策略详情 |
| `strategy eval <name>` | 评估策略信号 |
| `chat [--symbol]` | 交互式对话 |

## 策略系统

策略以 YAML 文件存储在 `strategies/` 目录下，可通过 Dashboard 可视化编辑或直接修改文件。

### 支持的规则类型

| 规则 | 说明 | 可配参数 |
|------|------|----------|
| `rsi` | RSI 超买超卖 | `oversold`, `overbought` |
| `ma_cross` | 均线交叉 | `fast` (如 ma5), `slow` (如 ma20) |
| `price_vs_ma` | 价格偏离均线 | `ma`, `threshold` (%) |
| `macd` | MACD 信号 | — |
| `bollinger` | 布林带位置 | — |
| `volume` | 成交量异动 | `high_ratio`, `low_ratio` |
| `pe_ratio` | 市盈率估值 | `low`, `high` |

### 策略风格

- `conservative`：保守型，阈值宽松，仓位小，止损紧
- `balanced`：均衡型，标准参数
- `aggressive`：激进型，阈值敏感，仓位大

## 项目结构

```
# Dashboard
app.py               # Streamlit 可视化界面

# Core Engine
market_data.py       # 市场数据获取 + 技术指标（yfinance）
news_fetcher.py      # 新闻搜索（Claude Web Search）
strategy.py          # 策略引擎（YAML 加载/评估/管理）
analyzer.py          # AI 综合分析（Claude）
daily_report.py      # 每日报告生成

# CLI
stock_assistant.py   # 命令行入口

# Config
strategies/          # 策略 YAML 文件
reports/             # 生成的报告（git ignored）
.env                 # API 密钥（git ignored）

# X Bot (independent)
bot.py               # X 自动回复 Bot
x_client.py          # X API 客户端
reply_generator.py   # X 回复生成器
```

## 支持的市场

通过 yfinance 支持全球主要市场：

- **美股**: `AAPL`, `MSFT`, `GOOGL`, `NVDA`
- **A股**: `600519.SS`（上证）, `000858.SZ`（深证）
- **港股**: `0700.HK`, `9988.HK`
- **其他**: 日股、欧股等 yfinance 支持的市场

## 每日自动报告

```bash
# crontab -e
# 每个工作日晚 9 点生成报告
0 21 * * 1-5 cd /path/to/project && python stock_assistant.py report >> /var/log/stock_report.log 2>&1
```

参考 `crontab_example.txt` 获取更多配置示例。

## 环境变量

| 环境变量 | 必需 | 说明 |
|---------|------|------|
| `ANTHROPIC_API_KEY` | 是 | Anthropic API 密钥（AI 分析 + 新闻搜索） |
| `X_API_KEY` | 否 | X API Key（仅 X Bot 需要） |
| `X_API_SECRET` | 否 | X API Secret |
| `X_ACCESS_TOKEN` | 否 | X Access Token |
| `X_ACCESS_TOKEN_SECRET` | 否 | X Access Token Secret |
| `X_BEARER_TOKEN` | 否 | X Bearer Token |
