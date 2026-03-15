"""AI 价值链分析引擎"""

from .models import AIChainSegment, Holding, EnrichedHolding, StockMeta
from .universe import UNIVERSE, get_stock_meta


def classify(ticker: str) -> StockMeta | None:
    """查询股票的 AI 链路分类"""
    return get_stock_meta(ticker)


def ai_purity_score(ticker: str) -> float:
    """返回 AI 纯度评分 (0-100)"""
    meta = get_stock_meta(ticker)
    return meta.ai_chain_score if meta else 0


def segment_breakdown(enriched: list[EnrichedHolding]) -> dict[AIChainSegment, float]:
    """计算各板块市值占比（USD标准化）

    Returns: {segment: weight_pct}
    """
    segment_values: dict[AIChainSegment, float] = {}
    total = 0

    for e in enriched:
        if e.meta:
            seg = e.meta.segment
            segment_values[seg] = segment_values.get(seg, 0) + e.market_value_usd
            total += e.market_value_usd

    if total == 0:
        return {}

    return {seg: val / total * 100 for seg, val in segment_values.items()}


def chain_coverage_score(enriched: list[EnrichedHolding]) -> float:
    """AI 链路覆盖度评分 (0-100)

    公式: (覆盖板块数/6) * 50 + (1 - HHI) * 50
    覆盖越全、分布越均匀得分越高
    """
    breakdown = segment_breakdown(enriched)
    if not breakdown:
        return 0

    all_segments = list(AIChainSegment)
    covered = len(breakdown)
    coverage_part = (covered / len(all_segments)) * 50

    # HHI (Herfindahl-Hirschman Index)
    weights = list(breakdown.values())
    total_w = sum(weights)
    if total_w == 0:
        return coverage_part

    normalized = [w / total_w for w in weights]
    hhi = sum(w ** 2 for w in normalized)
    diversity_part = (1 - hhi) * 50

    return coverage_part + diversity_part


def portfolio_ai_score(enriched: list[EnrichedHolding]) -> float:
    """组合整体 AI 纯度加权评分"""
    total_value = sum(e.market_value_usd for e in enriched)
    if total_value == 0:
        return 0

    weighted_score = 0
    for e in enriched:
        score = e.meta.ai_chain_score if e.meta else 0
        weighted_score += score * (e.market_value_usd / total_value)

    return weighted_score


def identify_gaps(enriched: list[EnrichedHolding]) -> list[AIChainSegment]:
    """识别未覆盖的板块"""
    breakdown = segment_breakdown(enriched)
    return [seg for seg in AIChainSegment if seg not in breakdown]
