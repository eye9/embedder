"""
Enhanced Excel Processor with URL support for hybrid TNVED code matching.

This module extends the existing ExcelProcessor to support URL-based code matching
in combination with semantic search, implementing the hybrid processing logic.
"""

import logging
import pandas as pd
from pathlib import Path
from typing import Iterator, Tuple, Optional, List, Dict, Any

from batch_processor.services.excel_processor import ExcelProcessor
from batch_processor.models.result import ProcessingResult
from services.hybrid_selector import HybridSelector, HybridProcessingResult

logger = logging.getLogger(__name__)


class EnhancedExcelProcessor(ExcelProcessor):
    """
    Enhanced Excel processor with URL column support and hybrid processing logic.
    
    This class extends the base ExcelProcessor to:
    - Detect and extract URLs from Excel files
    - Use hybrid selection (URL-first, semantic fallback)
    - Maintain backward compatibility with files without URL columns
    - Support all existing processing modes
    """
    
    def __init__(self, chunk_size: int = 1000):
        """
        Initialize enhanced Excel processor.
        
        Args:
            chunk_size: Number of rows to process in each chunk for memory efficiency
        """
        super().__init__(chunk_size)
        logger.info(f"EnhancedExcelProcessor initialized with chunk_size={chunk_size}")
    
    def process_file_with_hybrid_selector(
        self,
        file_path: Path,
        hybrid_selector: HybridSelector,
        process_mode: str = "all"
    ) -> Iterator[HybridProcessingResult]:
        """
        Process Excel file using hybrid selector with URL support.
        
        Args:
            file_path: Path to the Excel file
            hybrid_selector: HybridSelector instance for code selection
            process_mode: "all" or "empty_only"
            
        Yields:
            HybridProcessingResult for each processed row
        """
        logger.info(f"Processing file with hybrid selector: {file_path}, mode: {process_mode}")
        
        try:
            # Read file in chunks with URL support
            for chunk_df, chunk_start, total_rows, url_column in self.read_file_chunked_with_urls(file_path, process_mode):
                
                # Find description column
                description_col = next(
                    col for col in chunk_df.columns 
                    if "Product Detailed Description" in str(col)
                )
                
                logger.debug(f"Processing chunk: {len(chunk_df)} rows, URL column: {url_column}")
                
                # Process each row in the chunk
                for idx, row in chunk_df.iterrows():
                    try:
                        # Extract description
                        description = str(row[description_col]).strip() if pd.notna(row[description_col]) else ""
                        
                        if not description:
                            logger.debug(f"Skipping row {idx}: empty description")
                            continue
                        
                        # Extract URL if available
                        url = self.extract_url_from_row(row, url_column)
                        
                        # Use hybrid selector for code selection
                        result = hybrid_selector.select_code_with_url(
                            description=description,
                            url=url,
                            row_index=idx
                        )
                        
                        yield result
                        
                    except Exception as e:
                        logger.error(f"Error processing row {idx}: {e}")
                        # Yield error result
                        yield HybridProcessingResult(
                            row_index=idx,
                            original_description=description if 'description' in locals() else "",
                            original_url=url if 'url' in locals() else None,
                            tnved_code=None,
                            selection_reason=f"Processing error: {str(e)}",
                            match_source="none",
                            error_message=str(e)
                        )
                        
        except Exception as e:
            logger.error(f"Error processing file with hybrid selector: {e}")
            raise
    
    def process_file_with_backward_compatibility(
        self,
        file_path: Path,
        semantic_selector,  # TNVEDSelector
        process_mode: str = "all"
    ) -> Iterator[ProcessingResult]:
        """
        Process Excel file with backward compatibility for files without URL columns.
        
        This method ensures that files without URL columns are processed exactly
        as they were before, using only semantic search.
        
        Args:
            file_path: Path to the Excel file
            semantic_selector: TNVEDSelector instance for semantic search
            process_mode: "all" or "empty_only"
            
        Yields:
            ProcessingResult for each processed row
        """
        logger.info(f"Processing file with backward compatibility: {file_path}, mode: {process_mode}")
        
        # Check if file has URL column
        file_info = self.get_file_info(file_path)
        has_url_column = file_info.get("has_url_column", False)
        
        if has_url_column:
            logger.info("File has URL column but using backward compatibility mode - URLs will be ignored")
        
        # Use original chunked reading method for backward compatibility
        for chunk_df, chunk_start, total_rows in self.read_file_chunked(file_path, process_mode):
            
            # Find description column
            description_col = next(
                col for col in chunk_df.columns 
                if "Product Detailed Description" in str(col)
            )
            
            logger.debug(f"Processing chunk (backward compatibility): {len(chunk_df)} rows")
            
            # Process each row in the chunk
            for idx, row in chunk_df.iterrows():
                try:
                    # Extract description
                    description = str(row[description_col]).strip() if pd.notna(row[description_col]) else ""
                    
                    if not description:
                        logger.debug(f"Skipping row {idx}: empty description")
                        continue
                    
                    # Use semantic selector only (backward compatibility)
                    result = semantic_selector.select_code(
                        description=description,
                        row_index=idx
                    )
                    
                    yield result
                    
                except Exception as e:
                    logger.error(f"Error processing row {idx}: {e}")
                    # Yield error result
                    yield ProcessingResult(
                        row_index=idx,
                        original_description=description if 'description' in locals() else "",
                        tnved_code=None,
                        selection_reason=f"Processing error: {str(e)}",
                        error_message=str(e)
                    )
    
    def determine_processing_strategy(self, file_path: Path) -> Dict[str, Any]:
        """
        Determine the best processing strategy based on file characteristics.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Dictionary with processing strategy recommendations
        """
        logger.info(f"Determining processing strategy for: {file_path}")
        
        try:
            # Get file information
            file_info = self.get_file_info(file_path)
            
            has_url_column = file_info.get("has_url_column", False)
            url_column = file_info.get("url_column")
            rows_with_urls = file_info.get("rows_with_urls", 0)
            total_rows = file_info.get("total_rows", 0)
            
            # Calculate URL coverage
            url_coverage = (rows_with_urls / total_rows) if total_rows > 0 else 0.0
            
            # Determine strategy
            if not has_url_column:
                strategy = "semantic_only"
                reason = "No URL column detected in file"
                recommended_selector = "semantic"
            elif url_coverage == 0.0:
                strategy = "semantic_only"
                reason = "URL column exists but contains no valid URLs"
                recommended_selector = "semantic"
            elif url_coverage < 0.1:
                strategy = "hybrid_fallback_heavy"
                reason = f"Low URL coverage ({url_coverage:.1%}) - expect mostly semantic fallback"
                recommended_selector = "hybrid"
            elif url_coverage < 0.5:
                strategy = "hybrid_balanced"
                reason = f"Moderate URL coverage ({url_coverage:.1%}) - balanced hybrid approach"
                recommended_selector = "hybrid"
            else:
                strategy = "hybrid_url_heavy"
                reason = f"High URL coverage ({url_coverage:.1%}) - expect mostly URL matches"
                recommended_selector = "hybrid"
            
            result = {
                "strategy": strategy,
                "reason": reason,
                "recommended_selector": recommended_selector,
                "file_characteristics": {
                    "has_url_column": has_url_column,
                    "url_column_name": url_column,
                    "total_rows": total_rows,
                    "rows_with_urls": rows_with_urls,
                    "url_coverage": url_coverage
                },
                "processing_recommendations": {
                    "use_hybrid": has_url_column and url_coverage > 0.0,
                    "expect_url_matches": int(rows_with_urls * 0.8),  # Estimate 80% URL match rate
                    "expect_semantic_fallbacks": int(rows_with_urls * 0.2 + (total_rows - rows_with_urls))
                }
            }
            
            logger.info(f"Processing strategy: {strategy} - {reason}")
            return result
            
        except Exception as e:
            logger.error(f"Error determining processing strategy: {e}")
            return {
                "strategy": "semantic_only",
                "reason": f"Error analyzing file: {str(e)}",
                "recommended_selector": "semantic",
                "file_characteristics": {},
                "processing_recommendations": {
                    "use_hybrid": False,
                    "expect_url_matches": 0,
                    "expect_semantic_fallbacks": 0
                }
            }
    
    def generate_hybrid_processing_summary(
        self,
        file_path: Path,
        results: List[HybridProcessingResult],
        process_mode: str
    ) -> Dict[str, Any]:
        """
        Generate processing summary for hybrid processing results.
        
        Args:
            file_path: Path to the original Excel file
            results: List of HybridProcessingResult objects
            process_mode: Processing mode used
            
        Returns:
            Dictionary with detailed processing summary
        """
        logger.info(f"Generating hybrid processing summary for: {file_path}")
        
        try:
            # Basic statistics
            total_processed = len(results)
            successful_results = [r for r in results if r.tnved_code]
            error_results = [r for r in results if r.error_message]
            
            # Match source statistics
            url_matches = [r for r in results if r.match_source == "url"]
            semantic_matches = [r for r in results if r.match_source == "semantic"]
            no_matches = [r for r in results if r.match_source == "none"]
            
            # URL-specific statistics
            results_with_urls = [r for r in results if r.original_url]
            url_match_rate = (len(url_matches) / len(results_with_urls)) if results_with_urls else 0.0
            
            # Performance statistics
            processing_times = [r.processing_time_ms for r in results if r.processing_time_ms]
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0.0
            
            # Get file statistics for context
            file_stats = self.get_processing_statistics(file_path, process_mode)
            
            summary = {
                "file_path": str(file_path),
                "process_mode": process_mode,
                "processing_statistics": {
                    "total_rows_in_file": file_stats.get("total_rows", 0),
                    "rows_processed": total_processed,
                    "successful_processing": len(successful_results),
                    "processing_errors": len(error_results),
                    "success_rate": len(successful_results) / total_processed if total_processed > 0 else 0.0
                },
                "match_source_breakdown": {
                    "url_matches": len(url_matches),
                    "semantic_matches": len(semantic_matches),
                    "no_matches": len(no_matches),
                    "url_match_rate": url_match_rate,
                    "semantic_fallback_rate": len(semantic_matches) / len(results_with_urls) if results_with_urls else 0.0
                },
                "url_processing_stats": {
                    "rows_with_urls": len(results_with_urls),
                    "rows_without_urls": total_processed - len(results_with_urls),
                    "url_coverage": len(results_with_urls) / total_processed if total_processed > 0 else 0.0
                },
                "performance_metrics": {
                    "average_processing_time_ms": avg_processing_time,
                    "total_processing_time_ms": sum(processing_times),
                    "fastest_processing_ms": min(processing_times) if processing_times else 0.0,
                    "slowest_processing_ms": max(processing_times) if processing_times else 0.0
                }
            }
            
            # Generate human-readable message
            if process_mode == "empty_only":
                summary["message"] = (
                    f"Processed {total_processed} rows with empty HTS codes. "
                    f"Found codes for {len(successful_results)} rows "
                    f"({len(url_matches)} by URL, {len(semantic_matches)} by semantic search). "
                    f"URL match rate: {url_match_rate:.1%}. "
                    f"Average processing time: {avg_processing_time:.1f}ms per row."
                )
            else:
                summary["message"] = (
                    f"Processed {total_processed} rows. "
                    f"Found codes for {len(successful_results)} rows "
                    f"({len(url_matches)} by URL, {len(semantic_matches)} by semantic search). "
                    f"URL match rate: {url_match_rate:.1%}. "
                    f"Average processing time: {avg_processing_time:.1f}ms per row."
                )
            
            logger.info(f"Hybrid processing summary: {summary['message']}")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating hybrid processing summary: {e}")
            return {
                "file_path": str(file_path),
                "process_mode": process_mode,
                "error": str(e),
                "message": f"Processing completed with {len(results)} rows processed, but summary generation failed."
            }
    
    def write_hybrid_results(
        self,
        original_file: Path,
        results: List[HybridProcessingResult],
        output_file: Path,
        preserve_existing_hts: bool = True
    ) -> None:
        """
        Write hybrid processing results to Excel file with URL metadata and color coding.
        
        Color coding based on similarity score:
        - Score = 1.0 (URL match): No color (white)
        - Score >= 0.185: Green background
        - Score < 0.185: Red background
        
        Args:
            original_file: Path to the original Excel file
            results: List of HybridProcessingResult objects
            output_file: Path where to save the processed file
            preserve_existing_hts: Whether to preserve existing HTS codes
        """
        logger.info(f"Writing hybrid results to: {output_file}")
        
        try:
            # Convert hybrid results to standard format for compatibility
            standard_results = []
            for result in results:
                standard_result = {
                    'row_index': result.row_index,
                    'tnved_code': result.tnved_code,
                    'selection_reason': result.selection_reason,
                    'confidence_score': result.confidence_score,
                    'processing_time_ms': result.processing_time_ms,
                    'error_message': result.error_message
                }
                standard_results.append(standard_result)
            
            # Use parent class method for writing (includes color coding)
            self.write_results(original_file, standard_results, output_file, preserve_existing_hts)
            
            # Add URL-specific metadata if possible
            try:
                self._add_url_metadata_to_output(output_file, results)
            except Exception as e:
                logger.warning(f"Could not add URL metadata to output file: {e}")
            
            logger.info(f"Successfully wrote {len(results)} hybrid results to {output_file} with color coding")
            
        except Exception as e:
            logger.error(f"Failed to write hybrid results: {e}")
            raise
    
    def _add_url_metadata_to_output(
        self,
        output_file: Path,
        results: List[HybridProcessingResult]
    ) -> None:
        """
        Add URL-specific metadata columns to the output file.
        
        Args:
            output_file: Path to the output Excel file
            results: List of HybridProcessingResult objects
        """
        try:
            # Read the output file
            df = pd.read_excel(output_file, engine='openpyxl')
            
            # Create metadata columns
            df['Match_Source'] = ''
            df['URL_Normalized'] = ''
            df['Shop_Type'] = ''
            df['Product_ID'] = ''
            
            # Fill metadata from results
            for result in results:
                if 0 <= result.row_index < len(df):
                    df.loc[result.row_index, 'Match_Source'] = result.match_source or ''
                    df.loc[result.row_index, 'URL_Normalized'] = result.url_normalized or ''
                    df.loc[result.row_index, 'Shop_Type'] = result.shop_type or ''
                    df.loc[result.row_index, 'Product_ID'] = result.product_id or ''
            
            # Write back to file
            df.to_excel(output_file, index=False, engine='openpyxl')
            
            logger.debug(f"Added URL metadata columns to {output_file}")
            
        except Exception as e:
            logger.warning(f"Could not add URL metadata: {e}")
            # Don't raise - this is optional functionality