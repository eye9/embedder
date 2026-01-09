# Implementation Plan: URL-Based Code Matching

## Overview

This implementation plan extends the existing batch Excel processor with URL-based TNVED code matching capabilities. The system will first attempt to find codes by matching product URLs from e-commerce sites, then fall back to semantic search when URL matches are not found. The implementation integrates with the existing ChromaDB infrastructure and maintains full backward compatibility.

## Tasks

- [x] 1. Set up URL processing infrastructure
  - Create URL normalization component with shop-specific patterns
  - Set up URL database collection in ChromaDB
  - Implement URL validation and security sanitization
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 12.1, 12.2, 12.3, 12.4, 12.5, 10.1, 10.2, 10.5_

- [x] 1.1 Write property test for URL normalization

  - **Property 3: URL Normalization Consistency**
  - **Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5, 12.1, 12.2, 12.3, 12.4, 12.5**

- [ ]* 1.2 Write property test for security sanitization
  - **Property 12: Security and Sanitization**
  - **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5**

- [x] 2. Implement URL database management
  - [x] 2.1 Create URLDatabaseManager class
    - Implement URL record storage with normalized URLs as keys
    - Add batch loading from Excel files with URL, Code, Description columns
    - Implement duplicate URL handling and record updates
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 2.2 Write property test for URL database operations
    - **Property 4: URL Database Operations**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

  - [x] 2.3 Implement database management operations
    - Add statistics reporting for URL records by source and domain
    - Implement deletion by URL pattern or source name
    - Add export functionality for current URL-code mappings
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 2.4 Write property test for database management
    - **Property 7: Database Management Operations**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**

- [x] 3. Create URL matcher component
  - [x] 3.1 Implement URLMatcher class
    - Create exact URL lookup functionality with normalization
    - Add URL validation and suggestion features
    - Implement timeout handling for URL database queries
    - _Requirements: 3.1, 3.2, 9.1, 9.2, 9.3, 9.4, 9.5_

  - [x] 3.2 Write property test for URL input handling

    - **Property 11: URL Input Handling**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**

- [x] 4. Implement hybrid selector system
  - [x] 4.1 Create HybridSelector class
    - Implement URL-first search strategy with semantic fallback
    - Add configurable priority modes (first, only, disabled)
    - Implement timeout handling and error recovery
    - _Requirements: 3.1, 3.2, 3.3, 3.5, 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 4.2 Write property test for search priority and fallback

    - **Property 5: Search Priority and Fallback Behavior**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.5**

  - [x] 4.3 Write property test for URL priority configuration

    - **Property 9: URL Priority Configuration Behavior**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

  - [x] 4.4 Implement selection reason formatting
    - Create consistent explanation formatting for URL matches
    - Add fallback explanation formatting for semantic search
    - Implement error case explanation formatting
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 4.5 Write property test for selection reason formatting

    - **Property 6: Selection Reason Formatting**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**

- [x] 5. Checkpoint - Core URL processing components complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Enhance Excel processing for URL support
  - [ ] 6.1 Extend ExcelProcessor with URL column detection
    - Add URL column identification from multiple possible names
    - Implement URL extraction from Excel rows
    - Add file validation with URL column presence reporting
    - _Requirements: 1.1, 1.2_

  - [ ]* 6.2 Write property test for Excel URL column detection
    - **Property 1: Excel File URL Column Detection**
    - **Validates: Requirements 1.1, 1.2**

  - [ ] 6.3 Implement hybrid processing logic
    - Add logic to use both description and URL for code selection
    - Implement fallback to semantic-only for rows without URLs
    - Ensure backward compatibility for files without URL columns
    - _Requirements: 1.3, 1.4, 1.5_

  - [ ]* 6.4 Write property test for hybrid selection strategy
    - **Property 2: Hybrid Selection Strategy**
    - **Validates: Requirements 1.3, 1.4, 1.5**

- [ ] 7. Integrate with existing batch processor
  - [ ] 7.1 Update ProcessingTask worker
    - Integrate HybridSelector with existing TNVEDSelector classes
    - Add URL processing to background task workflow
    - Implement URL processing statistics tracking
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 7.2 Write property test for system integration
    - **Property 8: System Integration and Compatibility**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**

  - [ ]* 7.3 Write property test for statistics and monitoring
    - **Property 10: Statistics and Monitoring**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**

  - [ ] 7.4 Update web interface for URL processing
    - Add URL column detection to file upload validation
    - Update progress tracking to include URL processing metrics
    - Add URL processing statistics to completion reports
    - _Requirements: 1.1, 8.3, 8.5_

- [ ] 8. Implement URL data loading tools
  - [ ] 8.1 Create command-line URL data loader
    - Add CLI command for batch loading URL data from Excel
    - Implement source name specification and validation
    - Add progress reporting and error handling for batch loads
    - _Requirements: 2.1, 5.1_

  - [ ] 8.2 Create URL database management CLI
    - Add commands for database statistics and health checks
    - Implement URL record deletion by pattern or source
    - Add export functionality for URL-code mappings
    - _Requirements: 5.2, 5.3, 5.4, 5.5_

- [ ] 9. Add configuration and security features
  - [ ] 9.1 Implement URL processing configuration
    - Add environment variable configuration for URL features
    - Implement runtime configuration validation
    - Add configuration-based feature toggling
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ] 9.2 Implement security and logging enhancements
    - Add URL sanitization for log files with parameter masking
    - Implement parameterized queries for database security
    - Add security violation detection and logging
    - _Requirements: 10.3, 10.4_

- [ ] 10. Testing and validation
  - [ ]* 10.1 Create integration tests for URL processing workflow
    - Test complete URL database loading → Excel processing → URL matching
    - Test hybrid processing with mixed URL and non-URL rows
    - Test different priority configurations and fallback scenarios

  - [ ]* 10.2 Create security and performance tests
    - Test URL validation against malicious patterns
    - Test URL database performance with large datasets
    - Test memory usage during batch URL processing

  - [ ] 10.3 Create URL data validation tools
    - Implement URL format validation utilities
    - Add TNVED code format validation for URL data
    - Create data quality reporting for URL databases
    - _Requirements: 2.5_

- [ ] 11. Documentation and deployment preparation
  - [ ] 11.1 Update configuration documentation
    - Document new environment variables for URL processing
    - Add configuration examples for different deployment scenarios
    - Create troubleshooting guide for URL processing issues

  - [ ] 11.2 Create URL data management documentation
    - Document URL data loading procedures and file formats
    - Add examples of URL normalization for different shops
    - Create best practices guide for URL database maintenance

  - [ ] 11.3 Update Docker configuration
    - Add URL processing environment variables to docker-compose
    - Update volume mounts for URL data storage
    - Add health checks for URL database connectivity

- [ ] 12. Final checkpoint - Complete URL-based code matching system
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The system maintains full backward compatibility with existing batch processor
- URL processing can be disabled via configuration for fallback to semantic-only mode
- Security features ensure safe handling of URLs from untrusted sources