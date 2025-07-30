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

# Check if the Qwen2.5-3B model file exists
QWEN25_MODEL_PATH="${WORKING_DIR}/distiller_cm5_python/llm_server/models/qwen2.5-3b-instruct-q4_k_m.gguf"
if [ ! -f "$QWEN25_MODEL_PATH" ]; then
	echo "Qwen2.5-3B model file not found at $QWEN25_MODEL_PATH. Downloading..."
	# Create the directory if it doesn't exist
	mkdir -p "$(dirname "$QWEN25_MODEL_PATH")"
	# Download the Qwen2.5-3B model file
	wget -O "$QWEN25_MODEL_PATH" https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf
	if [ $? -ne 0 ]; then
		echo "Failed to download the Qwen2.5-3B model file."
		exit 1
	fi
	echo "Qwen2.5-3B model file downloaded successfully."
else
	echo "Qwen2.5-3B model file already exists at $QWEN25_MODEL_PATH."
fi

# Check if the Qwen3 Medical Expert model file exists
QWEN3_MEDICAL_MODEL_PATH="${WORKING_DIR}/distiller_cm5_python/llm_server/models/qwen3-0.6b-medical-expert-q6_k.gguf"
if [ ! -f "$QWEN3_MEDICAL_MODEL_PATH" ]; then
	echo "Qwen3 Medical Expert model file not found at $QWEN3_MEDICAL_MODEL_PATH. Downloading..."
	# Create the directory if it doesn't exist
	mkdir -p "$(dirname "$QWEN3_MEDICAL_MODEL_PATH")"
	# Download the Qwen3 Medical Expert model file
	wget -O "$QWEN3_MEDICAL_MODEL_PATH" https://huggingface.co/mradermacher/Qwen3-0.6B-Medical-Expert-i1-GGUF/resolve/main/Qwen3-0.6B-Medical-Expert.i1-Q6_K.gguf
	if [ $? -ne 0 ]; then
		echo "Failed to download the Qwen3 Medical Expert model file."
		exit 1
	fi
	echo "Qwen3 Medical Expert model file downloaded successfully."
else
	echo "Qwen3 Medical Expert model file already exists at $QWEN3_MEDICAL_MODEL_PATH."
fi

# Check if the MedGemma Medical Expert model file exists
GEMMA_MEDICAL_MODEL_PATH="${WORKING_DIR}/distiller_cm5_python/llm_server/models/medgemma-4b-it-Q4_K_M.gguf"
if [ ! -f "$GEMMA_MEDICAL_MODEL_PATH" ]; then
	echo "MedGemma Medical Expert model file not found at $GEMMA_MEDICAL_MODEL_PATH. Downloading..."
	# Create the directory if it doesn't exist
	mkdir -p "$(dirname "$GEMMA_MEDICAL_MODEL_PATH")"
	# Download the MedGemma Medical Expert model file
	wget -O "$GEMMA_MEDICAL_MODEL_PATH" https://huggingface.co/unsloth/medgemma-4b-it-GGUF/resolve/main/medgemma-4b-it-Q4_K_S.gguf
	if [ $? -ne 0 ]; then
		echo "Failed to download the MedGemma Medical Expert model file."
		exit 1
	fi
	echo "MedGemma Medical Expert model file downloaded successfully."
else
	echo "MedGemma Medical Expert model file already exists at $GEMMA_MEDICAL_MODEL_PATH."
fi
