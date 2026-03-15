"""News and information fetcher for stock analysis."""

import json
import os
from datetime import datetime

import anthropic


class NewsFetcher:
    """Fetch and summarize stock-related news using Claude with web search."""

    def __init__(self, api_key=None):
        self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    def search_stock_news(self, symbol, company_name=None, language="zh"):
        """Search for latest news about a stock using Claude's web search.

        Args:
            symbol: Stock ticker symbol.
            company_name: Company name for better search results.
            language: Response language ('zh' for Chinese, 'en' for English).

        Returns:
            Dict with news summary and key items.
        """
        name = company_name or symbol
        lang_instruction = "请用中文回答。" if language == "zh" else "Please answer in English."

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            tools=[{"type": "web_search_20250305"}],
            messages=[{
                "role": "user",
                "content": (
                    f"搜索 {name} ({symbol}) 最新的股票相关新闻和市场动态。"
                    f"包括：1) 最近的重大新闻 2) 分析师评级变动 3) 行业动态 4) 财报或重大事件。"
                    f"请整理成结构化的摘要，每条新闻注明来源和日期。{lang_instruction}"
                ),
            }],
        )
        return self._extract_text(response)

    def search_market_sentiment(self, symbols, language="zh"):
        """Search for overall market sentiment and how it affects given stocks.

        Args:
            symbols: List of stock ticker symbols.
            language: Response language.

        Returns:
            Dict with market sentiment analysis.
        """
        symbol_list = ", ".join(symbols)
        lang_instruction = "请用中文回答。" if language == "zh" else "Please answer in English."

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            tools=[{"type": "web_search_20250305"}],
            messages=[{
                "role": "user",
                "content": (
                    f"搜索当前整体市场情绪和宏观经济动态，特别关注对以下股票的影响：{symbol_list}。"
                    f"包括：1) 主要股指走势 2) 宏观经济指标 3) 央行政策动向 "
                    f"4) 地缘政治风险 5) 市场情绪指标（如VIX、融资融券等）。{lang_instruction}"
                ),
            }],
        )
        return self._extract_text(response)

    def search_sector_analysis(self, sector, language="zh"):
        """Search for sector-specific analysis.

        Args:
            sector: Industry sector name.
            language: Response language.

        Returns:
            Dict with sector analysis.
        """
        lang_instruction = "请用中文回答。" if language == "zh" else "Please answer in English."

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1536,
            tools=[{"type": "web_search_20250305"}],
            messages=[{
                "role": "user",
                "content": (
                    f"搜索 {sector} 行业板块的最新动态和分析。"
                    f"包括：1) 行业政策变化 2) 龙头企业动态 3) 行业趋势 4) 风险因素。"
                    f"{lang_instruction}"
                ),
            }],
        )
        return self._extract_text(response)

    def _extract_text(self, response):
        """Extract text content from Claude API response."""
        texts = []
        for block in response.content:
            if block.type == "text":
                texts.append(block.text)
        return "\n".join(texts)
