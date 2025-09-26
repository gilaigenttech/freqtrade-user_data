#!/usr/bin/env python3
"""
Simple FreqAI test strategy - minimal features to test FreqAI functionality
"""
import numpy as np
import pandas as pd
from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import DecimalParameter
from pandas import DataFrame
import talib.abstract as ta

class SimpleFreqAITest(IStrategy):
    timeframe = "5m"
    can_short = False
    startup_candle_count = 200

    # Disable FreqAI exit signals
    use_exit_signal = False

    # Simple ROI and stoploss
    minimal_roi = {
        "0": 0.1,
        "30": 0.05,
        "60": 0
    }
    stoploss = -0.05

    freqai_label_period = 12
    freqai_min_return = 0.002

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        print(f"\n=== SIMPLE TEST: Populating indicators for {metadata['pair']} ===")
        print(f"Dataframe shape: {dataframe.shape}")

        # Core indicators for fallback logic
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema_20"] = ta.EMA(dataframe, timeperiod=20)

        # Mirror indicators with FreqAI-compatible feature prefixes
        dataframe["%-rsi"] = dataframe["rsi"] / 100.0
        dataframe["%-ema_ratio"] = dataframe["ema_20"] / dataframe["close"]
        dataframe["%-momentum"] = dataframe["close"].pct_change(periods=3).fillna(0)

        print(f"Base columns after feature prep: {list(dataframe.columns)}")

        # Trigger FreqAI pipeline (adds &- predictions and auxiliary columns)
        dataframe = self.freqai.start(dataframe, metadata, self)

        freqai_columns = [col for col in dataframe.columns if col.startswith('&-')]
        print(f"FreqAI columns detected: {freqai_columns}")

        return dataframe

    freqai_prediction_threshold = DecimalParameter(0.5, 0.9, default=0.75, space='buy', optimize=True, load=True)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        print(f"\n=== SIMPLE TEST: Entry trend for {metadata['pair']} ===")
        dataframe.loc[:, 'enter_long'] = 0
        
        # Check FreqAI columns
        freqai_columns = [col for col in dataframe.columns if col.startswith('&-')]
        print(f"Available FreqAI columns: {freqai_columns}")
        
        if '&-enter_long' in dataframe.columns:
            enter_long_col = dataframe['&-enter_long']
            print(f"FreqAI prediction classes: {enter_long_col.unique()}")

            proba_col = None
            for col in dataframe.columns:
                if not isinstance(col, str):
                    continue
                lowered = col.lower()
                if lowered.endswith('enter'):
                    proba_col = col
                    break
            if proba_col is None:
                proba_candidates = [
                    col for col in dataframe.columns if isinstance(col, str) and not col.startswith('&')
                ]
                proba_col = proba_candidates[0] if proba_candidates else None

            if proba_col is not None:
                predictions = dataframe[proba_col]
                freqai_condition = predictions > self.freqai_prediction_threshold.value
                dataframe.loc[freqai_condition, 'enter_long'] = 1
                print(f"FreqAI probability column '{proba_col}' used, signals: {freqai_condition.sum()}")
            else:
                freqai_condition = enter_long_col.str.lower() == 'enter'
                dataframe.loc[freqai_condition, 'enter_long'] = 1
                print(f"FreqAI class-based signals: {freqai_condition.sum()}")
        else:
            print("No FreqAI column found - using simple fallback")
            # Simple fallback
            oversold = dataframe['rsi'] < 30
            dataframe.loc[oversold, 'enter_long'] = 1
            print(f"Fallback signals: {oversold.sum()}")
        
        total_signals = dataframe['enter_long'].sum()
        print(f"Total entry signals: {total_signals}")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        future_return = dataframe["close"].shift(-self.freqai_label_period) / dataframe["close"] - 1
        dataframe["&-enter_long"] = np.where(future_return > self.freqai_min_return, "enter", "hold")
        dataframe["&-enter_long"] = dataframe["&-enter_long"].fillna("hold")
        return dataframe

    freqai_info = {
    "identifier": "MyFreqAIModel",
        "features": [
            "%-rsi",
            "%-ema_ratio",
            "%-momentum",
        ],
        "label_period_candles": freqai_label_period,
        "model_training_parameters": {
            "n_estimators": 50,
            "max_depth": 6,
            "min_samples_split": 10,
            "min_samples_leaf": 5,
            "random_state": 42,
        },
    }