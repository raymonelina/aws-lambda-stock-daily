import pandas as pd
import logging

try:
    from .storage import read_data
except ImportError:
    from storage import read_data

logger = logging.getLogger(__name__)


def merge_data(existing_df, new_df):
    """Merges new data with existing data, deduplicates, and sorts."""
    if existing_df.empty:
        return new_df.sort_index()
    if new_df.empty:
        return existing_df.sort_index()

    combined_df = pd.concat([existing_df, new_df])
    combined_df = combined_df[~combined_df.index.duplicated(keep="last")]
    return combined_df.sort_index()


def load_and_merge_csvs(file_paths, s3_client, bucket_name, allow_index_mismatch=False):
    """Load multiple CSV files and merge on timestamp."""
    dataframes = []
    symbols = []
    for file_path in file_paths:
        df = read_data(s3_client, bucket_name, file_path)
        if not df.empty:
            symbol = file_path.replace('.csv', '')
            symbols.append(symbol)
            dataframes.append(df)
            logger.info(f"{symbol}: {len(df)} rows ({df.index.min().date()} to {df.index.max().date()})")
        else:
            logger.warning(f"Empty dataframe from {file_path.replace('.csv', '')}")
    
    if not dataframes:
        return pd.DataFrame()
    
    # Prefix columns with symbol names and merge
    for i, (df, symbol) in enumerate(zip(dataframes, symbols)):
        df.columns = [f"{symbol}_{col}" for col in df.columns]
        dataframes[i] = df
    
    # Merge all dataframes on timestamp index with validation
    merged_df = dataframes[0]
    for i, df in enumerate(dataframes[1:], 1):
        # Check for exact index match
        if not merged_df.index.equals(df.index):
            error_msg = (f"Index mismatch: {symbols[0]} has {len(merged_df.index)} rows "
                        f"({merged_df.index.min().date()} to {merged_df.index.max().date()}), "
                        f"{symbols[i]} has {len(df.index)} rows "
                        f"({df.index.min().date()} to {df.index.max().date()})")
            
            if allow_index_mismatch:
                logger.warning(error_msg)
            else:
                raise ValueError(error_msg)
        
        merged_df = pd.merge(merged_df, df, left_index=True, right_index=True, how='outer')
    
    merged_df = merged_df.sort_index()
    logger.info(f"Merged {len(symbols)} symbols: {', '.join(symbols)} into {len(merged_df)} rows")
    return merged_df