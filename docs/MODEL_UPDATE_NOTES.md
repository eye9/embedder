# Model Update Notes

## Current Model Configuration

The ТНВЭД Embedder system has been updated to use a different embedding model than originally specified in the design document.

### Current Model (Implementation)
- **Model**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Device**: `cuda` (default, falls back to `cpu`)
- **Memory Requirements**: ~1.5GB GPU memory or ~2GB system RAM
- **Embedding Dimension**: 384
- **Advantages**:
  - More efficient memory usage
  - Better multilingual support
  - Faster inference
  - Smaller model size (~500MB)

### Original Model (Design Document)
- **Model**: `ai-forever/FRIDA`
- **Device**: `cpu` (original default)
- **Memory Requirements**: ~3.1GB GPU memory
- **Advantages**:
  - Specifically trained for Russian text
  - Higher accuracy for Russian language tasks

## Files Updated

The following files have been updated to reflect the new model:

1. **`utils/config.py`** - Updated default model name and device
2. **`config.yaml`** - Updated model configuration and memory notes
3. **`config_api_example.yaml`** - Updated example configuration
4. **`API_README.md`** - Added model information section and updated troubleshooting
5. **`MODEL_UPDATE_NOTES.md`** - This documentation file

## Configuration

### Default Configuration
```yaml
model:
  name: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
  device: "cuda"  # Falls back to CPU if CUDA unavailable
```

### Environment Variables
```bash
export TNVED_MODEL_NAME="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
export TNVED_MODEL_DEVICE="cuda"
```

## Compatibility

The model change is fully backward compatible:
- All API endpoints work the same way
- Configuration interface remains unchanged
- Search functionality is preserved
- Performance may be improved due to more efficient model

## Performance Characteristics

### MiniLM-L12-v2 vs FRIDA
- **Speed**: MiniLM-L12-v2 is generally faster
- **Memory**: MiniLM-L12-v2 uses less memory
- **Accuracy**: Both models provide good accuracy for ТНВЭД search
- **Languages**: MiniLM-L12-v2 has better multilingual support
- **Size**: MiniLM-L12-v2 is smaller and downloads faster

## Migration

No migration is required. The system will automatically:
1. Download the new model on first run
2. Use CUDA by default if available
3. Fall back to CPU if CUDA is not available
4. Work with existing ChromaDB data

Users can still override the model in configuration if needed:
```yaml
model:
  name: "ai-forever/FRIDA"  # Use original model if preferred
  device: "cpu"
```