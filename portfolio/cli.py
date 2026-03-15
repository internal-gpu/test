"""CLI 入口 - AI 投资组合管理系统"""

import click
from rich.console import Console

from .config import load_portfolio, save_portfolio
from .models import EnrichedHolding, AIChainSegment
from .market_data import get_quotes, get_forex_rate
from .universe import get_stock_meta, UNIVERSE, get_all_by_segment
from .ai_chain import segment_breakdown, chain_coverage_score, portfolio_ai_score, identify_gaps
from .analysis import concentration_report, market_exposure, pnl_summary
from .screener import screen, recommend_for_gaps
from .rebalancer import suggest_rebalance, AGGRESSIVE_TARGETS
from . import display

console = Console()


def _enrich_holdings(portfolio, quotes, hkd_rate):
    """将持仓与行情数据合并"""
    enriched = []
    total_usd = 0

    # 第一遍: 计算所有市值
    for h in portfolio.holdings:
        q = quotes.get(h.ticker, {})
        price = q.get('price', 0)
        is_hk = '.HK' in h.ticker
        market_value = h.shares * price
        market_value_usd = market_value * hkd_rate if is_hk else market_value
        total_usd += market_value_usd

    # 加上现金
    cash_usd = 0
    for c in portfolio.cash:
        if c.currency == 'HKD':
            cash_usd += c.amount * hkd_rate
        else:
            cash_usd += c.amount

    portfolio_total = total_usd + cash_usd

    # 第二遍: 构建 EnrichedHolding
    for h in portfolio.holdings:
        q = quotes.get(h.ticker, {})
        price = q.get('price', 0)
        day_change = q.get('day_change_pct', 0)
        is_hk = '.HK' in h.ticker

        market_value = h.shares * price
        market_value_usd = market_value * hkd_rate if is_hk else market_value
        cost_value = h.shares * h.avg_cost
        cost_usd = cost_value * hkd_rate if is_hk else cost_value
        pnl = market_value_usd - cost_usd
        pnl_pct = (pnl / cost_usd * 100) if cost_usd else 0

        meta = get_stock_meta(h.ticker)
        if meta:
            h.segment = meta.segment

        enriched.append(EnrichedHolding(
            holding=h,
            meta=meta,
            current_price=price,
            market_value=market_value,
            unrealized_pnl=pnl,
            pnl_pct=pnl_pct,
            day_change_pct=day_change,
            weight_pct=(market_value_usd / portfolio_total * 100) if portfolio_total else 0,
            market_value_usd=market_value_usd,
        ))

    return enriched, cash_usd


def _load_and_enrich(config_path):
    """加载配置、获取行情、enrichment"""
    portfolio = load_portfolio(config_path)
    tickers = [h.ticker for h in portfolio.holdings]

    console.print("[dim]正在获取行情数据...[/dim]")
    quotes = get_quotes(tickers)
    hkd_rate = get_forex_rate()

    enriched, cash_usd = _enrich_holdings(portfolio, quotes, hkd_rate)
    return portfolio, enriched, cash_usd, quotes


@click.group(invoke_without_command=True)
@click.option('--config', '-c', default=None, help='配置文件路径 (默认 portfolio.yaml)')
@click.pass_context
def cli(ctx, config):
    """AI 价值链投资组合管理系统"""
    ctx.ensure_object(dict)
    ctx.obj['config'] = config
    if ctx.invoked_subcommand is None:
        ctx.invoke(dashboard)


@cli.command()
@click.pass_context
def dashboard(ctx):
    """总览仪表盘：持仓、盈亏、板块分布"""
    portfolio, enriched, cash_usd, _ = _load_and_enrich(ctx.obj.get('config'))

    seg_alloc = segment_breakdown(enriched)
    total_usd = sum(e.market_value_usd for e in enriched)
    total_pnl = sum(e.unrealized_pnl for e in enriched)
    chain_sc = chain_coverage_score(enriched)
    ai_sc = portfolio_ai_score(enriched)

    display.render_dashboard(
        enriched, seg_alloc, total_usd, total_pnl,
        chain_sc, ai_sc, cash_usd,
    )


@cli.command()
@click.pass_context
def holdings(ctx):
    """详细持仓列表"""
    portfolio, enriched, cash_usd, _ = _load_and_enrich(ctx.obj.get('config'))

    seg_alloc = segment_breakdown(enriched)
    total_usd = sum(e.market_value_usd for e in enriched)
    total_pnl = sum(e.unrealized_pnl for e in enriched)
    chain_sc = chain_coverage_score(enriched)
    ai_sc = portfolio_ai_score(enriched)

    display.render_dashboard(enriched, seg_alloc, total_usd, total_pnl, chain_sc, ai_sc, cash_usd)


@cli.command()
@click.pass_context
def analysis(ctx):
    """持仓分析：集中度、市场分布"""
    portfolio, enriched, cash_usd, _ = _load_and_enrich(ctx.obj.get('config'))

    # 集中度
    conc = concentration_report(enriched)
    display.render_concentration(conc)

    # 市场分布
    mkt = market_exposure(enriched)
    console.print(f"\n[bold]市场分布:[/bold]")
    for market, pct in mkt.items():
        console.print(f"  {market}: {pct:.1f}%")

    # 盈亏汇总
    pnl = pnl_summary(enriched)
    console.print(f"\n[bold]盈亏汇总:[/bold]")
    console.print(f"  总市值(USD): ${pnl['total_value_usd']:,.0f}")
    pnl_color = "green" if pnl['total_pnl_usd'] >= 0 else "red"
    console.print(f"  总盈亏: [{pnl_color}]${pnl['total_pnl_usd']:,.0f} ({pnl['total_pnl_pct']:+.2f}%)[/{pnl_color}]")

    if pnl['winners']:
        console.print(f"\n  [green]最佳表现:[/green]")
        for t, p in pnl['winners'][:3]:
            console.print(f"    {t}: +{p:.2f}%")
    if pnl['losers']:
        console.print(f"\n  [red]最差表现:[/red]")
        for t, p in pnl['losers'][:3]:
            console.print(f"    {t}: {p:.2f}%")


@cli.command()
@click.option('--segment', '-s', default=None, help='按板块筛选 (如 Chips/GPU)')
@click.option('--min-score', '-m', default=0, type=float, help='最低AI纯度分')
@click.option('--market', default=None, type=click.Choice(['US', 'HK']), help='按市场筛选')
@click.option('--no-held', is_flag=True, help='排除已持有标的')
@click.pass_context
def screener(ctx, segment, min_score, market, no_held):
    """AI 链路选股器"""
    seg = None
    if segment:
        for s in AIChainSegment:
            if segment.lower() in s.value.lower():
                seg = s
                break
        if not seg:
            console.print(f"[red]未知板块: {segment}[/red]")
            console.print(f"可选: {', '.join(s.value for s in AIChainSegment)}")
            return

    exclude = []
    if no_held:
        portfolio = load_portfolio(ctx.obj.get('config'))
        exclude = [h.ticker for h in portfolio.holdings]

    results = screen(segment=seg, min_score=min_score, exclude_held=exclude, market=market)

    if not results:
        console.print("[yellow]无符合条件的标的[/yellow]")
        return

    # 可选获取实时价格
    display.render_screener(results)


@cli.command()
@click.pass_context
def rebalance(ctx):
    """调仓建议"""
    portfolio, enriched, cash_usd, _ = _load_and_enrich(ctx.obj.get('config'))

    current = segment_breakdown(enriched)
    suggestions = suggest_rebalance(enriched)

    display.render_rebalance(suggestions, AGGRESSIVE_TARGETS, current)

    # 显示缺失板块推荐
    gaps = identify_gaps(enriched)
    if gaps:
        console.print(f"\n[yellow]未覆盖板块: {', '.join(g.value for g in gaps)}[/yellow]")
        recs = recommend_for_gaps(gaps, [h.ticker for h in portfolio.holdings])
        for seg, stocks in recs.items():
            console.print(f"\n  [bold]{seg.value} 推荐:[/bold]")
            for s in stocks:
                console.print(f"    {s.ticker} - {s.name_cn} ({s.sub_theme}, AI纯度:{s.ai_chain_score})")


@cli.command()
@click.pass_context
def chain(ctx):
    """AI 价值链全景图"""
    portfolio, enriched, cash_usd, _ = _load_and_enrich(ctx.obj.get('config'))

    seg_alloc = segment_breakdown(enriched)
    holdings_by_seg = {}
    for e in enriched:
        if e.meta:
            seg = e.meta.segment
            holdings_by_seg.setdefault(seg, []).append(e.holding.ticker)

    display.render_chain_map(seg_alloc, holdings_by_seg)


@cli.group(invoke_without_command=True)
@click.pass_context
def watchlist(ctx):
    """自选管理"""
    if ctx.invoked_subcommand is None:
        ctx.invoke(watchlist_show)


@watchlist.command('show')
@click.pass_context
def watchlist_show(ctx):
    """查看自选"""
    portfolio = load_portfolio(ctx.obj.get('config'))
    if not portfolio.watchlist:
        console.print("[dim]自选列表为空，使用 watchlist add <ticker> 添加[/dim]")
        return

    console.print("[dim]正在获取行情数据...[/dim]")
    quotes = get_quotes(portfolio.watchlist)
    metas = {t: get_stock_meta(t) for t in portfolio.watchlist}
    display.render_watchlist(portfolio.watchlist, quotes, metas)


@watchlist.command('add')
@click.argument('ticker')
@click.pass_context
def watchlist_add(ctx, ticker):
    """添加自选"""
    config_path = ctx.obj.get('config')
    portfolio = load_portfolio(config_path)
    ticker = ticker.upper()
    if ticker in portfolio.watchlist:
        console.print(f"[yellow]{ticker} 已在自选中[/yellow]")
        return
    portfolio.watchlist.append(ticker)
    save_portfolio(portfolio, config_path)
    meta = get_stock_meta(ticker)
    name = f" ({meta.name_cn})" if meta else ""
    console.print(f"[green]已添加 {ticker}{name} 到自选[/green]")


@watchlist.command('rm')
@click.argument('ticker')
@click.pass_context
def watchlist_rm(ctx, ticker):
    """移除自选"""
    config_path = ctx.obj.get('config')
    portfolio = load_portfolio(config_path)
    ticker = ticker.upper()
    if ticker not in portfolio.watchlist:
        console.print(f"[yellow]{ticker} 不在自选中[/yellow]")
        return
    portfolio.watchlist.remove(ticker)
    save_portfolio(portfolio, config_path)
    console.print(f"[green]已从自选移除 {ticker}[/green]")


def main():
    cli(obj={})


if __name__ == '__main__':
    main()
