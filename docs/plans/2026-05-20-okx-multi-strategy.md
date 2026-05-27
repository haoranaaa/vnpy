# OKX Multi-Strategy Runtime Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable the OKX auto-trading wrapper to run multiple CTA strategy instances for multiple symbols while preserving the current single-DOGE configuration.

**Architecture:** Keep vn.py's existing one-symbol-per-CTA-strategy model. Add a compatibility layer that normalizes either legacy `strategy` config or new `strategies` config into strategy specs, then loop setup/init/start/health state over those specs. Strategy IDs must be unique per strategy to avoid Telegram approval collisions.

**Tech Stack:** Python 3.12, pytest, vn.py CTA engine, OKX gateway, local JSON state/health files.

---

### Task 1: Strategy Spec Normalization

**Files:**
- Modify: `run_auto_trading.py`
- Test: `tests/test_auto_trading_wiring.py`

**Steps:**
1. Add failing tests for legacy `strategy` config and new `strategies` config.
2. Implement a helper that returns a list of specs with `strategy_name`, `vt_symbol`, and `setting`.
3. Preserve `DoubleMA_Auto` for legacy config.
4. Verify focused tests.

### Task 2: Multi-Strategy Setup And Lifecycle

**Files:**
- Modify: `run_auto_trading.py`
- Test: `tests/test_auto_trading_wiring.py`

**Steps:**
1. Add failing tests that `setup_strategy()` adds/subscribes multiple strategies.
2. Add failing tests that init/start loops over all strategy names.
3. Implement looped `upsert_strategy()`, `setup_strategy()`, and `init_and_start_strategies()`.
4. Verify focused tests.

### Task 3: Runtime State And Health

**Files:**
- Modify: `run_auto_trading.py`
- Modify: `tools/okx_auto_health.py`
- Test: `tests/test_okx_auto_health.py`

**Steps:**
1. Add failing health tests for per-symbol ticks and per-strategy readiness.
2. Store `state["strategies"]`, `state["latest_ticks"]`, and `state["latest_prices"]`.
3. Keep legacy `latest_tick_ts`/`latest_price` as aggregate compatibility fields.
4. Update health evaluation to require all configured strategy entries to be inited/trading and all tracked ticks fresh.
5. Verify focused tests.

### Task 4: Telegram Trade ID Safety

**Files:**
- Modify: `double_ma_telegram_strategy.py`
- Test: `tests/test_dynamic_sizing.py`

**Steps:**
1. Add failing test that generated trade IDs include the strategy name.
2. Change trade ID format to include `strategy_name`.
3. Verify focused tests.

### Task 5: Config And Documentation

**Files:**
- Modify: `config/trading_config.json`
- Modify: `README_AUTO_TRADING.md`

**Steps:**
1. Document `strategies` as the new multi-symbol option while keeping `strategy` compatibility.
2. Add an example using DOGE/BTC/ETH with conservative DEMO sizing notes.
3. Verify JSON parses and docs references are clear.

### Task 6: Final Verification

**Commands:**
- `.venv/bin/python -m pytest tests/test_auto_trading_wiring.py tests/test_okx_auto_health.py tests/test_dynamic_sizing.py tests/test_risk_engine.py -q`
- `.venv/bin/python -m pytest tests/test_auto_trading_wiring.py tests/test_telegram_async.py tests/test_dynamic_sizing.py tests/test_risk_engine.py tests/test_okx_auto_health.py tests/test_okx_auto_trading_script.py -q`
- `git diff --check`

**Expected:** All targeted tests pass, whitespace check passes, and unrelated dirty files remain untouched.
