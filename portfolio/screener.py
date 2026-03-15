"""AI 链路选股器"""

from .models import AIChainSegment, StockMeta
from .universe import UNIVERSE, get_all_by_segment


def screen(
    segment: AIChainSegment | None = None,
    min_score: float = 0,
    exclude_held: list[str] | None = None,
    market: str | None = None,
) -> list[StockMeta]:
    """筛选 AI 链路股票

    Args:
        segment: 按板块筛选
        min_score: 最低 AI 纯度分
        exclude_held: 排除已持有的 ticker
        market: "US" 或 "HK"
    """
    exclude = set(exclude_held or [])
    results = []

    for ticker, meta in UNIVERSE.items():
        if ticker in exclude:
            continue
        if segment and meta.segment != segment:
            continue
        if meta.ai_chain_score < min_score:
            continue
        if market and meta.market.value != market:
            continue
        results.append(meta)

    results.sort(key=lambda x: x.ai_chain_score, reverse=True)
    return results


def recommend_for_gaps(
    missing_segments: list[AIChainSegment],
    held_tickers: list[str],
    top_n: int = 3,
) -> dict[AIChainSegment, list[StockMeta]]:
    """为缺失板块推荐标的

    Returns: {segment: [top_n StockMeta sorted by ai_chain_score]}
    """
    recs = {}
    for seg in missing_segments:
        candidates = screen(segment=seg, exclude_held=held_tickers)
        recs[seg] = candidates[:top_n]
    return recs
