# Distiller CM5 Python

A comprehensive AI assistant application for the Distiller CM5 platform featuring conversational interface, LLM integration, MCP server support, and hardware interfacing capabilities.

## Installation & Dependencies

This project uses **uv** for fast, modern Python package management with `pyproject.toml`:

### Prerequisites
- Python 3.11+ 
- uv package manager ([Install uv](https://docs.astral.sh/uv/getting-started/installation/))

### Quick Setup
```bash
# Clone the repository
git clone <repository-url>
cd distiller-cm5-python

# Install dependencies using uv
uv sync

# Run the application
uv run python main.py
# or for GUI mode
uv run python main.py --gui
```

### Alternative Installation
```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

## How to Switch Model

To switch to a different model, follow these steps:

1. Ensure your model is in GGUF format
   - See: [How to create GGUF model](https://github.com/ggml-org/llama.cpp/discussions/2948)
2. Navigate to the path `/opt/distiller-cm5-python/distiller_cm5_python/llm_server`
3. Add your model to the `./models` directory
4. In `/opt/distiller-cm5-python/distiller_cm5_python/utils/default_config.json`, change:
   ```json
   "model_name": "qwen2.5-3b-instruct-q4_k_m.gguf"
   ```
   to your model file name
5. Run the application to test:
   ```bash
   cd distiller-cm5-python
   uv run python main.py
   # or using the provided scripts
   ./run.sh
   ```

## UI Pages

- **Prompt/Tool selection page** - Script in `/mcp-server`
- **Voice chat page** - Support scroll chat up and down

## Adding Custom Prompts

To add custom prompts, follow the example at:
`/opt/distiller-cm5-python/distiller_cm5_python/mcp_server/medical_assistant_server.py`

Once you reboot or manually rerun, you can find your customized LLM with customized prompt in the selection page.

**Note:** The longer the prompt, the longer it takes to cache.

## Development

### Development Dependencies
All dependencies are managed through `pyproject.toml`. For development:

```bash
# Install with development dependencies (if any)
uv sync --dev

# Run linting
uv run ruff check distiller_cm5_python/

# Run type checking  
uv run pyright distiller_cm5_python/

# Build distribution
uv build
```

### Project Structure
- `distiller_cm5_python/client/` - UI and client application
- `distiller_cm5_python/llm_server/` - Local LLM server implementation  
- `distiller_cm5_python/mcp_server/` - MCP protocol servers
- `distiller_cm5_python/utils/` - Utilities and configuration

## SDKs and Installation

Please check the [Distiller CM5 SDK repository](https://github.com/Pamir-AI/distiller-cm5-sdk/tree/debian) (side led work pending)

## Services and Triggers

### Available Services

Repository can be found here: [Distiller CM5 Services](https://github.com/Pamir-AI/distiller-cm5-services/tree/debian)

- **WiFi setup services** - The one you needed (default trigger if you long press enter button after boot screen)
- **LLM chat services** - Core chat functionality

## Debug Mode

Enter without spinning up the default LLM chat services, then show SSH info on screen. (WIP)

## Troubleshooting

### Cache Issues

When LLM cache runs into issues, delete the cache folder at:
```
/opt/distiller-cm5-python/distiller_cm5_python/llm_server/cache
```

This will reset the cache.

### Common Issues

- **Model loading fails:** Check if model file exists and is in correct GGUF format
