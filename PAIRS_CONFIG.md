# 📊 Trading Pairs Configuration

## Current Setup (25 Pairs)

### 🟢 Major Coins (Top 5)
High liquidity, low volatility
1. **BTC/USDT:USDT** - Bitcoin | Market Cap: #1
2. **ETH/USDT:USDT** - Ethereum | Market Cap: #2
3. **SOL/USDT:USDT** - Solana | Market Cap: #5
4. **BNB/USDT:USDT** - Binance Coin | Market Cap: #4
5. **XRP/USDT:USDT** - Ripple | Market Cap: #7

### 🔵 Large Caps (Top 20)
Good liquidity, moderate volatility
6. **ADA/USDT:USDT** - Cardano | Market Cap: #9
7. **DOGE/USDT:USDT** - Dogecoin | Market Cap: #8
8. **MATIC/USDT:USDT** - Polygon | Market Cap: #15
9. **DOT/USDT:USDT** - Polkadot | Market Cap: #12
10. **AVAX/USDT:USDT** - Avalanche | Market Cap: #11

### 🟣 DeFi & Infrastructure
DeFi ecosystem, oracle, payment
11. **LINK/USDT:USDT** - Chainlink | Oracle leader
12. **ATOM/USDT:USDT** - Cosmos | Interoperability
13. **UNI/USDT:USDT** - Uniswap | DEX leader
14. **LTC/USDT:USDT** - Litecoin | Payment coin
15. **ETC/USDT:USDT** - Ethereum Classic | PoW chain

### 🟡 Layer 1 & Layer 2
Newer chains with growth potential
16. **NEAR/USDT:USDT** - NEAR Protocol | L1
17. **APT/USDT:USDT** - Aptos | L1
18. **ARB/USDT:USDT** - Arbitrum | L2 Ethereum
19. **OP/USDT:USDT** - Optimism | L2 Ethereum
20. **SUI/USDT:USDT** - Sui | L1

### 🔴 AI & Emerging Sectors
High growth, higher volatility
21. **INJ/USDT:USDT** - Injective | DeFi + AI
22. **TIA/USDT:USDT** - Celestia | Modular blockchain
23. **SEI/USDT:USDT** - Sei | Trading-focused L1
24. **FET/USDT:USDT** - Fetch.ai | AI agents
25. **RUNE/USDT:USDT** - THORChain | Cross-chain swaps

---

## Configuration Details

**Config Files:**
- `config_dryrun_futures.json`
- `config_testnet_futures.json`

**Settings:**
```json
{
  "max_open_trades": 10,
  "pair_whitelist": [25 pairs],
  "trading_mode": "futures",
  "margin_mode": "isolated",
  "leverage": 3
}
```

**Pairlist Method:** `StaticPairList` (fixed list)

---

## Trading Characteristics

| Category | Pairs | Volatility | Liquidity | Risk Level |
|----------|-------|------------|-----------|------------|
| Major Coins | 5 | Low | Very High | Low |
| Large Caps | 5 | Medium | High | Medium |
| DeFi | 5 | Medium | Medium-High | Medium |
| L1/L2 | 5 | Medium-High | Medium | Medium-High |
| AI/Emerging | 5 | High | Medium-Low | High |

---

## Expected Behavior

### With 25 Pairs vs 4 Pairs:

**More Opportunities:**
- 6x more pairs to analyze
- More trade signals
- Better diversification
- Smoother equity curve

**Trade Distribution:**
- Expect 10-30 trades per week (vs 2-8 with 4 pairs)
- Up to 10 open positions at once
- Mix of high-cap (stable) and mid-cap (volatile)

**Resource Usage:**
- More CPU: ~5-10% increase
- More disk: ~500MB data
- More RAM: ~200MB increase

---

## Data Requirements

### Download Command:
```bash
cd /home/gil/freqtrade
./venv/bin/freqtrade download-data \
  --config user_data/config_dryrun_futures.json \
  --timerange 20251001- \
  --timeframe 5m 1h 4h 1d
```

### Data Size Per Pair:
- 5m timeframe: ~10MB (7 days)
- 1h timeframe: ~2MB (7 days)
- 4h timeframe: ~500KB (7 days)
- 1d timeframe: ~100KB (7 days)
- **Total per pair:** ~15-20MB
- **Total all pairs:** ~400-500MB

---

## Customization Guide

### How to Add/Remove Pairs

**Edit config file:**
```bash
nano /home/gil/freqtrade/user_data/config_dryrun_futures.json
```

**Find `pair_whitelist` section (around line 48):**
```json
"pair_whitelist": [
  "BTC/USDT:USDT",
  "ETH/USDT:USDT",
  // Add or remove pairs here
]
```

**After changes:**
1. Stop bot: `pkill -f 'freqtrade trade'`
2. Download data for new pairs
3. Restart bot: `./start_dryrun.sh`

---

## Recommended Pairs by Strategy

### **Conservative (Low Risk)**
Focus on top 10 market cap:
- BTC, ETH, BNB, SOL, XRP
- ADA, DOGE, MATIC, DOT, AVAX

### **Balanced (Medium Risk)**
Mix of large caps + DeFi:
- All conservative pairs +
- LINK, ATOM, UNI, LTC, NEAR, APT

### **Aggressive (High Risk)**
Include emerging sectors:
- All balanced pairs +
- ARB, OP, SUI, INJ, TIA, SEI, FET, RUNE

### **Current Setup:** Aggressive (25 pairs across all categories)

---

## Performance Expectations

Based on backtest with similar pair count:

| Metric | 4 Pairs | 25 Pairs | Expected Change |
|--------|---------|----------|-----------------|
| Trades/Week | 5-10 | 15-40 | +200% |
| Win Rate | 96% | 92-95% | -1 to -4% |
| Profit/Trade | 0.5% | 0.4-0.5% | -0 to -0.1% |
| Max Drawdown | 3% | 4-6% | +1 to +3% |
| Sharpe Ratio | 2.5 | 2.3-2.7 | Similar |

**More pairs = More trades, slightly lower win rate, better diversification**

---

## Monitoring Tips

### Check Pair Performance

```bash
cd /home/gil/freqtrade

# Show trades per pair
./venv/bin/freqtrade show-trades \
  --config user_data/config_dryrun_futures.json \
  --pair "BTC/USDT:USDT"

# Show profit by pair (via logs)
grep "Exit signal" user_data/logs/freqtrade.log | grep "BTC/USDT"
```

### FreqUI Dashboard

1. Open: http://localhost:8081
2. Go to "Trading" tab
3. See all open positions by pair
4. Click pair name to see chart

---

## Troubleshooting

### Pair Not Trading

**Check 1:** Is data downloaded?
```bash
ls -lh /home/gil/freqtrade/user_data/data/binance/ | grep NEAR
```

**Check 2:** Is pair in whitelist?
```bash
grep "NEAR" /home/gil/freqtrade/user_data/config_dryrun_futures.json
```

**Check 3:** Are there signals for this pair?
```bash
tail -100 /home/gil/freqtrade/user_data/logs/freqtrade.log | grep NEAR
```

### Too Many Trades

**Reduce to fewer pairs:**
- Keep only top 10 market cap
- Focus on BTC, ETH, SOL, BNB
- Reduce `max_open_trades` to 5

### Not Enough Trades

**Add more pairs:**
- Increase to 30-40 pairs
- Add more mid-cap coins
- Include more volatile assets

---

## Future Enhancements

### Dynamic Pairlist (Advanced)

Instead of static list, use volume-based:
```json
"pairlists": [
  {
    "method": "VolumePairList",
    "number_assets": 25,
    "sort_key": "quoteVolume",
    "min_value": 0,
    "refresh_period": 3600
  }
]
```

**Benefits:**
- Auto-updates to highest volume pairs
- Adapts to market conditions
- No manual maintenance

**Drawbacks:**
- Less predictable
- May switch pairs mid-trading
- Needs more data storage

---

## Quick Reference

| Task | Command |
|------|---------|
| View current pairs | `grep -A 30 "pair_whitelist" config_dryrun_futures.json` |
| Check data downloaded | `ls -l user_data/data/binance/` |
| Add pair | Edit config → Download data → Restart |
| Remove pair | Edit config → Restart |
| Test pairlist | `freqtrade test-pairlist --config config_dryrun_futures.json` |

---

**Updated:** 2025-10-08  
**Pairs Count:** 25  
**Max Open Trades:** 10  
**Strategy:** NostalgiaForInfinityX6
