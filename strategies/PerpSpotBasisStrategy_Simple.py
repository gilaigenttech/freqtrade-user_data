#!/usr/bin/env python3
"""
Simplified debug version without futures dependency
"""
import pandas as pd
from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import DecimalParameter
from pandas import DataFrame
import talib.abstract as ta
import numpy as np

class PerpSpotBasisStrategy_Simple(IStrategy):
    timeframe = "5m"
    can_short = False
    startup_candle_count = 200

    use_exit_signal = False

    minimal_roi = {
        "0": 0.10,    # Lower ROI for easier testing
        "60": 0.05,
        "120": 0.02,
        "240": 0
    }
    stoploss = -0.02  # Using config stoploss

    process_only_new_candles = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata['pair']
        print(f"Processing {pair} - Shape: {dataframe.shape}")

        # Basic technical indicators
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema_20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        
        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']

        # Volume indicators
        dataframe['volume_ma_20'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma_20']

        # Print some stats
        print(f"RSI range: {dataframe['rsi'].min():.1f} - {dataframe['rsi'].max():.1f}")
        print(f"EMA20 vs EMA50 crossovers: {(dataframe['ema_20'] > dataframe['ema_50']).sum()}")
        
        # Check for FreqAI columns
        freqai_cols = [col for col in dataframe.columns if col.startswith('&-')]
        if freqai_cols:
            print(f"FreqAI columns: {freqai_cols}")
            if '&-enter_long' in dataframe.columns:
                signal_range = dataframe['&-enter_long'].dropna()
                if len(signal_range) > 0:
                    print(f"FreqAI signal range: {signal_range.min():.3f} - {signal_range.max():.3f}")
                    print(f"Recent signals: {signal_range.tail(5).tolist()}")
                else:
                    print("FreqAI column exists but contains only NaN values")
        else:
            print("No FreqAI columns found")

        return dataframe

    freqai_prediction_threshold = DecimalParameter(0.5, 0.9, default=0.6, space='buy', optimize=True, load=True)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata['pair']
        print(f"\n=== ENTRY LOGIC for {pair} ===")
        
        # Initialize entry column
        dataframe.loc[:, 'enter_long'] = 0
        
        # Method 1: FreqAI signal (if available)
        freqai_entries = 0
        if '&-enter_long' in dataframe.columns:
            freqai_signal = dataframe['&-enter_long']
            threshold = self.freqai_prediction_threshold.value
            freqai_condition = freqai_signal > threshold
            
            # Count and apply FreqAI entries
            freqai_entries = freqai_condition.sum()
            if freqai_entries > 0:
                dataframe.loc[freqai_condition, 'enter_long'] = 1
                print(f"FreqAI entries: {freqai_entries} (threshold: {threshold})")
        
        # Method 2: Fallback technical analysis
        if freqai_entries == 0:
            print("Using fallback technical analysis...")
            
            # Conditions for entry
            oversold = dataframe['rsi'] < 35
            uptrend = dataframe['ema_20'] > dataframe['ema_50']
            macd_positive = dataframe['macd'] > dataframe['macdsignal']
            volume_surge = dataframe['volume_ratio'] > 1.2
            
            # Combine conditions (at least 2 of 4 must be true)
            condition_count = oversold.astype(int) + uptrend.astype(int) + macd_positive.astype(int) + volume_surge.astype(int)
            entry_condition = condition_count >= 2
            
            technical_entries = entry_condition.sum()
            if technical_entries > 0:
                dataframe.loc[entry_condition, 'enter_long'] = 1
                print(f"Technical analysis entries: {technical_entries}")
                
                # Show condition breakdown for the last few signals
                recent_entries = dataframe[entry_condition].tail(3)
                for idx in recent_entries.index:
                    print(f"  Entry at {dataframe.loc[idx, 'date']}: RSI={dataframe.loc[idx, 'rsi']:.1f}, "
                          f"EMA_cross={dataframe.loc[idx, 'ema_20'] > dataframe.loc[idx, 'ema_50']}, "
                          f"MACD_pos={dataframe.loc[idx, 'macd'] > dataframe.loc[idx, 'macdsignal']}, "
                          f"Vol_ratio={dataframe.loc[idx, 'volume_ratio']:.2f}")
        
        total_entries = dataframe['enter_long'].sum()
        print(f"Total entry signals: {total_entries}")
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        
        # Simple overbought exit
        overbought = dataframe['rsi'] > 70
        dataframe.loc[overbought, 'exit_long'] = 1
        
        return dataframe

    # Simplified FreqAI config - removed basis features that require futures data
    freqai_info = {
        "identifier": "SKLearnRandomForestClassifier",
        "features": [
            "rsi",
            "ema_20", 
            "ema_50",
            "adx",
            "macd",
            "macdsignal", 
            "macdhist",
            "volume_ratio",
        ],
        "label_period_candles": 12,
        "data_split_parameters": {"split_train": 0.8, "split_test": 0.2},
        "model_training_parameters": {
            "n_estimators": 50,
            "max_depth": 6,
            "random_state": 42
        }
    }