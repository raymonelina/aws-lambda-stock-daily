import pytest
import pandas as pd
from unittest.mock import Mock
from aws_lambda_alpaca_daily.csv_utils import load_and_merge_csvs, merge_data


@pytest.fixture
def mock_s3_client():
    return Mock()


@pytest.fixture
def matching_dataframes():
    """DataFrames with matching indices."""
    index = pd.to_datetime(['2023-01-01', '2023-01-02'])
    df1 = pd.DataFrame({'price_A': [100, 101]}, index=index)
    df2 = pd.DataFrame({'price_B': [200, 201]}, index=index)
    return df1, df2


@pytest.fixture
def mismatched_dataframes():
    """DataFrames with different indices."""
    df1 = pd.DataFrame({'price_A': [100, 101]}, index=pd.to_datetime(['2023-01-01', '2023-01-02']))
    df2 = pd.DataFrame({'price_B': [200, 201, 202]}, index=pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']))
    return df1, df2


def test_load_and_merge_csvs_matching_indices(mock_s3_client, matching_dataframes, monkeypatch):
    """Test successful merge with matching indices."""
    df1, df2 = matching_dataframes
    
    def mock_read_data(s3_client, bucket, key):
        return df1 if 'file1' in key else df2
    
    monkeypatch.setattr('aws_lambda_alpaca_daily.csv_utils.read_data', mock_read_data)
    
    result = load_and_merge_csvs(['file1.csv', 'file2.csv'], mock_s3_client, 'bucket')
    
    assert len(result) == 2
    assert 'file1_price_A' in result.columns
    assert 'file2_price_B' in result.columns


def test_load_and_merge_csvs_mismatched_indices_strict(mock_s3_client, mismatched_dataframes, monkeypatch):
    """Test that mismatched indices raise ValueError by default."""
    df1, df2 = mismatched_dataframes
    
    def mock_read_data(s3_client, bucket, key):
        return df1 if 'file1' in key else df2
    
    monkeypatch.setattr('aws_lambda_alpaca_daily.csv_utils.read_data', mock_read_data)
    
    with pytest.raises(ValueError, match="Index mismatch"):
        load_and_merge_csvs(['file1.csv', 'file2.csv'], mock_s3_client, 'bucket')


def test_load_and_merge_csvs_mismatched_indices_allow(mock_s3_client, mismatched_dataframes, monkeypatch, caplog):
    """Test that mismatched indices log warning when allowed."""
    df1, df2 = mismatched_dataframes
    
    def mock_read_data(s3_client, bucket, key):
        return df1 if 'file1' in key else df2
    
    monkeypatch.setattr('aws_lambda_alpaca_daily.csv_utils.read_data', mock_read_data)
    
    result = load_and_merge_csvs(['file1.csv', 'file2.csv'], mock_s3_client, 'bucket', allow_index_mismatch=True)
    
    assert "Index mismatch" in caplog.text
    assert len(result) == 3  # Outer join creates 3 rows


# --- Test merge_data ---
def test_merge_data_new_empty_existing_full():
    existing_df = pd.DataFrame(
        {
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000],
        },
        index=pd.to_datetime(["2023-01-01"]),
    )
    existing_df.index.name = "timestamp"
    new_df = pd.DataFrame()
    merged_df = merge_data(existing_df, new_df)
    pd.testing.assert_frame_equal(merged_df, existing_df)


def test_merge_data_existing_empty_new_full():
    existing_df = pd.DataFrame()
    new_df = pd.DataFrame(
        {
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000],
        },
        index=pd.to_datetime(["2023-01-01"]),
    )
    new_df.index.name = "timestamp"
    merged_df = merge_data(existing_df, new_df)
    pd.testing.assert_frame_equal(merged_df, new_df)


def test_merge_data_with_overlap():
    existing_df = pd.DataFrame(
        {
            "open": [100.0, 102.0],
            "high": [101.0, 103.0],
            "low": [99.0, 101.5],
            "close": [100.5, 102.5],
            "volume": [1000, 1100],
        },
        index=pd.to_datetime(["2023-01-01", "2023-01-02"]),
    )
    existing_df.index.name = "timestamp"

    new_df = pd.DataFrame(
        {
            "open": [102.0, 104.0],
            "high": [103.0, 105.0],
            "low": [101.5, 103.5],
            "close": [102.5, 104.5],
            "volume": [1100, 1200],
        },
        index=pd.to_datetime(["2023-01-02", "2023-01-03"]),
    )
    new_df.index.name = "timestamp"

    expected_df = pd.DataFrame(
        {
            "open": [100.0, 102.0, 104.0],
            "high": [101.0, 103.0, 105.0],
            "low": [99.0, 101.5, 103.5],
            "close": [100.5, 102.5, 104.5],
            "volume": [1000, 1100, 1200],
        },
        index=pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
    )
    expected_df.index.name = "timestamp"

    merged_df = merge_data(existing_df, new_df)
    pd.testing.assert_frame_equal(merged_df, expected_df)


def test_merge_data_no_overlap():
    existing_df = pd.DataFrame(
        {
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000],
        },
        index=pd.to_datetime(["2023-01-01"]),
    )
    existing_df.index.name = "timestamp"

    new_df = pd.DataFrame(
        {
            "open": [102.0],
            "high": [103.0],
            "low": [101.5],
            "close": [102.5],
            "volume": [1100],
        },
        index=pd.to_datetime(["2023-01-02"]),
    )
    new_df.index.name = "timestamp"

    expected_df = pd.DataFrame(
        {
            "open": [100.0, 102.0],
            "high": [101.0, 103.0],
            "low": [99.0, 101.5],
            "close": [100.5, 102.5],
            "volume": [1000, 1100],
        },
        index=pd.to_datetime(["2023-01-01", "2023-01-02"]),
    )
    expected_df.index.name = "timestamp"

    merged_df = merge_data(existing_df, new_df)
    pd.testing.assert_frame_equal(merged_df, expected_df)