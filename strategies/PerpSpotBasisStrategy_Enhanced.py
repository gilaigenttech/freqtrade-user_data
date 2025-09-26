#!/usr/bin/env python3
"""
Enhanced Perpetual-Spot Basis Trading Strategy with FreqAI
Features:
- Advanced basis features with volatility and momentum
- Signal filtering and quality scoring
- Dynamic risk management
- Hyperopt-compatible parameters
"""
import pandas as pd
from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import IntParameter, DecimalParameter, CategoricalParameter
from pandas import DataFrame
import talib.abstract as ta
import numpy as np
import os
from typing import Optional

class PerpSpotBasisStrategy_Enhanced(IStrategy):
    timeframe = "5m"
    can_short = False
    startup_candle_count = 300  # Increased for better indicator stability

    # Disable FreqAI exit signals - we'll manage exits ourselves
    use_exit_signal = True

    # Conservative default ROI and stoploss
    minimal_roi = {
        "0": 0.15,
        "30": 0.08,
        "60": 0.04,
        "120": 0
    }
    stoploss = -0.08

    # Process only new candles
    process_only_new_candles = True

    # Hyperopt parameters
    freqai_prediction_threshold = DecimalParameter(0.5, 0.9, default=0.75, space='buy', optimize=True, load=True)
    signal_quality_threshold = DecimalParameter(0.3, 0.8, default=0.6, space='buy', optimize=True, load=True)
    basis_volatility_threshold = DecimalParameter(0.01, 0.1, default=0.05, space='buy', optimize=True, load=True)
    volume_confirmation_multiplier = DecimalParameter(1.2, 3.0, default=2.0, space='buy', optimize=True, load=True)
    rsi_oversold_threshold = IntParameter(20, 40, default=30, space='buy', optimize=True, load=True)
    rsi_overbought_threshold = IntParameter(60, 80, default=70, space='sell', optimize=True, load=True)
    
    # Risk management parameters
    max_drawdown_threshold = DecimalParameter(0.05, 0.15, default=0.1, space='buy', optimize=True, load=True)
    position_size_multiplier = DecimalParameter(0.5, 1.5, default=1.0, space='buy', optimize=True, load=True)

    # FreqAI configuration
    freqai_label_period = 12
    freqai_min_return = 0.003

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata['pair']
        
        # Load futures data for basis calculations
        futures_data = self.load_futures_data(pair)
        if futures_data is not None:
            dataframe = self.merge_futures_data(dataframe, futures_data)
            dataframe = self.calculate_enhanced_basis_features(dataframe)
        
        # Enhanced technical indicators
        dataframe = self.calculate_enhanced_technical_indicators(dataframe)
        
        # Market structure features
        dataframe = self.calculate_market_structure_features(dataframe)
        
        # Volume analysis
        dataframe = self.calculate_enhanced_volume_features(dataframe)
        
        # Signal quality scoring
        dataframe = self.calculate_signal_quality_score(dataframe)
        
        # Risk metrics
        dataframe = self.calculate_risk_metrics(dataframe)

        # FreqAI feature engineering (prefix with %-)
        dataframe = self.prepare_freqai_features(dataframe)

        # Trigger FreqAI pipeline
        dataframe = self.freqai.start(dataframe, metadata, self)

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
                    futures_data = pd.read_feather(futures_path)
                    return futures_data
                except Exception as e:
                    continue
        
        return None

    def merge_futures_data(self, spot_df: pd.DataFrame, futures_df: pd.DataFrame) -> pd.DataFrame:
        """Merge spot and futures data on timestamp"""
        try:
            if not isinstance(spot_df.index, pd.DatetimeIndex):
                spot_df.index = pd.to_datetime(spot_df.index)
            if not isinstance(futures_df.index, pd.DatetimeIndex):
                futures_df.index = pd.to_datetime(futures_df.index)

            futures_columns = ['open_perp', 'high_perp', 'low_perp', 'close_perp', 'volume_perp']
            futures_df_renamed = futures_df[['open', 'high', 'low', 'close', 'volume']].copy()
            futures_df_renamed.columns = futures_columns

            merged_df = spot_df.join(futures_df_renamed, how='left')
            return merged_df
        except Exception as e:
            return spot_df

    def calculate_enhanced_basis_features(self, dataframe):
        """Enhanced basis features with volatility and momentum"""
        if 'close_perp' not in dataframe.columns:
            # Create dummy basis features if no futures data
            dataframe['basis'] = 0
            dataframe['basis_ma_10'] = 0
            dataframe['basis_ma_30'] = 0
            dataframe['basis_volatility'] = 0
            dataframe['basis_momentum'] = 0
            dataframe['basis_zscore'] = 0
            return dataframe

        # Basic basis calculation
        dataframe['basis'] = (dataframe['close_perp'] - dataframe['close']) / dataframe['close']
        dataframe['basis'] = dataframe['basis'].replace([np.inf, -np.inf], np.nan).ffill().bfill()

        # Basis moving averages
        dataframe['basis_ma_5'] = ta.SMA(dataframe['basis'], timeperiod=5)
        dataframe['basis_ma_10'] = ta.SMA(dataframe['basis'], timeperiod=10)
        dataframe['basis_ma_30'] = ta.SMA(dataframe['basis'], timeperiod=30)
        dataframe['basis_ma_100'] = ta.SMA(dataframe['basis'], timeperiod=100)

        # Basis volatility (rolling standard deviation)
        dataframe['basis_volatility'] = dataframe['basis'].rolling(window=20).std()
        
        # Basis momentum and acceleration
        dataframe['basis_momentum'] = dataframe['basis'] - dataframe['basis_ma_10']
        dataframe['basis_acceleration'] = dataframe['basis_momentum'] - dataframe['basis_momentum'].shift(1)
        
        # Basis z-score with adaptive window
        for window in [20, 50, 100]:
            basis_mean = dataframe['basis'].rolling(window=window).mean()
            basis_std = dataframe['basis'].rolling(window=window).std()
            dataframe[f'basis_zscore_{window}'] = (dataframe['basis'] - basis_mean) / basis_std
        
        # Use the most stable z-score
        dataframe['basis_zscore'] = dataframe['basis_zscore_50'].fillna(0)
        
        # Basis regime detection (trending vs mean-reverting)
        dataframe['basis_regime'] = np.where(
            abs(dataframe['basis_zscore']) > 2, 1,  # Trending
            0  # Mean-reverting
        )
        
        # Basis divergence from price momentum
        price_momentum = dataframe['close'].pct_change(10)
        dataframe['basis_price_divergence'] = dataframe['basis_momentum'] - price_momentum

        return dataframe

    def calculate_enhanced_technical_indicators(self, dataframe):
        """Enhanced technical indicators with multiple timeframes"""
        # Price indicators
        for period in [10, 20, 50, 100]:
            dataframe[f'ema_{period}'] = ta.EMA(dataframe, timeperiod=period)
            dataframe[f'sma_{period}'] = ta.SMA(dataframe, timeperiod=period)
        
        # RSI with multiple periods
        for period in [14, 21]:
            dataframe[f'rsi_{period}'] = ta.RSI(dataframe, timeperiod=period)
        dataframe['rsi'] = dataframe['rsi_14']  # Default
        
        # MACD with signal quality
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        dataframe['macd_strength'] = abs(dataframe['macdhist'])
        
        # Bollinger Bands with squeeze detection
        bb = ta.BBANDS(dataframe)
        dataframe['bb_upper'] = bb['upperband']
        dataframe['bb_middle'] = bb['middleband']
        dataframe['bb_lower'] = bb['lowerband']
        dataframe['bb_width'] = (dataframe['bb_upper'] - dataframe['bb_lower']) / dataframe['bb_middle']
        dataframe['bb_squeeze'] = dataframe['bb_width'] < dataframe['bb_width'].rolling(20).quantile(0.2)
        
        # ADX for trend strength
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['adx_strong'] = dataframe['adx'] > 25
        
        # Stochastic
        stoch = ta.STOCH(dataframe)
        dataframe['stoch_k'] = stoch['slowk']
        dataframe['stoch_d'] = stoch['slowd']
        
        return dataframe

    def calculate_market_structure_features(self, dataframe):
        """Market structure and regime detection"""
        # Higher highs and lower lows
        dataframe['hh'] = dataframe['high'] > dataframe['high'].shift(1)
        dataframe['ll'] = dataframe['low'] < dataframe['low'].shift(1)
        
        # Swing points
        dataframe['swing_high'] = (dataframe['high'] > dataframe['high'].shift(1)) & \
                                 (dataframe['high'] > dataframe['high'].shift(-1))
        dataframe['swing_low'] = (dataframe['low'] < dataframe['low'].shift(1)) & \
                                (dataframe['low'] < dataframe['low'].shift(-1))
        
        # Market volatility regime
        returns = dataframe['close'].pct_change()
        dataframe['volatility_20'] = returns.rolling(20).std()
        dataframe['volatility_regime'] = dataframe['volatility_20'] > dataframe['volatility_20'].rolling(100).median()
        
        # Price momentum across multiple timeframes
        for period in [5, 10, 20]:
            dataframe[f'momentum_{period}'] = dataframe['close'].pct_change(period)
        
        # Trend consistency
        dataframe['trend_consistency'] = (
            (dataframe['ema_10'] > dataframe['ema_20']).astype(int) +
            (dataframe['ema_20'] > dataframe['ema_50']).astype(int) +
            (dataframe['momentum_5'] > 0).astype(int) +
            (dataframe['momentum_10'] > 0).astype(int)
        ) / 4.0
        
        return dataframe

    def calculate_enhanced_volume_features(self, dataframe):
        """Enhanced volume analysis"""
        # Volume moving averages
        for period in [10, 20, 50]:
            dataframe[f'volume_ma_{period}'] = ta.SMA(dataframe['volume'], timeperiod=period)
        
        # Volume ratios
        dataframe['volume_ratio_10'] = dataframe['volume'] / dataframe['volume_ma_10']
        dataframe['volume_ratio_20'] = dataframe['volume'] / dataframe['volume_ma_20']
        
        # Volume trend
        dataframe['volume_trend'] = dataframe['volume_ma_10'] / dataframe['volume_ma_50']
        
        # On-balance volume and money flow
        dataframe['obv'] = ta.OBV(dataframe['close'], dataframe['volume'])
        dataframe['obv_ma'] = ta.SMA(dataframe['obv'], timeperiod=20)
        dataframe['obv_trend'] = dataframe['obv'] > dataframe['obv_ma']
        
        # Volume-weighted average price
        typical_price = (dataframe['high'] + dataframe['low'] + dataframe['close']) / 3
        dataframe['vwap'] = (typical_price * dataframe['volume']).rolling(20).sum() / \
                           dataframe['volume'].rolling(20).sum()
        
        # Volume surge detection
        dataframe['volume_surge'] = dataframe['volume'] > dataframe['volume'].rolling(50).quantile(0.8)
        
        return dataframe

    def calculate_signal_quality_score(self, dataframe):
        """Calculate a comprehensive signal quality score"""
        scores = []
        
        # Trend alignment score
        trend_score = dataframe['trend_consistency']
        scores.append(trend_score)
        
        # Volume confirmation score
        volume_score = np.minimum(dataframe['volume_ratio_20'] / 2.0, 1.0)  # Cap at 1.0
        scores.append(volume_score)
        
        # Volatility appropriateness (not too high, not too low)
        vol_score = 1 - abs(dataframe['volatility_20'] - dataframe['volatility_20'].rolling(100).median()) / \
                    dataframe['volatility_20'].rolling(100).std()
        vol_score = np.clip(vol_score, 0, 1)
        scores.append(vol_score)
        
        # MACD strength score
        macd_score = np.minimum(dataframe['macd_strength'] / dataframe['macd_strength'].rolling(50).quantile(0.8), 1.0)
        scores.append(macd_score)
        
        # ADX trend strength score
        adx_score = np.minimum(dataframe['adx'] / 50.0, 1.0)
        scores.append(adx_score)
        
        # Combine scores
        dataframe['signal_quality'] = pd.DataFrame(scores).T.mean(axis=1)
        dataframe['signal_quality'] = dataframe['signal_quality'].fillna(0)
        
        return dataframe

    def calculate_risk_metrics(self, dataframe):
        """Calculate risk metrics for position sizing"""
        # Recent drawdown
        returns = dataframe['close'].pct_change()
        cumulative_returns = (1 + returns).cumprod()
        rolling_max = cumulative_returns.rolling(50).max()
        dataframe['drawdown'] = (cumulative_returns - rolling_max) / rolling_max
        
        # Current risk level
        dataframe['risk_level'] = abs(dataframe['drawdown'])
        
        # Volatility-adjusted position sizing
        dataframe['position_multiplier'] = 1.0 / (1.0 + dataframe['volatility_20'] * 10)
        dataframe['position_multiplier'] = np.clip(dataframe['position_multiplier'], 0.2, 1.5)
        
        return dataframe

    def prepare_freqai_features(self, dataframe):
        """Prepare features for FreqAI with proper scaling"""
        features = {}
        
        # Basis features
        features['%-basis_zscore'] = dataframe.get('basis_zscore', 0).fillna(0).clip(-5, 5)
        features['%-basis_volatility'] = dataframe.get('basis_volatility', 0).fillna(0).clip(0, 0.1) * 100
        features['%-basis_momentum'] = dataframe.get('basis_momentum', 0).fillna(0).clip(-0.01, 0.01) * 1000
        features['%-basis_regime'] = dataframe.get('basis_regime', 0).fillna(0)
        
        # Technical indicators
        features['%-rsi'] = dataframe['rsi'].fillna(50) / 100.0
        features['%-adx'] = dataframe['adx'].fillna(20) / 100.0
        features['%-macd_strength'] = np.log1p(dataframe['macd_strength'].fillna(0))
        features['%-bb_width'] = dataframe['bb_width'].fillna(0).clip(0, 0.1) * 100
        
        # Market structure
        features['%-trend_consistency'] = dataframe['trend_consistency'].fillna(0)
        features['%-volatility_regime'] = dataframe['volatility_regime'].astype(int)
        features['%-momentum_5'] = dataframe['momentum_5'].fillna(0).clip(-0.05, 0.05) * 100
        features['%-momentum_10'] = dataframe['momentum_10'].fillna(0).clip(-0.1, 0.1) * 50
        
        # Volume features
        features['%-volume_ratio'] = np.log1p(dataframe['volume_ratio_20'].fillna(1))
        features['%-volume_trend'] = dataframe['volume_trend'].fillna(1).clip(0.5, 2.0)
        features['%-obv_trend'] = dataframe['obv_trend'].astype(int)
        
        # Signal quality
        features['%-signal_quality'] = dataframe['signal_quality'].fillna(0)
        
        # Add features to dataframe
        for key, value in features.items():
            dataframe[key] = value
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Simplified entry logic to generate more trades"""
        dataframe.loc[:, 'enter_long'] = 0
        
        # Base technical conditions
        rsi_condition = dataframe['rsi'] < 50  # More lenient RSI
        volume_condition = dataframe['volume'] > dataframe['volume'].rolling(20).mean() * 1.2  # Basic volume
        
        # Try FreqAI if available (but don't require it)
        freqai_condition = True  # Default to True if no FreqAI
        if '&-enter_long' in dataframe.columns:
            # Use FreqAI signals if available
            try:
                freqai_condition = dataframe['&-enter_long'].astype(str).str.lower() == 'enter'
                # Also try probability-based predictions
                for col in dataframe.columns:
                    if isinstance(col, str) and 'prediction' in col.lower():
                        prob_predictions = dataframe[col].fillna(0)
                        freqai_condition = freqai_condition | (prob_predictions > 0.5)
                        break
            except:
                freqai_condition = True  # Fallback if FreqAI fails
        
        # Basic signal quality (if available, otherwise skip)
        quality_condition = True
        if 'signal_quality' in dataframe.columns:
            quality_condition = dataframe['signal_quality'] > 0.4  # Lower threshold
        
        # Combine conditions - only require basic ones
        entry_condition = (
            rsi_condition &
            volume_condition &
            (freqai_condition | quality_condition)  # Either FreqAI OR basic quality
        )
        
        dataframe.loc[entry_condition, 'enter_long'] = 1
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Enhanced exit logic"""
        dataframe.loc[:, 'exit_long'] = 0
        
        # RSI overbought exit
        rsi_exit = dataframe['rsi'] > self.rsi_overbought_threshold.value
        
        # Trend reversal exit
        trend_exit = dataframe['trend_consistency'] < 0.2
        
        # Basis reversal (if available)
        basis_exit = False
        if 'basis_zscore' in dataframe.columns:
            basis_exit = dataframe['basis_zscore'] > 2
        
        # Volume exhaustion
        volume_exit = dataframe['volume_ratio_20'] < 0.5
        
        # Signal quality deterioration
        quality_exit = dataframe['signal_quality'] < 0.3
        
        exit_condition = rsi_exit | trend_exit | basis_exit | volume_exit | quality_exit
        dataframe.loc[exit_condition, 'exit_long'] = 1
        
        return dataframe

    def custom_stake_amount(self, pair: str, current_time, current_rate: float, 
                           proposed_stake: float, min_stake: float, max_stake: float, 
                           entry_tag: str, side: str, **kwargs) -> float:
        """Dynamic position sizing based on risk metrics"""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if dataframe.empty:
            return proposed_stake
        
        # Get current position multiplier
        current_multiplier = dataframe['position_multiplier'].iloc[-1]
        
        # Apply user-defined multiplier
        final_multiplier = current_multiplier * self.position_size_multiplier.value
        
        # Calculate final stake
        final_stake = proposed_stake * final_multiplier
        
        # Ensure within bounds
        return max(min_stake, min(final_stake, max_stake))

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """Set FreqAI targets with enhanced logic"""
        # Calculate future returns
        future_return = dataframe["close"].shift(-self.freqai_label_period) / dataframe["close"] - 1
        
        # More sophisticated labeling based on risk-adjusted returns
        volatility = dataframe['close'].pct_change().rolling(20).std()
        risk_adjusted_threshold = self.freqai_min_return * (1 + volatility * 2)
        
        # Create labels
        dataframe["&-enter_long"] = np.where(
            future_return > risk_adjusted_threshold,
            "enter",
            "hold"
        )
        
        dataframe["&-enter_long"] = dataframe["&-enter_long"].fillna("hold")
        
        return dataframe

    # FreqAI configuration - match config.json identifier
    freqai_info = {
        "identifier": "MyFreqAIModel_Enhanced",
        "features": [
            "%-basis_zscore", "%-basis_volatility", "%-basis_momentum", "%-basis_regime",
            "%-rsi", "%-adx", "%-macd_strength", "%-bb_width",
            "%-trend_consistency", "%-volatility_regime", "%-momentum_5", "%-momentum_10",
            "%-volume_ratio", "%-volume_trend", "%-obv_trend",
            "%-signal_quality"
        ],
        "label_period_candles": freqai_label_period,
        "data_split_parameters": {"test_size": 0.2, "shuffle": False},
        "model_training_parameters": {
            "n_estimators": 100,  # Increased for better performance
            "max_depth": 8,       # Slightly deeper trees
            "min_samples_split": 8,
            "min_samples_leaf": 4,
            "random_state": 42,
            "n_jobs": -1
        }
    }