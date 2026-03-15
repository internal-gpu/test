"""持仓分析模块"""

from .models import EnrichedHolding, AIChainSegment


def concentration_report(enriched: list[EnrichedHolding]) -> dict:
    """集中度分析

    Returns: {
        top_holdings: [(ticker, weight_pct), ...],
        hhi: float,  # 0-1, 越高越集中
        max_weight: float,
        risk_level: str,
    }
    """
    if not enriched:
        return {'top_holdings': [], 'hhi': 0, 'max_weight': 0, 'risk_level': 'N/A'}

    total = sum(e.market_value_usd for e in enriched)
    if total == 0:
        return {'top_holdings': [], 'hhi': 0, 'max_weight': 0, 'risk_level': 'N/A'}

    weights = [(e.holding.ticker, e.market_value_usd / total * 100) for e in enriched]
    weights.sort(key=lambda x: x[1], reverse=True)

    normalized = [w / 100 for _, w in weights]
    hhi = sum(w ** 2 for w in normalized)
    max_weight = weights[0][1] if weights else 0

    if hhi > 0.25:
        risk_level = "极高集中度"
    elif hhi > 0.15:
        risk_level = "高集中度"
    elif hhi > 0.10:
        risk_level = "中等集中度"
    else:
        risk_level = "分散"

    return {
        'top_holdings': weights[:5],
        'hhi': hhi,
        'max_weight': max_weight,
        'risk_level': risk_level,
    }


def market_exposure(enriched: list[EnrichedHolding]) -> dict[str, float]:
    """市场分布（港股 vs 美股）"""
    total = sum(e.market_value_usd for e in enriched)
    if total == 0:
        return {}

    exposure = {}
    for e in enriched:
        market = "港股" if ".HK" in e.holding.ticker else "美股"
        exposure[market] = exposure.get(market, 0) + e.market_value_usd / total * 100

    return exposure


def pnl_summary(enriched: list[EnrichedHolding]) -> dict:
    """盈亏汇总"""
    total_cost = sum(e.holding.shares * e.holding.avg_cost for e in enriched)
    total_value = sum(e.market_value for e in enriched)
    total_value_usd = sum(e.market_value_usd for e in enriched)
    total_pnl_usd = sum(e.unrealized_pnl for e in enriched)

    winners = [(e.holding.ticker, e.pnl_pct) for e in enriched if e.pnl_pct > 0]
    losers = [(e.holding.ticker, e.pnl_pct) for e in enriched if e.pnl_pct < 0]

    winners.sort(key=lambda x: x[1], reverse=True)
    losers.sort(key=lambda x: x[1])

    return {
        'total_value_usd': total_value_usd,
        'total_pnl_usd': total_pnl_usd,
        'total_pnl_pct': (total_pnl_usd / (total_value_usd - total_pnl_usd) * 100) if total_value_usd != total_pnl_usd else 0,
        'winners': winners[:5],
        'losers': losers[:5],
    }
