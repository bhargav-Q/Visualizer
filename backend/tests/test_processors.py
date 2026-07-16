import pytest
import sys
from unittest.mock import MagicMock

# Import processors directly
from processors.text_processor import process_text
from processors.tabular_processor import process_tabular_data

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

def test_tabular_processor_pure_python():
    """Test tabular processor with pure python dict."""
    
    mock_raw_data = {
        "headers": ["A", "B"],
        "rows": [
            [1, "test1"],
            [2, "test1"],
            [3, "test2"],
            [4, "test2"],
            [5, "test2"]
        ]
    }

    result = process_tabular_data(mock_raw_data)
    
    assert result.row_count == 5
    assert result.col_count == 2
    assert len(result.columns) == 2
    assert result.columns[0].name == "A"
    assert "A" in result.numeric_summary
    assert result.numeric_summary["A"].mean == 3.0
    assert "B" in result.categorical_summary
    assert result.categorical_summary["B"].unique == 2
