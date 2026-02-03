# Implementation Plan: Admin Data Upload Feature

## Overview

This implementation plan breaks down the admin data upload feature into discrete coding tasks. The feature adds a web interface for uploading TNVED codes and URL mappings, reusing existing optimized data processing services. Tasks are organized to build incrementally, with testing integrated throughout.

## Tasks

- [x] 1. Set up project structure and data models
  - Create `batch_processor/web/admin_upload.py` router module
  - Create `batch_processor/web/models/admin_models.py` for Pydantic models
  - Define AdminUploadResponse, UploadSummary, ProgressUpdate, AdminValidationResult models
  - Add configuration section to config.yaml for admin_upload settings
  - _Requirements: 4.1, 7.3, 11.1, 11.5, 12.1_

- [ ] 2. Implement file upload validator
  - [ ] 2.1 Create AdminUploadValidator class in batch_processor/web/validators/upload_validator.py
    - Implement validate_file_format() for extension and size validation
    - Implement validate_source_name() for alphanumeric/hyphen/underscore validation
    - Define constants for required columns, supported formats, max file size
    - _Requirements: 2.1, 2.2, 3.1, 3.2, 6.3, 9.3, 9.4, 11.1, 11.2_
  
  - [ ]* 2.2 Write property test for file format validation
    - **Property 1: File Format Acceptance**
    - **Validates: Requirements 2.1, 3.1**
  
  - [ ] 2.3 Implement validate_tnved_file() method
    - Read file using pandas (support Excel and Parquet)
    - Check for required columns: Code, Description
    - Return ValidationResult with missing columns list
    - _Requirements: 2.2, 6.1, 6.2_
  
  - [ ] 2.4 Implement validate_url_file() method
    - Read file using pandas (support Excel and Parquet)
    - Check for required columns: URL, Code
    - Check for optional column: Description
    - Return ValidationResult with missing columns list
    - _Requirements: 3.2, 6.1, 6.2_
  
  - [ ]* 2.5 Write property test for required column validation
    - **Property 2: Required Column Validation**
    - **Validates: Requirements 2.2, 3.2**
  
  - [ ]* 2.6 Write property test for source name validation
    - **Property 9: Source Name Validation**
    - **Validates: Requirements 9.3, 9.4**
  
  - [ ]* 2.7 Write unit tests for validator edge cases
    - Test empty files
    - Test files with no data rows
    - Test oversized files
    - _Requirements: 6.2, 11.1, 11.2_

- [ ] 3. Implement TNVED upload processor
  - [ ] 3.1 Create TNVEDUploadProcessor class in batch_processor/web/processors/tnved_processor.py
    - Initialize with db_path and batch_size parameters
    - Set up TextNormalizer and EmbeddingGenerator instances
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  
  - [ ] 3.2 Implement _normalize_codes() method
    - Convert codes to strings
    - Remove non-digit characters
    - Zero-pad to 10 digits
    - _Requirements: 2.3_
  
  - [ ]* 3.3 Write property test for TNVED code normalization
    - **Property 3: TNVED Code Normalization**
    - **Validates: Requirements 2.3**
  
  - [ ] 3.4 Implement _deduplicate_codes() method
    - Remove duplicate codes keeping first occurrence
    - Track deduplication count
    - _Requirements: 2.5, 12.5_
  
  - [ ]* 3.5 Write property test for deduplication by key
    - **Property 6: Deduplication by Key** (TNVED part)
    - **Validates: Requirements 2.5, 12.5**
  
  - [ ] 3.6 Implement process_upload() async method
    - Read file into DataFrame
    - Normalize codes
    - Deduplicate codes
    - Process in batches using OptimizedTNVEDLoader
    - Track valid and invalid records
    - Call progress_callback with updates
    - Return UploadSummary with statistics
    - _Requirements: 2.4, 2.6, 5.2, 5.3, 7.2, 7.3, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_
  
  - [ ]* 3.7 Write property test for error resilience
    - **Property 5: Error Resilience** (TNVED part)
    - **Validates: Requirements 2.4, 6.4, 6.6**
  
  - [ ]* 3.8 Write unit tests for TNVED processor
    - Test batch processing with valid data
    - Test handling of invalid codes
    - Test progress callback invocation
    - _Requirements: 2.4, 2.6, 5.2, 7.3_

- [ ] 4. Implement URL upload processor
  - [ ] 4.1 Create URLUploadProcessor class in batch_processor/web/processors/url_processor.py
    - Initialize with chroma_client and batch_size parameters
    - Create OptimizedURLDatabaseManager instance
    - _Requirements: 7.1, 7.3_
  
  - [ ] 4.2 Implement _validate_and_normalize_urls() method
    - Use URLNormalizer service to normalize URLs
    - Collect invalid URLs with error messages
    - Return valid DataFrame and error list
    - _Requirements: 3.3, 3.4_
  
  - [ ]* 4.3 Write property test for URL normalization consistency
    - **Property 4: URL Normalization Consistency**
    - **Validates: Requirements 3.3**
  
  - [ ] 4.4 Implement _validate_codes() method
    - Validate TNVED codes are 10 digits or can be normalized
    - Collect invalid codes with error messages
    - Return valid DataFrame and error list
    - _Requirements: 3.5_
  
  - [ ] 4.5 Implement _deduplicate_urls() method
    - Remove duplicate URLs keeping first occurrence
    - Track deduplication count
    - _Requirements: 3.6, 12.5_
  
  - [ ]* 4.6 Write property test for deduplication by key
    - **Property 6: Deduplication by Key** (URL part)
    - **Validates: Requirements 3.6, 12.5**
  
  - [ ] 4.7 Implement process_upload() async method
    - Read file into DataFrame
    - Validate and normalize URLs
    - Validate codes
    - Deduplicate URLs
    - Process in batches using OptimizedURLDatabaseManager
    - Track valid and invalid records by type
    - Call progress_callback with updates
    - Return UploadSummary with statistics
    - _Requirements: 3.4, 3.5, 3.7, 5.2, 5.3, 7.1, 7.3, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_
  
  - [ ]* 4.8 Write property test for error resilience
    - **Property 5: Error Resilience** (URL part)
    - **Validates: Requirements 3.4, 3.5, 6.4, 6.6**
  
  - [ ]* 4.9 Write unit tests for URL processor
    - Test batch processing with valid data
    - Test handling of invalid URLs
    - Test handling of invalid codes
    - Test progress callback invocation
    - _Requirements: 3.4, 3.5, 3.7, 5.2, 7.3_

- [ ] 5. Implement progress tracker
  - [ ] 5.1 Create UploadProgressTracker class in batch_processor/web/utils/progress_tracker.py
    - Initialize with total_records
    - Track processed_records and start_time
    - _Requirements: 5.1, 5.2_
  
  - [ ] 5.2 Implement update() method
    - Calculate progress percentage
    - Calculate records per second
    - Calculate ETA in seconds
    - Return ProgressUpdate model
    - _Requirements: 5.2, 5.3, 8.5_
  
  - [ ]* 5.3 Write property test for progress updates
    - **Property 13: Progress Updates During Processing**
    - **Validates: Requirements 5.2, 5.3**
  
  - [ ]* 5.4 Write unit tests for progress tracker
    - Test progress calculation accuracy
    - Test ETA calculation
    - Test records per second calculation
    - _Requirements: 5.2, 5.3, 8.5_

- [ ] 6. Implement admin upload router endpoints
  - [ ] 6.1 Create admin_upload.py router with authentication
    - Import FastAPI, UploadFile, Form, Depends
    - Import require_auth from auth.py
    - Create APIRouter with prefix="/admin/upload"
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 4.1_
  
  - [ ] 6.2 Implement GET /admin/upload/ endpoint
    - Serve HTML upload interface
    - Require authentication via require_auth dependency
    - Return HTMLResponse with upload form
    - _Requirements: 1.1, 1.2, 4.1, 4.2_
  
  - [ ] 6.3 Implement POST /admin/upload/tnved endpoint
    - Accept file: UploadFile and source_name: str
    - Require authentication
    - Save file to temporary location
    - Validate file using AdminUploadValidator
    - Process using TNVEDUploadProcessor
    - Return AdminUploadResponse with summary
    - Clean up temporary files
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 4.4, 4.5, 4.6, 9.1, 9.2, 10.5_
  
  - [ ] 6.4 Implement POST /admin/upload/urls endpoint
    - Accept file: UploadFile and source_name: str
    - Require authentication
    - Save file to temporary location
    - Validate file using AdminUploadValidator
    - Process using URLUploadProcessor
    - Return AdminUploadResponse with summary
    - Clean up temporary files
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 4.4, 4.5, 4.6, 9.1, 9.2, 10.5_
  
  - [ ] 6.5 Implement POST /admin/upload/validate endpoint
    - Accept file: UploadFile and upload_type: str
    - Require authentication
    - Validate file without processing
    - Return AdminValidationResult
    - _Requirements: 6.1, 6.2, 6.3_
  
  - [ ]* 6.6 Write property test for upload summary completeness
    - **Property 7: Upload Summary Completeness**
    - **Validates: Requirements 2.6, 3.7, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6**
  
  - [ ]* 6.7 Write property test for source name association
    - **Property 8: Source Name Association**
    - **Validates: Requirements 9.2**
  
  - [ ]* 6.8 Write property test for temporary file cleanup
    - **Property 11: Temporary File Cleanup**
    - **Validates: Requirements 10.5**
  
  - [ ]* 6.9 Write unit tests for router endpoints
    - Test authentication flow (valid/invalid credentials)
    - Test file upload mechanics
    - Test error responses for validation failures
    - _Requirements: 1.1, 1.2, 1.3, 6.1, 6.2, 6.3, 6.4_

- [ ] 7. Create frontend HTML and JavaScript
  - [ ] 7.1 Create admin_upload.html template in batch_processor/templates/
    - Create two upload sections (TNVED and URL)
    - Add source name input fields
    - Add file input fields with accept attributes
    - Add submit buttons
    - Add progress display divs (hidden by default)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_
  
  - [ ] 7.2 Implement JavaScript upload functions
    - Create uploadFile() function for form submission
    - Create pollProgress() function for progress updates
    - Create updateProgressBar() function for UI updates
    - Create showSummary() function for results display
    - Create showError() function for error display
    - _Requirements: 4.6, 5.1, 5.2, 5.3, 5.4, 5.5, 6.4, 6.5, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_
  
  - [ ] 7.3 Add CSS styling for upload interface
    - Style upload sections
    - Style progress bars
    - Style summary display
    - Style error messages
    - _Requirements: 4.1, 4.2, 5.1, 5.4, 5.5_

- [ ] 8. Implement error handling and logging
  - [ ] 8.1 Add error response models and handlers
    - Create error response format with timestamp and details
    - Add HTTPException handlers for validation errors
    - Add handlers for authentication errors (401)
    - Add handlers for file size errors (413)
    - Add handlers for concurrent upload conflicts (409)
    - _Requirements: 1.3, 5.5, 6.1, 6.2, 6.3, 6.4, 6.5, 11.2_
  
  - [ ] 8.2 Implement structured logging for admin uploads
    - Log upload initiation with user, filename, size
    - Log validation failures with details
    - Log processing progress at batch boundaries
    - Log completion with statistics
    - Log errors with full context
    - _Requirements: 2.6, 3.7, 6.4, 6.5, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_
  
  - [ ]* 8.3 Write property test for missing column error reporting
    - **Property 14: Missing Column Error Reporting**
    - **Validates: Requirements 6.1**
  
  - [ ]* 8.4 Write property test for unsupported format error reporting
    - **Property 15: Unsupported Format Error Reporting**
    - **Validates: Requirements 6.3**
  
  - [ ]* 8.5 Write unit tests for error handling
    - Test error response format
    - Test error logging
    - Test cleanup on failure
    - _Requirements: 5.5, 6.4, 10.5_

- [ ] 9. Implement concurrent upload handling
  - [ ] 9.1 Add session-based upload tracking
    - Create upload session manager
    - Track active uploads per user
    - Prevent multiple concurrent uploads per user
    - Return 409 Conflict if upload already in progress
    - _Requirements: 10.1, 10.2, 10.3_
  
  - [ ] 9.2 Implement temporary file management
    - Create user-specific temporary directories
    - Generate unique upload IDs
    - Clean up temporary files after processing
    - Clean up on error or timeout
    - _Requirements: 10.5, 11.5_
  
  - [ ]* 9.3 Write property test for concurrent upload isolation
    - **Property 10: Concurrent Upload Isolation**
    - **Validates: Requirements 10.1, 10.4**
  
  - [ ]* 9.4 Write unit tests for concurrent upload handling
    - Test session isolation
    - Test concurrent upload prevention
    - Test temporary file cleanup
    - _Requirements: 10.1, 10.2, 10.3, 10.5_

- [ ] 10. Implement database integration
  - [ ] 10.1 Add ChromaDB connection management
    - Load ChromaDB configuration from config.yaml
    - Initialize ChromaDB client
    - Verify collection existence (tnved, url_tnved_mapping)
    - _Requirements: 12.1, 12.2_
  
  - [ ] 10.2 Implement database statistics retrieval
    - Query total record count from tnved collection
    - Query total record count from url_tnved_mapping collection
    - Query record counts by source name
    - Include statistics in upload summary
    - _Requirements: 8.6, 9.5_
  
  - [ ]* 10.3 Write property test for additive data storage
    - **Property 12: Additive Data Storage**
    - **Validates: Requirements 12.3, 12.4**
  
  - [ ]* 10.4 Write integration tests for database operations
    - Test TNVED code storage
    - Test URL mapping storage
    - Test deduplication behavior
    - Test source name tracking
    - _Requirements: 9.2, 12.2, 12.3, 12.4, 12.5_

- [ ] 11. Add configuration and deployment setup
  - [ ] 11.1 Update config.yaml with admin_upload section
    - Add enabled flag
    - Add max_file_size_mb setting
    - Add batch_size setting
    - Add temp_dir path
    - Add cleanup_interval_hours
    - Add max_concurrent_uploads_per_user
    - Add supported_formats list
    - Add recommend_parquet_threshold_mb
    - Add large_file_threshold_mb
    - Add upload_timeout_minutes
    - _Requirements: 7.3, 11.1, 11.3, 11.4, 11.5_
  
  - [ ] 11.2 Register admin_upload router in main application
    - Import admin_upload router in main.py or app.py
    - Add router to FastAPI app with app.include_router()
    - Ensure authentication middleware is applied
    - _Requirements: 1.4, 4.1_
  
  - [ ] 11.3 Create deployment documentation
    - Document configuration options
    - Document authentication setup
    - Document file format recommendations
    - Document performance tuning
    - _Requirements: 7.3, 11.1, 11.3, 11.4, 11.5_

- [ ] 12. Checkpoint - Ensure all tests pass
  - Run all unit tests and property tests
  - Verify authentication flow works end-to-end
  - Verify TNVED upload flow works end-to-end
  - Verify URL upload flow works end-to-end
  - Verify error handling and validation
  - Ensure all tests pass, ask the user if questions arise

- [ ] 13. End-to-end integration testing
  - [ ]* 13.1 Write integration test for complete TNVED upload flow
    - Authenticate user
    - Upload TNVED file
    - Verify validation
    - Verify processing
    - Verify database storage
    - Verify summary accuracy
    - _Requirements: 1.2, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 12.2, 12.3_
  
  - [ ]* 13.2 Write integration test for complete URL upload flow
    - Authenticate user
    - Upload URL mapping file
    - Verify validation
    - Verify processing
    - Verify database storage
    - Verify summary accuracy
    - _Requirements: 1.2, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 12.2, 12.4_
  
  - [ ]* 13.3 Write integration test for error recovery flow
    - Upload invalid file
    - Verify error response
    - Verify temporary file cleanup
    - Retry with valid file
    - Verify success
    - _Requirements: 5.5, 6.1, 6.2, 6.3, 6.4, 10.5_
  
  - [ ]* 13.4 Write integration test for concurrent upload flow
    - Start two uploads simultaneously
    - Verify both complete successfully
    - Verify data integrity
    - Verify no corruption
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [ ] 14. Final checkpoint - Verify complete feature
  - Test with real Excel files
  - Test with real Parquet files
  - Test with large files (50+ MB)
  - Verify performance meets requirements (500-2000 records/sec)
  - Verify progress updates are responsive
  - Verify error messages are clear and helpful
  - Ensure all tests pass, ask the user if questions arise

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties using Hypothesis library
- Unit tests validate specific examples and edge cases
- Integration tests verify end-to-end workflows
- The implementation reuses existing services (OptimizedTNVEDLoader, OptimizedURLDatabaseManager)
- All code follows existing FastAPI patterns from batch_processor/web/
- Authentication uses existing auth.py mechanism
- Database uses existing ChromaDB collections
