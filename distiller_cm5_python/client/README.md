# Client

This directory contains the client-side components responsible for interacting with Large Language Models (LLMs) through various backends. The client can be launched via the main project entry point (`main.py` in the project root) and provides a Command-Line Interface (CLI).

> **Note**: MCP (Model Context Protocol) integration is currently under active development. The current client implementation provides direct communication with LLM providers, while advanced MCP features for tool orchestration are being developed.

Refer to the main project `README.md` for instructions on how to run the client.

## Architecture Overview

The client provides a unified interface to interact with different LLM providers through a clean architecture:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Input    │    │   Client Layer   │    │  LLM Backends   │
│      (CLI)      │───▶│   (Interfaces)   │───▶│   (Providers)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
  - Text Input             - MCP Client           - Local Server
  - Commands               - Message Parser       - OpenRouter API  
  - Interactive Chat       - Response Handler     - Custom APIs
```

## Interface

The client provides a single, powerful interaction mode:

### Command-Line Interface (`cli.py`)

A comprehensive text-based interface offering:

**Core Features:**
- **Interactive Chat**: Real-time conversation with LLM backends
- **Streaming Support**: Live response display with typing indicators
- **Command System**: Built-in commands for configuration and control
- **Multi-Provider Support**: Seamless switching between LLM providers
- **Cross-Platform**: Works on any terminal environment
- **Lightweight**: Minimal resource usage and dependencies

**Key Capabilities:**
- Real-time conversation history management
- Streaming response rendering
- Provider failover and error recovery
- Configurable inference parameters
- Session persistence and management

**Usage:**
```bash
# Start CLI (default mode)
python main.py

# CLI with specific options
python main.py --timeout 60 --temperature 0.8

# CLI with provider override
python main.py --provider openrouter
```

## Core Components

### `mid_layer/` - Client Logic Layer

Contains the essential client infrastructure for LLM communication:

#### `mcp_client.py` - Primary LLM Communication
- **`MCPClient` Class**: Central orchestrator for LLM interactions
- **Connection Management**: Handles provider connectivity and failover
- **Message Processing**: Manages conversation history and context
- **Streaming Support**: Real-time response handling
- **Error Recovery**: Robust error handling and reconnection logic

#### `llm_client.py` - Provider Abstractions  
- **`LLMClient` Base Class**: Common interface for all providers
- **Provider Implementations**: 
  - OpenAI-compatible APIs (OpenRouter, local servers)
  - Direct llama.cpp integration
  - Extensible for additional providers
- **Request/Response Handling**: Standardized communication patterns

#### `processors.py` - Message Processing Pipeline
- **`MessageProcessor`**: Conversation history management
- **`ToolProcessor`**: Function calling and tool integration (under development for MCP)
- **Context Management**: Efficient prompt construction and token management

### `llm_infra/` - Infrastructure Management

Local LLM infrastructure utilities:

#### `llama_manager.py` - Local Server Management
- **`LlamaCppServerManager`**: Automated server lifecycle management
- **Health Monitoring**: Server status checking and health validation
- **Process Control**: Clean startup/shutdown with proper resource cleanup
- **Integration**: Seamless integration with main application lifecycle

#### `parsing_utils.py` - Utility Functions
- Response parsing and formatting helpers
- Configuration validation utilities

## Key Features

### Multi-Provider Support
- **Unified Interface**: Single client interface works with any configured provider
- **Hot-Switching**: Change providers without restarting the application
- **Fallback Logic**: Automatic failover between providers
- **Provider-Specific Optimizations**: Tailored handling for different API types

### Advanced CLI Features
- **Rich Text Output**: Formatted response display with syntax highlighting
- **Command History**: Persistent command and conversation history
- **Tab Completion**: Auto-completion for commands and options
- **Error Recovery**: Graceful handling of connection and provider issues

### Configuration Integration
- **Centralized Config**: Full integration with the multi-provider configuration system
- **Environment Overrides**: Runtime configuration via environment variables
- **Profile Support**: Multiple configuration profiles for different use cases

### Performance Optimizations
- **Streaming**: Real-time response display for better user experience
- **Caching**: Intelligent response caching for repeated queries
- **Resource Management**: Efficient memory usage and cleanup
- **Background Processing**: Non-blocking operations for smooth interaction

## Development Architecture

### Modular Design
The client is designed with clear separation of concerns:

- **Presentation Layer**: CLI components handle user interaction and display
- **Business Logic**: Mid-layer handles LLM communication and processing  
- **Infrastructure**: LLM infrastructure management and utilities
- **Configuration**: Centralized configuration management

### Extensibility Points
- **New Providers**: Easy addition of new LLM providers via `LLMClient` interface
- **Custom Processors**: Plugin architecture for message and tool processing (MCP integration under development)
- **Command Extensions**: Modular command system for adding new functionality
- **Output Formatters**: Customizable response formatting and display

## Usage Examples

### Basic CLI Usage
```bash
# Start basic CLI
python main.py

# CLI with custom settings
python main.py --provider openrouter --temperature 0.9

# CLI with environment overrides
export LLM_MODEL_NAME="gpt-4"
export LLM_TEMPERATURE="0.7"
python main.py
```



### Advanced Configuration
```bash
# Custom configuration file
export MCP_CONFIG_FILE="/path/to/custom_config.json"
python main.py --gui

# Provider-specific settings
export LLM_API_KEY="your-api-key"
export LLM_SERVER_URL="https://api.custom-provider.com/v1"
python main.py
```

## Integration Points

### Framework Integration
- **Main Script**: Launched via `main.py` with automatic LLM backend management
- **Configuration System**: Full integration with multi-provider configuration
- **Logging**: Standardized logging via the utils logging system
- **Error Handling**: Consistent error handling with custom exception types

### External Dependencies
- **MCP Protocol**: Model Context Protocol for structured LLM interaction (under development)
- **Various LLM APIs**: OpenAI, OpenRouter, and local server compatibility
- **Standard Libraries**: Built using Python standard library for minimal dependencies

## Troubleshooting

### Common Issues

1. **LLM Connection Issues**
   - Check provider configuration in config file
   - Verify API keys and endpoints
   - Test network connectivity to remote providers

2. **Performance Issues**
   - Monitor resource usage during operation
   - Check network connectivity for remote providers
   - Verify local server health for llama-cpp provider

3. **Configuration Problems**
   - Verify config file syntax and structure
   - Check environment variable settings
   - Test with minimal configuration first

4. **Command/Response Issues**
   - Check streaming settings if responses seem slow
   - Verify model compatibility with provider
   - Test with different inference parameters

### Debug Mode
Enable detailed logging for troubleshooting:
```bash
export LOG_LEVEL="DEBUG"
python main.py
```

For complete setup instructions and configuration details, refer to the main project `README.md`. 