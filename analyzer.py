"""Claude-powered stock analyzer — combines data, news, and strategy signals."""

import json
import os
from datetime import datetime

import anthropic


class StockAnalyzer:
    """Intelligent stock analysis using Claude AI."""

    def __init__(self, api_key=None):
        self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    def analyze(self, stock_info, technicals, signals, news_summary, strategy, language="zh"):
        """Generate comprehensive analysis and recommendation.

        Args:
            stock_info: Dict with basic stock information.
            technicals: Dict with technical indicators.
            signals: Dict with strategy signal evaluation results.
            news_summary: String with recent news summary.
            strategy: Dict with strategy configuration.
            language: Response language.

        Returns:
            String with detailed analysis and recommendation.
        """
        lang_instruction = "请用中文回答。" if language == "zh" else "Please answer in English."
        risk_mgmt = strategy.get("risk_management", {})

        system_prompt = (
            "你是一位专业的股票分析助手。你的职责是基于提供的市场数据、技术指标、"
            "策略信号和新闻信息，为用户提供清晰、结构化的分析报告和操作建议。\n\n"
            "重要原则：\n"
            "1. 你不做最终决策，决策权在用户手中\n"
            "2. 分析必须基于提供的数据，不能凭空编造\n"
            "3. 明确标注风险和不确定性\n"
            "4. 建议必须包含具体的价格区间和仓位建议\n"
            "5. 考虑用户的风险管理参数\n"
        )

        data_text = (
            f"# 股票基本信息\n{json.dumps(stock_info, ensure_ascii=False, indent=2)}\n\n"
            f"# 技术指标\n{json.dumps(technicals, ensure_ascii=False, indent=2)}\n\n"
            f"# 策略信号评估\n{json.dumps(signals, ensure_ascii=False, indent=2)}\n\n"
            f"# 风险管理参数\n{json.dumps(risk_mgmt, ensure_ascii=False, indent=2)}\n\n"
            f"# 最新新闻和市场动态\n{news_summary}\n\n"
        )

        user_msg = (
            f"{data_text}\n"
            f"请基于以上所有信息，生成一份完整的分析报告，包括：\n\n"
            f"1. **综合评估**：当前股票的整体状态（多空判断）\n"
            f"2. **技术面分析**：基于技术指标的分析\n"
            f"3. **消息面分析**：基于新闻和市场动态的判断\n"
            f"4. **策略信号汇总**：策略规则的触发情况\n"
            f"5. **操作建议**：\n"
            f"   - 建议操作（买入/卖出/持有/观望）\n"
            f"   - 建议价格区间\n"
            f"   - 建议仓位比例（参考最大仓位 {risk_mgmt.get('max_position_pct', 20)}%）\n"
            f"   - 止损位（参考止损 {risk_mgmt.get('stop_loss_pct', 8)}%）\n"
            f"   - 止盈位（参考止盈 {risk_mgmt.get('take_profit_pct', 20)}%）\n"
            f"6. **风险提示**：需要关注的风险因素\n"
            f"7. **后续关注点**：接下来需要重点关注的事件或指标\n\n"
            f"{lang_instruction}"
        )

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=3000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_msg}],
        )
        return response.content[0].text

    def compare_strategies(self, symbol, results_by_strategy, language="zh"):
        """Compare multiple strategy results for the same stock.

        Args:
            symbol: Stock ticker symbol.
            results_by_strategy: Dict mapping strategy name to signal results.
            language: Response language.

        Returns:
            String with strategy comparison analysis.
        """
        lang_instruction = "请用中文回答。" if language == "zh" else "Please answer in English."

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": (
                    f"以下是股票 {symbol} 在不同策略下的信号评估结果：\n\n"
                    f"{json.dumps(results_by_strategy, ensure_ascii=False, indent=2)}\n\n"
                    f"请对比分析各策略的信号差异，指出一致性和分歧，并给出综合判断。{lang_instruction}"
                ),
            }],
        )
        return response.content[0].text

    def chat(self, messages, context=None):
        """Interactive chat for follow-up questions about analysis.

        Args:
            messages: List of message dicts (role, content).
            context: Optional context string prepended as system message.

        Returns:
            Assistant reply string.
        """
        system = (
            "你是一位专业的股票分析助手，正在与用户讨论投资策略和股票分析。"
            "回答应当专业、简洁、实用。决策权始终在用户手中。"
        )
        if context:
            system += f"\n\n当前分析上下文：\n{context}"

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            system=system,
            messages=messages,
        )
        return response.content[0].text
