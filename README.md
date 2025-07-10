# How to Switch Model

To switch to a different model, follow these steps:

1. Ensure your model is in GGUF format
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

## Adding Custom Prompts

To add custom prompts, follow the example at:
`/home/distiller/distiller-cm5-python/distiller_cm5_python/mcp_server/medical_assistant_server.py`

Once you reboot or manually rerun, you can find your customized LLM with customized prompt in the selection page.

**Note:** The longer the prompt, the longer it takes to cache.

## Troubleshooting

When LLM cache runs into issues, delete the cache folder at:
`/home/distiller/distiller-cm5-python/distiller_cm5_python/llm_server/cache`

This will reset the cache. 