#!/bin/bash
# Freqtrade Dry Run Startup Script
# Usage: ./start_dryrun.sh

set -e

FREQTRADE_DIR="/home/gil/freqtrade"
CONFIG_FILE="$FREQTRADE_DIR/user_data/config_dryrun_futures.json"
STRATEGY="NostalgiaForInfinityX6"

echo "🤖 Starting Freqtrade Dry Run..."
echo "📁 Working directory: $FREQTRADE_DIR"
echo "⚙️  Config: $CONFIG_FILE"
echo "📊 Strategy: $STRATEGY"
echo ""

# Check if config exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Error: Config file not found: $CONFIG_FILE"
    echo "Please edit config_dryrun_futures.json and add your API keys"
    exit 1
fi

# Check if running already
if pgrep -f "freqtrade trade" > /dev/null; then
    echo "⚠️  Freqtrade is already running!"
    echo "Process ID: $(pgrep -f 'freqtrade trade')"
    echo ""
    echo "To stop it, run: pkill -f 'freqtrade trade'"
    exit 1
fi

cd "$FREQTRADE_DIR"

# Start in screen session
if command -v screen &> /dev/null; then
    echo "🚀 Starting Freqtrade in DRY RUN mode..."
echo ""

# Start freqtrade in screen session
cd /home/gil/freqtrade
screen -dmS freqtrade ./venv/bin/freqtrade trade \
  --config user_data/config_dryrun_futures.json \
  --strategy NostalgiaForInfinityX6

sleep 2
    
    echo "✅ Freqtrade started successfully!"
    echo ""
    echo "📺 To view: screen -r freqtrade"
    echo "📋 To detach: Press Ctrl+A then D"
    echo "📜 View logs: tail -f user_data/logs/freqtrade.log"
    echo "🛑 To stop: screen -S freqtrade -X quit"
    
else
    echo "⚠️  'screen' not found. Starting in foreground..."
    echo "Press Ctrl+C to stop"
    echo ""
    ./venv/bin/freqtrade trade \
        --config "$CONFIG_FILE" \
        --strategy "$STRATEGY"
fi
