"""
Tests for data models
"""

import pytest
from models.tnved_record import TNVEDRecord
from models.search_result import SearchResult


class TestTNVEDRecord:
    """Tests for TNVEDRecord data model"""
    
    def test_valid_record_creation(self):
        """Test creating a valid ТНВЭД record"""
        record = TNVEDRecord(
            code="0901110000",
            text_ex="КОФЕ НЕЖАРЕНЫЙ НЕОСВОБОЖДЕННЫЙ ОТ КОФЕИНА",
            normalized_text="кофе нежареный неосвобожденный от кофеин"
        )
        
        assert record.code == "0901110000"
        assert record.text_ex == "КОФЕ НЕЖАРЕНЫЙ НЕОСВОБОЖДЕННЫЙ ОТ КОФЕИНА"
        assert record.normalized_text == "кофе нежареный неосвобожденный от кофеин"
    
    def test_empty_code_raises_error(self):
        """Test that empty code raises ValueError"""
        with pytest.raises(ValueError, match="ТНВЭД code cannot be empty"):
            TNVEDRecord(
                code="",
                text_ex="Some description",
                normalized_text="some description"
            )
    
    def test_empty_text_ex_raises_error(self):
        """Test that empty text_ex raises ValueError"""
        with pytest.raises(ValueError, match="TextEx description cannot be empty"):
            TNVEDRecord(
                code="0901110000",
                text_ex="",
                normalized_text="some description"
            )
    
    def test_normalized_text_can_be_empty(self):
        """Test that normalized_text can be empty (edge case)"""
        # This might happen if normalization removes all content
        record = TNVEDRecord(
            code="0901110000",
            text_ex="!!!",
            normalized_text=""
        )
        assert record.normalized_text == ""


class TestSearchResult:
    """Tests for SearchResult data model"""
    
    def test_valid_result_creation(self):
        """Test creating a valid search result"""
        result = SearchResult(
            code="0901110000",
            description="КОФЕ НЕЖАРЕНЫЙ НЕОСВОБОЖДЕННЫЙ ОТ КОФЕИНА",
            normalized_text="кофе нежареный неосвобожденный от кофеин",
            similarity_score=0.89
        )
        
        assert result.code == "0901110000"
        assert result.description == "КОФЕ НЕЖАРЕНЫЙ НЕОСВОБОЖДЕННЫЙ ОТ КОФЕИНА"
        assert result.normalized_text == "кофе нежареный неосвобожденный от кофеин"
        assert result.similarity_score == 0.89
    
    def test_empty_code_raises_error(self):
        """Test that empty code raises ValueError"""
        with pytest.raises(ValueError, match="ТНВЭД code cannot be empty"):
            SearchResult(
                code="",
                description="Some description",
                normalized_text="some description",
                similarity_score=0.5
            )
    
    def test_similarity_score_bounds(self):
        """Test that similarity score must be between 0 and 1"""
        # Valid scores
        SearchResult(
            code="0901110000",
            description="Test",
            normalized_text="test",
            similarity_score=0.0
        )
        
        SearchResult(
            code="0901110000",
            description="Test",
            normalized_text="test",
            similarity_score=1.0
        )
        
        SearchResult(
            code="0901110000",
            description="Test",
            normalized_text="test",
            similarity_score=0.5
        )
    
    def test_similarity_score_below_zero_raises_error(self):
        """Test that similarity score below 0 raises ValueError"""
        with pytest.raises(ValueError, match="Similarity score must be between 0 and 1"):
            SearchResult(
                code="0901110000",
                description="Test",
                normalized_text="test",
                similarity_score=-0.1
            )
    
    def test_similarity_score_above_one_raises_error(self):
        """Test that similarity score above 1 raises ValueError"""
        with pytest.raises(ValueError, match="Similarity score must be between 0 and 1"):
            SearchResult(
                code="0901110000",
                description="Test",
                normalized_text="test",
                similarity_score=1.1
            )
