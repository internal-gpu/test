"""调仓建议引擎"""

from dataclasses import dataclass
from .models import AIChainSegment, EnrichedHolding
from .ai_chain import segment_breakdown, identify_gaps
from .universe import UNIVERSE, get_all_by_segment


# 激进 AI 主题目标权重
AGGRESSIVE_TARGETS = {
    AIChainSegment.MODELS_CLOUD: 25,
    AIChainSegment.CHIPS_GPU: 25,
    AIChainSegment.OPTICAL_NETWORKING: 20,
    AIChainSegment.HPC_INFRA: 15,
    AIChainSegment.MINING_TO_HPC: 10,
    AIChainSegment.STORAGE: 5,
}


@dataclass
class Suggestion:
    action: str  # "BUY", "SELL", "TRIM", "ADD"
    ticker: str
    name: str
    segment: AIChainSegment
    reason: str
    priority: int  # 1=最高, 3=最低


def suggest_rebalance(
    enriched: list[EnrichedHolding],
    threshold_pct: float = 5,
    targets: dict[AIChainSegment, float] | None = None,
) -> list[Suggestion]:
    """生成调仓建议

    Args:
        enriched: 持仓数据
        threshold_pct: 偏离目标超过此百分比才建议调仓
        targets: 目标权重，默认用激进 AI 主题

    Returns: 按优先级排序的建议列表
    """
    if targets is None:
        targets = AGGRESSIVE_TARGETS

    current = segment_breakdown(enriched)
    held_tickers = {e.holding.ticker for e in enriched}
    suggestions = []

    # 1. 识别超配板块 -> 建议减仓
    for seg, target_w in targets.items():
        current_w = current.get(seg, 0)
        diff = current_w - target_w

        if diff > threshold_pct:
            # 找到该板块中 AI 纯度最低的持仓建议减
            seg_holdings = [
                e for e in enriched
                if e.meta and e.meta.segment == seg
            ]
            seg_holdings.sort(key=lambda e: e.meta.ai_chain_score if e.meta else 0)

            for e in seg_holdings[:1]:
                suggestions.append(Suggestion(
                    action="TRIM",
                    ticker=e.holding.ticker,
                    name=e.meta.name if e.meta else e.holding.ticker,
                    segment=seg,
                    reason=f"{seg.value} 超配 {diff:.1f}%，AI纯度 {e.meta.ai_chain_score if e.meta else 0} 较低",
                    priority=2,
                ))

    # 2. 识别低配板块 -> 建议加仓或买入新标的
    for seg, target_w in targets.items():
        current_w = current.get(seg, 0)
        diff = target_w - current_w

        if diff > threshold_pct:
            # 先看已持有的该板块标的是否可以加仓
            seg_held = [
                e for e in enriched
                if e.meta and e.meta.segment == seg
            ]

            if seg_held:
                # 加仓 AI 纯度最高的
                best = max(seg_held, key=lambda e: e.meta.ai_chain_score if e.meta else 0)
                suggestions.append(Suggestion(
                    action="ADD",
                    ticker=best.holding.ticker,
                    name=best.meta.name if best.meta else best.holding.ticker,
                    segment=seg,
                    reason=f"{seg.value} 低配 {diff:.1f}%，建议加仓（AI纯度 {best.meta.ai_chain_score if best.meta else 0}）",
                    priority=1,
                ))
            else:
                # 推荐新标的
                candidates = get_all_by_segment(seg)
                candidates = [c for c in candidates if c.ticker not in held_tickers]
                candidates.sort(key=lambda c: c.ai_chain_score, reverse=True)

                for c in candidates[:2]:
                    suggestions.append(Suggestion(
                        action="BUY",
                        ticker=c.ticker,
                        name=c.name,
                        segment=seg,
                        reason=f"{seg.value} 未覆盖，推荐 {c.name_cn}（{c.sub_theme}，AI纯度 {c.ai_chain_score}）",
                        priority=1,
                    ))

    # 3. 识别 AI 纯度过低的持仓
    for e in enriched:
        if e.meta and e.meta.ai_chain_score < 40 and e.weight_pct > 10:
            already_suggested = any(s.ticker == e.holding.ticker for s in suggestions)
            if not already_suggested:
                suggestions.append(Suggestion(
                    action="SELL",
                    ticker=e.holding.ticker,
                    name=e.meta.name if e.meta else e.holding.ticker,
                    segment=e.meta.segment,
                    reason=f"AI纯度仅 {e.meta.ai_chain_score}，占比 {e.weight_pct:.1f}% 过高，建议替换为高AI纯度标的",
                    priority=2,
                ))

    suggestions.sort(key=lambda s: s.priority)
    return suggestions
