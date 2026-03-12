# Wheeely Stock Screener

## What This Is

A stock screening module for the Wheeely options wheel strategy bot. Screens stocks using Finnhub fundamental data (market cap, debt/equity, margins, sales growth) and Alpaca market data (price, volume, RSI, SMA200, options availability), then scores and ranks candidates for wheel suitability. Results display as a Rich table with color-coded scores, filter elimination summaries, and progress indicators. Users configure screening via YAML presets (conservative/moderate/aggressive) with custom overrides. Integrates as standalone `run-screener` CLI and `run-strategy --screen` flag.

## Core Value

Automatically identify wheel-strategy-suitable stocks by combining fundamental health checks with technical screening, replacing manual symbol selection with data-driven filtering.

## Requirements

### Validated

- ✓ Alpaca API integration for trading, stock data, and option data — existing
- ✓ CLI entry point pattern with Typer — v1.0
- ✓ Symbol list management via config/symbol_list.txt — existing
- ✓ BrokerClient facade over Alpaca SDK clients — existing
- ✓ Strategy parameter configuration via config/params.py — existing
- ✓ Environment-based credential management via .env — existing
- ✓ YAML-based screening config with preset profiles and custom overrides — v1.0 (CONF-01..04)
- ✓ Finnhub API integration with rate limiting and fallback chains — v1.0 (SAFE-01, SAFE-02, SAFE-04)
- ✓ Alpaca market data for technical screening (RSI, SMA200, volume) — v1.0 (FILT-05..08)
- ✓ 10 screening filters with cheap-first pipeline ordering — v1.0 (FILT-01..10)
- ✓ Wheel suitability scoring with 3 weighted components — v1.0 (SCOR-01, SCOR-02)
- ✓ Rich table output with color-coded scores and filter summaries — v1.0 (OUTP-01, OUTP-02)
- ✓ Progress indicators during rate-limited API calls — v1.0 (OUTP-04)
- ✓ Position-safe symbol list export — v1.0 (OUTP-03, SAFE-03)
- ✓ Standalone `run-screener` CLI and `run-strategy --screen` integration — v1.0 (CLI-01..04)
- ✓ Human-readable config validation errors (Rich Panels) — v1.0 (Phase 6)
- ✓ Complete pyproject.toml dependency declarations — v1.0 (Phase 6)

### Active

(None — all requirements validated through M001)

### Out of Scope

- Real-time streaming screener (WebSocket-based continuous monitoring) — batch screening sufficient for wheel strategy
- Web UI for screening results — CLI-only tool
- Backtesting screener results against historical performance — separate domain
- Finviz scraping — using Finnhub API instead for reliable fundamental data
- Custom indicator development (MACD, Bollinger, etc.) — RSI and SMA200 sufficient for v1.0
- AI/ML screening — rule-based filters are transparent and debuggable
- Multi-broker support — only Alpaca is used

## Completed Milestones

### M001 — Screener Fix + Covered Calls ✅

**Goal:** Debug and fix the stock screening pipeline (zero stocks survive filtering), add HV percentile ranking, earnings proximity filtering, options chain liquidity validation, and covered call screening for the wheel's second leg.

**Outcome:** All 10 slices shipped (S01–S10). 25/25 requirements validated. 345 tests passing, zero failures.

**Key deliverables:**
- Fixed zero-results pipeline bug (D/E normalization + preset differentiation)
- 4-stage screening pipeline: technicals → earnings → fundamentals → options chain
- 3 differentiated presets with sector avoid/prefer lists
- HV percentile ranking and earnings proximity exclusion
- Options chain OI/spread validation with put premium yield display
- `run-call-screener` standalone CLI for covered call recommendations
- `run-strategy` integration with call screener for assigned positions

## Current Milestone

None — no active milestone.

## Context

Tech stack: Python 3.13, alpaca-py, finnhub-python, ta, pydantic, rich, typer, pyyaml.
345 tests passing, zero failures. 28/28 v1.0 requirements satisfied. 25/25 M001 requirements validated.

---
*Last updated: 2026-03-11 after M001 completion*
