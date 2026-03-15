#!/usr/bin/env python3
"""Stock Strategy Assistant — CLI tool for intelligent stock analysis and strategy management."""

import argparse
import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()


def cmd_analyze(args):
    """Analyze a specific stock."""
    from market_data import MarketData
    from news_fetcher import NewsFetcher
    from analyzer import StockAnalyzer
    from strategy import load_strategy, evaluate_signals

    market = MarketData()
    news = NewsFetcher()
    analyzer = StockAnalyzer()

    symbol = args.symbol.upper()
    print(f"\n{'='*60}")
    print(f"  Analyzing {symbol}...")
    print(f"{'='*60}\n")

    # Fetch data
    print("[1/4] Fetching stock data...")
    stock_info = market.get_stock_info(symbol)
    print(f"  {stock_info.get('name', symbol)} | Price: {stock_info.get('current_price')} {stock_info.get('currency')}")

    print("[2/4] Calculating technicals...")
    technicals = market.calculate_technicals(symbol)

    # Strategy signals
    signals = None
    strategy = None
    if args.strategy:
        print(f"[3/4] Evaluating strategy '{args.strategy}'...")
        strategy = load_strategy(args.strategy)
        signals = evaluate_signals(strategy, technicals, stock_info)
        print(f"  Buy signals: {signals['buy_signals']} | Sell: {signals['sell_signals']} | Hold: {signals['hold_signals']}")
    else:
        print("[3/4] No strategy specified (use --strategy <name> for signal evaluation)")
        signals = {"signals": [], "note": "No strategy specified"}
        strategy = {"risk_management": {}}

    print("[4/4] Fetching news and generating AI analysis...")
    stock_news = news.search_stock_news(symbol, stock_info.get("name"), language=args.lang)
    analysis = analyzer.analyze(stock_info, technicals, signals, stock_news, strategy, language=args.lang)

    print(f"\n{'='*60}")
    print(analysis)
    print(f"\n{'='*60}\n")


def cmd_report(args):
    """Generate daily report."""
    from daily_report import generate_daily_report

    print("\nGenerating daily report...\n")
    path = generate_daily_report(strategy_name=args.strategy, language=args.lang)
    print(f"\nDone! Open the report: {path}")


def cmd_watch(args):
    """Quick watch — show key metrics for symbols."""
    from market_data import MarketData

    market = MarketData()
    symbols = args.symbols

    print(f"\n{'Symbol':<12} {'Price':>10} {'Change%':>10} {'RSI':>8} {'Volume':>10} {'MA20':>10}")
    print("-" * 62)

    for sym in symbols:
        try:
            info = market.get_stock_info(sym)
            tech = market.calculate_technicals(sym)
            price = info.get("current_price", 0)
            prev = info.get("previous_close", price)
            change_pct = ((price - prev) / prev * 100) if prev else 0
            rsi = tech.get("rsi_14", "-")
            vol = info.get("volume", 0)
            ma20 = tech.get("ma20", "-")

            vol_str = f"{vol/1e6:.1f}M" if isinstance(vol, (int, float)) and vol >= 1e6 else str(vol)
            rsi_str = f"{rsi:.1f}" if isinstance(rsi, float) else str(rsi)
            ma20_str = f"{ma20:.2f}" if isinstance(ma20, float) else str(ma20)

            sign = "+" if change_pct >= 0 else ""
            print(f"{sym:<12} {price:>10.2f} {sign}{change_pct:>9.2f}% {rsi_str:>8} {vol_str:>10} {ma20_str:>10}")
        except Exception as e:
            print(f"{sym:<12} Error: {e}")

    print()


def cmd_strategy_list(args):
    """List all strategies."""
    from strategy import list_strategies, load_strategy

    strategies = list_strategies()
    if not strategies:
        print("\nNo strategies found. Create one with: python stock_assistant.py strategy create <name>")
        return

    print(f"\n{'Name':<20} {'Style':<15} {'Symbols':<30} {'Rules'}")
    print("-" * 75)
    for name in strategies:
        try:
            s = load_strategy(name)
            symbols = ", ".join(s.get("symbols", []))
            print(f"{name:<20} {s.get('style', 'N/A'):<15} {symbols:<30} {len(s.get('rules', []))}")
        except Exception as e:
            print(f"{name:<20} Error: {e}")
    print()


def cmd_strategy_create(args):
    """Create a new strategy."""
    from strategy import create_default_strategy

    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    strategy = create_default_strategy(args.name, symbols, style=args.style)
    print(f"\nStrategy '{args.name}' created with {len(strategy['rules'])} rules for {len(symbols)} symbols.")
    print(f"Style: {args.style}")
    print(f"Symbols: {', '.join(symbols)}")
    print(f"\nEdit the strategy file to customize: strategies/{args.name}.yaml")


def cmd_strategy_show(args):
    """Show strategy details."""
    import yaml
    from strategy import load_strategy

    strategy = load_strategy(args.name)
    print(f"\n{yaml.dump(strategy, allow_unicode=True, default_flow_style=False, sort_keys=False)}")


def cmd_strategy_eval(args):
    """Evaluate strategy signals for its stocks."""
    from market_data import MarketData
    from strategy import load_strategy, evaluate_signals

    market = MarketData()
    strategy = load_strategy(args.name)
    symbols = strategy.get("symbols", [])

    print(f"\nEvaluating strategy '{args.name}' ({strategy.get('style', 'N/A')})...\n")

    for symbol in symbols:
        try:
            info = market.get_stock_info(symbol)
            tech = market.calculate_technicals(symbol)
            result = evaluate_signals(strategy, tech, info)

            print(f"--- {symbol} ({info.get('name', '')}) ---")
            print(f"Buy: {result['buy_signals']} | Sell: {result['sell_signals']} | Hold: {result['hold_signals']}")
            for sig in result["signals"]:
                icon = {"buy": "+", "sell": "-", "hold": "="}[sig["action"]]
                print(f"  [{icon}] {sig['name']}: {sig['reason']}")
            print()
        except Exception as e:
            print(f"--- {symbol} --- Error: {e}\n")


def cmd_chat(args):
    """Interactive chat mode for follow-up analysis."""
    from analyzer import StockAnalyzer

    analyzer = StockAnalyzer()
    messages = []
    context = None

    if args.symbol:
        from market_data import MarketData
        market = MarketData()
        try:
            info = market.get_stock_info(args.symbol.upper())
            tech = market.calculate_technicals(args.symbol.upper())
            context = f"Stock: {args.symbol.upper()} ({info.get('name')}), Price: {info.get('current_price')}, Technicals: {json.dumps(tech)}"
        except Exception:
            pass

    print("\nStock Assistant Chat (type 'exit' to quit)")
    print("-" * 40)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if user_input.lower() in ("exit", "quit", "q"):
            print("Bye!")
            break

        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})
        try:
            reply = analyzer.chat(messages, context=context)
            messages.append({"role": "assistant", "content": reply})
            print(f"\nAssistant: {reply}")
        except Exception as e:
            print(f"\nError: {e}")
            messages.pop()


def main():
    parser = argparse.ArgumentParser(
        description="Stock Strategy Assistant — AI-powered stock analysis and strategy management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s watch AAPL MSFT GOOGL          Quick overview of stocks
  %(prog)s analyze AAPL --strategy my_us   Full analysis with strategy
  %(prog)s strategy create my_us AAPL,MSFT --style balanced
  %(prog)s strategy list                   List all strategies
  %(prog)s strategy eval my_us             Evaluate strategy signals
  %(prog)s report --strategy my_us         Generate daily report
  %(prog)s chat --symbol AAPL              Interactive analysis chat
        """,
    )
    parser.add_argument("--lang", default="zh", choices=["zh", "en"], help="Output language (default: zh)")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # watch
    p_watch = subparsers.add_parser("watch", help="Quick watch stocks")
    p_watch.add_argument("symbols", nargs="+", help="Stock symbols to watch")
    p_watch.set_defaults(func=cmd_watch)

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Full analysis for a stock")
    p_analyze.add_argument("symbol", help="Stock ticker symbol")
    p_analyze.add_argument("--strategy", "-s", help="Strategy name to evaluate")
    p_analyze.set_defaults(func=cmd_analyze)

    # report
    p_report = subparsers.add_parser("report", help="Generate daily report")
    p_report.add_argument("--strategy", "-s", help="Specific strategy (default: all)")
    p_report.set_defaults(func=cmd_report)

    # strategy
    p_strategy = subparsers.add_parser("strategy", help="Strategy management")
    strat_sub = p_strategy.add_subparsers(dest="strat_command")

    p_strat_list = strat_sub.add_parser("list", help="List strategies")
    p_strat_list.set_defaults(func=cmd_strategy_list)

    p_strat_create = strat_sub.add_parser("create", help="Create a new strategy")
    p_strat_create.add_argument("name", help="Strategy name")
    p_strat_create.add_argument("symbols", help="Comma-separated stock symbols")
    p_strat_create.add_argument("--style", default="balanced", choices=["conservative", "balanced", "aggressive"])
    p_strat_create.set_defaults(func=cmd_strategy_create)

    p_strat_show = strat_sub.add_parser("show", help="Show strategy details")
    p_strat_show.add_argument("name", help="Strategy name")
    p_strat_show.set_defaults(func=cmd_strategy_show)

    p_strat_eval = strat_sub.add_parser("eval", help="Evaluate strategy signals")
    p_strat_eval.add_argument("name", help="Strategy name")
    p_strat_eval.set_defaults(func=cmd_strategy_eval)

    # chat
    p_chat = subparsers.add_parser("chat", help="Interactive analysis chat")
    p_chat.add_argument("--symbol", help="Pre-load context for a stock symbol")
    p_chat.set_defaults(func=cmd_chat)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
