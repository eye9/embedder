# ТНВЭД Embedder API

REST API service for semantic search of ТНВЭД codes using vector embeddings.

## Model Information

The API uses the **sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2** model by default, which provides:

- **Multilingual support**: Optimized for Russian and other languages
- **Compact size**: Efficient MiniLM architecture (L12 layers)
- **High performance**: Good balance between speed and accuracy
- **GPU acceleration**: CUDA enabled by default for faster processing

**Default Configuration:**
- Model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Device: `cuda` (falls back to `cpu` if GPU unavailable)
- Embedding dimension: 384

## Features

- 🔍 **Semantic Search**: Find ТНВЭД codes by text description using AI embeddings
- 📊 **Data Loading**: Load ТНВЭД data from Excel files into vector database
- 🔒 **Authentication**: API key-based authentication (optional)
- 🚦 **Rate Limiting**: Configurable request rate limiting
- 🌐 **CORS Support**: Cross-origin resource sharing for web applications
- 📝 **Request Logging**: Comprehensive request/response logging
- 🛡️ **Security Headers**: Built-in security headers for protection
- 📚 **Auto Documentation**: OpenAPI/Swagger documentation

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure the Service

Copy the example configuration:

```bash
cp config_api_example.yaml config.yaml
```

Edit `config.yaml` to match your needs:

```yaml
api:
  enabled: true
  host: "0.0.0.0"
  port: 8000
  auth:
    enabled: false  # Set to true for production
    api_keys:
      - "your-secret-api-key"
```

### 3. Start the Server

```bash
python start_api.py
```

Or using uvicorn directly:

```bash
uvicorn tnved_api:app --host 0.0.0.0 --port 8000
```

### 4. Access the API

- **API Base URL**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs (if auth disabled)
- **Health Check**: http://localhost:8000/api/v1/health

## API Endpoints

### 🔍 Search ТНВЭД Codes

**POST** `/api/v1/search`

Search for ТНВЭД codes by text description.

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "кофейные зерна арабика",
    "top_k": 5
  }'
```

**Response:**
```json
{
  "results": [
    {
      "code": "0901110000",
      "description": "КОФЕ НЕЖАРЕНЫЙ НЕОСВОБОЖДЕННЫЙ ОТ КОФЕИНА",
      "normalized_text": "кофе нежареный неосвобожденный от кофеин",
      "similarity_score": 0.89
    }
  ],
  "query_time_ms": 45.2
}
```

### 📊 Load Data

**POST** `/api/v1/load`

Load ТНВЭД data from Excel file into the database.

```bash
curl -X POST "http://localhost:8000/api/v1/load" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/tnved.xlsx",
    "batch_size": 100
  }'
```

**Response:**
```json
{
  "records_loaded": 13265,
  "load_time_ms": 125000.5
}
```

### 📋 Get Code Details

**GET** `/api/v1/code/{code}`

Get detailed information about a specific ТНВЭД code.

```bash
curl "http://localhost:8000/api/v1/code/0901110000"
```

**Response:**
```json
{
  "code": "0901110000",
  "description": "КОФЕ НЕЖАРЕНЫЙ НЕОСВОБОЖДЕННЫЙ ОТ КОФЕИНА",
  "normalized_text": "кофе нежареный неосвобожденный от кофеин"
}
```

### 🏥 Health Check

**GET** `/api/v1/health`

Check service health and status.

```bash
curl "http://localhost:8000/api/v1/health"
```

**Response:**
```json
{
  "status": "healthy",
  "database_records": 13265,
  "model_loaded": true,
  "version": "1.0.0"
}
```

### 📈 Statistics

**GET** `/api/v1/stats`

Get service usage statistics.

```bash
curl "http://localhost:8000/api/v1/stats"
```

**Response:**
```json
{
  "total_searches": 1523,
  "total_records": 13265,
  "avg_search_time_ms": 42.3,
  "uptime_seconds": 86400,
  "database_stats": {
    "total_records": 13265,
    "collection_name": "tnved"
  }
}
```

## Authentication

When authentication is enabled, include your API key in requests:

### Using Header

```bash
curl -H "X-API-Key: your-api-key" "http://localhost:8000/api/v1/search"
```

### Using Bearer Token

```bash
curl -H "Authorization: Bearer your-api-key" "http://localhost:8000/api/v1/search"
```

## Rate Limiting

The API includes rate limiting to prevent abuse:

- **Default**: 60 requests per minute per IP
- **Configurable**: Set `api.rate_limit.requests_per_minute` in config
- **Headers**: Rate limit info included in response headers

When rate limit is exceeded:
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Maximum 60 requests per minute.",
  "details": {"type": "too_many_requests"}
}
```

## Error Handling

The API returns structured error responses:

```json
{
  "error": "error_type",
  "message": "Human-readable error message",
  "details": {
    "additional": "error details"
  }
}
```

### Common Error Codes

- **400**: Bad Request (invalid input)
- **401**: Unauthorized (invalid API key)
- **404**: Not Found (code not found)
- **422**: Validation Error (invalid request format)
- **429**: Too Many Requests (rate limit exceeded)
- **500**: Internal Server Error

## Configuration

### Environment Variables

You can configure the API using environment variables:

```bash
export TNVED_API_HOST="0.0.0.0"
export TNVED_API_PORT="8000"
export TNVED_API_ENABLED="true"
export TNVED_MODEL_NAME="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
export TNVED_DATABASE_PATH="./chroma_db"
```

### Configuration File

Use `config.yaml` for detailed configuration:

```yaml
api:
  enabled: true
  host: "0.0.0.0"
  port: 8000
  auth:
    enabled: true
    api_keys:
      - "production-api-key-1"
      - "production-api-key-2"
  cors:
    enabled: true
    origins:
      - "https://yourdomain.com"
      - "https://app.yourdomain.com"
  rate_limit:
    requests_per_minute: 100
```

## Deployment

### Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "start_api.py"]
```

Build and run:

```bash
docker build -t tnved-api .
docker run -p 8000:8000 -v $(pwd)/config.yaml:/app/config.yaml tnved-api
```

### Production

For production deployment:

1. **Enable Authentication**:
   ```yaml
   api:
     auth:
       enabled: true
       api_keys: ["secure-random-key"]
   ```

2. **Configure HTTPS**: Use a reverse proxy (nginx, traefik)

3. **Set Resource Limits**: Configure memory and CPU limits

4. **Monitor Logs**: Set up log aggregation and monitoring

5. **Database Backup**: Backup ChromaDB data regularly

## Development

### Running Tests

```bash
python test_api_basic.py
```

### Development Mode

Start with auto-reload:

```bash
uvicorn tnved_api:app --reload --host 0.0.0.0 --port 8000
```

### API Documentation

When authentication is disabled, access interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Troubleshooting

### Common Issues

1. **Model Loading Fails**
   - Check internet connection for model download
   - Verify model name: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
   - Check available disk space (~500MB for model files)

2. **Database Connection Issues**
   - Verify database path exists and is writable
   - Check ChromaDB version compatibility

3. **High Memory Usage**
   - MiniLM-L12-v2 requires ~1.5GB GPU memory or ~2GB system RAM
   - Reduce batch size in configuration if needed
   - Use CPU instead of CUDA if GPU memory limited

4. **Slow Search Performance**
   - Enable CUDA if GPU available (default)
   - Optimize database configuration
   - Consider batch size adjustments for your hardware

### Logs

Check logs for detailed error information:

```bash
tail -f logs/tnved_embedder.log
```

## Support

For issues and questions:

1. Check the logs for error details
2. Verify configuration settings
3. Test with simple requests first
4. Check system resources (memory, disk space)

## License

This API is part of the ТНВЭД Embedder System.
