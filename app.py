"""AI 投资组合 Web 仪表盘"""

import os
import webbrowser
import threading
from flask import Flask, render_template, jsonify, request

from portfolio.config import load_portfolio, save_portfolio
from portfolio.models import EnrichedHolding, AIChainSegment
from portfolio.market_data import get_quotes, get_forex_rate, clear_cache
from portfolio.universe import get_stock_meta, UNIVERSE, get_all_by_segment
from portfolio.ai_chain import segment_breakdown, chain_coverage_score, portfolio_ai_score, identify_gaps
from portfolio.analysis import concentration_report, market_exposure, pnl_summary
from portfolio.screener import screen, recommend_for_gaps
from portfolio.rebalancer import suggest_rebalance, AGGRESSIVE_TARGETS

app = Flask(__name__)


def _enrich_holdings(portfolio, quotes, hkd_rate):
    """将持仓与行情数据合并（复用 cli.py 逻辑）"""
    enriched = []
    total_usd = 0

    for h in portfolio.holdings:
        q = quotes.get(h.ticker, {})
        price = q.get('price', 0)
        is_hk = '.HK' in h.ticker
        market_value = h.shares * price
        market_value_usd = market_value * hkd_rate if is_hk else market_value
        total_usd += market_value_usd

    cash_usd = 0
    for c in portfolio.cash:
        if c.currency == 'HKD':
            cash_usd += c.amount * hkd_rate
        else:
            cash_usd += c.amount

    portfolio_total = total_usd + cash_usd

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


def _load_data():
    """加载并组装完整仪表盘数据"""
    portfolio = load_portfolio()
    tickers = [h.ticker for h in portfolio.holdings]
    quotes = get_quotes(tickers)
    hkd_rate = get_forex_rate()
    enriched, cash_usd = _enrich_holdings(portfolio, quotes, hkd_rate)
    return portfolio, enriched, cash_usd


def _stock_meta_to_dict(meta):
    if not meta:
        return None
    return {
        'ticker': meta.ticker,
        'name': meta.name,
        'name_cn': meta.name_cn,
        'market': meta.market.value,
        'segment': meta.segment.value,
        'sub_theme': meta.sub_theme,
        'ai_chain_score': meta.ai_chain_score,
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/dashboard')
def api_dashboard():
    """完整仪表盘数据"""
    portfolio, enriched, cash_usd = _load_data()

    total_usd = sum(e.market_value_usd for e in enriched)
    total_pnl = sum(e.unrealized_pnl for e in enriched)
    seg_alloc = segment_breakdown(enriched)
    chain_sc = chain_coverage_score(enriched)
    ai_sc = portfolio_ai_score(enriched)
    conc = concentration_report(enriched)
    mkt_exp = market_exposure(enriched)
    pnl = pnl_summary(enriched)
    gaps = identify_gaps(enriched)

    holdings_data = []
    for e in enriched:
        holdings_data.append({
            'ticker': e.holding.ticker,
            'name': e.meta.name if e.meta else e.holding.ticker,
            'name_cn': e.meta.name_cn if e.meta else '',
            'segment': e.meta.segment.value if e.meta else 'N/A',
            'ai_score': e.meta.ai_chain_score if e.meta else 0,
            'shares': e.holding.shares,
            'avg_cost': e.holding.avg_cost,
            'current_price': round(e.current_price, 2),
            'market_value_usd': round(e.market_value_usd, 2),
            'pnl_pct': round(e.pnl_pct, 2),
            'unrealized_pnl': round(e.unrealized_pnl, 2),
            'day_change_pct': round(e.day_change_pct, 2),
            'weight_pct': round(e.weight_pct, 2),
            'currency': 'HKD' if '.HK' in e.holding.ticker else 'USD',
        })

    seg_alloc_data = {seg.value: round(pct, 2) for seg, pct in seg_alloc.items()}
    targets_data = {seg.value: pct for seg, pct in AGGRESSIVE_TARGETS.items()}

    return jsonify({
        'summary': {
            'total_value_usd': round(total_usd, 2),
            'total_pnl_usd': round(total_pnl, 2),
            'total_pnl_pct': round(pnl['total_pnl_pct'], 2),
            'cash_usd': round(cash_usd, 2),
            'ai_score': round(ai_sc, 1),
            'chain_coverage': round(chain_sc, 1),
            'risk_level': conc['risk_level'],
            'hhi': round(conc['hhi'], 4),
        },
        'holdings': holdings_data,
        'segment_allocation': seg_alloc_data,
        'target_allocation': targets_data,
        'market_exposure': mkt_exp,
        'pnl': {
            'winners': pnl['winners'][:5],
            'losers': pnl['losers'][:5],
        },
        'gaps': [g.value for g in gaps],
    })


@app.route('/api/rebalance')
def api_rebalance():
    """调仓建议"""
    portfolio, enriched, cash_usd = _load_data()
    suggestions = suggest_rebalance(enriched)
    current = segment_breakdown(enriched)
    gaps = identify_gaps(enriched)

    suggestions_data = [{
        'action': s.action,
        'ticker': s.ticker,
        'name': s.name,
        'segment': s.segment.value,
        'reason': s.reason,
        'priority': s.priority,
    } for s in suggestions]

    gap_recs = {}
    if gaps:
        recs = recommend_for_gaps(gaps, [h.ticker for h in portfolio.holdings])
        for seg, stocks in recs.items():
            gap_recs[seg.value] = [_stock_meta_to_dict(s) for s in stocks]

    return jsonify({
        'suggestions': suggestions_data,
        'current': {seg.value: round(pct, 2) for seg, pct in current.items()},
        'targets': {seg.value: pct for seg, pct in AGGRESSIVE_TARGETS.items()},
        'gap_recommendations': gap_recs,
    })


@app.route('/api/screener')
def api_screener():
    """股票池"""
    segment_filter = request.args.get('segment')
    min_score = float(request.args.get('min_score', 0))
    market = request.args.get('market')

    seg = None
    if segment_filter:
        for s in AIChainSegment:
            if segment_filter.lower() in s.value.lower():
                seg = s
                break

    results = screen(segment=seg, min_score=min_score, market=market)
    return jsonify([_stock_meta_to_dict(s) for s in results])


@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    """刷新行情缓存"""
    clear_cache()
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    threading.Timer(1.5, lambda: webbrowser.open(f'http://localhost:{port}')).start()
    print(f"\n  AI 投资组合仪表盘已启动: http://localhost:{port}\n")
    app.run(host='0.0.0.0', port=port, debug=False)
