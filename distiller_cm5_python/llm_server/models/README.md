# Models Directory

This directory contains the LLM models used by the Distiller CM5 Python application.

## Model Files

Models should be in GGUF format and placed in this directory. The default configuration expects:

- `qwen2.5-3b-instruct-q4_k_m.gguf` - Default Qwen 2.5 3B model

## Download Models

Models can be downloaded using the install script or manually:

```bash
# Using install script (recommended)
./install.sh

# Manual download example
wget -O qwen2.5-3b-instruct-q4_k_m.gguf \
  https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf
```

## Configuration

Update the model path in `distiller_cm5_python/utils/default_config.json` to use different models:

```json
{
  "llm_providers": {
    "llama-cpp": {
      "model_name": "qwen2.5-3b-instruct-q4_k_m.gguf"
    }
  }
}
```

## Storage Requirements

- Models typically range from 2GB to 8GB depending on quantization
- Ensure sufficient disk space before downloading
- Use appropriate quantization levels for your hardware capabilities