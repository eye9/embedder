"""
Tests for data models
"""

import pytest
from models.tnved_record import TNVEDRecord
from models.search_result import SearchResult, SourceType
from models.product_record import ProductRecord


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
            similarity_score=0.89,
            source_type=SourceType.REFERENCE.value
        )
        
        assert result.code == "0901110000"
        assert result.description == "КОФЕ НЕЖАРЕНЫЙ НЕОСВОБОЖДЕННЫЙ ОТ КОФЕИНА"
        assert result.normalized_text == "кофе нежареный неосвобожденный от кофеин"
        assert result.similarity_score == 0.89
        assert result.source_type == "reference"
        assert result.source_name is None
        assert result.source_id is None
    
    def test_valid_result_with_source_info(self):
        """Test creating a search result with source information"""
        result = SearchResult(
            code="0901110000",
            description="Кофе арабика зерновой 1кг",
            normalized_text="кофе арабика зерновой килограмм",
            similarity_score=0.95,
            source_type=SourceType.PRODUCT.value,
            source_name="customs_2024_q1",
            source_id="декларация_12345"
        )
        
        assert result.source_type == "product"
        assert result.source_name == "customs_2024_q1"
        assert result.source_id == "декларация_12345"
    
    def test_empty_code_raises_error(self):
        """Test that empty code raises ValueError"""
        with pytest.raises(ValueError, match="ТНВЭД code cannot be empty"):
            SearchResult(
                code="",
                description="Some description",
                normalized_text="some description",
                similarity_score=0.5,
                source_type=SourceType.REFERENCE.value
            )
    
    def test_invalid_source_type_raises_error(self):
        """Test that invalid source_type raises ValueError"""
        with pytest.raises(ValueError, match="Invalid source_type"):
            SearchResult(
                code="0901110000",
                description="Test",
                normalized_text="test",
                similarity_score=0.5,
                source_type="invalid_type"
            )
    
    def test_similarity_score_bounds(self):
        """Test that similarity score must be between 0 and 1"""
        # Valid scores
        SearchResult(
            code="0901110000",
            description="Test",
            normalized_text="test",
            similarity_score=0.0,
            source_type=SourceType.REFERENCE.value
        )
        
        SearchResult(
            code="0901110000",
            description="Test",
            normalized_text="test",
            similarity_score=1.0,
            source_type=SourceType.REFERENCE.value
        )
        
        SearchResult(
            code="0901110000",
            description="Test",
            normalized_text="test",
            similarity_score=0.5,
            source_type=SourceType.REFERENCE.value
        )
    
    def test_similarity_score_below_zero_raises_error(self):
        """Test that similarity score below 0 raises ValueError"""
        with pytest.raises(ValueError, match="Similarity score must be between 0 and 1"):
            SearchResult(
                code="0901110000",
                description="Test",
                normalized_text="test",
                similarity_score=-0.1,
                source_type=SourceType.REFERENCE.value
            )
    
    def test_similarity_score_above_one_raises_error(self):
        """Test that similarity score above 1 raises ValueError"""
        with pytest.raises(ValueError, match="Similarity score must be between 0 and 1"):
            SearchResult(
                code="0901110000",
                description="Test",
                normalized_text="test",
                similarity_score=1.1,
                source_type=SourceType.REFERENCE.value
            )


class TestProductRecord:
    """Tests for ProductRecord data model"""
    
    def test_valid_product_record_creation(self):
        """Test creating a valid product record"""
        record = ProductRecord(
            code="0901110000",
            description="Кофе арабика зерновой 1кг",
            normalized_text="кофе арабика зерновой килограмм",
            source_name="customs_2024_q1"
        )
        
        assert record.code == "0901110000"
        assert record.description == "Кофе арабика зерновой 1кг"
        assert record.normalized_text == "кофе арабика зерновой килограмм"
        assert record.source_name == "customs_2024_q1"
        assert record.source_id is None
    
    def test_product_record_with_source_id(self):
        """Test creating a product record with source ID"""
        record = ProductRecord(
            code="0901110000",
            description="Кофе арабика зерновой 1кг",
            normalized_text="кофе арабика зерновой килограмм",
            source_name="customs_2024_q1",
            source_id="декларация_12345"
        )
        
        assert record.source_id == "декларация_12345"
    
    def test_empty_code_raises_error(self):
        """Test that empty code raises ValueError"""
        with pytest.raises(ValueError, match="ТНВЭД code cannot be empty"):
            ProductRecord(
                code="",
                description="Some product",
                normalized_text="some product",
                source_name="test_source"
            )
    
    def test_empty_description_raises_error(self):
        """Test that empty description raises ValueError"""
        with pytest.raises(ValueError, match="Product description cannot be empty"):
            ProductRecord(
                code="0901110000",
                description="",
                normalized_text="some product",
                source_name="test_source"
            )
    
    def test_empty_source_name_raises_error(self):
        """Test that empty source_name raises ValueError"""
        with pytest.raises(ValueError, match="Source name cannot be empty"):
            ProductRecord(
                code="0901110000",
                description="Some product",
                normalized_text="some product",
                source_name=""
            )


class TestSourceType:
    """Tests for SourceType enumeration"""
    
    def test_source_type_values(self):
        """Test that SourceType has correct values"""
        assert SourceType.REFERENCE.value == "reference"
        assert SourceType.PRODUCT.value == "product"
    
    def test_source_type_enum_members(self):
        """Test that SourceType has expected members"""
        assert len(SourceType) == 2
        assert SourceType.REFERENCE in SourceType
        assert SourceType.PRODUCT in SourceType
