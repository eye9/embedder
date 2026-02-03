# Requirements Document

## Introduction

This document specifies requirements for an admin data upload feature that enables administrators to upload TNVED code data and URL mappings through a web interface. The feature replaces manual CLI-based data loading with a user-friendly web interface while maintaining the same data validation and processing capabilities.

## Glossary

- **TNVED_Code**: A 10-digit product classification code used in customs and trade (e.g., "0123456789")
- **URL_Mapping**: An association between a product URL and its corresponding TNVED code
- **Admin_User**: An authenticated user with administrative privileges to upload data
- **Upload_Session**: A single data upload operation tracked from file submission to completion
- **Batch_Processor**: The system component that processes uploaded data in batches
- **ChromaDB**: The vector database used for storing TNVED codes and URL mappings
- **Data_Source**: The origin identifier for uploaded data (e.g., "import_26-01", "supplier_catalog_2024")
- **Upload_File**: An Excel (.xlsx, .xls) or Parquet (.parquet) file containing data to be uploaded
- **Validation_Error**: An error indicating that uploaded data does not meet format or content requirements

## Requirements

### Requirement 1: Admin Authentication and Authorization

**User Story:** As a system administrator, I want to authenticate before uploading data, so that only authorized users can modify the database.

#### Acceptance Criteria

1. WHEN an unauthenticated user attempts to access the upload interface, THE System SHALL redirect them to the authentication page
2. WHEN a user provides valid admin credentials, THE System SHALL grant access to the upload interface
3. WHEN a user provides invalid credentials, THE System SHALL reject access and display an error message
4. THE System SHALL use the existing authentication mechanism from batch_processor/web/auth.py
5. THE System SHALL maintain session state for authenticated admin users

### Requirement 2: TNVED Code Data Upload

**User Story:** As an admin user, I want to upload TNVED codes with descriptions, so that the system has up-to-date product classification data.

#### Acceptance Criteria

1. WHEN an admin uploads a file with TNVED data, THE System SHALL accept Excel (.xlsx, .xls) and Parquet (.parquet) formats
2. THE System SHALL require columns named "Code" and "Description" in the uploaded file
3. WHEN processing TNVED codes, THE System SHALL normalize codes to 10-digit format by zero-padding
4. WHEN a TNVED code is invalid, THE System SHALL record a validation error and continue processing remaining records
5. THE System SHALL remove duplicate TNVED codes keeping the first occurrence
6. WHEN the upload completes, THE System SHALL report the count of successfully loaded records and validation errors

### Requirement 3: URL Mapping Data Upload

**User Story:** As an admin user, I want to upload URL mappings with TNVED codes, so that product URLs can be associated with classification codes.

#### Acceptance Criteria

1. WHEN an admin uploads a file with URL mapping data, THE System SHALL accept Excel (.xlsx, .xls) and Parquet (.parquet) formats
2. THE System SHALL require columns named "URL", "Code", and optionally "Description" in the uploaded file
3. WHEN processing URL mappings, THE System SHALL normalize URLs using the URLNormalizer service
4. WHEN a URL is invalid, THE System SHALL record a validation error and continue processing remaining records
5. WHEN a TNVED code in a URL mapping is invalid, THE System SHALL record a validation error and continue processing
6. THE System SHALL remove duplicate URLs keeping the first occurrence
7. WHEN the upload completes, THE System SHALL report counts of successfully loaded records, invalid URLs, and invalid codes

### Requirement 4: File Upload Interface

**User Story:** As an admin user, I want a clear upload interface, so that I can easily submit data files.

#### Acceptance Criteria

1. THE System SHALL provide a web page at /admin/upload for data uploads
2. THE System SHALL display two upload sections: one for TNVED codes and one for URL mappings
3. WHEN displaying the upload form, THE System SHALL show accepted file formats (.xlsx, .xls, .parquet)
4. THE System SHALL provide a text input field for the data source name
5. THE System SHALL provide a file selection button for choosing the upload file
6. THE System SHALL provide a submit button to initiate the upload
7. WHEN a file is selected, THE System SHALL display the selected filename

### Requirement 5: Upload Progress Tracking

**User Story:** As an admin user, I want to see upload progress, so that I know the system is processing my data.

#### Acceptance Criteria

1. WHEN an upload begins, THE System SHALL display a progress indicator
2. WHILE processing data, THE System SHALL update progress showing percentage completed
3. WHILE processing data, THE System SHALL display the current batch being processed
4. WHEN processing completes, THE System SHALL display a completion message
5. IF an error occurs during processing, THEN THE System SHALL display an error message with details

### Requirement 6: Upload Validation and Error Reporting

**User Story:** As an admin user, I want detailed validation feedback, so that I can correct data issues.

#### Acceptance Criteria

1. WHEN an admin submits a file without required columns, THE System SHALL reject the upload and list missing columns
2. WHEN an admin submits an empty file, THE System SHALL reject the upload with an appropriate message
3. WHEN an admin submits a file with an unsupported format, THE System SHALL reject the upload and list supported formats
4. WHEN validation errors occur during processing, THE System SHALL collect all errors and display them after processing
5. THE System SHALL display validation error counts by type (invalid URLs, invalid codes, missing data)
6. WHEN the upload completes with errors, THE System SHALL still save valid records and report what was saved

### Requirement 7: Batch Processing Configuration

**User Story:** As an admin user, I want uploads to process efficiently, so that large files complete in reasonable time.

#### Acceptance Criteria

1. THE System SHALL use the existing OptimizedURLDatabaseManager for URL mapping uploads
2. THE System SHALL use the existing OptimizedTNVEDLoader for TNVED code uploads
3. THE System SHALL process data in batches of 5000 records by default
4. THE System SHALL use GPU acceleration when available for embedding generation
5. WHEN processing large files, THE System SHALL maintain responsive progress updates

### Requirement 8: Upload Results Summary

**User Story:** As an admin user, I want a summary after upload, so that I can verify the operation succeeded.

#### Acceptance Criteria

1. WHEN an upload completes, THE System SHALL display total records processed
2. WHEN an upload completes, THE System SHALL display successfully loaded record count
3. WHEN an upload completes, THE System SHALL display validation error counts by type
4. WHEN an upload completes, THE System SHALL display processing time in seconds and minutes
5. WHEN an upload completes, THE System SHALL display processing speed in records per second
6. WHEN an upload completes, THE System SHALL display the current total record count in the database

### Requirement 9: Data Source Tracking

**User Story:** As an admin user, I want to specify the data source, so that uploaded data can be traced to its origin.

#### Acceptance Criteria

1. THE System SHALL require a source name for each upload
2. WHEN storing records, THE System SHALL associate each record with the provided source name
3. THE System SHALL validate that source names contain only alphanumeric characters, hyphens, and underscores
4. WHEN a source name is invalid, THE System SHALL reject the upload with a validation message
5. THE System SHALL display statistics showing record counts by source name

### Requirement 10: Concurrent Upload Handling

**User Story:** As a system administrator, I want the system to handle concurrent uploads safely, so that multiple admins can work simultaneously.

#### Acceptance Criteria

1. WHEN multiple admins upload data simultaneously, THE System SHALL process each upload independently
2. THE System SHALL use session-based tracking to isolate upload operations by user
3. WHEN an upload is in progress, THE System SHALL allow the same user to view progress but not start another upload
4. THE System SHALL ensure database writes from concurrent uploads do not corrupt data
5. WHEN an upload completes, THE System SHALL clean up session-specific temporary files

### Requirement 11: File Size and Performance Limits

**User Story:** As a system administrator, I want reasonable file size limits, so that the system remains responsive.

#### Acceptance Criteria

1. THE System SHALL accept files up to 100 MB in size
2. WHEN a file exceeds the size limit, THE System SHALL reject the upload with a clear message
3. THE System SHALL recommend Parquet format for files larger than 10 MB
4. WHEN processing files larger than 50 MB, THE System SHALL display an estimated completion time
5. THE System SHALL maintain a maximum upload timeout of 30 minutes

### Requirement 12: Database Integration

**User Story:** As a system administrator, I want uploads to integrate with existing data, so that the database remains consistent.

#### Acceptance Criteria

1. THE System SHALL use the existing ChromaDB instance configured in config.yaml
2. THE System SHALL use the existing collection names ("tnved" for codes, "url_tnved_mapping" for URLs)
3. WHEN uploading TNVED codes, THE System SHALL add to existing codes without removing previous data
4. WHEN uploading URL mappings, THE System SHALL add to existing mappings without removing previous data
5. THE System SHALL apply the same deduplication logic as the CLI loaders (by URL for mappings, by code for TNVED)
