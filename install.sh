#!/bin/bash
WORKING_DIR=$(pwd)

# Check if the .venv directory exists
if [ ! -d ".venv" ]; then
  echo "Virtual environment not found. Installing dependencies..."
  # Install dependencies using uv
  uv sync
  if [ $? -ne 0 ]; then
    echo "Failed to install dependencies."
    exit 1
  fi
  echo "Dependencies installed successfully."
else
  echo "Virtual environment already exists."
  uv sync
fi

# Check if the LLM model file exists
MODEL_PATH="${WORKING_DIR}/distiller-cm5-python/llm_server/models/qwen2.5-3b-instruct-q4_k_m.gguf"
if [ ! -f "$MODEL_PATH" ]; then
  echo "Model file not found at $MODEL_PATH. Downloading..."
  # Create the directory if it doesn't exist
  mkdir -p "$(dirname "$MODEL_PATH")"
  # Download the model file
  wget -O "$MODEL_PATH" https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf
  if [ $? -ne 0 ]; then
    echo "Failed to download the model file."
    exit 1
  fi
  echo "Model file downloaded successfully."
else
  echo "Model file already exists at $MODEL_PATH."
fi 