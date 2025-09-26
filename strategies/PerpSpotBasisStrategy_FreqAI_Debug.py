#!/usr/bin/env python3
"""
FreqAI Debug strategy - debugging FreqAI signal generation
"""
import pandas as pd
from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import IntParameter, DecimalParameter
from pandas import DataFrame
import talib.abstract as ta
import numpy as np
import os

class PerpSpotBasisStrategy_FreqAI_Debug(IStrategy):
    timeframe = "5m"
    can_short = False
    startup_candle_count = 200

    # Disable FreqAI exit signals
    use_exit_signal = False

    # ROI and stoploss - use more conservative stoploss
    minimal_roi = {
        "0": 0.217,
        "31": 0.058,
        "65": 0.04,
        "142": 0
    }
    stoploss = -0.05  # Less aggressive stoploss

    # Process only new candles
    process_only_new_candles = True

    freqai_label_period = 12
    freqai_min_return = 0.003

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata['pair']
        print(f"\n=== DEBUG: Populating indicators for {pair} ===")
        print(f"Dataframe shape: {dataframe.shape}")
        print(f"Dataframe columns: {list(dataframe.columns)}")

        # Load futures data for basis calculations
        futures_data = self.load_futures_data(pair)
        if futures_data is not None:
            print(f"Futures data loaded successfully. Shape: {futures_data.shape}")
            dataframe = self.merge_futures_data(dataframe, futures_data)
            dataframe = self.calculate_basis_features(dataframe)
        else:
            print("No futures data loaded - proceeding without basis features")

        # Technical indicators
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema_20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        macd = ta.MACD(dataframe)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"] = macd["macdhist"]

        # Volume features
        dataframe = self.calculate_volume_features(dataframe)

        # FreqAI-specific feature engineering (prefix with %-)
        dataframe["%-basis_zscore"] = dataframe.get("basis_zscore", 0).fillna(0).clip(-5, 5)
        dataframe["%-basis_ma_ratio"] = (
            dataframe.get("basis_ma_10", 0) / dataframe.get("basis_ma_30", 1)
        ).replace([np.inf, -np.inf], 0).fillna(0).clip(-5, 5)
        dataframe["%-basis_roc"] = dataframe.get("basis_roc", 0).fillna(0).clip(-5, 5)
        dataframe["%-volume_ratio_ma"] = dataframe.get("volume_ratio_ma", 0).replace([np.inf, -np.inf], 0).fillna(0).clip(0, 5)
        dataframe["%-rsi"] = dataframe["rsi"].fillna(50) / 100.0
        dataframe["%-adx"] = dataframe["adx"].fillna(20) / 100.0
        dataframe["%-ema_ratio"] = (
            dataframe["ema_20"].ffill().bfill() /
            dataframe["ema_50"].replace(0, np.nan).ffill().bfill()
        ).replace([np.inf, -np.inf], 1).clip(0.5, 1.5)
        dataframe["%-macd_norm"] = (dataframe["macd"].fillna(0) / dataframe["close"].replace(0, np.nan)).replace([np.inf, -np.inf], 0).fillna(0)
        dataframe["%-macdsignal_norm"] = (dataframe["macdsignal"].fillna(0) / dataframe["close"].replace(0, np.nan)).replace([np.inf, -np.inf], 0).fillna(0)
        dataframe["%-momentum"] = dataframe["close"].pct_change(periods=3).fillna(0)

        freqai_feature_columns = [col for col in dataframe.columns if col.startswith("%-")]
        print(f"FreqAI feature columns: {freqai_feature_columns}")

        # Trigger FreqAI pipeline (adds &- predictions)
        dataframe = self.freqai.start(dataframe, metadata, self)

        print(f"Final dataframe columns: {list(dataframe.columns)}")
        print(f"Final dataframe shape: {dataframe.shape}")
        
        # Check for FreqAI columns
        freqai_columns = [col for col in dataframe.columns if col.startswith('&-')]
        print(f"FreqAI columns detected: {freqai_columns}")

        return dataframe

    def load_futures_data(self, pair: str) -> pd.DataFrame:
        """Load futures data with multiple fallback paths"""
        pair_formatted = pair.replace('/', '_')
        
        possible_paths = [
            f"/home/gil/freqtrade/user_data/data/binance/futures/{pair_formatted}-5m-futures.feather",
            f"/home/gil/freqtrade/user_data/data/binance/{pair_formatted}-5m-futures.feather",
            f"user_data/data/binance/futures/{pair_formatted}-5m-futures.feather",
            f"user_data/data/binance/{pair_formatted}-5m-futures.feather",
        ]
        
        for futures_path in possible_paths:
            if os.path.exists(futures_path):
                try:
                    print(f"Loading futures data from: {futures_path}")
                    futures_data = pd.read_feather(futures_path)
                    print(f"Futures data loaded: {len(futures_data)} rows")
                    return futures_data
                except Exception as e:
                    print(f"Error loading from {futures_path}: {e}")
                    continue
        
        print(f"No futures data found for {pair}")
        return None

    def merge_futures_data(self, spot_df: pd.DataFrame, futures_df: pd.DataFrame) -> pd.DataFrame:
        """Merge spot and futures data on timestamp"""
        try:
            # Ensure both dataframes have datetime index
            if not isinstance(spot_df.index, pd.DatetimeIndex):
                spot_df.index = pd.to_datetime(spot_df.index)
            if not isinstance(futures_df.index, pd.DatetimeIndex):
                futures_df.index = pd.to_datetime(futures_df.index)

            # Rename futures columns to avoid conflicts
            futures_columns = ['open_perp', 'high_perp', 'low_perp', 'close_perp', 'volume_perp']
            futures_df_renamed = futures_df[['open', 'high', 'low', 'close', 'volume']].copy()
            futures_df_renamed.columns = futures_columns

            # Merge on index (timestamp)
            merged_df = spot_df.join(futures_df_renamed, how='left')
            print(f"Merged dataframe shape: {merged_df.shape}")

            return merged_df
        except Exception as e:
            print(f"Error merging futures data: {e}")
            return spot_df

    def calculate_basis_features(self, dataframe):
        """Calculate perpetual-spot basis features"""
        try:
            if 'close_perp' not in dataframe.columns:
                print("No perpetual data available for basis calculation")
                return dataframe

            # Basic basis calculation
            dataframe['basis'] = (dataframe['close_perp'] - dataframe['close']) / dataframe['close']

            # Remove infinite or NaN values
            dataframe['basis'] = dataframe['basis'].replace([np.inf, -np.inf], np.nan)

            # Fill NaN with forward fill, then backward fill
            dataframe['basis'] = dataframe['basis'].ffill().bfill()

            # Basis moving averages
            dataframe['basis_ma_10'] = ta.SMA(dataframe['basis'], timeperiod=10)
            dataframe['basis_ma_30'] = ta.SMA(dataframe['basis'], timeperiod=30)

            # Basis rate of change
            dataframe['basis_roc'] = ta.ROC(dataframe['basis'], timeperiod=5)

            # Basis z-score (normalized basis)
            basis_mean = dataframe['basis'].rolling(window=100).mean()
            basis_std = dataframe['basis'].rolling(window=100).std()
            dataframe['basis_zscore'] = (dataframe['basis'] - basis_mean) / basis_std

            # Fill any remaining NaN values
            dataframe['basis_zscore'] = dataframe['basis_zscore'].fillna(0)

            print(f"Basis calculation completed")
            non_nan_basis = dataframe['basis'].dropna()
            if len(non_nan_basis) > 0:
                print(f"Basis stats - Mean: {non_nan_basis.mean():.6f}, Std: {non_nan_basis.std():.6f}")
                print(f"Basis Z-score range: {dataframe['basis_zscore'].min():.2f} to {dataframe['basis_zscore'].max():.2f}")

            return dataframe
        except Exception as e:
            print(f"Error calculating basis features: {e}")
            return dataframe

    def calculate_volume_features(self, dataframe):
        """Enhanced volume analysis features"""
        try:
            # Volume moving averages
            dataframe['volume_ma_10'] = ta.SMA(dataframe['volume'], timeperiod=10)
            dataframe['volume_ma_30'] = ta.SMA(dataframe['volume'], timeperiod=30)

            # Volume ratio (current vs moving average)
            dataframe['volume_ratio_ma'] = dataframe['volume'] / dataframe['volume_ma_30']

            # On-balance volume (OBV)
            dataframe['obv'] = ta.OBV(dataframe['close'], dataframe['volume'])

            # Volume weighted average price (VWAP)
            vwap_period = 20
            cumulative_price_volume = (dataframe['close'] * dataframe['volume']).rolling(vwap_period).sum()
            cumulative_volume = dataframe['volume'].rolling(vwap_period).sum()
            dataframe['vwap'] = cumulative_price_volume / cumulative_volume

            return dataframe
        except Exception as e:
            print(f"Error calculating volume features: {e}")
            return dataframe

    freqai_prediction_threshold = DecimalParameter(0.5, 0.9, default=0.75, space='buy', optimize=True, load=True)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        print(f"\n=== DEBUG: Populating entry trend for {metadata['pair']} ===")
        print(f"Dataframe shape: {dataframe.shape}")
        
        # Initialize all entry signals to 0
        dataframe.loc[:, 'enter_long'] = 0
        
        # Check FreqAI columns
        freqai_columns = [col for col in dataframe.columns if col.startswith('&-')]
        print(f"Available FreqAI columns: {freqai_columns}")
        
        # Check if FreqAI enter_long signal exists
        if '&-enter_long' in dataframe.columns:
            enter_long_col = dataframe['&-enter_long']
            print(f"FreqAI &-enter_long unique values: {enter_long_col.unique()}")

            proba_col = None
            for col in dataframe.columns:
                if not isinstance(col, str):
                    continue
                if col.lower().endswith('enter') and not col.startswith('&-'):
                    proba_col = col
                    break

            if proba_col:
                predictions = dataframe[proba_col].fillna(0)
                freqai_condition = predictions > self.freqai_prediction_threshold.value
                print(f"FreqAI probability column '{proba_col}' used, signals above threshold: {freqai_condition.sum()}")
                dataframe.loc[freqai_condition, 'enter_long'] = 1
            else:
                freqai_condition = enter_long_col.astype(str).str.lower() == 'enter'
                print(f"FreqAI class-based signals: {freqai_condition.sum()}")
                dataframe.loc[freqai_condition, 'enter_long'] = 1

            if dataframe['enter_long'].sum() == 0:
                print("  - No FreqAI signals above threshold, using fallback")
                oversold = dataframe['rsi'] < 40
                uptrend = dataframe['ema_20'] > dataframe['ema_50']

                fallback_condition = oversold & uptrend
                print(f"  - Fallback oversold signals: {oversold.sum()}")
                print(f"  - Fallback uptrend signals: {uptrend.sum()}")
                print(f"  - Combined fallback signals: {fallback_condition.sum()}")

                dataframe.loc[fallback_condition, 'enter_long'] = 1
        else:
            print("No &-enter_long column found! Using fallback conditions")
            # More permissive fallback when no FreqAI
            oversold = dataframe['rsi'] < 40
            uptrend = dataframe['ema_20'] > dataframe['ema_50']
            
            fallback_condition = oversold & uptrend
            print(f"Fallback signals: {fallback_condition.sum()}")
            dataframe.loc[fallback_condition, 'enter_long'] = 1
        
        total_signals = dataframe['enter_long'].sum()
        print(f"Total entry signals generated: {total_signals}")
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0

        # RSI overbought exit
        strong_overbought = dataframe['rsi'] > 75
        dataframe.loc[strong_overbought, 'exit_long'] = 1

        exit_signals = dataframe['exit_long'].sum()
        print(f"Total exit signals generated: {exit_signals}")

        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        future_return = dataframe["close"].shift(-self.freqai_label_period) / dataframe["close"] - 1
        dataframe["&-enter_long"] = np.where(
            future_return > self.freqai_min_return,
            "enter",
            "hold"
        )
        dataframe["&-enter_long"] = dataframe["&-enter_long"].fillna("hold")
        print(f"Set FreqAI targets for {metadata['pair']} with threshold {self.freqai_min_return}")
        return dataframe

    # FreqAI configuration - match config.json identifier
    freqai_info = {
        "identifier": "MyFreqAIModel",
        "features": [
            "%-basis_zscore",
            "%-basis_ma_ratio", 
            "%-basis_roc",
            "%-volume_ratio_ma",
            "%-rsi",
            "%-adx",
            "%-ema_ratio",
            "%-macd_norm",
            "%-macdsignal_norm",
            "%-momentum",
        ],
        "label_period_candles": freqai_label_period,
        "data_split_parameters": {"test_size": 0.2, "shuffle": False},
        "model_training_parameters": {
            "n_estimators": 50,
            "max_depth": 6,
            "min_samples_split": 10,
            "min_samples_leaf": 5,
            "random_state": 42,
            "n_jobs": -1
        }
    }