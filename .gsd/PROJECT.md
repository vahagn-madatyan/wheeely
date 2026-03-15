# Wheeely Stock Screener

## What This Is

A stock screening module for the Wheeely options wheel strategy bot. Screens stocks using Finnhub fundamental data (market cap, debt/equity, margins, sales growth) and Alpaca market data (price, volume, RSI, SMA200, options availability), then scores and ranks candidates for wheel suitability. Results display as a Rich table with color-coded scores, filter elimination summaries, and progress indicators. Users configure screening via YAML presets (conservative/moderate/aggressive) with custom overrides. Integrates as standalone `run-screener` CLI, `run-strategy --screen` flag, and `run-call-screener` for covered calls.

## Core Value

Automatically identify wheel-strategy-suitable stocks by combining fundamental health checks with technical screening, replacing manual symbol selection with data-driven filtering.

## Current State

Fully functional 4-stage screening pipeline (technicals → earnings → fundamentals → options chain) with 3 differentiated presets, HV percentile ranking, earnings proximity exclusion, options chain OI/spread validation, put premium yield display, covered call screener, strategy integration, and top-N performance cap (`--top-n` flag). "Perf 1M" column shows 1-month price performance in the results table. 368 tests passing, zero failures.

Tech stack: Python 3.13, alpaca-py, finnhub-python, ta, pydantic, rich, typer, pyyaml.

## Architecture / Key Patterns

- **Entry point:** `scripts/run_strategy.py:main()` — registered as `run-strategy` console script
- **Screener entry:** `scripts/run_screener.py:main()` — registered as `run-screener` console script
- **Call screener:** `scripts/run_call_screener.py:main()` — registered as `run-call-screener` console script
- **Pipeline:** `screener/pipeline.py:run_pipeline()` — 4-stage orchestrator (universe → bars → Stage 1 → Stage 1b → Stage 2 → Stage 3 → score → sort)
- **Filters:** Pure functions taking `ScreenedStock` + config → `FilterResult`, never raise
- **Config:** YAML presets + Pydantic validation via `screener/config_loader.py`
- **Display:** Rich tables with Console injection for testability via `screener/display.py`
- **Data:** `screener/finnhub_client.py` (rate-limited Finnhub) + `screener/market_data.py` (Alpaca bars)
- **Models:** `models/screened_stock.py` — progressive dataclass populated through pipeline stages
- **Logging shadow:** Project's `logging/` package shadows stdlib; all modules use `import logging as stdlib_logging`

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [x] M001: Screener Fix + Covered Calls — Fixed broken pipeline, added HV percentile, earnings filter, options chain validation, covered call screening
- [x] M002: Top-N Performance Cap — `--top-n` CLI flag limits expensive stage processing by selecting worst monthly performers from Stage 1 survivors; Perf 1M column in results table
- [ ] M003: Execution Cleanup — Unify put and call screening to symmetric `screen_puts()`/`screen_calls()` pattern with spread filter, annualized return scoring, DTE minimum 7 days; remove dead code
