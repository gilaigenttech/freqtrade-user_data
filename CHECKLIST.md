# 📋 Dry Run to Live Trading Checklist

## Phase 1: Dry Run Setup ✅

### Step 1: Get Binance Testnet API Keys
- [ ] Visit https://testnet.binancefuture.com/
- [ ] Login with GitHub/Google
- [ ] Generate API Key + Secret
- [ ] Save keys securely

### Step 2: Configure Dry Run
- [ ] Edit `config_dryrun_futures.json`
- [ ] Add Binance Testnet API keys
- [ ] Verify `"dry_run": true`
- [ ] Check `"trading_mode": "futures"`
- [ ] Set reasonable `max_open_trades: 6`

### Step 3: Download Data
```bash
cd /home/gil/freqtrade
./venv/bin/freqtrade download-data \
  --config user_data/config_dryrun_futures.json \
  --timerange 20251001- \
  --timeframe 5m 1h 4h 1d
```
- [ ] Data downloaded successfully
- [ ] Check `user_data/data/binance/` has files

### Step 4: Start Dry Run
```bash
cd /home/gil/freqtrade/user_data
./start_dryrun.sh
```
- [ ] Bot starts without errors
- [ ] Check logs: `tail -f logs/freqtrade.log`
- [ ] Verify pairs being analyzed
- [ ] Confirm strategy loaded

### Step 5: Monitor First 24 Hours
- [ ] No critical errors in logs
- [ ] Strategy populating indicators
- [ ] Seeing "enter_short" signals (tag 603)
- [ ] Position sizing correct (~166 USDT per trade with 1000 wallet)
- [ ] Leverage applied (3x for futures)

### Step 6: Setup Telegram (Optional but Recommended) 📱
- [ ] Message @BotFather → `/newbot`
- [ ] Save bot token
- [ ] Message @userinfobot → Get chat_id
- [ ] Update config with token and chat_id
- [ ] Set `"enabled": true` in telegram section
- [ ] Restart bot
- [ ] Receive startup message
- [ ] Test `/status` command
- [ ] Test `/profit` command

**Full Telegram guide:** `cat TELEGRAM_SETUP.md`

---

## Phase 2: Dry Run Validation (1-2 Weeks) ✅

### Daily Checks
- [ ] Check for new trades: `freqtrade show-trades`
- [ ] Monitor profit/loss
- [ ] Review logs for errors
- [ ] Verify grinding behavior not too aggressive
- [ ] Check max drawdown stays reasonable (<20%)

### What to Look For:
✅ **Good Signs:**
- Profitable overall or close to breakeven
- Win rate >50%
- Trades closing successfully
- Grinding adds positions gradually
- No repeated errors

❌ **Red Flags:**
- Massive drawdowns (>30%)
- Many simultaneous positions (>10)
- Positions stuck for weeks
- Strategy errors/crashes
- Excessive DCA (>20 entries per trade)

---

## Phase 3: Google Cloud Setup ✅

### Step 1: Create GCP Account
- [ ] Sign up at https://cloud.google.com
- [ ] Claim $300 free credit (90 days)
- [ ] Enable Compute Engine API

### Step 2: Create VM Instance
**Recommended Specs:**
- Machine: e2-medium (2 vCPU, 4GB RAM)
- OS: Ubuntu 22.04 LTS
- Disk: 30GB SSD
- Region: us-central1 (or closest to you)

```bash
gcloud compute instances create freqtrade-bot \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB
```
- [ ] VM created successfully
- [ ] Note external IP address

### Step 3: Install Freqtrade on VM
```bash
# SSH into VM
gcloud compute ssh freqtrade-bot

# Update & install
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git build-essential

# Clone & install
git clone https://github.com/freqtrade/freqtrade.git
cd freqtrade
./setup.sh -i
```
- [ ] Freqtrade installed
- [ ] Virtual environment created

### Step 4: Transfer Configuration
```bash
# Option A: SCP from local
gcloud compute scp --recurse \
  /home/gil/freqtrade/user_data \
  freqtrade-bot:~/freqtrade/

# Option B: Git (recommended)
# Push your config to private GitHub repo first
cd ~/freqtrade
git clone https://github.com/YOUR_USER/freqtrade-config.git user_data
```
- [ ] Config files transferred
- [ ] Strategy file present
- [ ] API keys configured

### Step 5: Setup Auto-Start Service
```bash
# Create systemd service
sudo nano /etc/systemd/system/freqtrade.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable freqtrade
sudo systemctl start freqtrade
```
- [ ] Service created
- [ ] Auto-start enabled
- [ ] Bot running on VM

---

## Phase 4: Going Live Preparation ✅

### Before Going Live, You MUST:

#### 1. Dry Run Performance Check
- [ ] Ran dry run for minimum 2 weeks
- [ ] Overall profitable or small loss (<5%)
- [ ] Understand strategy behavior
- [ ] Comfortable with risk

#### 2. Create LIVE Binance API Keys
- [ ] Login to Binance.com
- [ ] Go to API Management
- [ ] Create new API key
- [ ] **Enable Futures Trading** permission
- [ ] **DISABLE Withdrawal** permission
- [ ] Enable IP whitelist (add GCP VM IP)
- [ ] Enable 2FA requirement

#### 3. Security Setup
- [ ] 2FA enabled on Binance
- [ ] API keys IP whitelisted
- [ ] Strong API key restrictions (trading only)
- [ ] Secure password manager for keys
- [ ] Never commit keys to Git

#### 4. Risk Configuration
Create `config_live_futures.json`:
```json
{
  "dry_run": false,  // ⚠️ LIVE TRADING!
  "stake_amount": 50,  // Start small!
  "max_open_trades": 3,  // Conservative
  "tradable_balance_ratio": 0.5,  // Use 50% max
  "exchange": {
    "key": "LIVE_API_KEY",
    "secret": "LIVE_API_SECRET"
  }
}
```

- [ ] Set fixed `stake_amount` (50-100 USDT)
- [ ] Reduce `max_open_trades` (3-4)
- [ ] Set `tradable_balance_ratio: 0.5`
- [ ] Enable `stoploss_on_exchange: true`

#### 5. Funding & Testing
- [ ] Deposit initial capital (500-1000 USDT)
- [ ] Test with minimum stake first
- [ ] Verify orders execute correctly
- [ ] Check leverage applies correctly

---

## Phase 5: Live Trading Monitoring ✅

### First Week of Live Trading:

#### Daily Tasks:
- [ ] Check Telegram alerts (if enabled)
- [ ] Review open positions
- [ ] Check for errors in logs
- [ ] Monitor drawdown
- [ ] Verify positions size correctly

#### Weekly Tasks:
- [ ] Review total P&L
- [ ] Check win rate
- [ ] Analyze closed trades
- [ ] Adjust parameters if needed
- [ ] Backup logs and database

#### Red Flags to Stop Trading:
❌ **STOP if you see:**
- Drawdown >15% in first week
- Repeated API errors
- Positions not closing
- Unexpected leverage
- Funding fees too high

---

## Emergency Procedures 🚨

### How to Stop Bot Immediately:

**On Local Machine:**
```bash
pkill -f 'freqtrade trade'
# or if using screen:
screen -S freqtrade -X quit
```

**On GCP VM:**
```bash
sudo systemctl stop freqtrade
```

### How to Close All Positions:

**Via FreqUI:**
1. Open FreqUI in browser
2. Go to "Open Trades"
3. Click "Force Exit All"

**Via Command Line:**
```bash
freqtrade forceexit all --config config_live_futures.json
```

---

## Recommended Timeline

| Week | Activity | Status |
|------|----------|--------|
| Week 1 | Setup dry run locally | [ ] |
| Week 2-3 | Monitor dry run performance | [ ] |
| Week 4 | Setup GCP VM | [ ] |
| Week 5 | Run dry run on GCP | [ ] |
| Week 6 | Create live config, start with $500 | [ ] |
| Week 7+ | Monitor and gradually increase capital | [ ] |

---

## Support Resources

- **Freqtrade Docs:** https://www.freqtrade.io/en/stable/
- **Strategy Analysis:** https://www.freqtrade.io/en/stable/strategy-analysis/
- **Discord Community:** https://discord.gg/freqtrade
- **GitHub Issues:** https://github.com/freqtrade/freqtrade/issues

---

## Quick Reference Commands

### Check Status:
```bash
freqtrade show-trades --config CONFIG_FILE
freqtrade status --config CONFIG_FILE
```

### View Logs:
```bash
tail -f user_data/logs/freqtrade.log
```

### Force Exit:
```bash
freqtrade forceexit TRADE_ID --config CONFIG_FILE
freqtrade forceexit all --config CONFIG_FILE
```

### Download Fresh Data:
```bash
freqtrade download-data --config CONFIG_FILE --timerange 20251001-
```

---

**Remember:** 
- ⚠️ Start small ($500-1000)
- ⚠️ Never risk more than you can afford to lose
- ⚠️ Monitor daily when live
- ⚠️ Have an exit strategy

Good luck! 🚀
