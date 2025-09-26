# user_data/strategies/MyFreqAIStrategy.py
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class MyFreqAIStrategy(IStrategy):
    timeframe = "5m"
    can_short = False
    startup_candle_count = 200

    # Plot configuration for visualizing indicators and signals
    plot_config = {
        # Main plot - price chart with EMAs and Bollinger Bands
        'main_plot': {
            'tema': {},
            'ema_20': {'color': 'orange'},
            'ema_50': {'color': 'blue'},
            'bb_upper': {'color': 'gray', 'type': 'line'},
            'bb_lower': {'color': 'gray', 'type': 'line'},
            'bb_middle': {'color': 'gray', 'type': 'line'},
        },
        # Subplots
        'subplots': {
            'RSI & ADX': {
                'rsi': {'color': 'red'},
                'adx': {'color': 'purple'},
            },
            'MACD': {
                'macd': {'color': 'blue'},
                'macdsignal': {'color': 'orange'},
                'macdhist': {'type': 'bar', 'color': 'gray'},
            },
            'Signals': {
                'enter_long': {'color': 'green', 'type': 'scatter'},
                'exit_long': {'color': 'red', 'type': 'scatter'},
            }
        }
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Basic technical indicators
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema_20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_50"] = ta.EMA(dataframe, timeperiod=50)

        # Additional indicators for futures trading
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["macd"], dataframe["macdsignal"], dataframe["macdhist"] = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe["bb_upper"], dataframe["bb_middle"], dataframe["bb_lower"] = ta.BBANDS(dataframe, timeperiod=20)

        # For futures perp-spot arbitrage features, we would need data from both markets
        # These features would be calculated if we had access to both spot and perp data
        # For now, we'll create placeholder features that demonstrate the concept

        # Basis-related features (perp price - spot price) / spot price
        # In a real implementation, you'd load both datasets and calculate:
        # dataframe["basis"] = (perp_close - spot_close) / spot_close
        # dataframe["basis_ma"] = ta.SMA(dataframe["basis"], timeperiod=20)
        # dataframe["basis_zscore"] = (dataframe["basis"] - dataframe["basis"].rolling(100).mean()) / dataframe["basis"].rolling(100).std()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Use FreqAI predictions for entry signals, with fallback to basic RSI condition
        dataframe.loc[:, 'enter_long'] = dataframe.get('&-enter_long', dataframe['rsi'] < 30)
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Use FreqAI predictions for exit signals, with fallback to basic RSI condition
        dataframe.loc[:, 'exit_long'] = dataframe.get('&-exit_long', dataframe['rsi'] > 70)
        return dataframe
