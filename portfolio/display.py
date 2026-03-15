"""Rich 终端渲染"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich import box

from .models import EnrichedHolding, AIChainSegment
from .rebalancer import Suggestion

console = Console()


def _pnl_color(val: float) -> str:
    if val > 0:
        return "green"
    elif val < 0:
        return "red"
    return "white"


def _fmt_pct(val: float) -> str:
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.2f}%"


def _fmt_money(val: float, currency: str = "USD") -> str:
    if currency == "HKD":
        return f"HK${val:,.2f}"
    return f"${val:,.2f}"


def render_dashboard(
    enriched: list[EnrichedHolding],
    segment_alloc: dict[AIChainSegment, float],
    total_value_usd: float,
    total_pnl_usd: float,
    chain_score: float,
    ai_score: float,
    cash_usd: float = 0,
):
    """主仪表盘"""
    pnl_pct = (total_pnl_usd / (total_value_usd - total_pnl_usd) * 100) if total_value_usd != total_pnl_usd else 0
    pnl_color = _pnl_color(total_pnl_usd)

    # 标题
    header = Text()
    header.append("AI Portfolio Dashboard", style="bold cyan")
    header.append("  |  总市值: ", style="white")
    header.append(f"${total_value_usd:,.0f}", style="bold white")
    if cash_usd > 0:
        header.append(f" + 现金 ${cash_usd:,.0f}", style="dim")
    header.append("  |  盈亏: ", style="white")
    header.append(f"{_fmt_pct(pnl_pct)}", style=f"bold {pnl_color}")
    console.print(Panel(header, box=box.DOUBLE))

    # 持仓表
    table = Table(title="持仓明细", box=box.ROUNDED, show_lines=False)
    table.add_column("代码", style="cyan", width=12)
    table.add_column("板块", width=18)
    table.add_column("AI纯度", justify="right", width=7)
    table.add_column("现价", justify="right", width=10)
    table.add_column("成本", justify="right", width=10)
    table.add_column("持仓数", justify="right", width=8)
    table.add_column("市值(USD)", justify="right", width=12)
    table.add_column("盈亏%", justify="right", width=9)
    table.add_column("日涨跌", justify="right", width=8)
    table.add_column("占比", justify="right", width=7)

    for e in sorted(enriched, key=lambda x: x.market_value_usd, reverse=True):
        seg_name = e.meta.segment.value if e.meta else "未分类"
        ai_score_val = str(int(e.meta.ai_chain_score)) if e.meta else "-"
        currency = "HKD" if ".HK" in e.holding.ticker else "USD"

        table.add_row(
            e.holding.ticker,
            seg_name,
            ai_score_val,
            f"{e.current_price:,.2f}",
            f"{e.holding.avg_cost:,.2f}",
            f"{e.holding.shares:,.0f}",
            f"${e.market_value_usd:,.0f}",
            Text(_fmt_pct(e.pnl_pct), style=_pnl_color(e.pnl_pct)),
            Text(_fmt_pct(e.day_change_pct), style=_pnl_color(e.day_change_pct)),
            f"{e.weight_pct:.1f}%",
        )

    console.print(table)

    # 板块分布
    render_allocation_bar(segment_alloc)

    # 评分
    score_text = Text()
    score_text.append(f"链路覆盖度: {chain_score:.0f}/100", style="bold yellow")
    score_text.append("  |  ", style="dim")
    score_text.append(f"AI纯度(加权): {ai_score:.0f}/100", style="bold magenta")
    console.print(Panel(score_text, title="组合评分", box=box.ROUNDED))


def render_allocation_bar(segment_alloc: dict[AIChainSegment, float]):
    """板块分布柱状图"""
    if not segment_alloc:
        console.print("[dim]无板块数据[/dim]")
        return

    COLORS = {
        AIChainSegment.MODELS_CLOUD: "blue",
        AIChainSegment.CHIPS_GPU: "green",
        AIChainSegment.OPTICAL_NETWORKING: "yellow",
        AIChainSegment.STORAGE: "magenta",
        AIChainSegment.HPC_INFRA: "cyan",
        AIChainSegment.MINING_TO_HPC: "red",
    }

    table = Table(title="AI 链路板块分布", box=box.ROUNDED, show_lines=False)
    table.add_column("板块", width=20)
    table.add_column("占比", justify="right", width=8)
    table.add_column("分布", width=40)

    for seg in AIChainSegment:
        pct = segment_alloc.get(seg, 0)
        color = COLORS.get(seg, "white")
        bar_len = int(pct / 2.5)  # 40 char max = 100%
        bar = "█" * bar_len + "░" * (40 - bar_len)
        table.add_row(
            Text(seg.value, style=f"bold {color}"),
            f"{pct:.1f}%",
            Text(bar, style=color),
        )

    console.print(table)


def render_screener(stocks: list, prices: dict[str, dict] | None = None):
    """选股器结果展示"""
    table = Table(title="AI 链路股票池", box=box.ROUNDED)
    table.add_column("代码", style="cyan", width=10)
    table.add_column("名称", width=12)
    table.add_column("中文", width=10)
    table.add_column("板块", width=18)
    table.add_column("子主题", width=22)
    table.add_column("AI纯度", justify="right", width=7)
    if prices:
        table.add_column("现价", justify="right", width=10)
        table.add_column("日涨跌", justify="right", width=8)
    table.add_column("备注", width=30)

    for s in stocks:
        row = [
            s.ticker, s.name, s.name_cn,
            s.segment.value, s.sub_theme,
            str(int(s.ai_chain_score)),
        ]
        if prices and s.ticker in prices:
            p = prices[s.ticker]
            row.append(f"{p['price']:.2f}")
            row.append(Text(_fmt_pct(p['day_change_pct']), style=_pnl_color(p['day_change_pct'])))
        elif prices:
            row.extend(["-", "-"])
        row.append(s.notes[:30] if s.notes else "")
        table.add_row(*row)

    console.print(table)


def render_rebalance(suggestions: list[Suggestion], targets: dict[AIChainSegment, float],
                     current: dict[AIChainSegment, float]):
    """调仓建议展示"""
    # 目标 vs 当前对比
    cmp_table = Table(title="目标 vs 当前板块配置", box=box.ROUNDED)
    cmp_table.add_column("板块", width=20)
    cmp_table.add_column("目标", justify="right", width=8)
    cmp_table.add_column("当前", justify="right", width=8)
    cmp_table.add_column("偏差", justify="right", width=8)
    cmp_table.add_column("状态", width=10)

    for seg in AIChainSegment:
        target = targets.get(seg, 0)
        curr = current.get(seg, 0)
        diff = curr - target
        status = "✓ 适中" if abs(diff) < 5 else ("↑ 超配" if diff > 0 else "↓ 低配")
        status_color = "green" if abs(diff) < 5 else ("red" if diff > 0 else "yellow")
        cmp_table.add_row(
            seg.value,
            f"{target:.0f}%",
            f"{curr:.1f}%",
            Text(f"{diff:+.1f}%", style=_pnl_color(-diff)),
            Text(status, style=status_color),
        )

    console.print(cmp_table)

    if not suggestions:
        console.print("[green]当前持仓与目标配置匹配良好，无需调仓[/green]")
        return

    # 建议列表
    sug_table = Table(title="调仓建议", box=box.ROUNDED)
    sug_table.add_column("优先级", width=6)
    sug_table.add_column("操作", width=6)
    sug_table.add_column("代码", style="cyan", width=12)
    sug_table.add_column("名称", width=15)
    sug_table.add_column("板块", width=18)
    sug_table.add_column("原因", width=50)

    ACTION_COLORS = {"BUY": "bold green", "ADD": "green", "TRIM": "yellow", "SELL": "bold red"}

    for s in suggestions:
        priority_stars = "★" * (4 - s.priority)
        sug_table.add_row(
            priority_stars,
            Text(s.action, style=ACTION_COLORS.get(s.action, "white")),
            s.ticker,
            s.name,
            s.segment.value,
            s.reason,
        )

    console.print(sug_table)


def render_chain_map(segment_alloc: dict[AIChainSegment, float],
                     holdings_by_seg: dict[AIChainSegment, list[str]]):
    """AI 链路全景图"""
    console.print(Panel("[bold cyan]AI 价值链全景图[/bold cyan]", box=box.DOUBLE))

    CHAIN_ORDER = [
        (AIChainSegment.MODELS_CLOUD, "🧠 模型/云", "训练+推理+应用"),
        (AIChainSegment.CHIPS_GPU, "⚡ 芯片/GPU", "算力核心"),
        (AIChainSegment.OPTICAL_NETWORKING, "🔗 光通信/网络", "数据传输"),
        (AIChainSegment.STORAGE, "💾 存储", "数据存储"),
        (AIChainSegment.HPC_INFRA, "🏗️ HPC/基础设施", "服务器/散热/电力"),
        (AIChainSegment.MINING_TO_HPC, "⛏️ 矿转HPC", "算力转型"),
    ]

    for seg, label, desc in CHAIN_ORDER:
        pct = segment_alloc.get(seg, 0)
        tickers = holdings_by_seg.get(seg, [])
        held = ", ".join(tickers) if tickers else "[dim]未持有[/dim]"

        status = f"[bold]{label}[/bold] ({desc})"
        detail = f"  配置: {pct:.1f}%  |  持有: {held}"

        if pct > 0:
            console.print(f"  ├─ {status}")
            console.print(f"  │  {detail}")
        else:
            console.print(f"  ├─ [dim]{status}[/dim]")
            console.print(f"  │  [dim]{detail}[/dim]")
        console.print("  │")


def render_watchlist(tickers: list[str], prices: dict[str, dict], metas: dict):
    """自选列表"""
    table = Table(title="自选列表", box=box.ROUNDED)
    table.add_column("代码", style="cyan", width=10)
    table.add_column("名称", width=15)
    table.add_column("板块", width=18)
    table.add_column("现价", justify="right", width=10)
    table.add_column("日涨跌", justify="right", width=8)
    table.add_column("AI纯度", justify="right", width=7)

    for t in tickers:
        meta = metas.get(t)
        p = prices.get(t, {})
        price = p.get('price', 0)
        chg = p.get('day_change_pct', 0)

        table.add_row(
            t,
            meta.name if meta else "-",
            meta.segment.value if meta else "-",
            f"{price:.2f}" if price else "-",
            Text(_fmt_pct(chg), style=_pnl_color(chg)) if price else Text("-"),
            str(int(meta.ai_chain_score)) if meta else "-",
        )

    console.print(table)


def render_concentration(report: dict):
    """集中度报告"""
    console.print(Panel(
        f"[bold]集中度风险: {report['risk_level']}[/bold]\n"
        f"HHI 指数: {report['hhi']:.4f}\n"
        f"最大单一持仓: {report['max_weight']:.1f}%",
        title="集中度分析",
        box=box.ROUNDED,
    ))

    if report['top_holdings']:
        table = Table(title="前5大持仓", box=box.SIMPLE)
        table.add_column("代码", style="cyan")
        table.add_column("占比", justify="right")
        for ticker, weight in report['top_holdings']:
            table.add_row(ticker, f"{weight:.1f}%")
        console.print(table)
