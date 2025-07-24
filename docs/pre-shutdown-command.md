# Pre-Shutdown Command Feature

## Overview

The Distiller CM5 Python application now supports executing a custom command before system shutdown. This allows users to perform cleanup tasks, save state, or trigger external actions before the system powers off.

## Configuration

The pre-shutdown command is configured in `default_config.json` under the `system` section:

```json
{
  ...
  "system": {
    "pre_shutdown_command": "/path/to/your/script.sh",
    "pre_shutdown_timeout": 5
  }
}
```

### Configuration Options

- **`pre_shutdown_command`**: The command or script to execute before shutdown. Can include arguments.
- **`pre_shutdown_timeout`**: Maximum time (in seconds) to wait for the command to complete. Default: 5 seconds.

## How It Works

1. User initiates shutdown through the GUI power button
2. Confirmation dialog appears
3. User clicks "Proceed"
4. **E-ink display hardware is released** (if in use)
5. **Pre-shutdown command executes** (if configured)
6. System sends shutdown signal via UART
7. Application performs cleanup and exits

## Examples

### Basic Script
```json
{
  "system": {
    "pre_shutdown_command": "/home/user/backup_data.sh"
  }
}
```

### Command with Arguments
```json
{
  "system": {
    "pre_shutdown_command": "/usr/local/bin/notify-server shutdown initiated"
  }
}
```

### Complex Shell Command
```json
{
  "system": {
    "pre_shutdown_command": "cd /home/user && ./backup.sh && echo 'Backup complete'"
  }
}
```

### Python Script
```json
{
  "system": {
    "pre_shutdown_command": "python3 /opt/scripts/save_state.py --mode shutdown"
  }
}
```

## Example Pre-Shutdown Script

Create a script at `/opt/shutdown_cleanup.sh`:

```bash
#!/bin/bash

# Log shutdown event
echo "[$(date)] System shutdown initiated" >> /var/log/distiller_shutdown.log

# Save application state
if [ -f /tmp/app_state.json ]; then
    cp /tmp/app_state.json /opt/saved_states/last_state_$(date +%Y%m%d_%H%M%S).json
fi

# Sync filesystem
sync

# Notify external service (example)
curl -X POST http://monitoring.local/api/shutdown \
    -H "Content-Type: application/json" \
    -d '{"device": "distiller-cm5", "time": "'$(date -Iseconds)'"}'

echo "Pre-shutdown tasks completed"
```

Make it executable:
```bash
chmod +x /opt/shutdown_cleanup.sh
```

Configure in `default_config.json`:
```json
{
  "system": {
    "pre_shutdown_command": "/opt/shutdown_cleanup.sh",
    "pre_shutdown_timeout": 10
  }
}
```

## Important Notes

1. **Non-blocking**: The command runs with a timeout to prevent hanging the shutdown process
2. **Error handling**: If the command fails or times out, shutdown proceeds normally
3. **Shell commands**: Complex commands with `cd`, `&&`, pipes, etc. are supported (executed with shell=True)
4. **E-ink Display**: The application's e-ink hardware is automatically released before the pre-shutdown command runs, allowing your command to use the display
5. **Security**: Ensure your script has appropriate permissions and doesn't expose sensitive data
6. **Logging**: Command output and errors are logged to the application log
7. **Testing**: Test your command separately before configuring it for shutdown

## Troubleshooting

### Command Not Executing
- Check the command path is absolute and correct
- Verify the script has execute permissions (`chmod +x`)
- Check application logs for error messages

### Command Timing Out
- Increase `pre_shutdown_timeout` if your script needs more time
- Ensure your script doesn't wait for user input
- Add logging to your script to debug where it's getting stuck

### Debugging
Enable debug logging to see command execution details:
```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

## Use Cases

1. **Backup State**: Save application data or configuration before shutdown
2. **Notification**: Send alerts to monitoring systems or administrators
3. **Hardware Control**: Safely power down connected peripherals
4. **Cleanup**: Remove temporary files or release resources
5. **Logging**: Record shutdown events for auditing