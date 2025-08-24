import pytest
import pandas as pd
from datetime import date
from unittest.mock import Mock, patch
from aws_lambda_alpaca_daily.data_sources import DataSource, AlpacaDataSource, MockDataSource


class TestDataSource:
    """Test the abstract DataSource base class."""
    
    def test_data_source_is_abstract(self):
        """Test that DataSource cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DataSource("test")


class TestMockDataSource:
    """Test the MockDataSource implementation."""
    
    @pytest.fixture
    def mock_source(self):
        return MockDataSource()
    
    def test_mock_data_source_initialization(self, mock_source):
        """Test MockDataSource initialization."""
        assert mock_source.name == "Mock"
    
    def test_fetch_data_returns_dataframe(self, mock_source):
        """Test that fetch_data returns a DataFrame with correct structure."""
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 5)
        
        df = mock_source.fetch_data("AAPL", start_date, end_date)
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert list(df.columns) == ['open', 'high', 'low', 'close', 'volume']
        assert df.index.name == "timestamp"
        assert len(df) == 5  # 5 days
    
    def test_fetch_data_consistent_per_symbol(self, mock_source):
        """Test that mock data is consistent for the same symbol."""
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 3)
        
        df1 = mock_source.fetch_data("AAPL", start_date, end_date)
        df2 = mock_source.fetch_data("AAPL", start_date, end_date)
        
        pd.testing.assert_frame_equal(df1, df2)
    
    def test_fetch_data_different_per_symbol(self, mock_source):
        """Test that mock data differs between symbols."""
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 3)
        
        df_aapl = mock_source.fetch_data("AAPL", start_date, end_date)
        df_googl = mock_source.fetch_data("GOOGL", start_date, end_date)
        
        assert not df_aapl.equals(df_googl)


class TestAlpacaDataSource:
    """Test the AlpacaDataSource implementation."""
    
    @pytest.fixture
    def alpaca_source(self):
        return AlpacaDataSource("test_key", "test_secret")
    
    def test_alpaca_data_source_initialization(self, alpaca_source):
        """Test AlpacaDataSource initialization."""
        assert alpaca_source.name == "Alpaca"
        assert alpaca_source.api_key == "test_key"
        assert alpaca_source.secret_key == "test_secret"
    
    @patch('aws_lambda_alpaca_daily.data_sources.StockHistoricalDataClient')
    def test_fetch_data_success(self, mock_client_class, alpaca_source):
        """Test successful data fetching from Alpaca API."""
        # Mock the client and response
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Create mock response data
        mock_df = pd.DataFrame({
            'open': [100.0, 101.0],
            'high': [102.0, 103.0],
            'low': [99.0, 100.0],
            'close': [101.0, 102.0],
            'volume': [1000, 1100],
            'extra_col': [1, 2]  # Should be filtered out
        }, index=pd.date_range('2023-01-01', periods=2, tz='US/Eastern'))
        mock_df.index.name = "timestamp"
        
        mock_bars = Mock()
        mock_bars.data = {'AAPL': 'mock_data'}
        mock_bars.df = pd.concat({'AAPL': mock_df}, names=['symbol'])
        mock_client.get_stock_bars.return_value = mock_bars
        
        result = alpaca_source.fetch_data("AAPL", date(2023, 1, 1), date(2023, 1, 2))
        
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert list(result.columns) == ['open', 'high', 'low', 'close', 'volume']
        assert result.index.name == "timestamp"
        assert str(result.index.tz) == 'UTC'  # Should be converted to UTC
    
    @patch('aws_lambda_alpaca_daily.data_sources.StockHistoricalDataClient')
    def test_fetch_data_no_data(self, mock_client_class, alpaca_source):
        """Test handling when no data is returned from Alpaca API."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_bars = Mock()
        mock_bars.data = {}  # No data
        mock_client.get_stock_bars.return_value = mock_bars
        
        result = alpaca_source.fetch_data("AAPL", date(2023, 1, 1), date(2023, 1, 2))
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty
    
    @patch('aws_lambda_alpaca_daily.data_sources.StockHistoricalDataClient')
    def test_fetch_data_api_error(self, mock_client_class, alpaca_source, caplog):
        """Test handling of API errors."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_stock_bars.side_effect = Exception("API Error")
        
        result = alpaca_source.fetch_data("AAPL", date(2023, 1, 1), date(2023, 1, 2))
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty
        assert "Error fetching Alpaca data for AAPL: API Error" in caplog.text