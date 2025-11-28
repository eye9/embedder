# Implementation Plan: ТНВЭД Embedder System

## Overview
Этот план реализации преобразует проект системы ТНВЭД Embedder в серию пошаговых задач для создания системы автоматического подбора кодов ТНВЭД с использованием векторного поиска.

## Tasks

- [x] 1. Set up project structure and dependencies





  - Create directory structure for core modules (models, services, utils)
  - Set up requirements.txt with all necessary dependencies
  - Create configuration management system with config.yaml support
  - Initialize logging configuration
  - _Requirements: 4.1, 4.5_

- [x] 2. Implement core data models and configuration












  - [x] 2.1 Create data models for TNVEDRecord and SearchResult

    - Write dataclasses for TNVEDRecord and SearchResult with proper typing
    - Add validation methods for data integrity
    - _Requirements: 1.1, 2.4_

  - [x] 2.2 Implement Config class with file and environment loading

    - Create Config dataclass with all system parameters
    - Implement from_file() and from_env() class methods
    - Add default value handling and validation
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 2.3 Write property test for configuration parameter respect
    - **Property 10: Configuration Parameter Respect**
    - **Validates: Requirements 4.2, 4.3, 4.4**

  - [ ]* 2.4 Write property test for configuration fallback behavior
    - **Property 11: Configuration Fallback Behavior**
    - **Validates: Requirements 4.5**

- [ ] 3. Implement text normalization pipeline

  - [x] 3.1 Create TextNormalizer class with Natasha integration



    - Implement lowercase conversion functionality
    - Integrate Natasha library for Russian text lemmatization
    - Add whitespace and special character cleanup
    - _Requirements: 1.2, 1.3, 5.2, 5.3_

  - [ ]* 3.2 Write property test for text normalization consistency
    - **Property 2: Text Normalization Consistency**
    - **Validates: Requirements 1.2, 1.3, 5.2, 5.3**

  - [ ]* 3.3 Write unit tests for TextNormalizer edge cases
    - Test empty strings, special characters, mixed case inputs
    - Test Natasha integration with sample Russian words
    - _Requirements: 1.2, 1.3_

- [x] 4. Implement embedding generation system





  - [x] 4.1 Create EmbeddingGenerator class with FRIDA model


    - Initialize ai-forever/FRIDA model from HuggingFace
    - Implement batch processing for efficient embedding generation
    - Add model caching and device management (CPU/GPU)
    - _Requirements: 1.4, 2.2_

  - [ ]* 4.2 Write property test for embedding determinism
    - **Property 3: Embedding Determinism**
    - **Validates: Requirements 1.4, 2.2, 5.4**

  - [ ]* 4.3 Write unit tests for EmbeddingGenerator
    - Test model loading and initialization
    - Test batch processing with different batch sizes
    - Test embedding dimension consistency
    - _Requirements: 1.4_

- [x] 5. Implement ChromaDB management system




  - [x] 5.1 Create ChromaDBManager class


    - Implement persistent ChromaDB client initialization
    - Create collection management with proper configuration
    - Implement batch insertion with upsert functionality
    - Add similarity search with configurable top-k results
    - _Requirements: 1.5, 2.3, 3.1, 3.2_

  - [ ]* 5.2 Write property test for storage round-trip integrity
    - **Property 4: Storage Round-Trip Integrity**
    - **Validates: Requirements 1.5**

  - [ ]* 5.3 Write property test for duplicate code idempotence
    - **Property 8: Duplicate Code Idempotence**
    - **Validates: Requirements 3.2**

  - [ ]* 5.4 Write unit tests for ChromaDBManager
    - Test collection creation and connection
    - Test batch insertion with sample data
    - Test query execution and result format
    - _Requirements: 3.1, 3.2_

- [-] 6. Implement ТНВЭД data loader


  - [x] 6.1 Create TNVEDLoader class



    - Implement Excel file reading with pandas
    - Integrate TextNormalizer and EmbeddingGenerator
    - Add batch processing with progress logging
    - Implement error handling for file operations
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 3.3, 3.4, 3.5_

  - [ ]* 6.2 Write property test for Excel data extraction completeness
    - **Property 1: Excel Data Extraction Completeness**
    - **Validates: Requirements 1.1**

  - [ ]* 6.3 Write property test for load operation count accuracy
    - **Property 9: Load Operation Count Accuracy**
    - **Validates: Requirements 3.5**

  - [ ]* 6.4 Write unit tests for TNVEDLoader
    - Test Excel file reading with sample data
    - Test batch processing and error handling
    - Test progress reporting functionality
    - _Requirements: 1.1, 3.3, 3.4, 3.5_

- [x] 7. Checkpoint - Ensure core loading functionality works



  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement ТНВЭД search system




  - [x] 8.1 Create TNVEDSearcher class


    - Implement query normalization using same pipeline as loader
    - Add embedding generation for search queries
    - Implement similarity search with ChromaDB integration
    - Add result formatting and ranking
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 5.5_

  - [ ]* 8.2 Write property test for search normalization consistency
    - **Property 5: Search Normalization Consistency**
    - **Validates: Requirements 2.1**

  - [ ]* 8.3 Write property test for search result structure and ranking
    - **Property 6: Search Result Structure and Ranking**
    - **Validates: Requirements 2.3, 2.4, 5.5**

  - [ ]* 8.4 Write property test for invalid query handling
    - **Property 7: Invalid Query Handling**
    - **Validates: Requirements 2.5**

  - [ ]* 8.5 Write unit tests for TNVEDSearcher
    - Test query processing and normalization
    - Test search result formatting
    - Test error handling for invalid queries
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 9. Create command-line interface scripts




  - [x] 9.1 Create load_tnved.py script


    - Implement CLI for loading Excel files into ChromaDB
    - Add command-line argument parsing
    - Integrate with Config system for parameter management
    - Add progress reporting and error handling
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 3.5_

  - [x] 9.2 Create search_tnved.py script



    - Implement CLI for searching ТНВЭД codes
    - Add command-line argument parsing for queries and top-k
    - Format and display search results
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ]* 9.3 Write integration tests for CLI scripts
    - Test end-to-end workflow: load data then search
    - Test CLI argument parsing and error handling
    - _Requirements: 1.1, 2.1_

- [x] 10. Checkpoint - Ensure CLI functionality works






  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Implement REST API service
  - [ ] 11.1 Create FastAPI application structure
    - Set up FastAPI app with proper configuration
    - Implement request/response models with Pydantic
    - Add CORS, authentication, and rate limiting middleware
    - _Requirements: API functionality_

  - [ ] 11.2 Implement core API endpoints
    - Create POST /api/v1/search endpoint with SearchRequest/Response models
    - Create POST /api/v1/load endpoint for data loading
    - Create GET /api/v1/code/{code} endpoint for code details
    - Add GET /api/v1/health and GET /api/v1/stats endpoints
    - _Requirements: API functionality_

  - [ ] 11.3 Add API security and monitoring
    - Implement API key authentication
    - Add request rate limiting
    - Implement request/response logging
    - Add error handling with proper HTTP status codes
    - _Requirements: API functionality_

  - [ ]* 11.4 Write API integration tests
    - Test all endpoints with valid and invalid requests
    - Test authentication and rate limiting
    - Test error handling and status codes
    - _Requirements: API functionality_

- [ ] 12. Implement extensibility layer for future integrations
  - [ ] 12.1 Create LLM provider abstraction
    - Implement abstract LLMProvider base class
    - Create OpenAIProvider and LocalLLMProvider implementations
    - Add configuration support for LLM providers
    - _Requirements: Extensibility for LLM integration_

  - [ ] 12.2 Create LangChain compatibility layer
    - Implement TNVEDVectorStore wrapper for LangChain
    - Create TNVEDEmbeddings wrapper for LangChain
    - Implement TNVEDSearchTool and TNVEDCodeDetailsTool for agents
    - _Requirements: Extensibility for LangChain integration_

  - [ ]* 12.3 Write unit tests for extensibility components
    - Test LLM provider abstractions
    - Test LangChain wrapper functionality
    - Test agent tool implementations
    - _Requirements: Extensibility_

- [ ] 13. Create deployment configuration
  - [ ] 13.1 Create Docker configuration
    - Write Dockerfile for containerized deployment
    - Create docker-compose.yml for development setup
    - Add environment variable configuration
    - _Requirements: Deployment support_

  - [ ] 13.2 Create production configuration files
    - Create production config.yaml template
    - Add systemd service file for Linux deployment
    - Create requirements.txt with pinned versions
    - Add deployment documentation
    - _Requirements: Production deployment_

- [ ] 14. Final checkpoint and documentation
  - [ ] 14.1 Create comprehensive README.md
    - Document installation and setup procedures
    - Add usage examples for CLI and API
    - Document configuration options
    - Add troubleshooting guide
    - _Requirements: Documentation_

  - [ ] 14.2 Final testing and validation
    - Run all property-based tests with full iterations
    - Test with real ТНВЭД data file
    - Validate API endpoints with sample requests
    - Performance testing with large datasets
    - _Requirements: All requirements validation_

- [ ] 15. Final checkpoint - Complete system validation
  - Ensure all tests pass, ask the user if questions arise.