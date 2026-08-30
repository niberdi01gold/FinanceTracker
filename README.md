# FinanceTracker

A Telegram bot that consolidates a Binance crypto wallet and an Interactive Brokers stock portfolio into one view, sends scheduled reports, and raises technical-analysis alerts.

Built because checking two platforms every morning is two platforms too many.

---

## What it does

**On demand** — eleven Telegram commands. `/resumen` returns total net worth across both platforms; `/cartera` and `/ibkr` break each one down; `/rendimiento` reports historical return against the first recorded snapshot; `/mercado` shows whether the NYSE is open and how long until it closes.

**On a schedule** — a daily report at 08:00 Santiago time with the day-over-day change, a weekly report every Monday, Binance alerts every 4 hours, IBKR alerts every 30 minutes while the market is open, and volatility checks hourly.

**On its own initiative** — technical alerts. RSI below 30 or above 70 flags oversold and overbought conditions. An EMA20/EMA50 crossover flags a possible trend change. A move of 3% or more in an hour flags a volatility spike.

---

## Stack

| Component | Choice |
| --- | --- |
| Bot framework | `python-telegram-bot` (async) |
| Scheduling | APScheduler with per-job timezones |
| Crypto data | Binance API + CoinGecko for candles |
| Stock data | IBKR Client Portal Gateway + yfinance |
| Indicators | `ta` (RSI, EMA) over pandas |
| Storage | SQLite snapshots for historical return |

---

## Design notes

**Market hours are enforced, not assumed.** IBKR alerts check `mercado_abierto()` before firing — no point analysing a stock at 3 AM New York time. The check runs in `America/New_York` while daily reports run in `America/Santiago`, so both stay correct across daylight saving shifts.

**Snapshots make return calculable.** Every daily report writes a row to SQLite before reporting. That is what lets `/rendimiento` compare against the first record, the last week, and the last month without calling any API.

**The IBKR gateway can be offline.** It only runs when the user starts it locally, so every IBKR call degrades to a readable "offline" message instead of crashing the bot. Binance reporting continues either way.

**Volatility uses in-process state.** Prices from the previous run are held in memory and compared against the current fetch, which is why the alert measures an actual hourly delta rather than a rolling 24h figure.

---

## Setup

```bash
git clone https://github.com/niberdi01gold/FinanceTracker.git
cd FinanceTracker
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
IBKR_ACCOUNT_ID=your_account_id
IBKR_URL=https://localhost:5000
```

Give the Binance key **read-only** permissions. The bot never places orders and does not need trading access.

Then run:

```bash
python main.py
```

For IBKR data, the Client Portal Gateway must be running locally and authenticated at `localhost:5000`.

---

## Commands

| Command | Returns |
| --- | --- |
| `/resumen` | Net worth across both platforms |
| `/cartera` | Binance holdings with prices |
| `/ibkr` | IBKR positions with unrealised P&L |
| `/total` | Combined portfolio value |
| `/mercado` | NYSE status and time to open/close |
| `/rendimiento` | Historical return, all-time high and low |
| `/dividendos` | Dividends received |
| `/agregar_dividendo` | Record a dividend: `TICKER AMOUNT` |
| `/btc` `/eth` | Single-asset price and holdings |
| `/ayuda` | Command list |

---

## Limits

- Binance tracking covers BTC and ETH only; other assets need adding to `binance_module.py`.
- IBKR tickers are hardcoded in `TICKERS_IBKR` and must match the account's position order.
- Alerts are informational. They are not trading signals and the bot never executes trades.
- Volatility state lives in memory, so a restart resets the hourly comparison baseline.

---

## License

MIT
