"""
Background processing task for Excel file processing.

This module implements the Celery task that handles background processing of Excel files,
including progress tracking, error handling, and real-time updates.
"""

import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from celery import Task
from celery.exceptions import Retry

from batch_processor.workers.celery_app import celery_app
from batch_processor.services.excel_processor import ExcelProcessor
from batch_processor.services.file_manager import FileManager
from batch_processor.services.tnved_selector import SelectorFactory
from batch_processor.services.progress_tracker import get_progress_tracker
from batch_processor.services.tnved_integration import get_tnved_integration, TNVEDIntegrationError
from batch_processor.services.monitoring import get_metrics_collector
from batch_processor.services.logging_service import get_structured_logger
from batch_processor.models.result import ProcessingResult
from batch_processor.config.settings import get_config


logger = logging.getLogger(__name__)

# Initialize structured logger
structured_logger = get_structured_logger(__name__)


def process_file_sync(
    session_id: str,
    file_path: str,
    process_mode: str,
    algorithm: str,
    user: str = "anonymous",
    **kwargs
) -> Dict[str, Any]:
    """
    Synchronous version of file processing for when Celery is not available.
    
    Args:
        session_id: Unique session identifier
        file_path: Path to the Excel file to process
        process_mode: "all" or "empty_only"
        algorithm: "similarity_top1" or "llm_reasoning"
        user: Username for logging
        **kwargs: Additional configuration parameters
        
    Returns:
        Dictionary with processing results and metadata
    """
    logger.info(
        f"Starting synchronous processing: session={session_id}, "
        f"file={file_path}, mode={process_mode}, algorithm={algorithm}, user={user}"
    )
    
    # Log processing start
    structured_logger.log_processing_start(
        task_id="sync_" + session_id,
        session_id=session_id,
        user=user,
        filename=Path(file_path).name,
        total_rows=0,  # Will be updated after validation
        algorithm=algorithm,
        process_mode=process_mode
    )
    
    start_time = time.time()
    
    try:
        # Initialize services
        config = get_config()
        excel_processor = ExcelProcessor(chunk_size=config.processing.chunk_size)
        file_manager = FileManager(base_path=config.files.temp_dir)
        
        # Initialize TNVED integration
        try:
            tnved_integration = get_tnved_integration()
            logger.info("TNVED integration initialized for sync processing")
        except Exception as e:
            logger.error(f"Failed to initialize TNVED integration: {e}")
            # Fall back to basic processing without TNVED codes
            return _process_file_without_tnved(
                session_id, file_path, process_mode, excel_processor, file_manager, start_time
            )
        
        # Convert file path to Path object
        file_path_obj = Path(file_path)
        
        # Validate the file
        is_valid, error_msg, total_rows = excel_processor.validate_file(file_path_obj)
        if not is_valid:
            return {
                "status": "failed",
                "error": error_msg,
                "stage": "validation"
            }
        
        logger.info(f"File validation successful: {total_rows} total rows")
        
        # Get file info for processing statistics
        file_info = excel_processor.get_file_info(file_path_obj)
        
        # Calculate rows to process based on mode
        if process_mode == "empty_only":
            rows_to_process = file_info['rows_with_descriptions'] - file_info['rows_with_existing_codes']
        else:
            rows_to_process = file_info['rows_with_descriptions']
        
        logger.info(f"Processing {rows_to_process} rows in {process_mode} mode")
        
        # Create selector
        try:
            selector = tnved_integration.create_selector(algorithm, **kwargs)
        except Exception as e:
            logger.error(f"Failed to create selector: {e}")
            return _process_file_without_tnved(
                session_id, file_path, process_mode, excel_processor, file_manager, start_time
            )
        
        # Process the file with actual TNVED integration
        import pandas as pd
        
        # Read the original file
        df = pd.read_excel(file_path_obj, engine='openpyxl')
        
        # Find description column
        description_col = None
        for col in df.columns:
            if "Product Detailed Description" in str(col):
                description_col = col
                break
        
        if not description_col:
            return {
                "status": "failed",
                "error": "Required column 'Product Detailed Description' not found",
                "stage": "processing"
            }
        
        # Process rows with TNVED codes
        results = []
        processed_count = 0
        error_count = 0
        
        for idx, row in df.iterrows():
            try:
                description = str(row[description_col]).strip()
                if not description or description.lower() in ['nan', 'none', '']:
                    continue
                
                # Check if we should skip this row based on process_mode
                if process_mode == "empty_only":
                    existing_code = str(row.get('HTS Code', '')).strip()
                    if existing_code and existing_code.lower() not in ['nan', 'none', '']:
                        continue
                
                # Process with selector
                result = selector.select_code(description, idx)
                results.append(result)
                processed_count += 1
                
                if not result.is_successful():
                    error_count += 1
                
            except Exception as e:
                logger.error(f"Failed to process row {idx}: {e}")
                error_count += 1
        
        # Add results to dataframe
        df['TNVED_Code'] = ''
        df['Selection_Reason'] = ''
        
        for result in results:
            if result.row_index < len(df):
                df.loc[result.row_index, 'TNVED_Code'] = result.tnved_code or ''
                df.loc[result.row_index, 'Selection_Reason'] = result.selection_reason
        
        # Create session directory and save the processed file
        session_dir = file_manager.create_session_directory(session_id)
        output_path = file_manager.save_processed_file(
            session_id,
            df,
            file_path_obj.name
        )
        
        # Calculate final metrics
        end_time = time.time()
        processing_time = end_time - start_time
        
        logger.info(f"Synchronous processing completed in {processing_time:.2f} seconds")
        
        # Log processing completion
        structured_logger.log_processing_complete(
            task_id="sync_" + session_id,
            session_id=session_id,
            user=user,
            success=True,
            processed_rows=processed_count,
            error_count=error_count,
            duration_ms=processing_time * 1000,
            output_file=str(output_path)
        )
        
        return {
            "status": "completed",
            "output_file": str(output_path),
            "processed_rows": processed_count,
            "total_rows": total_rows,
            "error_count": error_count,
            "processing_time_seconds": processing_time,
            "algorithm_used": algorithm,
            "processing_mode": process_mode,
            "message": f"File processed successfully with {processed_count} TNVED codes assigned"
        }
        
    except Exception as e:
        logger.error(f"Synchronous processing failed: {e}", exc_info=True)
        structured_logger.log_error(e, {
            "session_id": session_id,
            "file_path": file_path,
            "algorithm": algorithm,
            "process_mode": process_mode
        })
        return {
            "status": "failed",
            "error": str(e),
            "stage": "processing"
        }


def _process_file_without_tnved(
    session_id: str,
    file_path: str,
    process_mode: str,
    excel_processor: Any,
    file_manager: Any,
    start_time: float
) -> Dict[str, Any]:
    """
    Fallback processing without TNVED integration.
    
    This creates the output file structure but doesn't assign actual TNVED codes.
    """
    try:
        import pandas as pd
        
        file_path_obj = Path(file_path)
        
        # Read the original file
        df = pd.read_excel(file_path_obj, engine='openpyxl')
        
        # Add the required output columns
        df['TNVED_Code'] = ''
        df['Selection_Reason'] = 'TNVED integration not available - manual assignment required'
        
        # Create session directory and save the processed file
        session_dir = file_manager.create_session_directory(session_id)
        output_path = file_manager.save_processed_file(
            session_id,
            df,
            file_path_obj.name
        )
        
        # Calculate final metrics
        end_time = time.time()
        processing_time = end_time - start_time
        
        return {
            "status": "completed",
            "output_file": str(output_path),
            "processed_rows": 0,
            "total_rows": len(df),
            "error_count": 0,
            "processing_time_seconds": processing_time,
            "algorithm_used": "none",
            "processing_mode": process_mode,
            "message": "File processed without TNVED integration - manual code assignment required"
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": f"Fallback processing failed: {e}",
            "stage": "fallback_processing"
        }


class ProcessingTaskError(Exception):
    """Custom exception for processing task errors."""
    pass


class ProcessingTask(Task):
    """
    Celery task for processing Excel files with TNVED code assignment.
    
    This task handles the complete workflow of:
    1. File validation
    2. Chunked processing with progress updates
    3. TNVED code selection using configured algorithms
    4. Result compilation and file generation
    5. Error handling and recovery
    
    Features:
    - Memory-efficient chunked processing
    - Real-time progress tracking
    - Configurable processing algorithms
    - Comprehensive error handling
    - Automatic retry on transient failures
    """
    
    # Task configuration
    autoretry_for = (ConnectionError, TimeoutError)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    soft_time_limit = 1800  # 30 minutes
    time_limit = 2400       # 40 minutes
    
    def __init__(self):
        """Initialize the processing task."""
        self.excel_processor = None
        self.file_manager = None
        self.tnved_integration = None
        self.progress_tracker = None
        self.metrics_collector = None
        self._config = None
    
    def _initialize_services(self):
        """Initialize required services lazily."""
        if self.excel_processor is None:
            self._config = get_config()
            self.excel_processor = ExcelProcessor(
                chunk_size=self._config.processing.chunk_size
            )
            self.file_manager = FileManager(
                base_path=self._config.files.temp_dir
            )
            self.progress_tracker = get_progress_tracker()
            self.metrics_collector = get_metrics_collector()
            
            # Initialize TNVED integration
            try:
                self.tnved_integration = get_tnved_integration()
                logger.info("TNVED integration initialized successfully")
            except TNVEDIntegrationError as e:
                logger.error(f"Failed to initialize TNVED integration: {e}")
                raise ProcessingTaskError(f"TNVED integration initialization failed: {e}")
            except Exception as e:
                logger.error(f"Unexpected error initializing TNVED integration: {e}")
                raise ProcessingTaskError(f"TNVED integration initialization failed: {e}")
    
    def run(
        self,
        session_id: str,
        file_path: str,
        process_mode: str,
        algorithm: str,
        user: str = "anonymous",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Main task execution method.
        
        Args:
            session_id: Unique session identifier
            file_path: Path to the Excel file to process
            process_mode: "all" or "empty_only"
            algorithm: "similarity_top1" or "llm_reasoning"
            user: Username for logging
            **kwargs: Additional configuration parameters
            
        Returns:
            Dictionary with processing results and metadata
        """
        logger.info(
            f"Starting processing task: session={session_id}, "
            f"file={file_path}, mode={process_mode}, algorithm={algorithm}, user={user}"
        )
        
        # Log processing start
        structured_logger.log_processing_start(
            task_id=self.request.id,
            session_id=session_id,
            user="celery_worker",  # Could be enhanced to track actual user
            filename=Path(file_path).name,
            total_rows=0,  # Will be updated after validation
            algorithm=algorithm,
            process_mode=process_mode
        )
        
        start_time = time.time()
        
        try:
            # Initialize services
            self._initialize_services()
            
            # Convert file path to Path object
            file_path_obj = Path(file_path)
            
            # Update task state to indicate processing has started
            self.progress_tracker.update_progress(
                task_id=self.request.id,
                status='processing',
                progress=0.0,
                processed_rows=0,
                total_rows=0,
                error_count=0,
                stage='validation',
                message='Validating Excel file...'
            )
            
            # Validate the file
            validation_result = self.excel_processor.validate_file(file_path_obj)
            if not validation_result.is_valid:
                return {
                    "status": "failed",
                    "error": validation_result.error_message,
                    "stage": "validation"
                }
            
            total_rows = validation_result.total_rows
            logger.info(f"File validation successful: {total_rows} total rows")
            
            # Get file size for metrics
            file_size = file_path_obj.stat().st_size
            
            # Start metrics tracking
            self.metrics_collector.start_processing_metrics(
                task_id=self.request.id,
                session_id=session_id,
                user="celery_worker",
                file_size_bytes=file_size,
                total_rows=total_rows,
                algorithm=algorithm,
                process_mode=process_mode,
                chunk_size=self._config.processing.chunk_size
            )
            
            # Get processing statistics
            stats = self.excel_processor.get_processing_statistics(
                file_path_obj, process_mode
            )
            rows_to_process = stats['rows_to_process']
            
            # Update progress after validation
            self.progress_tracker.update_progress(
                task_id=self.request.id,
                status='processing',
                progress=0.05,
                processed_rows=0,
                total_rows=rows_to_process,
                error_count=0,
                stage='processing',
                message=f'Processing {rows_to_process} rows...',
                validation_stats=stats
            )
            
            # Create TNVED selector
            selector = self._create_selector(algorithm, **kwargs)
            
            # Process the file in chunks
            results = self._process_file_chunked(
                file_path_obj,
                process_mode,
                selector,
                rows_to_process
            )
            
            # Generate output file
            output_path = self._generate_output_file(
                session_id,
                file_path_obj,
                results,
                process_mode
            )
            
            # Calculate final metrics
            end_time = time.time()
            processing_time = end_time - start_time
            error_count = sum(1 for r in results if not r.is_successful())
            successful_count = len(results) - error_count
            
            # Generate completion summary
            completion_summary = self.excel_processor.generate_completion_summary(
                file_path_obj,
                process_mode,
                len(results),
                error_count
            )
            
            # Final success state
            final_result = {
                "status": "completed",
                "output_file": str(output_path),
                "session_id": session_id,
                "processing_time_seconds": round(processing_time, 2),
                "total_rows": total_rows,
                "processed_rows": len(results),
                "successful_rows": successful_count,
                "error_count": error_count,
                "algorithm": algorithm,
                "process_mode": process_mode,
                "completion_summary": completion_summary
            }
            
            # Complete metrics tracking
            self.metrics_collector.complete_processing_metrics(
                task_id=self.request.id,
                success=True
            )
            
            # Log processing completion
            structured_logger.log_processing_complete(
                task_id=self.request.id,
                session_id=session_id,
                user="celery_worker",
                success=True,
                processed_rows=len(results),
                error_count=error_count,
                duration_ms=processing_time * 1000,
                output_file=str(output_path)
            )
            
            logger.info(
                f"Processing completed successfully: {successful_count}/{len(results)} "
                f"rows processed in {processing_time:.2f}s"
            )
            
            return final_result
            
        except Exception as e:
            error_msg = f"Processing task failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Complete metrics tracking with failure
            if hasattr(self, 'metrics_collector') and self.metrics_collector:
                self.metrics_collector.complete_processing_metrics(
                    task_id=self.request.id,
                    success=False,
                    error_message=error_msg
                )
            
            # Log processing failure
            structured_logger.log_error(e, {
                "task_id": self.request.id,
                "session_id": session_id,
                "file_path": file_path,
                "algorithm": algorithm,
                "process_mode": process_mode
            })
            
            return {
                "status": "failed",
                "error": error_msg,
                "session_id": session_id,
                "processing_time_seconds": time.time() - start_time
            }
    
    def _create_selector(self, algorithm: str, **kwargs) -> Any:
        """
        Create TNVED selector based on algorithm configuration.
        
        Args:
            algorithm: Algorithm name
            **kwargs: Additional selector parameters
            
        Returns:
            Configured TNVEDSelector instance
        """
        try:
            # Get default configuration
            config = self._config or get_config()
            
            # Prepare selector parameters
            selector_params = {
                'confidence_threshold': kwargs.get(
                    'confidence_threshold', 
                    config.processing.confidence_threshold
                ),
                'top_k': kwargs.get('top_k', config.processing.llm_top_k)
            }
            
            # Create selector using integration
            selector = self.tnved_integration.create_selector(algorithm, **selector_params)
            logger.info(f"Created {algorithm} selector")
            
            return selector
            
        except Exception as e:
            error_msg = f"Failed to create selector for algorithm '{algorithm}': {e}"
            logger.error(error_msg)
            raise ProcessingTaskError(error_msg)
    
    def _process_file_chunked(
        self,
        file_path: Path,
        process_mode: str,
        selector: Any,
        total_rows_to_process: int
    ) -> List[ProcessingResult]:
        """
        Process Excel file in chunks with progress tracking.
        
        Args:
            file_path: Path to Excel file
            process_mode: Processing mode
            selector: TNVED selector instance
            total_rows_to_process: Total number of rows that will be processed
            
        Returns:
            List of ProcessingResult objects
        """
        results = []
        processed_count = 0
        error_count = 0
        chunk_number = 0
        
        logger.info(f"Starting chunked processing: {total_rows_to_process} rows to process")
        
        try:
            for chunk, start_row, total_file_rows in self.excel_processor.read_file_chunked(
                file_path, process_mode
            ):
                chunk_number += 1
                chunk_size = len(chunk)
                
                logger.debug(f"Processing chunk {chunk_number}: {chunk_size} rows")
                
                # Process each row in the chunk
                chunk_results = self._process_chunk(
                    chunk, 
                    selector, 
                    start_row,
                    chunk_number
                )
                
                results.extend(chunk_results)
                processed_count += len(chunk_results)
                
                # Count errors in this chunk
                chunk_errors = sum(1 for r in chunk_results if not r.is_successful())
                error_count += chunk_errors
                
                # Calculate progress
                progress = min(processed_count / total_rows_to_process, 1.0) if total_rows_to_process > 0 else 1.0
                
                # Estimate time remaining
                if processed_count > 0:
                    elapsed_time = time.time() - self.request.started_at if hasattr(self.request, 'started_at') else 0
                    if elapsed_time > 0:
                        estimated_total_time = elapsed_time / progress
                        estimated_remaining = max(0, estimated_total_time - elapsed_time)
                    else:
                        estimated_remaining = None
                else:
                    estimated_remaining = None
                
                # Update progress
                self.progress_tracker.update_progress(
                    task_id=self.request.id,
                    status='processing',
                    progress=progress,
                    processed_rows=processed_count,
                    total_rows=total_rows_to_process,
                    error_count=error_count,
                    stage='processing',
                    message=f'Processed {processed_count}/{total_rows_to_process} rows...',
                    estimated_time_remaining=estimated_remaining,
                    chunk_number=chunk_number
                )
                
                logger.debug(
                    f"Chunk {chunk_number} completed: {len(chunk_results)} results, "
                    f"{chunk_errors} errors, {progress:.1%} total progress"
                )
        
        except Exception as e:
            logger.error(f"Chunked processing failed: {e}")
            raise ProcessingTaskError(f"File processing failed: {e}")
        
        logger.info(
            f"Chunked processing completed: {processed_count} rows processed, "
            f"{error_count} errors across {chunk_number} chunks"
        )
        
        return results
    
    def _process_chunk(
        self,
        chunk: Any,  # pandas DataFrame
        selector: Any,
        start_row: int,
        chunk_number: int
    ) -> List[ProcessingResult]:
        """
        Process a single chunk of data.
        
        Args:
            chunk: DataFrame chunk to process
            selector: TNVED selector instance
            start_row: Starting row index in original file
            chunk_number: Chunk number for logging
            
        Returns:
            List of ProcessingResult objects for this chunk
        """
        chunk_results = []
        
        # Find the description column
        description_col = None
        for col in chunk.columns:
            if "Product Detailed Description" in str(col):
                description_col = col
                break
        
        if not description_col:
            logger.error(f"No description column found in chunk {chunk_number}")
            return chunk_results
        
        # Process each row in the chunk
        for idx, row in chunk.iterrows():
            try:
                description = str(row[description_col]).strip()
                if not description or description.lower() in ['nan', 'none', '']:
                    continue
                
                # Calculate actual row index in original file
                actual_row_index = start_row + (idx - chunk.index[0])
                
                # Select TNVED code
                result = selector.select_code(description, actual_row_index)
                chunk_results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to process row {idx} in chunk {chunk_number}: {e}")
                
                # Create error result
                error_result = ProcessingResult(
                    row_index=start_row + (idx - chunk.index[0]),
                    original_description=str(row.get(description_col, '')),
                    tnved_code=None,
                    selection_reason=f"Processing error: {str(e)}",
                    error_message=str(e)
                )
                chunk_results.append(error_result)
        
        logger.debug(f"Chunk {chunk_number} processing completed: {len(chunk_results)} results")
        return chunk_results
    
    def _generate_output_file(
        self,
        session_id: str,
        original_file: Path,
        results: List[ProcessingResult],
        process_mode: str
    ) -> Path:
        """
        Generate the output Excel file with processing results.
        
        Args:
            session_id: Session identifier
            original_file: Path to original Excel file
            results: List of processing results
            process_mode: Processing mode used
            
        Returns:
            Path to generated output file
        """
        try:
            # Convert results to dictionary format for Excel processor
            results_dict = []
            for result in results:
                results_dict.append({
                    'row_index': result.row_index,
                    'tnved_code': result.tnved_code or '',
                    'selection_reason': result.selection_reason
                })
            
            # Generate output filename
            original_name = original_file.stem
            timestamp = int(time.time())
            output_filename = f"{original_name}_processed_{timestamp}.xlsx"
            
            # Get output path from file manager
            output_path = self.file_manager.get_session_directory(session_id) / output_filename
            
            # Write results using Excel processor
            preserve_existing = (process_mode == "empty_only")
            self.excel_processor.write_results(
                original_file,
                results_dict,
                output_path,
                preserve_existing_hts=preserve_existing
            )
            
            logger.info(f"Output file generated: {output_path}")
            return output_path
            
        except Exception as e:
            error_msg = f"Failed to generate output file: {e}"
            logger.error(error_msg)
            raise ProcessingTaskError(error_msg)


# Register the task with Celery
@celery_app.task(bind=True, base=ProcessingTask, name='batch_processor.workers.processing_task.process_excel_file')
def process_excel_file(
    self,
    session_id: str,
    file_path: str,
    process_mode: str = "all",
    algorithm: str = "similarity_top1",
    user: str = "anonymous",
    **kwargs
) -> Dict[str, Any]:
    """
    Celery task entry point for Excel file processing.
    
    Args:
        session_id: Unique session identifier
        file_path: Path to Excel file to process
        process_mode: "all" or "empty_only"
        algorithm: "similarity_top1" or "llm_reasoning"
        user: Username for logging
        **kwargs: Additional configuration parameters
        
    Returns:
        Dictionary with processing results
    """
    return self.run(session_id, file_path, process_mode, algorithm, user, **kwargs)


# Convenience function for task creation
def create_processing_task(
    session_id: str,
    file_path: str,
    process_mode: str = "all",
    algorithm: str = "similarity_top1",
    **kwargs
) -> Any:
    """
    Create and queue a processing task.
    
    Args:
        session_id: Unique session identifier
        file_path: Path to Excel file to process
        process_mode: "all" or "empty_only"
        algorithm: "similarity_top1" or "llm_reasoning"
        **kwargs: Additional configuration parameters
        
    Returns:
        Celery AsyncResult object
    """
    logger.info(
        f"Creating processing task: session={session_id}, "
        f"algorithm={algorithm}, mode={process_mode}"
    )
    
    return process_excel_file.delay(
        session_id=session_id,
        file_path=file_path,
        process_mode=process_mode,
        algorithm=algorithm,
        **kwargs
    )