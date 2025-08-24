import pandas as pd
import logging
from typing import List, Dict, Any

try:
    from .csv_utils import load_and_merge_csvs
    from .storage import write_data
except ImportError:
    from csv_utils import load_and_merge_csvs
    from storage import write_data

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """Configurable feature extractor that can add/remove different features."""
    
    def __init__(self, features: List[str] = None):
        self.features = features or ['moving_averages', 'technical_indicators', 'price_changes']
        self.ma_windows = [5, 20, 50]
        self.rsi_window = 14
        
    def extract_features(self, input_files: List[str], output_file: str, s3_client=None, bucket_name: str = None) -> pd.DataFrame:
        """Main feature extraction pipeline: load -> extract -> save."""
        logger.info(f"Starting feature extraction with features: {self.features}")
        
        # Load and merge input data
        merged_df = load_and_merge_csvs(input_files, s3_client, bucket_name)
        
        if merged_df.empty:
            logger.warning("No data to process for feature extraction")
            return pd.DataFrame()
        
        # Extract features
        features_df = self.extract(merged_df)
        
        # Save output
        write_data(s3_client, features_df, bucket_name, output_file)
        
        logger.info("Completed feature extraction")
        return features_df
    
    def extract(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract configured features from merged data."""
        result_df = df.copy()
        
        if 'moving_averages' in self.features:
            result_df = self._add_moving_averages(result_df)
        
        if 'technical_indicators' in self.features:
            result_df = self._add_technical_indicators(result_df)
        
        if 'price_changes' in self.features:
            result_df = self._add_price_changes(result_df)
        
        return result_df
    
    def _add_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add moving averages for specified windows."""
        close_columns = [col for col in df.columns if 'close' in col.lower()]
        
        for col in close_columns:
            symbol = col.split('_')[0] if '_' in col else col.replace('close', '').strip()
            for window in self.ma_windows:
                ma_col = f"{symbol}_ma_{window}" if symbol else f"ma_{window}"
                df[ma_col] = df[col].rolling(window=window).mean()
        
        return df
    
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add RSI and other technical indicators."""
        close_columns = [col for col in df.columns if 'close' in col.lower()]
        
        for col in close_columns:
            symbol = col.split('_')[0] if '_' in col else col.replace('close', '').strip()
            rsi_col = f"{symbol}_rsi" if symbol else "rsi"
            df[rsi_col] = self._calculate_rsi(df[col])
        
        return df
    
    def _add_price_changes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add price change features."""
        close_columns = [col for col in df.columns if 'close' in col.lower()]
        
        for col in close_columns:
            symbol = col.split('_')[0] if '_' in col else col.replace('close', '').strip()
            
            # Daily returns
            returns_col = f"{symbol}_returns" if symbol else "returns"
            df[returns_col] = df[col].pct_change()
            
            # Price change from previous day
            change_col = f"{symbol}_price_change" if symbol else "price_change"
            df[change_col] = df[col].diff()
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """Calculate RSI (Relative Strength Index)."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi