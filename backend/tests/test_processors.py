import pytest
import sys
from unittest.mock import MagicMock

# Import processors directly
from processors.text_processor import process_text
from processors.tabular_processor import process_dataframe

def test_text_processor_success(mocker):
    """Test text processor successfully parses OpenAI API response without hitting the real API."""
    
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"summary": "Test summary.", "keywords": [{"word": "test", "score": 0.99}]}'))
    ]
    
    # Mock the OpenAI client creation
    mock_openai = mocker.patch("processors.text_processor.OpenAI")
    mock_client_instance = mock_openai.return_value
    mock_client_instance.chat.completions.create.return_value = mock_response

    result = process_text("This is a test document.", page_count=1, paragraph_count=1)
    
    assert result.summary == "Test summary."
    assert len(result.keywords) == 1
    assert result.keywords[0].word == "test"
    assert result.keywords[0].score == 0.99
    assert result.word_count == 5

def test_tabular_processor_mocked_pandas(mocker):
    """Test tabular processor by mocking pandas and numpy to bypass AppLocker."""
    # Pre-emptively mock pandas and numpy so they are never loaded from disk
    mock_pd = MagicMock()
    mock_np = MagicMock()
    sys.modules["pandas"] = mock_pd
    sys.modules["numpy"] = mock_np
    
    # Create a mock dataframe
    mock_df = MagicMock()
    mock_df.shape = (10, 2)
    mock_df.columns = ["A", "B"]
    
    # Mock Series behavior
    mock_series_a = MagicMock()
    mock_series_a.dtype = "int64"
    mock_series_b = MagicMock()
    mock_series_b.dtype = "object"
    
    # __getitem__ mock
    def getitem_side_effect(key):
        if key == "A": return mock_series_a
        return mock_series_b
    mock_df.__getitem__.side_effect = getitem_side_effect
    
    # head().replace().values.tolist() chain for preview rows
    mock_preview = MagicMock()
    mock_preview.replace.return_value.values.tolist.return_value = [[1, "test"]]
    mock_df.head.return_value = mock_preview

    # Type checking mocks
    mock_pd.api.types.is_datetime64_any_dtype.return_value = False
    mock_pd.api.types.is_numeric_dtype.side_effect = lambda x: x == mock_series_a
    mock_pd.api.types.is_object_dtype.side_effect = lambda x: x == mock_series_b
    mock_pd.api.types.is_string_dtype.return_value = False
    
    # Numeric stats
    mock_series_a.mean.return_value = 5.0
    mock_series_a.median.return_value = 5.0
    mock_series_a.min.return_value = 1.0
    mock_series_a.max.return_value = 10.0
    mock_series_a.std.return_value = 2.5
    mock_pd.notna.return_value = True
    
    # Categorical stats
    mock_series_b.nunique.return_value = 1
    mock_series_b.value_counts.return_value.head.return_value.items.return_value = [("test", 10)]

    # Groupby for charts
    mock_df.groupby.return_value.__getitem__.return_value.mean.return_value.nlargest.return_value.items.return_value = [("test", 5.0)]

    # Execute
    result = process_dataframe(mock_df)
    
    assert result.row_count == 10
    assert result.col_count == 2
    assert len(result.columns) == 2
    assert result.columns[0].name == "A"
    assert "A" in result.numeric_summary
    assert result.numeric_summary["A"].mean == 5.0
    assert "B" in result.categorical_summary
    assert result.categorical_summary["B"].unique == 1
    
    # Cleanup sys.modules just in case
    del sys.modules["pandas"]
    del sys.modules["numpy"]
