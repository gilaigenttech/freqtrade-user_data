# 🚀 Freqtrade Dry Run & Google Cloud Deployment Guide

## Phase 1: Local Dry Run Testing (Start Here!)

### Step 1: Create Binance Testnet API Keys

**For Futures Trading:**
1. Go to https://testnet.binancefuture.com/
2. Login with GitHub or Google
3. Click "API Key" in top right
4. Create new API key
5. Save the Key and Secret securely

**Important:** Binance Futures Testnet is separate from regular Binance Testnet!

### Step 2: Configure Dry Run

Edit `config_dryrun_futures.json`:

```bash
cd /home/gil/freqtrade/user_data
nano config_dryrun_futures.json
```

Update these fields:
```json
{
  "exchange": {
    "name": "binance",
    "key": "YOUR_TESTNET_API_KEY",
    "secret": "YOUR_TESTNET_API_SECRET",
    "urls": {
      "api": "https://testnet.binancefuture.com"
    }
  }
}
```

### Step 3: Download Required Data

```bash
cd /home/gil/freqtrade

# Download recent data for your pairs (last 7 days)
./venv/bin/freqtrade download-data \
  --config /home/gil/freqtrade/user_data/config_dryrun_futures.json \
  --timerange 20251001- \
  --timeframe 5m 1h 4h 1d

# This will download BTC, ETH, SOL, BNB data
```

### Step 4: Start Dry Run

```bash
cd /home/gil/freqtrade

# Start dry run in foreground (for testing)
./venv/bin/freqtrade trade \
  --config /home/gil/freqtrade/user_data/config_dryrun_futures.json \
  --strategy NostalgiaForInfinityX6

# Or run in background with screen/tmux
screen -S freqtrade
./venv/bin/freqtrade trade \
  --config /home/gil/freqtrade/user_data/config_dryrun_futures.json \
  --strategy NostalgiaForInfinityX6
# Press Ctrl+A then D to detach
# screen -r freqtrade to reattach
```

### Step 5: Monitor Dry Run

```bash
# View logs
tail -f /home/gil/freqtrade/user_data/logs/freqtrade.log

# Check status via FreqUI (if enabled)
# Open browser: http://localhost:8080

# Check trades
./venv/bin/freqtrade show-trades --config /home/gil/freqtrade/user_data/config_dryrun_futures.json
```

### What to Monitor During Dry Run:

✅ **First 24 Hours:**
- Strategy loads without errors
- Pairs are being analyzed
- Entry signals generate
- Position sizing correct
- Leverage applied properly (3x)

✅ **First Week:**
- Short entries triggering (should see tag 603 initially)
- Exit signals working
- Grinding/DCA behavior reasonable
- No excessive position accumulation
- Profit/loss tracking accurate

✅ **Red Flags:**
- ❌ Too many simultaneous positions (>6)
- ❌ Rapid DCA entries (too aggressive)
- ❌ Positions held too long (>30 days)
- ❌ Large drawdowns (>20%)
- ❌ Strategy errors in logs

---

## Phase 2: Google Cloud VM Setup

### Option A: Small Instance (Budget-Friendly)

**Recommended Specs:**
- **Machine Type:** e2-small (2 vCPU, 2 GB RAM)
- **OS:** Ubuntu 22.04 LTS
- **Disk:** 20 GB SSD
- **Cost:** ~$15-20/month

**Good for:** 
- Running 1-2 strategies
- Up to 10 pairs
- 5m-1h timeframes

### Option B: Medium Instance (Recommended)

**Recommended Specs:**
- **Machine Type:** e2-medium (2 vCPU, 4 GB RAM)
- **OS:** Ubuntu 22.04 LTS
- **Disk:** 30 GB SSD
- **Cost:** ~$30-35/month

**Good for:**
- Running 2-4 strategies
- Up to 20 pairs
- Multiple timeframes
- FreqUI enabled

### Option C: Preemptible/Spot Instance (Advanced)

**Specs:**
- **Machine Type:** e2-medium (Spot)
- **Cost:** ~$8-12/month (70% cheaper!)
- **Risk:** Can be terminated anytime (need auto-restart)

---

## Phase 3: Google Cloud Setup Steps

### Step 1: Create VM Instance

```bash
# Using gcloud CLI (install from cloud.google.com/sdk)
gcloud compute instances create freqtrade-bot \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB \
  --boot-disk-type=pd-ssd \
  --tags=http-server,https-server

# Or use Google Cloud Console web interface:
# 1. Go to console.cloud.google.com
# 2. Compute Engine > VM Instances
# 3. Click "Create Instance"
# 4. Configure as above
```

### Step 2: Firewall Rules (Optional - for FreqUI access)

```bash
# Allow FreqUI access on port 8081
gcloud compute firewall-rules create freqtrade-ui \
  --allow tcp:8081 \
  --source-ranges 0.0.0.0/0 \
  --target-tags http-server

# IMPORTANT: Use IP whitelist for security:
gcloud compute firewall-rules update freqtrade-ui \
  --source-ranges YOUR_HOME_IP/32
```

### Step 3: Connect to VM

```bash
# SSH into VM
gcloud compute ssh freqtrade-bot --zone=us-central1-a

# Or use Cloud Console SSH button
```

### Step 4: Install Freqtrade on GCP VM

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv git build-essential

# Clone your repo or fresh install
cd ~
git clone https://github.com/freqtrade/freqtrade.git
cd freqtrade

# Install Freqtrade
./setup.sh -i

# Or clone your existing config
# git clone YOUR_FREQTRADE_CONFIG_REPO user_data
```

### Step 5: Transfer Your Configuration

**Option A: Git Repository (Recommended)**

```bash
# On your local machine, create a private repo
cd /home/gil/freqtrade/user_data
git init
git add config_dryrun_futures.json strategies/
git commit -m "Initial config"
gh repo create freqtrade-config --private
git push

# On GCP VM
cd ~/freqtrade
rm -rf user_data
git clone https://github.com/YOUR_USERNAME/freqtrade-config.git user_data
```

**Option B: SCP Transfer**

```bash
# From your local machine
gcloud compute scp --recurse \
  /home/gil/freqtrade/user_data \
  freqtrade-bot:~/freqtrade/ \
  --zone=us-central1-a
```

### Step 6: Setup Systemd Service (Auto-Start)

Create service file on GCP VM:

```bash
sudo nano /etc/systemd/system/freqtrade.service
```

Content:
```ini
[Unit]
Description=Freqtrade Trading Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/freqtrade
ExecStart=/home/YOUR_USERNAME/freqtrade/venv/bin/freqtrade trade \
  --config /home/YOUR_USERNAME/freqtrade/user_data/config_dryrun_futures.json \
  --strategy NostalgiaForInfinityX6 \
  --logfile /home/YOUR_USERNAME/freqtrade/user_data/logs/freqtrade.log
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable freqtrade
sudo systemctl start freqtrade

# Check status
sudo systemctl status freqtrade

# View logs
journalctl -u freqtrade -f
```

---

## Phase 4: Monitoring & Alerts

### Setup Telegram Bot (Highly Recommended!)

**Benefits:**
- 📱 Real-time trade notifications on your phone
- 🎯 Remote control from anywhere
- 💰 Instant profit/loss updates
- ⚠️ Error alerts

**Quick Setup (5 minutes):**

1. **Create Telegram Bot:**
   ```
   1. Open Telegram app
   2. Message @BotFather
   3. Send: /newbot
   4. Choose name: "My Freqtrade Bot"
   5. Choose username: my_freqtrade_bot
   6. Save the token: 1234567890:ABCdef...
   ```

2. **Get Chat ID:**
   ```
   1. Message @userinfobot on Telegram
   2. It will reply with: Id: 123456789
   3. Save that number as your chat_id
   ```

3. **Update config:**
   ```json
   "telegram": {
     "enabled": true,
     "token": "YOUR_BOT_TOKEN_FROM_BOTFATHER",
     "chat_id": "YOUR_CHAT_ID_FROM_USERINFOBOT"
   }
   ```

4. **Restart bot and test:**
   ```bash
   # Restart bot
   sudo systemctl restart freqtrade
   
   # Send command to your bot in Telegram:
   /status
   
   # Bot should reply with current trades!
   ```

**📱 Full Telegram Setup Guide:** 
```bash
cat /home/YOUR_USERNAME/freqtrade/user_data/TELEGRAM_SETUP.md
```

**Useful Commands:**
- `/status` - Show open trades
- `/profit` - Show profit summary  
- `/balance` - Show account balance
- `/daily` - Daily profit report
- `/forceexit <id>` - Close a trade remotely
- `/help` - Show all available commands

**This is essential for monitoring your bot remotely!** 📱🚀

---

### FreqUI Setup (Web Interface)

1. **Update config:**
   ```json
   "api_server": {
     "enabled": true,
     "listen_ip_address": "0.0.0.0",
     "listen_port": 8081,
     "jwt_secret_key": "RANDOM_SECURE_STRING",
     "username": "admin",
     "password": "SECURE_PASSWORD"
   }
   ```

2. **Access FreqUI:**
   ```
   http://YOUR_GCP_VM_EXTERNAL_IP:8081
   ```

### Setup Alerts

Create monitoring script:

```bash
nano ~/check_freqtrade.sh
```

```bash
#!/bin/bash
if ! systemctl is-active --quiet freqtrade; then
  echo "Freqtrade is down! Restarting..." | mail -s "Alert" your@email.com
  sudo systemctl restart freqtrade
fi
```

Add to crontab:
```bash
crontab -e
# Add: */5 * * * * /home/YOUR_USERNAME/check_freqtrade.sh
```

---

## Phase 5: Going Live Checklist

### Before Switching to Live Trading:

✅ **1. Dry Run Success (2+ weeks)**
- [ ] Strategy profitable in dry run
- [ ] No critical errors
- [ ] Behavior as expected
- [ ] Comfortable with risk

✅ **2. Risk Management**
- [ ] Set `stake_amount` to fixed amount (e.g., 100 USDT)
- [ ] Set `max_open_trades` to 3-4 initially
- [ ] Enable `stoploss_on_exchange: true`
- [ ] Set `tradable_balance_ratio: 0.5` (only use 50%)

✅ **3. API Security**
- [ ] Create LIVE Binance API keys
- [ ] Enable IP whitelist on Binance
- [ ] Restrict to trading only (no withdrawals)
- [ ] Use API key with futures trading permission

✅ **4. Live Config Changes**

```json
{
  "dry_run": false,  // CHANGE THIS!
  "stake_amount": 100,  // Fixed amount
  "max_open_trades": 4,  // Conservative
  "tradable_balance_ratio": 0.5,  // Use 50% of balance
  "exchange": {
    "key": "LIVE_API_KEY",
    "secret": "LIVE_API_SECRET"
  }
}
```

✅ **5. Start Small**
- Begin with $500-1000 capital
- Monitor daily for first week
- Gradually increase if successful

---

## Quick Start Commands Summary

### Local Dry Run:
```bash
cd /home/gil/freqtrade

# Start dry run
./venv/bin/freqtrade trade \
  --config user_data/config_dryrun_futures.json \
  --strategy NostalgiaForInfinityX6
```

### GCP Deployment:
```bash
# Create VM
gcloud compute instances create freqtrade-bot --zone=us-central1-a --machine-type=e2-medium

# SSH
gcloud compute ssh freqtrade-bot

# Install & run
cd ~/freqtrade
./venv/bin/freqtrade trade --config user_data/config_live.json --strategy NostalgiaForInfinityX6
```

---

## Cost Estimation

| Component | Cost/Month |
|-----------|------------|
| GCP e2-medium VM | $30 |
| Network egress | $2-5 |
| **Total** | **~$35/month** |

**Savings Tips:**
- Use Spot/Preemptible instances (-70%)
- Use e2-small if running 1 strategy (-50%)
- Use GCP free tier ($300 credit first 90 days)

---

## Support & Resources

- **Freqtrade Docs:** https://www.freqtrade.io
- **Discord:** https://discord.gg/freqtrade
- **GitHub:** https://github.com/freqtrade/freqtrade
- **GCP Docs:** https://cloud.google.com/compute/docs

---

**IMPORTANT SAFETY NOTES:**

⚠️ **Never commit API keys to Git**
⚠️ **Always start with small amounts**
⚠️ **Enable 2FA on exchange**
⚠️ **Whitelist GCP VM IP on Binance**
⚠️ **Monitor daily when live**
⚠️ **Have stop-loss always enabled**

---

Good luck! Start with local dry run for 2 weeks before deploying to GCP! 🚀
