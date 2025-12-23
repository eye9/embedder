# Implementation Plan: Product Data Support

## Overview

This implementation plan extends the existing ТНВЭД Embedder System to support loading and searching product data with pre-assigned ТНВЭД codes. The approach maintains full backward compatibility while adding new capabilities through enhanced services and CLI options.

## Tasks

- [x] 1. Extend data models for product support
  - Enhance SearchResult model to include source information
  - Create ProductRecord model for product data handling
  - Add source type enumeration for type safety
  - _Requirements: 2.4, 3.5_

- [ ]* 1.1 Write property tests for enhanced data models
  - **Property 7: Search Result Completeness**
  - **Validates: Requirements 2.4, 3.5, 4.5**

- [x] 2. Enhance ChromaDBManager for unified collection support
  - [x] 2.1 Add unique ID generation for product records
    - Implement `_generate_unique_id()` method with code + counter pattern
    - Add ID collision detection and resolution
    - _Requirements: 1.2, 5.2_

  - [ ]* 2.2 Write property test for unique ID generation
    - **Property 2: Unique ID Generation**
    - **Validates: Requirements 1.2, 5.2**

  - [x] 2.3 Add source type metadata support
    - Extend `add_batch()` to handle source_type metadata
    - Add migration logic for existing records
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ]* 2.4 Write property test for source type consistency
    - **Property 3: Source Type Consistency**
    - **Validates: Requirements 1.3, 2.1, 2.2**

  - [x] 2.5 Add source filtering capabilities to query method
    - Extend `query()` method with source_type filter parameter
    - Implement metadata-based filtering logic
    - _Requirements: 3.2, 4.4_

  - [ ]* 2.6 Write property test for source filtering
    - **Property 9: Source Filtering**
    - **Validates: Requirements 3.2, 4.4**

- [x] 3. Create ProductLoader service
  - [x] 3.1 Implement ProductLoader class
    - Create new service extending TNVEDLoader functionality
    - Add source name and source ID handling
    - Implement Excel format compatibility
    - _Requirements: 1.1, 1.4_

  - [ ]* 3.2 Write property test for Excel format compatibility
    - **Property 1: Excel Format Compatibility**
    - **Validates: Requirements 1.1**

  - [x] 3.3 Implement duplicate handling logic
    - Add logic to store multiple products with same code
    - Ensure unique ID generation for duplicates
    - _Requirements: 1.5_

  - [ ]* 3.4 Write property test for duplicate handling
    - **Property 5: Duplicate Handling**
    - **Validates: Requirements 1.5**

  - [x] 3.5 Add source information preservation
    - Store source name and optional source ID in metadata
    - Validate source information completeness
    - _Requirements: 1.4_

  - [ ]* 3.6 Write property test for source information preservation
    - **Property 4: Source Information Preservation**
    - **Validates: Requirements 1.4**

- [x] 4. Create EnhancedSearcher service
  - [x] 4.1 Implement enhanced search functionality
    - Create service that searches across both reference and product records
    - Add result grouping and prioritization logic
    - _Requirements: 3.1, 3.4, 7.2_

  - [ ]* 4.2 Write property test for unfiltered search scope
    - **Property 8: Unfiltered Search Scope**
    - **Validates: Requirements 3.1, 7.2**

  - [x] 4.3 Add result prioritization logic
    - Implement reference record prioritization over product records
    - Maintain similarity score ordering within each type
    - _Requirements: 3.4_

  - [ ]* 4.4 Write property test for result prioritization
    - **Property 10: Result Grouping and Prioritization**
    - **Validates: Requirements 3.4**

  - [x] 4.5 Implement code-specific query functionality
    - Add method to retrieve all records for specific ТНВЭД code
    - Support both reference and product records
    - _Requirements: 5.5_

  - [ ]* 4.6 Write property test for code query completeness
    - **Property 16: Code Query Completeness**
    - **Validates: Requirements 5.5**

- [x] 5. Checkpoint - Core functionality complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement data migration functionality
  - [ ] 6.1 Create DataMigration service
    - Add automatic migration for existing records
    - Implement source_type assignment for legacy data
    - _Requirements: 2.3, 7.5_

  - [ ]* 6.2 Write property test for legacy data migration
    - **Property 6: Legacy Data Migration**
    - **Validates: Requirements 2.3, 7.5**

  - [ ] 6.3 Add referential integrity validation
    - Ensure consistent code values across related records
    - Validate metadata completeness after migration
    - _Requirements: 5.3_

  - [ ]* 6.4 Write property test for referential integrity
    - **Property 14: Referential Integrity**
    - **Validates: Requirements 5.3**

- [-] 7. Enhance CLI scripts
  - [-] 7.1 Extend load_tnved.py with product support
    - Add --source-type parameter for loading mode selection
    - Add --source-name parameter for source identification
    - Maintain backward compatibility with existing parameters
    - _Requirements: 4.1, 4.2, 7.1_

  - [ ]* 7.2 Write property test for CLI parameter propagation
    - **Property 11: CLI Parameter Propagation**
    - **Validates: Requirements 4.1, 4.2**

  - [ ] 7.3 Add enhanced statistics display
    - Show separate counts for reference vs product records
    - Display source information in loading summary
    - _Requirements: 4.3_

  - [ ]* 7.4 Write property test for statistics display
    - **Property 12: Statistics Display**
    - **Validates: Requirements 4.3**

  - [ ] 7.5 Extend search_tnved.py with filtering support
    - Add --source-filter parameter for result filtering
    - Enhance result display to show source information
    - _Requirements: 4.4, 4.5_

  - [ ] 7.6 Add code format validation
    - Implement ТНВЭД code format validation
    - Add validation to both loading and search operations
    - _Requirements: 5.1_

  - [ ]* 7.7 Write property test for code format validation
    - **Property 13: Code Format Validation**
    - **Validates: Requirements 5.1**

- [ ] 8. Configuration system enhancements
  - [ ] 8.1 Extend config.yaml with new options
    - Add source configuration section
    - Add search behavior preferences
    - Add display format options
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ] 8.2 Update Config class to handle new settings
    - Add validation for new configuration options
    - Implement default value handling
    - _Requirements: 6.2_

  - [ ]* 8.3 Write property test for configuration behavior
    - **Property 17: Configuration Behavior**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

- [ ] 9. Backward compatibility validation
  - [ ] 9.1 Test existing API compatibility
    - Verify all existing methods work without modification
    - Ensure response formats remain compatible
    - _Requirements: 7.3, 7.4_

  - [ ]* 9.2 Write property test for backward compatibility
    - **Property 15: Backward Compatibility**
    - **Validates: Requirements 5.4, 7.1, 7.3, 7.4**

  - [ ] 9.3 Create compatibility test suite
    - Test existing scripts and workflows
    - Validate that old commands work unchanged
    - _Requirements: 7.1, 7.4_

- [ ] 10. Integration and final testing
  - [ ] 10.1 Integration testing
    - Test complete workflows: load product data → search → verify results
    - Test mixed data scenarios (reference + product records)
    - Validate performance with large datasets
    - _Requirements: All requirements_

  - [ ]* 10.2 Write integration tests
    - Test end-to-end workflows
    - Test error handling scenarios
    - Test performance characteristics

  - [ ] 10.3 Documentation updates
    - Update README.md with new functionality
    - Add examples for product data loading
    - Document new CLI parameters and configuration options

- [ ] 11. Final checkpoint - Complete system validation
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties using pytest-hypothesis
- Unit tests validate specific examples and edge cases
- Integration tests ensure end-to-end functionality works correctly
- Backward compatibility is maintained throughout all changes