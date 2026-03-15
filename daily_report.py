"""Daily report generator — automated analysis report for all tracked stocks."""

import json
import os
from datetime import datetime
from pathlib import Path

from market_data import MarketData
from news_fetcher import NewsFetcher
from analyzer import StockAnalyzer
from strategy import load_strategy, list_strategies, evaluate_signals

REPORTS_DIR = Path("reports")


def generate_daily_report(strategy_name=None, language="zh"):
    """Generate a daily analysis report for all strategies or a specific one.

    Args:
        strategy_name: Specific strategy to report on, or None for all.
        language: Report language ('zh' or 'en').

    Returns:
        Path to the generated report file.
    """
    REPORTS_DIR.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    market = MarketData()
    news = NewsFetcher()
    analyzer = StockAnalyzer()

    strategies = [strategy_name] if strategy_name else list_strategies()
    if not strategies:
        return _write_report(today, "没有找到任何策略配置。请先创建策略：python stock_assistant.py strategy create <name>")

    report_sections = []
    report_sections.append(f"# 每日股票分析报告\n\n**日期**: {today}\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_sections.append("---\n")

    # Market sentiment (collect all symbols first)
    all_symbols = set()
    loaded_strategies = {}
    for s_name in strategies:
        try:
            strat = load_strategy(s_name)
            loaded_strategies[s_name] = strat
            all_symbols.update(strat.get("symbols", []))
        except FileNotFoundError:
            report_sections.append(f"\n## ⚠ 策略 '{s_name}' 未找到\n")

    if all_symbols:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching market sentiment...")
        try:
            sentiment = news.search_market_sentiment(list(all_symbols), language=language)
            report_sections.append(f"\n## 市场整体情绪\n\n{sentiment}\n\n---\n")
        except Exception as e:
            report_sections.append(f"\n## 市场整体情绪\n\n获取失败: {e}\n\n---\n")

    # Per-strategy analysis
    for s_name, strat in loaded_strategies.items():
        report_sections.append(f"\n## 策略: {strat.get('name', s_name)}\n")
        report_sections.append(f"**风格**: {strat.get('style', 'N/A')} | **描述**: {strat.get('description', 'N/A')}\n")

        symbols = strat.get("symbols", [])
        for symbol in symbols:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Analyzing {symbol}...")
            report_sections.append(f"\n### {symbol}\n")

            try:
                stock_info = market.get_stock_info(symbol)
                technicals = market.calculate_technicals(symbol)
                signals = evaluate_signals(strat, technicals, stock_info)

                # Fetch news
                company_name = stock_info.get("name")
                stock_news = news.search_stock_news(symbol, company_name, language=language)

                # AI analysis
                analysis = analyzer.analyze(stock_info, technicals, signals, stock_news, strat, language=language)

                report_sections.append(f"\n{analysis}\n")
            except Exception as e:
                report_sections.append(f"\n分析失败: {e}\n")

            report_sections.append("\n---\n")

    # Footer
    report_sections.append(
        "\n\n> **免责声明**: 本报告由 AI 生成，仅供参考，不构成投资建议。"
        "投资有风险，决策需谨慎。所有操作建议仅基于公开数据和预设策略规则的分析结果。\n"
    )

    report_content = "\n".join(report_sections)
    return _write_report(today, report_content)


def _write_report(date_str, content):
    """Write report content to a markdown file.

    Args:
        date_str: Date string for filename.
        content: Report content.

    Returns:
        Path to the written report file.
    """
    REPORTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%H%M%S")
    path = REPORTS_DIR / f"report_{date_str}_{timestamp}.md"
    path.write_text(content, encoding="utf-8")
    print(f"\nReport saved to: {path}")
    return path


if __name__ == "__main__":
    generate_daily_report()
