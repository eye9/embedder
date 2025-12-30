# Batch Excel Processor - Web User Interface

## Overview

The Batch Excel Processor now includes a complete web user interface for uploading Excel files, tracking processing progress in real-time, and downloading results with TNVED codes.

## Features

- **Authentication**: Secure login with HTTP Basic Auth
- **File Upload**: Drag-and-drop Excel file upload with validation
- **Processing Options**: Choose between processing all rows or only empty HTS codes
- **Algorithm Selection**: Select between similarity-based and LLM-based code selection
- **Real-time Progress**: Live progress tracking with WebSocket updates
- **Download Results**: Secure download of processed files
- **Responsive Design**: Works on desktop and mobile devices

## Running the Application

### Quick Start (Recommended)

Use the provided startup script that automatically sets the configuration:

**Windows:**
```bash
# Using the batch file
start_batch_web.bat

# Or using Python script
python start_batch_web.py
```

**Linux/Mac:**
```bash
# Set environment variable and start
export BATCH_PROCESSOR_CONFIG=batch_processor_config.yaml
python -m uvicorn batch_processor.web.app:app --host 0.0.0.0 --port 8000 --reload
```

### Manual Start (Without Redis)

If you want to start manually, make sure to set the configuration file:

```bash
# Windows PowerShell
$env:BATCH_PROCESSOR_CONFIG = "batch_processor_config.yaml"
python -m uvicorn batch_processor.web.app:app --host 0.0.0.0 --port 8000 --reload

# Windows CMD
set BATCH_PROCESSOR_CONFIG=batch_processor_config.yaml
python -m uvicorn batch_processor.web.app:app --host 0.0.0.0 --port 8000 --reload

# Linux/Mac
export BATCH_PROCESSOR_CONFIG=batch_processor_config.yaml
python -m uvicorn batch_processor.web.app:app --host 0.0.0.0 --port 8000 --reload
```

**Note**: Without Redis, the following limitations apply:
- No real-time WebSocket updates (polling fallback is used)
- No background task processing (files processed synchronously)
- No progress persistence between server restarts

### Full Setup (With Redis and Celery)

For full functionality including background processing and real-time updates:

1. **Start Redis**:
   ```bash
   # Windows (if Redis is installed)
   redis-server
   
   # Or using Docker
   docker run -d -p 6379:6379 redis:7-alpine
   ```

2. **Start Celery Worker**:
   ```bash
   celery -A batch_processor.workers.celery_app worker --loglevel=info
   ```

3. **Start Web Application**:
   ```bash
   python -m uvicorn batch_processor.web.app:app --host 0.0.0.0 --port 8000 --reload
   ```

### Using Docker Compose

For the easiest setup, use Docker Compose:

```bash
docker-compose up -d
```

## Accessing the Application

1. Open your browser and navigate to: `http://localhost:8000`
2. Log in with your configured credentials (see `config.yaml` for auth settings)
3. Upload an Excel file with a "Product Detailed Description" column
4. Select processing options and algorithm
5. Monitor progress in real-time
6. Download the processed file with TNVED codes

## File Requirements

Your Excel file must contain:
- A column named "Product Detailed Description" with product descriptions
- Optionally, an "HTS Code" column for existing codes (when using "empty_only" mode)

## Configuration

The application uses the existing configuration system. Key settings:

```yaml
# Web server settings
web:
  host: "0.0.0.0"
  port: 8000
  debug: false

# Authentication settings
auth:
  enabled: true
  users:
    admin: "password123"
    user: "userpass"

# Redis settings (optional)
redis:
  url: "redis://localhost:6379/0"

# Processing settings
processing:
  max_file_size_mb: 100
  supported_extensions: [".xlsx", ".xls"]
```

## API Endpoints

The web interface uses these API endpoints:

- `GET /` - Main web interface
- `POST /upload` - Upload and process file
- `POST /upload/validate` - Validate file without processing
- `GET /task/{task_id}/status` - Get task status
- `GET /task/{task_id}/download/file` - Download processed file
- `WebSocket /ws/{task_id}` - Real-time progress updates

## Troubleshooting

### Configuration File Not Found

If you see errors about configuration not being loaded:
```
Configuration file not found
```

**Solution**: Make sure to set the `BATCH_PROCESSOR_CONFIG` environment variable:
```bash
# Windows PowerShell
$env:BATCH_PROCESSOR_CONFIG = "batch_processor_config.yaml"

# Windows CMD  
set BATCH_PROCESSOR_CONFIG=batch_processor_config.yaml

# Linux/Mac
export BATCH_PROCESSOR_CONFIG=batch_processor_config.yaml
```

Or use the provided startup scripts that handle this automatically.

### File Validation Errors

If you get "Validation failed" errors when uploading files:

1. **Check file format**: Ensure your file is .xlsx or .xls
2. **Check required column**: Your file must have a "Product Detailed Description" column
3. **Test validation**: Use the test script to check your file:
   ```bash
   python test_file_validation.py your_file.xlsx
   ```

### Redis Connection Errors

If you see Redis connection errors:
```
ERROR: Error 22 connecting to localhost:6379
```

This is normal if Redis is not running. The application will:
- Log a warning about Redis being unavailable
- Continue running with polling-based progress updates
- Process files synchronously instead of in background

### File Upload Issues

- Ensure your Excel file has the required "Product Detailed Description" column
- Check file size limits in configuration (default: 100MB)
- Verify file format is .xlsx or .xls

### Authentication Issues

- Check your username/password in the configuration
- Ensure `auth.enabled` is set correctly
- Clear browser cache if experiencing login issues

## Development

The web interface consists of:

- **HTML Template**: `batch_processor/templates/index.html`
- **CSS Styles**: `batch_processor/static/css/styles.css`
- **JavaScript**: `batch_processor/static/js/app.js`
- **FastAPI Routes**: `batch_processor/web/app.py`

To modify the interface:
1. Edit the HTML/CSS/JS files
2. Restart the server with `--reload` flag for automatic reloading
3. Clear browser cache to see changes

## Security Notes

- The application uses HTTP Basic Auth for simplicity
- In production, consider using HTTPS and more robust authentication
- File uploads are validated and stored in session-specific directories
- Automatic cleanup removes files after 24 hours
- Path validation prevents directory traversal attacks