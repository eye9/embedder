# Implementation Plan: Batch Excel Processor

## Overview

This implementation plan creates a web-based batch processing system for Excel files containing product descriptions. The system will integrate with the existing TNVED embedder to automatically assign TNVED codes to products and provide detailed reasoning for each assignment. The implementation follows a modular architecture with FastAPI for the web interface, Celery for background processing, and Redis for task management and progress tracking.

## Tasks

- [x] 1. Set up project structure and dependencies
  - Create directory structure for the batch processor
  - Set up requirements.txt with FastAPI, Celery, Redis, and Excel processing dependencies
  - Create configuration management system
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 7.1_

- [ ]* 1.1 Write property test for configuration management
  - **Property 11: Configuration Parameter Respect and Fallback**
  - **Validates: Requirements 4.2, 4.3, 4.4, 4.5**

- [x] 2. Implement core data models and utilities
  - [x] 2.1 Create data models for processing sessions and results
    - Implement ProcessingSession, ProcessingResult, and TaskMetrics dataclasses
    - Add validation and serialization methods
    - _Requirements: 2.1, 2.2, 2.3, 4.1, 4.2, 4.3_

  - [ ]* 2.2 Write property test for data model validation
    - **Property 4: Output File Structure Consistency**
    - **Validates: Requirements 2.3, 2.5, 4.1, 4.2, 4.3**

  - [x] 2.3 Implement file management utilities
    - Create FileManager class for session-based file handling
    - Implement secure file storage and cleanup mechanisms
    - Add path validation to prevent directory traversal
    - _Requirements: 6.1, 6.2, 6.4, 6.5_

  - [ ]* 2.4 Write property test for file security and isolation
    - **Property 8: User Data Isolation**
    - **Property 10: Security Path Validation**
    - **Validates: Requirements 6.1, 6.3, 6.5**

- [x] 3. Implement Excel processing engine
  - [x] 3.1 Create ExcelProcessor class with chunked reading
    - Implement memory-efficient Excel file processing using pandas
    - Add file validation for required columns
    - Implement selective processing modes (all vs empty_only)
    - _Requirements: 2.1, 8.2, 8.3, 8.4_

  - [ ]* 3.2 Write property test for Excel processing
    - **Property 2: File Validation Completeness**
    - **Property 3: Row Processing Completeness**
    - **Validates: Requirements 1.4, 1.5, 2.1, 2.2, 2.4**

  - [x] 3.3 Implement selective processing mode logic
    - Add filtering for rows with existing HTS codes
    - Implement row counting and reporting for selective mode
    - _Requirements: 8.2, 8.3, 8.4, 8.5_

  - [ ]* 3.4 Write property test for selective processing
    - **Property 12: Selective Processing Mode Behavior**
    - **Property 13: Processing Mode Reporting**
    - **Validates: Requirements 8.2, 8.3, 8.4, 8.5**

- [x] 4. Implement TNVED code selection algorithms
  - [x] 4.1 Create abstract TNVEDSelector base class and factory
    - Define interface for code selection algorithms
    - Implement SelectorFactory for algorithm instantiation
    - _Requirements: 3.1, 3.2, 3.5_

  - [x] 4.2 Implement SimilarityTop1Selector
    - Integrate with existing TNVEDSearcher
    - Add confidence threshold handling and quality indicators
    - Format selection reasons with score and source information
    - _Requirements: 3.1, 3.3, 9.1, 9.3_

  - [ ]* 4.3 Write property test for similarity-based selection
    - **Property 5: Algorithm Selection Behavior (similarity_top1)**
    - **Property 14: Quality Assessment Integration (similarity)**
    - **Validates: Requirements 3.1, 3.3, 3.5, 9.1, 9.3**

  - [x] 4.4 Implement LLMReasoningSelector
    - Create LLM integration for analyzing top-k results
    - Implement reasoning explanation generation
    - Add fallback to similarity_top1 when LLM fails
    - _Requirements: 3.2, 3.4, 9.2_

  - [ ]* 4.5 Write property test for LLM-based selection
    - **Property 5: Algorithm Selection Behavior (llm_reasoning)**
    - **Property 14: Quality Assessment Integration (LLM)**
    - **Validates: Requirements 3.2, 3.4, 3.5, 9.2**

- [x] 5. Checkpoint - Core processing components complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement task queue and background processing
  - [x] 6.1 Set up Celery configuration and Redis integration
    - Configure Celery with Redis as broker and result backend
    - Set up task routing and worker configuration
    - _Requirements: 5.1, 5.2, 7.3_

  - [x] 6.2 Implement ProcessingTask worker
    - Create Celery task for background file processing
    - Implement progress tracking and error handling
    - Add chunked processing with real-time updates
    - _Requirements: 2.2, 2.4, 5.2, 5.3, 7.1, 7.2_

  - [ ]* 6.3 Write property test for background processing
    - **Property 7: Progress Tracking Accuracy**
    - **Property 11: Comprehensive Logging**
    - **Validates: Requirements 5.2, 5.3, 5.4, 5.5, 7.1, 7.2, 7.4**

  - [x] 6.4 Implement ProgressTracker for real-time updates
    - Create Redis-based progress tracking system
    - Implement WebSocket notification publishing
    - _Requirements: 5.2, 5.3, 5.4, 5.5_

- [x] 7. Implement web application and API
  - [x] 7.1 Create FastAPI application structure
    - Set up FastAPI app with authentication middleware
    - Implement basic routing and error handling
    - _Requirements: 1.1, 1.2, 1.3_

  - [ ]* 7.2 Write property test for authentication
    - **Property 1: Authentication Behavior Consistency**
    - **Validates: Requirements 1.2, 1.3**

  - [x] 7.3 Implement file upload endpoints
    - Create file upload API with validation
    - Implement task creation and session management
    - Add processing mode selection (all vs empty_only)
    - _Requirements: 1.4, 1.5, 8.1_

  - [x] 7.4 Implement task status and download endpoints
    - Create API endpoints for task status checking
    - Implement file download with security validation
    - _Requirements: 4.4, 5.4, 6.1_

  - [ ]* 7.5 Write property test for file download
    - **Property 6: Download Availability**
    - **Validates: Requirements 4.4, 4.5**

  - [x] 7.6 Implement WebSocket for real-time progress
    - Create WebSocket endpoint for progress updates
    - Implement client-side progress tracking
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 8. Create web user interface
  - [x] 8.1 Create HTML templates and static files
    - Design authentication form and file upload interface
    - Create progress tracking UI with real-time updates
    - Implement download interface for completed files
    - _Requirements: 1.1, 5.1, 8.1_

  - [x] 8.2 Implement client-side JavaScript
    - Add file upload with progress tracking
    - Implement WebSocket connection for real-time updates
    - Create dynamic UI updates for processing status
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] 9. Implement security and cleanup systems
  - [ ] 9.1 Add authentication and session management
    - Implement HTTP Basic Auth with user validation
    - Create session-based access control
    - _Requirements: 1.2, 1.3, 6.1, 6.3_

  - [ ] 9.2 Implement automatic file cleanup
    - Create scheduled cleanup tasks for expired files
    - Implement session-based file isolation
    - _Requirements: 6.2, 6.4_

  - [ ]* 9.3 Write property test for cleanup scheduling
    - **Property 9: Automatic Cleanup Scheduling**
    - **Validates: Requirements 6.2, 6.4**

- [ ] 10. Integration and system testing
  - [ ] 10.1 Create integration with existing TNVED system
    - Connect to existing TNVEDSearcher and ChromaDB
    - Test with real TNVED data and embeddings
    - Verify algorithm performance and accuracy
    - _Requirements: 2.2, 3.1, 3.2_

  - [ ]* 10.2 Write integration tests for end-to-end workflow
    - Test complete upload → process → download workflow
    - Test concurrent user scenarios and data isolation
    - Test error recovery and fallback mechanisms

  - [ ] 10.3 Implement monitoring and logging
    - Add comprehensive logging for all operations
    - Implement metrics collection for performance monitoring
    - Create health check endpoints
    - _Requirements: 7.1, 7.2, 7.4_

- [ ] 11. Deployment preparation
  - [ ] 11.1 Create Docker configuration
    - Write Dockerfile for the application
    - Create docker-compose.yml with Redis and workers
    - Set up environment variable configuration
    - _Requirements: 7.3_

  - [ ] 11.2 Create production configuration
    - Set up production-ready configuration files
    - Implement environment-based settings
    - Add security configurations and rate limiting
    - _Requirements: 6.5, 7.3_

- [ ] 12. Final checkpoint - Complete system testing
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The system integrates with existing TNVED embedder components
- Background processing ensures scalability for large files
- Real-time progress tracking provides excellent user experience