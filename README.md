# Distiller CM5 Python

## How to Switch Model

To switch to a different model, follow these steps:

1. Ensure your model is in GGUF format
   - See: [How to create GGUF model](https://github.com/ggml-org/llama.cpp/discussions/2948)
2. Navigate to the path `/home/distiller/distiller-cm5-python/distiller_cm5_python/llm_server`
3. Add your model to the `./models` directory
4. In `/home/distiller/distiller-cm5-python/distiller_cm5_python/utils/default_config.json`, change:
   ```json
   "model_name": "qwen2.5-3b-instruct-q4_k_m.gguf"
   ```
   to your model file name
5. Reboot or manually trigger to test:
   ```bash
   cd distiller-cm5-python
   ./run.sh
   ```

## UI Pages

- **Prompt/Tool selection page** - Script in `/mcp-server`
- **Voice chat page** - Support scroll chat up and down

## Adding Custom Prompts

To add custom prompts, follow the example at:
`/home/distiller/distiller-cm5-python/distiller_cm5_python/mcp_server/medical_assistant_server.py`

Once you reboot or manually rerun, you can find your customized LLM with customized prompt in the selection page.

**Note:** The longer the prompt, the longer it takes to cache.

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
/home/distiller/distiller-cm5-python/distiller_cm5_python/llm_server/cache
```

This will reset the cache.

### Common Issues

- **Model loading fails:** Check if model file exists and is in correct GGUF format
