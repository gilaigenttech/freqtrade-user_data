# 🚀 Freqtrade Setup - Complete Guide

Welcome to your Freqtrade trading bot setup! Everything you need is here.

## 📚 Available Guides

### **Getting Started:**
- 📋 **QUICKSTART.txt** - Fast 5-step setup guide
- ✅ **CHECKLIST.md** - Complete step-by-step checklist
- 🚀 **DEPLOYMENT_GUIDE.md** - Full deployment to Google Cloud

### **Configuration:**
- 🎨 **FREQUI_GUIDE.md** - Web interface setup (port 8081)
- 📱 **TELEGRAM_SETUP.md** - Mobile notifications setup
- 🎯 **TESTNET_VS_DRYRUN.md** - Dry run vs live testnet comparison

### **Quick References:**
- `./start_dryrun.sh` - Start in dry run mode (simulated)
- `./start_testnet.sh` - Start in live testnet mode (real orders, fake money)
- `./check_status.sh` - Quick dashboard

---

## 🎯 Quick Start (First Time)

```bash
# 1. Get Binance Testnet API Keys
#    Visit: https://testnet.binancefuture.com/

# 2. Add keys to config
nano config_testnet_futures.json
# Update "key" and "secret"

# 3. Download data
cd /home/gil/freqtrade
./venv/bin/freqtrade download-data \
  --config user_data/config_testnet_futures.json \
  --timerange 20251001- \
  --timeframe 5m 1h 4h 1d

# 4. Start bot
cd user_data
./start_testnet.sh

# 5. Open FreqUI
# Browser: http://localhost:8081
# Login: admin / IPXJ_w_f1KdDrgkUbufT_w
```

---

## 📱 Setup Telegram (Optional but Recommended!)

```bash
# 1. Create bot with @BotFather on Telegram
#    Send: /newbot

# 2. Get chat ID from @userinfobot

# 3. Update config
nano config_testnet_futures.json

# Find telegram section, update:
"telegram": {
  "enabled": true,
  "token": "YOUR_TOKEN_FROM_BOTFATHER",
  "chat_id": "YOUR_CHAT_ID"
}

# 4. Restart bot
pkill -f 'freqtrade trade'
./start_testnet.sh

# 5. Test in Telegram
# Send to your bot: /status
```

**Full guide:** `cat TELEGRAM_SETUP.md`

---

## 🎨 FreqUI Access

**URL:** http://localhost:8081

**Login:**
- Username: `admin`
- Password: `IPXJ_w_f1KdDrgkUbufT_w`

**Features:**
- 📊 Real-time dashboard
- 💰 Profit tracking
- 📈 Live charts
- 🎯 Force exit trades
- 📜 View logs

**Full guide:** `cat FREQUI_GUIDE.md`

---

## 📋 Configuration Files

| File | Purpose | Mode |
|------|---------|------|
| `config_dryrun_futures.json` | Dry run (simulated) | Zero risk |
| `config_testnet_futures.json` | Live testnet (real orders, fake money) | Zero risk |
| *(future) config_live_futures.json* | Live production | Real money! |

---

## �� Recommended Progression

| Week | Mode | Config | Purpose |
|------|------|--------|---------|
| 1-2 | **Dry Run** | config_dryrun_futures.json | Learn the bot |
| 3-4 | **Live Testnet** | config_testnet_futures.json | Test real orders |
| 5-6 | **Live Testnet** | config_testnet_futures.json | Validate stability |
| 7+ | **Live (Small!)** | config_live_futures.json | Real trading |

**NEVER skip testnet!** It catches issues dry run can't.

---

## 🔧 Common Commands

```bash
# Start bot (dry run)
./start_dryrun.sh

# Start bot (live testnet)
./start_testnet.sh

# Check status
./check_status.sh

# View logs
tail -f logs/freqtrade.log

# Stop bot
pkill -f 'freqtrade trade'

# Reattach to screen
screen -r freqtrade

# Show trades
cd /home/gil/freqtrade/user_data
../venv/bin/freqtrade show-trades \
  --config config_testnet_futures.json
```

---

## 📱 Telegram Commands

Once Telegram is setup:

```
/status        - Show open trades
/profit        - Show profit summary
/balance       - Show balance
/daily         - Daily profit
/forceexit 1   - Exit trade #1
/help          - All commands
```

---

## 🆘 Troubleshooting

### Bot won't start
```bash
# Check logs
tail -50 logs/freqtrade.log

# Verify config
cd /home/gil/freqtrade
./venv/bin/freqtrade show-config \
  --config user_data/config_testnet_futures.json
```

### No trades appearing
- Wait 24-48 hours
- Check logs for errors
- Verify data downloaded
- Check API keys valid

### FreqUI won't load
```bash
# Check bot running
./check_status.sh

# Check port 8081
netstat -tulpn | grep 8081

# Restart bot
pkill -f 'freqtrade trade'
./start_testnet.sh
```

### Telegram not working
```bash
# Verify config
grep -A 3 '"telegram"' config_testnet_futures.json

# Test bot token
curl -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -d "chat_id=<CHAT_ID>" \
  -d "text=Test"
```

---

## 📊 What to Expect

### Dry Run (Week 1-2):
- Simulated trades
- Instant fills
- No slippage
- Learn strategy behavior

### Live Testnet (Week 3-6):
- Real orders on testnet
- Orders may not fill
- Slippage happens
- Production-like behavior

### Live Production (Week 7+):
- Real money
- Real profits/losses
- Start with $500-1000
- Scale slowly

---

## 🔒 Security Checklist

- [ ] API keys have trading-only permission
- [ ] No withdrawal permission on API keys
- [ ] Testnet keys for testing (not production!)
- [ ] Telegram token kept private
- [ ] FreqUI password changed from default
- [ ] 2FA enabled on exchange
- [ ] IP whitelist on exchange API
- [ ] config_secret.json in .gitignore

---

## 📈 Performance Expectations

Based on Q1 2025 backtest:

| Metric | Dry Run | Live Testnet | Expected |
|--------|---------|--------------|----------|
| Win Rate | 96.4% | 90-95% | Normal |
| Profit % | 87.44% | 75-85% | Good |
| Trades | 169 | 140-160 | Expected |

**Lower testnet performance is NORMAL** due to:
- Real slippage
- Orders not filling
- Partial fills
- Market timing

---

## 🎯 Today's Goals

- [ ] Read QUICKSTART.txt
- [ ] Get Binance Testnet API keys
- [ ] Configure config_testnet_futures.json
- [ ] Download data
- [ ] Start bot
- [ ] Access FreqUI (http://localhost:8081)
- [ ] Setup Telegram (optional)
- [ ] Monitor first 24 hours

---

## 📚 Learn More

**View any guide:**
```bash
cat QUICKSTART.txt           # Fast start
cat CHECKLIST.md             # Complete checklist
cat FREQUI_GUIDE.md          # Web interface
cat TELEGRAM_SETUP.md        # Mobile alerts
cat TESTNET_VS_DRYRUN.md     # Mode comparison
cat DEPLOYMENT_GUIDE.md      # Google Cloud
```

**Freqtrade Documentation:**
- https://www.freqtrade.io/en/stable/

**Community:**
- Discord: https://discord.gg/freqtrade
- GitHub: https://github.com/freqtrade/freqtrade

---

## 🚀 Ready to Start?

```bash
# Read the quick start
cat QUICKSTART.txt

# When ready
./start_testnet.sh

# Open FreqUI
# http://localhost:8081

# Enjoy! 🎉
```

---

**Need help?** Check the guides above or visit the Freqtrade Discord!

**Good luck trading! 🚀💰**
