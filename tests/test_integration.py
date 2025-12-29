"""
Integration tests for Product Data Support feature

These tests validate complete workflows:
1. Load product data → search → verify results
2. Mixed data scenarios (reference + product records)
3. Performance with large datasets
4. End-to-end CLI workflows

Requirements: All requirements
"""

import pytest
import tempfile
import pandas as pd
import time
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Dict

from services.product_loader import ProductLoader
from services.tnved_loader import TNVEDLoader
from services.enhanced_searcher import EnhancedSearcher
from services.text_normalizer import TextNormalizer
from services.embedding_generator import EmbeddingGenerator
from utils.config import Config


@pytest.fixture
def temp_db_path():
    """Create temporary database path for integration testing"""
    import gc
    
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    
    # Force cleanup
    gc.collect()
    time.sleep(0.1)
    
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except:
        pass


@pytest.fixture
def config():
    """Create test configuration"""
    return Config()


@pytest.fixture
def components(temp_db_path, config):
    """Create initialized components for testing"""
    normalizer = TextNormalizer()
    embedder = EmbeddingGenerator(config.model.name, config.model.device)
    
    return {
        'normalizer': normalizer,
        'embedder': embedder,
        'db_path': temp_db_path
    }


@pytest.fixture
def sample_reference_data():
    """Create sample reference data"""
    return pd.DataFrame({
        'Code': ['0901110000', '0902000000', '1701110000'],
        'TextEx': [
            'КОФЕ НЕЖАРЕНЫЙ НЕОСВОБОЖДЕННЫЙ ОТ КОФЕИНА',
            'ЧАЙ ЗЕЛЕНЫЙ',
            'САХАР БЕЛЫЙ КРИСТАЛЛИЧЕСКИЙ'
        ]
    })


@pytest.fixture
def sample_product_data():
    """Create sample product data"""
    return pd.DataFrame({
        'Code': ['0901110000', '0901110000', '0902000000'],
        'TextEx': [
            'Кофе арабика зерновой 1кг',
            'Кофе арабика молотый 500г', 
            'Чай зеленый листовой премиум'
        ],
        'SourceID': ['декларация_001', 'декларация_002', 'каталог_003']
    })


class TestCompleteWorkflows:
    """Test complete end-to-end workflows"""
    
    def test_load_product_data_then_search_workflow(self, components, sample_product_data):
        """Test: Load product data → search → verify results"""
        # Create temporary Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            temp_excel = temp_file.name
            sample_product_data.to_excel(temp_excel, index=False)
        
        try:
            # Step 1: Load product data
            loader = ProductLoader(
                components['db_path'],
                components['normalizer'],
                components['embedder'],
                batch_size=10
            )
            
            loaded_count = loader.load_from_excel(temp_excel, "test_source")
            assert loaded_count == 3
            
            # Step 2: Initialize searcher and perform search
            searcher = EnhancedSearcher(
                components['db_path'],
                components['normalizer'],
                components['embedder']
            )
            
            # Step 3: Search for coffee products
            results = searcher.search("кофе арабика", top_k=5)
            
            # Step 4: Verify results
            assert len(results) >= 2  # Should find both coffee products
            
            # Verify all results are product type
            for result in results:
                if result.code == '0901110000':
                    assert result.source_type == "product"
                    assert result.source_name == "test_source"
            
            # Step 5: Test source filtering
            product_results = searcher.search("кофе", source_filter="product")
            assert len(product_results) >= 2
            assert all(r.source_type == "product" for r in product_results)
            
        finally:
            Path(temp_excel).unlink(missing_ok=True)
    
    def test_mixed_data_scenarios(self, components, sample_reference_data, sample_product_data):
        """Test mixed data scenarios (reference + product records)"""
        # Create temporary Excel files
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as ref_file:
            ref_excel = ref_file.name
            sample_reference_data.to_excel(ref_excel, index=False)
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as prod_file:
            prod_excel = prod_file.name
            sample_product_data.to_excel(prod_excel, index=False)
        
        try:
            # Step 1: Load reference data
            ref_loader = TNVEDLoader(
                components['db_path'],
                components['normalizer'],
                components['embedder'],
                batch_size=10
            )
            ref_count = ref_loader.load_from_excel(ref_excel)
            assert ref_count == 3
            
            # Step 2: Load product data
            prod_loader = ProductLoader(
                components['db_path'],
                components['normalizer'],
                components['embedder'],
                batch_size=10
            )
            prod_count = prod_loader.load_from_excel(prod_excel, "mixed_test_source")
            assert prod_count == 3
            
            # Step 3: Initialize searcher
            searcher = EnhancedSearcher(
                components['db_path'],
                components['normalizer'],
                components['embedder']
            )
            
            # Step 4: Test unfiltered search (should return both types)
            all_results = searcher.search("кофе", top_k=10)
            
            # Should have both reference and product records
            source_types = {r.source_type for r in all_results}
            assert "reference" in source_types
            assert "product" in source_types
            
            # Step 5: Test result prioritization (reference first)
            coffee_results = [r for r in all_results if r.code == '0901110000']
            if len(coffee_results) > 1:
                # Reference records should come before product records
                ref_indices = [i for i, r in enumerate(coffee_results) if r.source_type == "reference"]
                prod_indices = [i for i, r in enumerate(coffee_results) if r.source_type == "product"]
                
                if ref_indices and prod_indices:
                    assert min(ref_indices) < min(prod_indices)
            
            # Step 6: Test source filtering
            ref_only = searcher.search("кофе", source_filter="reference")
            assert all(r.source_type == "reference" for r in ref_only)
            
            prod_only = searcher.search("кофе", source_filter="product")
            assert all(r.source_type == "product" for r in prod_only)
            
            # Step 7: Test code-specific queries
            code_results = searcher.get_all_records_for_code("0901110000")
            assert len(code_results) >= 3  # 1 reference + 2 product records
            
            code_source_types = {r.source_type for r in code_results}
            assert "reference" in code_source_types
            assert "product" in code_source_types
            
        finally:
            Path(ref_excel).unlink(missing_ok=True)
            Path(prod_excel).unlink(missing_ok=True)
    
    def test_performance_with_large_dataset(self, components):
        """Test performance with larger datasets"""
        # Create larger dataset (100 records)
        codes = [f"090111{i:04d}" for i in range(100)]
        descriptions = [f"Кофе продукт номер {i}" for i in range(100)]
        
        large_data = pd.DataFrame({
            'Code': codes,
            'TextEx': descriptions,
            'SourceID': [f"source_{i}" for i in range(100)]
        })
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            temp_excel = temp_file.name
            large_data.to_excel(temp_excel, index=False)
        
        try:
            # Measure loading performance
            start_time = time.time()
            
            loader = ProductLoader(
                components['db_path'],
                components['normalizer'],
                components['embedder'],
                batch_size=20
            )
            
            loaded_count = loader.load_from_excel(temp_excel, "performance_test")
            load_time = time.time() - start_time
            
            assert loaded_count == 100
            
            # Performance check: should load 100 records in reasonable time
            # This is a basic sanity check, not a strict performance requirement
            assert load_time < 60  # Should complete within 1 minute
            
            # Measure search performance
            searcher = EnhancedSearcher(
                components['db_path'],
                components['normalizer'],
                components['embedder']
            )
            
            search_start = time.time()
            results = searcher.search("кофе продукт", top_k=10)
            search_time = time.time() - search_start
            
            assert len(results) > 0
            # Search should be fast
            assert search_time < 5  # Should complete within 5 seconds
            
        finally:
            Path(temp_excel).unlink(missing_ok=True)


class TestCLIIntegration:
    """Test CLI script integration"""
    
    def test_load_tnved_cli_product_mode(self, components, sample_product_data):
        """Test load_tnved.py CLI with product mode"""
        # Create temporary Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            temp_excel = temp_file.name
            sample_product_data.to_excel(temp_excel, index=False)
        
        try:
            # Test CLI loading in product mode
            cmd = [
                sys.executable, "load_tnved.py",
                temp_excel,
                "--source-type", "product",
                "--source-name", "cli_test_source",
                "--db-path", components['db_path'],
                "--batch-size", "10",
                "--quiet"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Should succeed
            assert result.returncode == 0, f"CLI failed: {result.stderr}"
            
            # Verify data was loaded
            searcher = EnhancedSearcher(
                components['db_path'],
                components['normalizer'],
                components['embedder']
            )
            
            stats = searcher.get_database_stats()
            assert stats['product_records'] == 3
            assert stats['reference_records'] == 0
            
        finally:
            Path(temp_excel).unlink(missing_ok=True)
    
    def test_search_tnved_cli_with_filtering(self, components, sample_product_data):
        """Test search_tnved.py CLI with source filtering"""
        # First load some data
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            temp_excel = temp_file.name
            sample_product_data.to_excel(temp_excel, index=False)
        
        try:
            # Load data first
            loader = ProductLoader(
                components['db_path'],
                components['normalizer'],
                components['embedder']
            )
            loader.load_from_excel(temp_excel, "cli_search_test")
            
            # Test CLI search with product filter
            cmd = [
                sys.executable, "search_tnved.py",
                "кофе",
                "--db-path", components['db_path'],
                "--source-filter", "product",
                "--format", "json",
                "--quiet"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Should succeed
            assert result.returncode == 0, f"CLI search failed: {result.stderr}"
            
            # Parse JSON output
            import json
            results = json.loads(result.stdout)
            
            assert len(results) >= 2  # Should find coffee products
            assert all(r['source_type'] == 'product' for r in results)
            
        finally:
            Path(temp_excel).unlink(missing_ok=True)


class TestErrorHandling:
    """Test error handling in integration scenarios"""
    
    def test_invalid_excel_file_handling(self, components):
        """Test handling of invalid Excel files"""
        # Create invalid Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            temp_excel = temp_file.name
            # Write invalid content
            temp_file.write(b"This is not an Excel file")
        
        try:
            loader = ProductLoader(
                components['db_path'],
                components['normalizer'],
                components['embedder']
            )
            
            with pytest.raises(Exception):  # Should raise DataLoadError or similar
                loader.load_from_excel(temp_excel, "error_test")
                
        finally:
            Path(temp_excel).unlink(missing_ok=True)
    
    def test_empty_database_search(self, components):
        """Test searching in empty database"""
        searcher = EnhancedSearcher(
            components['db_path'],
            components['normalizer'],
            components['embedder']
        )
        
        # Should return empty results, not error
        results = searcher.search("кофе", top_k=5)
        assert results == []
        
        # Stats should show empty database
        stats = searcher.get_database_stats()
        assert stats['total_records'] == 0
    
    def test_malformed_data_handling(self, components):
        """Test handling of malformed data in Excel"""
        # Create Excel with missing required columns
        malformed_data = pd.DataFrame({
            'WrongColumn': ['value1', 'value2'],
            'AnotherWrong': ['value3', 'value4']
        })
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            temp_excel = temp_file.name
            malformed_data.to_excel(temp_excel, index=False)
        
        try:
            loader = ProductLoader(
                components['db_path'],
                components['normalizer'],
                components['embedder']
            )
            
            with pytest.raises(Exception):  # Should raise DataLoadError
                loader.load_from_excel(temp_excel, "malformed_test")
                
        finally:
            Path(temp_excel).unlink(missing_ok=True)


class TestBackwardCompatibility:
    """Test backward compatibility scenarios"""
    
    def test_existing_api_compatibility(self, components, sample_reference_data):
        """Test that existing APIs work without modification"""
        # Load reference data using old TNVEDLoader
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            temp_excel = temp_file.name
            sample_reference_data.to_excel(temp_excel, index=False)
        
        try:
            # Use original TNVEDLoader (should still work)
            loader = TNVEDLoader(
                components['db_path'],
                components['normalizer'],
                components['embedder']
            )
            
            count = loader.load_from_excel(temp_excel)
            assert count == 3
            
            # Use EnhancedSearcher (should work with old data)
            searcher = EnhancedSearcher(
                components['db_path'],
                components['normalizer'],
                components['embedder']
            )
            
            results = searcher.search("кофе", top_k=5)
            assert len(results) >= 1
            
            # Results should have source_type "reference" (auto-assigned)
            coffee_results = [r for r in results if r.code == '0901110000']
            assert len(coffee_results) >= 1
            assert coffee_results[0].source_type == "reference"
            
        finally:
            Path(temp_excel).unlink(missing_ok=True)
    
    def test_mixed_old_new_data(self, components, sample_reference_data, sample_product_data):
        """Test mixing old reference data with new product data"""
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as ref_file:
            ref_excel = ref_file.name
            sample_reference_data.to_excel(ref_excel, index=False)
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as prod_file:
            prod_excel = prod_file.name
            sample_product_data.to_excel(prod_excel, index=False)
        
        try:
            # Load reference data with old loader
            ref_loader = TNVEDLoader(
                components['db_path'],
                components['normalizer'],
                components['embedder']
            )
            ref_count = ref_loader.load_from_excel(ref_excel)
            assert ref_count == 3
            
            # Load product data with new loader
            prod_loader = ProductLoader(
                components['db_path'],
                components['normalizer'],
                components['embedder']
            )
            prod_count = prod_loader.load_from_excel(prod_excel, "compatibility_test")
            assert prod_count == 3
            
            # Search should work across both types
            searcher = EnhancedSearcher(
                components['db_path'],
                components['normalizer'],
                components['embedder']
            )
            
            results = searcher.search("кофе", top_k=10)
            
            # Should find both reference and product records
            source_types = {r.source_type for r in results}
            assert "reference" in source_types
            assert "product" in source_types
            
        finally:
            Path(ref_excel).unlink(missing_ok=True)
            Path(prod_excel).unlink(missing_ok=True)