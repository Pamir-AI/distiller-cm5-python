# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The Distiller CM5 Python project is a comprehensive AI assistant application for the Distiller CM5 platform. It features a conversational interface that supports both command-line and GUI modes, LLM integration, MCP (Model Context Protocol) server support, and hardware interfacing capabilities including audio, display, and LED control.

## Architecture

### Core Components

**Client Layer (`distiller_cm5_python/client/`):**
- `cli.py`: Main CLI interface and argument parsing
- `mid_layer/`: Core business logic including LLM client, MCP client, and processors
- `ui/`: Qt-based GUI application with QML components for voice assistant interface
- `llm_infra/`: LLM server management and parsing utilities

**Server Layer:**
- `llm_server/`: Local LLM server implementation using llama-cpp-python
- `mcp_server/`: MCP protocol servers for various tools and assistants

**Utilities (`distiller_cm5_python/utils/`):**
- Configuration management, logging, hardware interfaces (UART, server utilities)
- Default configuration in `default_config.json`
- Battery and specialized hardware config in TOML format

**Hardware Integration:**
- Audio processing using faster_whisper and pyaudio
- E-ink display control via distiller-cm5-sdk
- LED control via GPIO  
- Input monitoring and device interfacing

### Key Design Patterns

**Dual Interface Architecture:**
- CLI mode: Direct command-line interaction
- GUI mode: Qt/QML-based voice assistant interface with visual feedback

**Modular LLM Integration:**
- Support for local llama-cpp servers and remote providers (OpenRouter)
- Automatic server lifecycle management
- Configurable model parameters and streaming

**Hardware Abstraction:**
- Clean separation between software logic and hardware interfaces
- Graceful degradation when hardware is unavailable
- UART-based power management signaling

## Development Commands

### Environment Setup
```bash
# Install dependencies and setup virtual environment
./install.sh

# Alternative: Quick setup with uv
uv sync

# Note: For full hardware functionality, also install distiller-cm5-sdk
# See: https://github.com/Pamir-AI/distiller-cm5-sdk/tree/debian
```

### Running the Application
```bash
# CLI mode (default)
./run.sh

# GUI mode
./run.sh --gui
# or
./spin_up.sh

# Direct Python execution
python main.py [--gui]
```

### Model Management
```bash
# Download required LLM model (handled by install.sh)
wget -O distiller_cm5_python/llm_server/models/qwen2.5-3b-instruct-q4_k_m.gguf \
  https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf
```

### Testing and Development
```bash
# Test hardware components individually
python distiller_cm5_python/client/ui/bridge/EinkDriver.py
python distiller_cm5_python/utils/uart_utils.py

# Build Debian package
./build-deb.sh

# Clean build artifacts
./build-deb.sh clean

# Lint code (ruff configured in pyproject.toml)
uv run ruff check distiller_cm5_python/
# Alternative if not using uv
ruff check distiller_cm5_python/

# Type checking (if pyright is available)
uv run pyright distiller_cm5_python/

# Build distribution package
uv build
```

## Configuration

### Configuration Format
The application uses **JSON configuration files** for primary configuration, with some specialized components using TOML format. The main configuration is managed through JSON for compatibility.

### Primary Configuration
Configuration is managed through `distiller_cm5_python/utils/default_config.json`:

**LLM Providers:**
- `llama-cpp`: Local server configuration with model path and parameters
- `openrouter`: Remote API configuration
- Switch providers via `application.active_llm_provider` field

**Key Settings:**
- Model parameters: temperature, top_p, max_tokens, context length
- Logging configuration and file output
- MCP server script paths
- Display settings (dark mode support)

### Configuration Files

**Main Application Config:** `distiller_cm5_python/utils/default_config.json`
```json
{
  "llm_providers": {
    "llama-cpp": {
      "server_url": "http://127.0.0.1:8000",
      "model_name": "qwen2.5-3b-instruct-q4_k_m.gguf",
      "temperature": 0.7,
      "n_ctx": 32768,
      "max_tokens": 4096
    }
  },
  "active_llm_provider": "llama-cpp",
  "logging": {
    "level": "INFO",
    "file_enabled": false
  }
}
```

**Battery Configuration:** `distiller_cm5_python/utils/battery_config.toml`
```toml
[battery.thresholds]
critical = 1              # 1% - trigger shutdown
low = 15                  # 15% - show warning
warning = 25              # 25% - show low battery notice
temperature_warning = 55.0 # 55°C - show temperature warning
charging_current = 0.01    # 0.01A - minimum current to consider charging

[battery.colors]
critical = "#FF0000"      # Red - critical
low = "#FF8800"           # Orange - low
warning = "#FFAA00"       # Yellow - warning
good = "#00AA00"          # Green - good
```

**Display Configuration:** Battery and display settings are managed through TOML configuration files for specialized hardware components.

### Model Configuration
To switch models:
1. Update `model_name` in the `llm_providers.llama-cpp` section of `default_config.json`
2. Ensure model file exists in `distiller_cm5_python/llm_server/models/`
3. Model must be in GGUF format

### Battery Configuration
Battery monitoring behavior can be customized in `battery_config.toml`:
- **Thresholds**: Critical (1%), low (15%), warning (25%), temperature warning (55°C)
- **Colors**: UI color scheme for different battery states
- **Icons**: Battery icon names for charging/discharging states
- **Monitoring intervals**: Update frequency for battery status checks

### Hardware Configuration
Hardware components are configured through TOML files:
- **Battery**: Hardware paths and monitoring settings in `battery_config.toml`
- **Display**: E-ink display settings, refresh rates, and UI preferences in `display_config.toml`
- **GPIO**: Pin assignments for LED control
- **UART**: Device configuration for power management
- **Audio**: Device selection and parameters

### Configuration Loading
The application uses a centralized configuration loading system:
- **Automatic fallbacks**: If config files are missing, defaults are used
- **Environment overrides**: Environment variables can override config values
- **Mixed format support**: JSON for primary config, TOML for specialized hardware components

## Common Development Tasks

### Adding New MCP Servers
1. Create server script in `distiller_cm5_python/mcp_server/`
2. Follow the pattern of existing servers (e.g., `medical_assistant_server.py`)
3. Update configuration to reference new server script
4. Register available tools/prompts in the server

### Extending Hardware Support
1. Add new hardware modules to `distiller_cm5_python/client/ui/bridge/`
2. Implement clean initialization and cleanup patterns
3. Add error handling for hardware unavailability
4. Update requirements.txt for new hardware dependencies

### GUI Component Development
1. QML components located in `distiller_cm5_python/client/ui/Components/`
2. Bridge classes connect QML to Python logic
3. Follow existing patterns for event handling and state management
4. Use AppInfoManager for application state coordination

### LLM Integration Changes
1. Core LLM client logic in `distiller_cm5_python/client/mid_layer/llm_client.py`
2. Server management in `distiller_cm5_python/client/llm_infra/llama_manager.py`
3. Support both streaming and non-streaming responses
4. Handle timeout and error scenarios gracefully

## Dependencies and Platform Support

### Core Dependencies
- `fastapi`, `uvicorn`: Web server framework for LLM server
- `llama-cpp-python`: Local LLM inference
- `mcp`: Model Context Protocol support
- `PyQt6`, `qasync`: GUI framework
- `faster_whisper`: Speech-to-text processing
- `pyaudio`: Audio input/output

### Hardware Dependencies
- `evdev`: Input event handling
- `numba`: Performance optimization

### Platform Requirements
- **Target**: ARM64 Linux (CM5 platform) 
- **Development**: Compatible with x86_64 Linux
- **Python**: 3.11+ required (supports 3.11, 3.12, 3.13)
- **Hardware**: Optional hardware gracefully handled when unavailable
- **Package Manager**: uv preferred for dependency management, configured for aarch64 platform preference

## Error Handling Patterns

### User-Facing Errors
Use `UserVisibleError` from `distiller_cm5_python.utils.distiller_exception` for errors that should be displayed to users.

### Hardware Errors
Hardware components should gracefully handle unavailability and provide meaningful error messages with suggested solutions.

### Server Management
LLM server lifecycle is managed automatically with proper cleanup on application shutdown.

## Integration Notes

### SDK Integration
The application requires the companion `distiller-cm5-sdk` for hardware control:
- **E-ink Display**: Uses SDK's Display class exclusively for all e-ink operations
- **Path Resolution**: Automatically detects SDK installation at `/opt/distiller-cm5-sdk`
- **Dependency**: The SDK must be installed for e-ink functionality to work

### Service Integration
Designed to work with `distiller-cm5-services` for system-level integration and service management.

### Power Management
UART-based signaling provides power state information to the broader system architecture.

## Troubleshooting

### Cache Issues
When LLM cache runs into issues, delete the cache folder:
```bash
rm -rf distiller_cm5_python/llm_server/cache
```

### Common Issues
- **Model loading fails**: Check if model file exists in GGUF format at `distiller_cm5_python/llm_server/models/`
- **Hardware components fail**: Hardware gracefully degrades when unavailable; check device permissions and connections
- **GUI won't start**: Ensure PyQt6 dependencies are installed and display is available

## Memory Annotations

### Display and Rendering
- Always use monochrome 1-bit colors and the eink display where this GUI will be running does not support chroma besides 1-bit colors.
- This project does not need RGB colors, only monochrome colors should be used. This App is going to be displayed on a 1-bit color eink display. Hence only white and black should be used, no share nothing. Just pure white or pure black.

### Performance and Resource Management
- Always remember to not use Animations, Transitions or Heavy processing QML stuff as this project is going to be running on a small raspberrypi cm5 with limited resources.

## UI Navigation and Focus Management Architecture

### Navigation System Overview

The application implements a **three-key navigation system** (Up, Down, Enter) specifically designed for hardware with limited input capabilities:

**Navigation Flow:**
```
Hardware Keys → InputMonitor.py → Qt Key Events → main.qml (keyHandler) → FocusManager → UI Components
```

**Key Components:**
- `FocusManager.qml`: Singleton managing global focus state and navigation
- `NavigableItem.qml`: Base component for all focusable UI elements  
- `InputMonitor.py`: Hardware input monitoring and Qt key event translation
- `MCPClientBridge.py`: Primary bridge connecting Python logic to QML UI

### Focus Management Patterns

**Centralized Focus Control:**
- `FocusManager` singleton maintains `currentFocusItems[]` array and `currentFocusIndex`
- Focus wraps around from last to first item for circular navigation
- Special navigation modes: scroll mode, hold-to-talk, dialog focus preservation

**Focus Collection Pattern:**
```javascript
function collectFocusItems() {
    focusableItems = [];
    // Add navigable items in priority order
    if (header.serverSelectButton && header.serverSelectButton.navigable)
        focusableItems.push(header.serverSelectButton);
    FocusManager.initializeFocusItems(focusableItems, scrollView);
}
```

### QML Component Architecture

**Component Hierarchy:**
```
Item
├── PageBase.qml (common page functionality)
├── NavigableItem.qml (focus management base)
│   ├── AppButton.qml (buttons)
│   ├── ConversationView.qml (scrollable content)
│   └── Various input components
```

**Single Page Architecture:**
- No traditional routing - single `VoiceAssistantPage.qml`
- Modal dialogs for additional screens (lazy-loaded for memory efficiency)
- State-based content switching within main page

### Bridge Classes and Communication Patterns

**MCPClientBridge Structure:**
```
MCPClientBridge
├── ConversationManager (message history)
├── StatusManager (application state)
├── ServerDiscovery (MCP server detection)
├── ConnectionManager (server connections)
└── ErrorHandler (error processing)
```

**Communication Patterns:**
```python
# Python to QML
@pyqtSignal
bridgeReady = pyqtSignal()

@pyqtSlot(result=str)
def getWifiMacAddress(self):
    return self.network_utils.get_wifi_mac_address()
```

```javascript
// QML to Python
bridge.submit_query(transcribedText.trim())

// Signal connections
Connections {
    target: bridge
    function onTranscriptionComplete(full_text) {
        transcribedText = full_text;
    }
}
```

### State Management Architecture

**Application State Flow:**
```
MCPClientBridge (Python) → QML Properties → UI State Updates → Visual Changes
```

**Key State Properties:**
- `appState`: Current application mode (idle, listening, processing, etc.)
- `isConnected`: Server connection status
- `visualFocus`: Individual component focus state
- `scrollModeActive`: Special navigation mode

### Development Patterns for QML Components

**Adding New Focusable Components:**
1. Extend `NavigableItem` base component
2. Implement `activate()` function for Enter key handling
3. Add component to parent's `focusableItems` array
4. Use `ThemeManager` for consistent monochrome styling
5. Set `navigable: true` property

**Creating New Dialogs:**
1. Use lazy loading pattern with `Qt.createComponent()`
2. Preserve focus state before opening dialog
3. Restore focus state when closing dialog
4. Connect to parent's signal handling system

**Bridge Integration Best Practices:**
1. Use `@pyqtSlot` decorators for QML-callable methods
2. Emit `pyqtSignal` for Python-to-QML communication
3. Handle async operations with proper event loops
4. Implement cleanup in bridge component destructors

**State Management Guidelines:**
1. Use centralized state in `StatusManager`
2. Implement state timeouts and recovery logic
3. Batch UI updates to prevent excessive redraws
4. Handle state transitions gracefully with proper error handling

**Dialog Management Pattern:**
```javascript
function getServerListDialog() {
    if (!serverListDialog) {
        var component = Qt.createComponent("Components/ServerListDialog.qml");
        serverListDialog = component.createObject(voiceAssistantPage);
        // Connect signals and setup focus preservation
    }
    return serverListDialog;
}
```

**Property Binding for Reactive UI:**
```javascript
// Responsive state-based styling
enabled: isConnected && appState !== "processing"
backgroundColor: visualFocus ? ThemeManager.textColor : ThemeManager.backgroundColor
```

### Hardware-Specific Optimizations

This architecture is specifically optimized for:
- **E-ink displays**: Monochrome colors only, no animations or transitions
- **Limited input devices**: Three-key navigation (Up/Down/Enter)
- **Resource constraints**: Lazy loading, efficient memory usage, minimal redraws
- **Hardware integration**: GPIO, UART, audio processing integration

The modular bridge design enables easy testing and maintenance while centralized focus management ensures consistent navigation behavior across all UI components.