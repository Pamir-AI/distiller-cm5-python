# E-Ink Event-Driven Display Mode

## Overview

The Distiller CM5 Python project now supports two display refresh modes for e-ink displays:
1. **Timer-based mode** (legacy): Fixed or adaptive intervals between frame captures
2. **Event-driven mode** (new): Next frame captured only after display completes refresh

## Configuration

The display mode is controlled by the `eink_timer_based_mode` flag in `display_config.py`:

```python
config = {
    "display": {
        # ...
        "eink_timer_based_mode": False,  # False = event-driven, True = timer-based
        # ...
    }
}
```

## Mode Comparison

### Timer-Based Mode (Legacy)
- Captures frames at fixed intervals (e.g., every 1000ms)
- May attempt to update display while still busy
- Can waste CPU cycles capturing unchanged frames
- Risk of display artifacts if timing misaligned

### Event-Driven Mode (Recommended)
- Captures next frame only after display completes refresh
- Guarantees display is ready before next update
- Eliminates overrun artifacts
- More efficient CPU usage
- Automatic flow control based on display speed

## Architecture

### Key Components

1. **EinkDriver**
   - Thread-safe `_is_busy` flag tracks display state
   - `set_completion_callback()` allows notification on refresh complete
   - `pic_display()` and related methods manage busy state

2. **EInkRendererBridge**
   - `displayComplete` Qt signal emitted when display finishes
   - Hooks driver callback to Qt signal system

3. **EInkRenderer**
   - Implements event-driven capture path
   - `_capture_next_frame()` triggered by display completion
   - Maintains timer-based compatibility for legacy support

## Implementation Details

### Driver Changes
```python
# Thread-safe busy tracking
def is_busy(self) -> bool:
    with self._busy_lock:
        return self._is_busy

# Completion notification
def set_completion_callback(self, callback: Optional[Callable[[], None]]) -> None:
    with self._busy_lock:
        self._completion_callback = callback
```

### Display Update Flow
1. Frame captured from QML content
2. Data sent to e-ink display via SPI
3. Driver sets busy flag and starts refresh
4. Hardware completes refresh, BUSY pin goes high
5. Driver clears busy flag and invokes callback
6. Qt signal triggers next frame capture

## Performance Benefits

- **Reduced CPU usage**: No wasted capture cycles
- **Zero overruns**: Display always ready for updates  
- **Adaptive performance**: Automatically adjusts to display speed
- **Better responsiveness**: Updates as fast as hardware allows

## Hardware Requirements

- E-ink display with BUSY pin properly connected
- GPIO pull-up resistor on BUSY pin (usually internal)
- SPI connection for data transfer

## Troubleshooting

### Display Always Busy
- Check BUSY pin GPIO connection
- Verify pull-up resistor enabled
- Ensure display power is stable

### No Completion Callbacks
- Verify e-ink hardware is connected
- Check SPI communication is working
- Monitor logs for timeout warnings

### Switching Modes
To switch between modes, change `eink_timer_based_mode` in config and restart the application. The active mode is logged at startup.

## Testing

Test scripts are provided:
- `test_eink_event_driven.py`: Validates event-driven functionality
- `test_eink_with_timeout.py`: Tests with hardware timeout protection

Run tests with:
```bash
python test_eink_event_driven.py
```

## Future Enhancements

- Dynamic mode switching without restart
- Performance metrics and reporting
- Automatic fallback to timer mode on hardware issues
- Configurable busy timeout values