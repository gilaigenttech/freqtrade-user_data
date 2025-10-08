# 🎯 Freqtrade Command Reference

## ⚠️ IMPORTANT: Command Syntax

**CORRECT format:**
```bash
freqtrade [COMMAND] --config [CONFIG_FILE] [OPTIONS]
          ^^^^^^^
          Command comes FIRST!
```

**WRONG format:**
```bash
❌ freqtrade --config config.json --strategy MyStrategy
   (Missing command!)
```

---

## 🚀 Starting the Bot

### Method 1: Use the Scripts (Recommended!)

```bash
# Dry run (simulated trading)
cd /home/gil/freqtrade/user_data
./start_dryrun.sh

# Live testnet (real orders, fake money)
cd /home/gil/freqtrade/user_data
./start_testnet.sh
```

### Method 2: Manual Start

```bash
# From freqtrade root directory
cd /home/gil/freqtrade

# Dry run
./venv/bin/freqtrade trade \
  --config user_data/config_dryrun_futures.json \
  --strategy NostalgiaForInfinityX6

# Live testnet
./venv/bin/freqtrade trade \
  --config user_data/config_testnet_futures.json \
  --strategy NostalgiaForInfinityX6
```

### Method 3: Background (with screen)

```bash
cd /home/gil/freqtrade

# Start in background
screen -dmS freqtrade ./venv/bin/freqtrade trade \
  --config user_data/config_dryrun_futures.json \
  --strategy NostalgiaForInfinityX6

# Reattach to view
screen -r freqtrade

# Detach: Press Ctrl+A then D
```

---

## 📊 Monitoring Commands

### Show Trades

```bash
cd /home/gil/freqtrade

# All trades
./venv/bin/freqtrade show-trades \
  --config user_data/config_dryrun_futures.json

# Only open trades
./venv/bin/freqtrade show-trades \
  --config user_data/config_dryrun_futures.json \
  --trade-ids open
```

### Show Profit

```bash
cd /home/gil/freqtrade

./venv/bin/freqtrade show-profit \
  --config user_data/config_dryrun_futures.json
```

### Show Config

```bash
cd /home/gil/freqtrade

./venv/bin/freqtrade show-config \
  --config user_data/config_dryrun_futures.json
```

### View Logs

```bash
# Live tail
tail -f /home/gil/freqtrade/user_data/logs/freqtrade.log

# Last 50 lines
tail -50 /home/gil/freqtrade/user_data/logs/freqtrade.log

# Search for errors
grep ERROR /home/gil/freqtrade/user_data/logs/freqtrade.log
```

---

## 📥 Data Management

### Download Data

```bash
cd /home/gil/freqtrade

./venv/bin/freqtrade download-data \
  --config user_data/config_dryrun_futures.json \
  --timerange 20251001- \
  --timeframe 5m 1h 4h 1d
```

### List Downloaded Data

```bash
cd /home/gil/freqtrade

./venv/bin/freqtrade list-data \
  --config user_data/config_dryrun_futures.json
```

---

## 🔄 Process Management

### Check if Running

```bash
ps aux | grep freqtrade | grep -v grep
```

### Stop the Bot

```bash
# Kill by process name
pkill -f 'freqtrade trade'

# Or quit screen session
screen -S freqtrade -X quit
```

### Restart

```bash
# Stop
pkill -f 'freqtrade trade'

# Wait
sleep 2

# Start
cd /home/gil/freqtrade/user_data
./start_dryrun.sh
```

---

## 📈 Backtesting

### Run Backtest

```bash
cd /home/gil/freqtrade

./venv/bin/freqtrade backtesting \
  --config user_data/config_dryrun_futures.json \
  --strategy NostalgiaForInfinityX6 \
  --timerange 20250101-20250401
```

### Show Backtest Results

```bash
cd /home/gil/freqtrade

./venv/bin/freqtrade backtesting-show \
  --export-filename user_data/backtest_results/backtest-result-YYYY-MM-DD_HH-MM-SS.json
```

---

## 🎨 FreqUI Web Interface

### Access FreqUI

1. Make sure bot is running
2. Open browser: **http://localhost:8081**
3. Login:
   - Username: `admin`
   - Password: `IPXJ_w_f1KdDrgkUbufT_w`

### Check FreqUI Status

```bash
# Check if port is listening
netstat -tuln | grep 8081

# Or
lsof -i :8081
```

---

## 🔍 Troubleshooting Commands

### Verify Config is Valid

```bash
cd /home/gil/freqtrade

./venv/bin/freqtrade show-config \
  --config user_data/config_dryrun_futures.json
```

### Test Pairlist

```bash
cd /home/gil/freqtrade

./venv/bin/freqtrade test-pairlist \
  --config user_data/config_dryrun_futures.json
```

### List Available Strategies

```bash
cd /home/gil/freqtrade

./venv/bin/freqtrade list-strategies \
  --userdir user_data
```

### Check Database

```bash
cd /home/gil/freqtrade

# Show trades from database
./venv/bin/freqtrade show-trades \
  --config user_data/config_dryrun_futures.json \
  --db-url sqlite:///user_data/tradesv3.dryrun.sqlite
```

---

## 📱 Telegram Commands

Once Telegram is set up, use these in your Telegram bot:

```
/start      - Start the bot
/stop       - Stop the bot
/status     - Show open trades
/profit     - Show profit summary
/balance    - Show balance
/daily      - Daily profit
/weekly     - Weekly profit
/monthly    - Monthly profit
/count      - Trade count
/locks      - Show locked pairs
/unlock     - Unlock a pair
/reload_config - Reload configuration
/show_config - Show current config
/stopbuy    - Stop buying (only close)
/forceexit <trade_id> - Force exit a trade
/help       - Show all commands
```

---

## 🛠️ Common Tasks

### 1. First Time Setup

```bash
# 1. Download data
cd /home/gil/freqtrade
./venv/bin/freqtrade download-data \
  --config user_data/config_dryrun_futures.json \
  --timerange 20251001-

# 2. Start bot
cd user_data
./start_dryrun.sh

# 3. Open FreqUI
# Browser: http://localhost:8081
```

### 2. Daily Monitoring

```bash
# Check status
cd /home/gil/freqtrade/user_data
./check_status.sh

# View logs
tail -f logs/freqtrade.log

# Check trades
cd /home/gil/freqtrade
./venv/bin/freqtrade show-trades \
  --config user_data/config_dryrun_futures.json
```

### 3. Switch from Dry Run to Testnet

```bash
# 1. Stop dry run
pkill -f 'freqtrade trade'

# 2. Update testnet API keys
nano /home/gil/freqtrade/user_data/config_testnet_futures.json

# 3. Start testnet
cd /home/gil/freqtrade/user_data
./start_testnet.sh
```

---

## 📚 Quick Reference Card

| Task | Command |
|------|---------|
| Start (dry run) | `cd /home/gil/freqtrade && ./venv/bin/freqtrade trade --config user_data/config_dryrun_futures.json --strategy NostalgiaForInfinityX6` |
| Start (testnet) | `cd /home/gil/freqtrade && ./venv/bin/freqtrade trade --config user_data/config_testnet_futures.json --strategy NostalgiaForInfinityX6` |
| Stop | `pkill -f 'freqtrade trade'` |
| Show trades | `cd /home/gil/freqtrade && ./venv/bin/freqtrade show-trades --config user_data/config_dryrun_futures.json` |
| View logs | `tail -f /home/gil/freqtrade/user_data/logs/freqtrade.log` |
| Check running | `ps aux \| grep freqtrade \| grep -v grep` |
| FreqUI | `http://localhost:8081` |

---

## 🎯 Pro Tips

1. **Always run from `/home/gil/freqtrade`** (not user_data!)
2. **Use relative path** `user_data/config_...` not absolute
3. **Use scripts** instead of manual commands (easier!)
4. **Check logs** if something doesn't work
5. **Wait 24-48 hours** for first trades to appear

---

**Need help?** Check the other guides:
- `cat QUICKSTART.txt` - Fast start
- `cat README.md` - Main guide
- `cat FREQUI_GUIDE.md` - Web interface
- `cat TELEGRAM_SETUP.md` - Telegram setup
