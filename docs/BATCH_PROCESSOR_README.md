# Batch Excel Processor

A web-based batch processing system for Excel files containing product descriptions. The system integrates with the existing TNVED embedder to automatically assign TNVED codes to products and provide detailed reasoning for each assignment.

## Features

- **Web Interface**: User-friendly web interface for file upload and progress tracking
- **Batch Processing**: Efficient processing of large Excel files with thousands of products
- **Real-time Progress**: WebSocket-based real-time progress updates
- **Multiple Algorithms**: Support for similarity-based and LLM-based code selection
- **Secure**: Session-based file isolation and automatic cleanup
- **Scalable**: Celery-based background processing with Redis queue

## Quick Start

### Using Docker (Recommended)

1. **Start the services**:
   ```bash
   docker-compose up -d
   ```

2. **Access the web interface**:
   Open http://localhost:8000 in your browser

3. **Default credentials**:
   - Username: `admin`
   - Password: `admin123`

### Manual Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Redis**:
   ```bash
   redis-server
   ```

3. **Start the web server**:
   ```bash
   python start_batch_processor.py web
   ```

4. **Start a worker** (in another terminal):
   ```bash
   python start_batch_processor.py worker
   ```

## Configuration

The system can be configured using:

1. **YAML file**: `batch_processor_config.yaml`
2. **Environment variables**: See configuration documentation
3. **Command line arguments**: For development

### Key Configuration Options

- **Processing**: Chunk size, algorithms, confidence thresholds
- **Security**: Authentication, session timeouts, file limits
- **Performance**: Worker settings, Redis configuration
- **Files**: Storage locations, cleanup policies

## Excel File Format

Your Excel file must contain:

- **Required column**: `Product Detailed Description`
- **Optional column**: `HTS Code` (for selective processing)

The system will add:

- **TNVED_Code**: The assigned TNVED code (with color coding)
- **Selection_Reason**: Explanation for the code selection

### Color Coding

The system automatically applies color coding to TNVED_Code cells based on confidence:

- **🟢 Green** (`Score >= 0.185`): High confidence match - code can be used
- **🔴 Red** (`Score < 0.185`): Low confidence - manual review recommended  
- **⚪ White** (`Score = 1.0`): URL match - highest reliability

See [Color Coding Guide](COLOR_CODING_GUIDE.md) for details.

## Processing Modes

1. **Process All Rows**: Process every row regardless of existing codes
2. **Process Empty Only**: Skip rows that already have HTS codes

## Algorithms

1. **Similarity Top 1**: Select the code with highest similarity score
2. **LLM Reasoning**: Use LLM to analyze top-k results and provide reasoning

## Development

### Setup Development Environment

```bash
pip install -r requirements-dev.txt
```

### Run Tests

```bash
pytest
```

### Code Formatting

```bash
black batch_processor/
isort batch_processor/
```

### Type Checking

```bash
mypy batch_processor/
```

## Architecture

- **FastAPI**: Web application framework
- **Celery**: Background task processing
- **Redis**: Task queue and caching
- **WebSocket**: Real-time progress updates
- **Docker**: Containerized deployment

## Monitoring

- **Logs**: Application logs in `logs/batch_processor.log`
- **Health Checks**: Built-in health check endpoints
- **Metrics**: Processing statistics and performance data

## Security

- **Authentication**: HTTP Basic Auth with configurable users
- **File Isolation**: Session-based temporary directories
- **Path Validation**: Protection against directory traversal
- **Automatic Cleanup**: Scheduled file cleanup after 24 hours

## Support

For issues and questions, please refer to the project documentation or create an issue in the project repository.
