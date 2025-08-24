import pandas as pd
import logging
from abc import ABC, abstractmethod
from datetime import datetime, date
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.historical import StockHistoricalDataClient

logger = logging.getLogger(__name__)


class DataSource(ABC):
    """Generic base class for data sources."""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def fetch_data(self, symbol: str, start_date: date, end_date: date, **kwargs) -> pd.DataFrame:
        """Fetch data for a symbol within date range."""
        pass


class AlpacaDataSource(DataSource):
    """Alpaca API data source implementation."""
    
    def __init__(self, api_key: str, secret_key: str):
        super().__init__("Alpaca")
        self.api_key = api_key
        self.secret_key = secret_key
    
    def fetch_data(self, symbol: str, start_date: date, end_date: date, **kwargs) -> pd.DataFrame:
        """Fetches historical stock data from Alpaca API."""
        try:
            data_client = StockHistoricalDataClient(self.api_key, self.secret_key)
            request_params = StockBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=TimeFrame.Day,
                start=start_date,
                end=end_date,
            )
            bars = data_client.get_stock_bars(request_params)

            if bars and bars.data and symbol in bars.data:
                df = bars.df.loc[symbol]
                # Convert timezone to UTC
                df.index = df.index.tz_convert("UTC")
                df = df[["open", "high", "low", "close", "volume"]]
                df.index.name = "timestamp"
                return df
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error fetching Alpaca data for {symbol}: {e}")
            return pd.DataFrame()


class MockDataSource(DataSource):
    """Mock data source for testing."""
    
    def __init__(self):
        super().__init__("Mock")
    
    def fetch_data(self, symbol: str, start_date: date, end_date: date, **kwargs) -> pd.DataFrame:
        """Generate mock stock data."""
        import numpy as np
        
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        np.random.seed(hash(symbol) % 2**32)  # Consistent data per symbol
        
        # Generate realistic stock data
        base_price = 100
        prices = []
        current_price = base_price
        
        for _ in date_range:
            change = np.random.normal(0, 0.02)  # 2% daily volatility
            current_price *= (1 + change)
            prices.append(current_price)
        
        df = pd.DataFrame({
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, len(prices))
        }, index=date_range)
        
        df.index.name = "timestamp"
        logger.info(f"Generated mock data for {symbol}: {len(df)} rows")
        return df