import "Components"
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

PageBase {
    // Process other keys normally
    // Add these transition methods that are necessary for proper state handling

    id: voiceAssistantPage

    property string _serverName: ""
    property string serverName: _serverName
    property bool isListening: state === "listening"
    property bool isProcessing: ["processing", "thinking", "toolExecution"].includes(state)
    property bool isServerConnected: bridge && bridge.ready ? bridge.isConnected : false
    property string statusText: conversationView && conversationView.scrollModeActive ? "Scroll Mode (↑↓ to scroll)" : _statusText
    property string _statusText: getStatusTextForState(state)
    property var focusableItems: []
    property var previousFocusedItem: null
    property string transcribedText: ""
    property bool transcriptionInProgress: false
    property bool conversationScrollMode: false // Track if conversation is in scroll mode
    property bool showStatusInBothPlaces: true // Set to true to show status in voice area instead of header
    property bool cacheRestoring: state === "cacheRestoring" // Flag to track if cache is being restored

    // Helper function to get status text for current state
    function getStatusTextForState(currentState) {
        switch (currentState) {
        case "disconnected":
            return "Not connected";
        case "idle":
            return "Tap to Talk";
        case "listening":
            return "Listening...";
        case "processing":
            return "Processing...";
        case "thinking":
            return "Thinking...";
        case "toolExecution":
            return "Executing Tool...";
        case "cacheRestoring":
            return "Restoring cache...";
        case "error":
            return "Error Occurred";
        default:
            return "Tap to Talk";
        }
    }

    function findChild(parent, objectName) {
        if (!parent)
            return null;

        for (var i = 0; i < parent.children.length; i++) {
            var child = parent.children[i];
            if (child.objectName === objectName)
                return child;

            var found = findChild(child, objectName);
            if (found)
                return found;
        }
        return null;
    }

    function collectFocusItems() {
        focusableItems = [];
        // Add server select button first (highest priority)
        if (header) {
            if (header.serverSelectButton && header.serverSelectButton.navigable)
                focusableItems.push(header.serverSelectButton);

            if (header.infoButton && header.infoButton.navigable)
                focusableItems.push(header.infoButton);

            if (header.closeButton && header.closeButton.navigable)
                focusableItems.push(header.closeButton);
        }
        // Add conversation view for keyboard scrolling
        if (conversationView && conversationView.navigable)
            focusableItems.push(conversationView);

        // Add voice input area buttons only if we have a server connection
        if (voiceInputArea) {
            // Add the voice button if server is connected
            if (voiceInputArea.voiceButton && voiceInputArea.voiceButton.navigable)
                focusableItems.push(voiceInputArea.voiceButton);

            // Then add the reset button
            if (voiceInputArea.resetButton && voiceInputArea.resetButton.navigable)
                focusableItems.push(voiceInputArea.resetButton);

            // Add the battery indicator
            if (voiceInputArea.batteryIndicator && voiceInputArea.batteryIndicator.navigable)
                focusableItems.push(voiceInputArea.batteryIndicator);
        }
        // Initialize focus manager with proper activation handling
        FocusManager.initializeFocusItems(focusableItems, conversationView);
    }

    function ensureFocusableItemsHaveFocus() {
        if (FocusManager.currentFocusIndex < 0 || FocusManager.currentFocusItems.length === 0) {
            collectFocusItems();
            if (voiceInputArea && voiceInputArea.voiceButton && voiceInputArea.voiceButton.navigable)
                FocusManager.setFocusToItem(voiceInputArea.voiceButton);
            else if (focusableItems.length > 0)
                FocusManager.setFocusToItem(focusableItems[0]);
        }
    }

    // Function to reset focus state - updated to use the consolidated timer
    function resetFocusState() {
        console.log("Resetting focus state after restart");
        // First clear any existing focus
        FocusManager.clearFocus();
        FocusManager.currentFocusItems = [];
        FocusManager.currentFocusIndex = -1;
        FocusManager.lockFocus = false;
        // Immediately collect focus items to ensure they're available
        collectFocusItems();
        // Then start the timer to ensure UI elements are ready
        focusTimer.isRestoreFocus = false;
        // This is a reset operation, not restore
        focusTimer.start();
        // Force a check immediately after resetting focus
        Qt.callLater(function () {
            if (FocusManager.currentFocusItems.length === 0) {
                console.log("No focus items available after reset, forcing recollection");
                collectFocusItems();
                if (voiceInputArea && voiceInputArea.voiceButton && voiceInputArea.voiceButton.navigable)
                    FocusManager.setFocusToItem(voiceInputArea.voiceButton);
                else if (focusableItems.length > 0)
                    FocusManager.setFocusToItem(focusableItems[0]);
            }
        });
    }

    // Function to restart the application
    function restartApplication() {
        console.log("Restarting application...");
        // Use the dedicated restart method
        if (bridge && bridge.ready) {
            // Use the dedicated restart method
            if (typeof bridge.restartApplication === "function") {
                // Reset focus state immediately to clear any stuck state
                FocusManager.clearFocus();
                FocusManager.lockFocus = false;
                bridge.restartApplication();
                messageToast.showMessage("Restarting application...", 2000);
            } else {
                // Fallback if the method isn't available
                messageToast.showMessage("Unable to restart - bridge method not available", 3000);
            }
        } else {
            // Fallback if bridge is not available
            messageToast.showMessage("Unable to restart - bridge not ready", 3000);
        }
    }

    // Move to thinking state (for external calls)
    function setThinkingState() {
        setAppState("thinking");
        // Update action timestamp
        stateResetTimer.lastActionTimestamp = Date.now();
    }

    // Move to tool execution state (for external calls)
    function setToolExecutionState() {
        setAppState("executing_tool");
        // Update action timestamp
        stateResetTimer.lastActionTimestamp = Date.now();
    }

    // Function to handle server reconnection
    function reconnectToServer() {
        if (bridge && bridge.ready) {
            // Store the current focus before the operation
            previousFocusedItem = FocusManager.currentFocusItems[FocusManager.currentFocusIndex];
            // Set reconnecting state
            state = "disconnected";
            // Attempt to reconnect
            bridge.reconnectToServer();
            // Use the reconnection timer
            serverReconnectTimer.start();
            return true;
        }
        return false;
    }

    // Move to specified state with proper UI updates
    function setAppState(newState) {
        console.log("Setting app state to: " + newState);
        // Map newState to a valid state in our state machine
        if (newState === "listening")
            state = "listening";
        else if (newState === "processing")
            state = "processing";
        else if (newState === "thinking")
            state = "thinking";
        else if (newState === "executing_tool")
            state = "toolExecution";
        else if (newState === "restoring_cache")
            state = "cacheRestoring";
        else if (newState === "error")
            state = "error";
        else if (newState === "idle")
            state = "idle";
        else if (newState === "disconnected")
            state = "disconnected";
    }

    // Default state
    state: isServerConnected ? "idle" : "disconnected"
    pageName: "Voice Assistant"
    onServerNameChanged: {
        _serverName = serverName;
    }
    // State change monitoring
    onStateChanged: {
        console.log("State changed to: " + state);
        stateResetTimer.lastActionTimestamp = Date.now();
        // Update voice input area state to match page state
        if (voiceInputArea && voiceInputArea.setAppState) {
            if (state === "listening")
                voiceInputArea.setAppState("listening");
            else if (state === "processing")
                voiceInputArea.setAppState("processing");
            else if (state === "thinking")
                voiceInputArea.setAppState("thinking");
            else if (state === "toolExecution")
                voiceInputArea.setAppState("executing_tool");
            else if (state === "cacheRestoring")
                voiceInputArea.setAppState("restoring_cache");
            else if (state === "error")
                voiceInputArea.setAppState("error");
            else if (state === "idle")
                voiceInputArea.setAppState("idle");
        }
    }
    // Server connection state monitor
    onIsServerConnectedChanged: {
        if (isServerConnected) {
            if (state === "disconnected")
                state = "idle";
        } else {
            state = "disconnected";
        }
    }
    Component.onCompleted: {
        collectFocusItems();
        // Explicitly disable conversationView navigability initially to prevent it from capturing focus
        if (conversationView)
            conversationView.navigable = false;

        // Force focus to server select button
        if (header && header.serverSelectButton && header.serverSelectButton.navigable) {
            console.log("Setting initial focus to server select button");
            FocusManager.setFocusToItem(header.serverSelectButton);
            // Delay enabling of conversationView navigability
            Qt.callLater(function () {
                if (conversationView)
                    conversationView.navigable = true;
            });
        } else if (voiceInputArea && voiceInputArea.voiceButton && voiceInputArea.voiceButton.navigable) {
            // Fall back to voice button if server select button isn't available
            FocusManager.setFocusToItem(voiceInputArea.voiceButton);
        }
    }
    // Override key handling to ignore certain keys during cache restoration
    Keys.onPressed: function (event) {
        // Log key presses
        console.log("Key Pressed:", event.key, " | Current Focus:", FocusManager.currentFocusItems[FocusManager.currentFocusIndex] ? FocusManager.currentFocusItems[FocusManager.currentFocusIndex].objectName : "None", " | Scroll Mode:", conversationScrollMode);
        // During cache restoration, block keys that could change state
        if (state === "cacheRestoring") {
            if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
                console.log("Key press blocked - cache is being restored");
                messageToast.showMessage("Please wait, cache restoration might take a few minutes...", 2000);
                event.accepted = true;
                return;
            }
        }
    }

    // State machine
    StateGroup {
        id: stateMachine

        states: [
            State {
                name: "disconnected"

                PropertyChanges {
                    target: voiceInputArea
                    enabled: false
                }
            },
            State {
                name: "idle"

                PropertyChanges {
                    target: voiceInputArea
                    enabled: true
                }

                PropertyChanges {
                    target: voiceAssistantPage
                    _statusText: "Tap to Talk"
                }
            },
            State {
                name: "listening"

                PropertyChanges {
                    target: voiceInputArea
                    enabled: true
                }

                PropertyChanges {
                    target: voiceAssistantPage
                    _statusText: "Listening..."
                }
            },
            State {
                name: "processing"

                PropertyChanges {
                    target: voiceInputArea
                    enabled: false
                }

                PropertyChanges {
                    target: voiceAssistantPage
                    _statusText: "Processing..."
                }
            },
            State {
                name: "thinking"

                PropertyChanges {
                    target: voiceInputArea
                    enabled: false
                }

                PropertyChanges {
                    target: voiceAssistantPage
                    _statusText: "Processing..."
                }
            },
            State {
                name: "toolExecution"

                PropertyChanges {
                    target: voiceInputArea
                    enabled: false
                }

                PropertyChanges {
                    target: voiceAssistantPage
                    _statusText: "Processing..."
                }
            },
            State {
                name: "cacheRestoring"

                PropertyChanges {
                    target: voiceInputArea
                    enabled: false
                }

                PropertyChanges {
                    target: voiceAssistantPage
                    _statusText: "Restoring cache..."
                }
            },
            State {
                name: "error"

                PropertyChanges {
                    target: voiceInputArea
                    enabled: true
                }

                PropertyChanges {
                    target: voiceAssistantPage
                    _statusText: "Error Occurred"
                }
            }
        ]
        // State change handlers moved to onStateChanged
        onStateChanged: {
            if (state === "idle") {
                stateResetTimer.toolExecutionActive = false;
                conversationView.setResponseInProgress(false);
                if (voiceInputArea && voiceInputArea.resetState)
                    voiceInputArea.resetState();
            } else if (state === "listening") {
                transcribedText = "";
                voiceInputArea.transcribedText = "";
                if (voiceInputArea && voiceInputArea.setAppState)
                    voiceInputArea.setAppState("listening");
                stateResetTimer.lastActionTimestamp = Date.now();
            } else if (state === "processing") {
                conversationView.setResponseInProgress(true);
                if (voiceInputArea && voiceInputArea.setAppState)
                    voiceInputArea.setAppState("processing");
                stateResetTimer.lastActionTimestamp = Date.now();
            } else if (state === "error") {
                stateResetTimer.toolExecutionActive = false;
                conversationView.setResponseInProgress(false);
                if (voiceInputArea && voiceInputArea.setErrorState)
                    voiceInputArea.setErrorState();
            }
        }
    }

    // Consolidated failsafe timer for state management and stuck detection
    Timer {
        id: stateResetTimer

        property bool toolExecutionActive: false
        property real lastActionTimestamp: Date.now()

        interval: 10000 // 10 seconds timeout for periodic check
        repeat: true // Now repeating to handle both periodic check and timeout
        running: true // Always running to check for stuck states
        onTriggered: {
            // Check for stuck processing state (was stateCheckTimer's job)
            // Exclude cache restoration from timeout logic - it has its own lifecycle
            if (isProcessing && state !== "cacheRestoring" && (Date.now() - lastActionTimestamp > 15000)) {
                console.log("StateResetTimer triggered: Detected stuck state after inactivity");
                voiceAssistantPage.state = "idle";
            }
        }
    }

    // Consolidated focus management timer
    Timer {
        id: focusTimer

        property bool isRestoreFocus: false // Tracks which type of focus operation this is

        interval: 250 // Middle ground between original 200 and 300ms
        repeat: false
        running: false
        onTriggered: {
            // Always collect focus items regardless of the focus operation type
            collectFocusItems();
            if (isRestoreFocus) {
                // This was the restoreFocusTimer functionality - restore after dialog
                // Always prioritize the voice button after server selection if connected
                if (isServerConnected && voiceInputArea && voiceInputArea.voiceButton && voiceInputArea.voiceButton.navigable) {
                    FocusManager.setFocusToItem(voiceInputArea.voiceButton);
                    console.log("Focus set to voice button after server selection");
                } else if (previousFocusedItem && previousFocusedItem.navigable) {
                    FocusManager.setFocusToItem(previousFocusedItem);
                } else if (focusableItems.length > 0) {
                    for (var i = 0; i < focusableItems.length; i++) {
                        if (focusableItems[i] !== header.serverSelectButton) {
                            FocusManager.setFocusToItem(focusableItems[i]);
                            break;
                        }
                    }
                }
            } else {
                // This was the focusResetTimer functionality - after app restart
                // Set focus to voice button if available
                if (voiceInputArea && voiceInputArea.voiceButton && voiceInputArea.voiceButton.navigable) {
                    FocusManager.setFocusToItem(voiceInputArea.voiceButton);
                    console.log("Focus reset to voice button");
                } else if (focusableItems.length > 0) {
                    FocusManager.setFocusToItem(focusableItems[0]);
                    console.log("Focus reset to first focusable item");
                }
                // Force focus to keyHandler in main window to ensure key navigation works
                if (mainWindow && mainWindow.keyHandler) {
                    mainWindow.keyHandler.forceActiveFocus();
                    console.log("Focus forced to key handler");
                }
            }
            // Always ensure focusable items have focus as a final step
            ensureFocusableItemsHaveFocus();
        }
    }

    // Safety check to ensure focus is restored properly after dialogs
    Timer {
        id: focusSafetyCheckTimer

        interval: 500
        repeat: true
        running: true
        onTriggered: {
            // If there are no focusable items, recollect them
            if (FocusManager.currentFocusItems.length === 0 || FocusManager.currentFocusIndex < 0 || FocusManager.currentFocusIndex >= FocusManager.currentFocusItems.length) {
                console.log("Focus safety check: Restoring focus items");
                collectFocusItems();
                if (voiceInputArea && voiceInputArea.voiceButton && voiceInputArea.voiceButton.navigable)
                    FocusManager.setFocusToItem(voiceInputArea.voiceButton);
                else if (focusableItems.length > 0)
                    FocusManager.setFocusToItem(focusableItems[0]);
            }
        }
    }

    Connections {
        function onBridgeReady() {
            if (conversationView)
                conversationView.updateModel(bridge.get_conversation());

            // Reinitialize focus when the bridge signals it's ready (including after restart)
            Qt.callLater(resetFocusState);
        }

        function onTranscriptionUpdate(transcription) {
            transcribedText += transcription + " ";
            voiceInputArea.transcribedText = transcribedText;
            transcriptionInProgress = true;
        }

        function onTranscriptionComplete(full_text) {
            if (full_text && full_text.trim().length > 0) {
                transcribedText = full_text;
                voiceInputArea.transcribedText = transcribedText;
                // Submit the transcribed text to the server after a short delay
                transcriptionTimer.start();
                // Update state to thinking
                state = "thinking";
            } else {
                // Handle empty transcription the same way as short audio error
                console.log("Empty transcription detected, treating as error");
                // Show error state and message
                messageToast.showMessage("Error: Empty voice message", 3000);
                state = "error";
                // Reset conversation view state
                conversationView.setResponseInProgress(false);
            }
            transcriptionInProgress = false;
        }

        // Handler for SSH information events
        function onSshInfoReceived(content, eventId, timestamp) {
            console.log("SSH Info received: " + content);
            // Add to conversation if not empty
            if (content && content.trim().length > 0) {
                // Update the UI to show SSH connection info
                if (conversationView)
                    conversationView.updateModel(bridge.get_conversation());

                // Show a toast notification for the SSH info
                messageToast.showMessage("SSH Connection Info: " + content, 5000);
            }
        }

        // Handler for function events
        function onFunctionReceived(content, eventId, timestamp) {
            console.log("Function info received: " + content);
            // Add the function information to the conversation view
            if (conversationView)
                conversationView.updateModel(bridge.get_conversation());
        }

        // Handler for observation events
        function onObservationReceived(content, eventId, timestamp) {
            console.log("Observation received: " + content);
            // Add the observation to the conversation view
            if (conversationView)
                conversationView.updateModel(bridge.get_conversation());
        }

        // Handler for cache events
        function onCacheEventReceived(content, eventId, timestamp) {
            console.log("Cache event received: " + content);
            // Check message to determine which operation is happening
            if (content && content.toLowerCase().includes("restoring")) {
                console.log("Cache restoration in progress, disabling voice button");
                state = "cacheRestoring";
                // Show a toast message about the operation
                messageToast.showMessage("Restoring model cache, might take a few minutes...", 3000);
            } else if (content && content.toLowerCase().includes("restored")) {
                console.log("Cache restoration completed, re-enabling voice button");
                state = "idle";
                // Show a toast message about the completion
                messageToast.showMessage("Cache restored successfully", 3000);
            } else if (content && content.toLowerCase().includes("failed")) {
                console.log("Cache restoration failed");
                state = "error";
                // Show a toast message about the failure
                messageToast.showMessage("Cache restoration failed: " + content, 5000);
            }
            // Add the cache operation to the conversation view
            if (conversationView)
                conversationView.updateModel(bridge.get_conversation());
        }

        // Handler for plan events
        function onPlanReceived(content, eventId, timestamp) {
            console.log("Plan received: " + content);
            // Add the plan to the conversation view
            if (conversationView)
                conversationView.updateModel(bridge.get_conversation());
        }

        // Handler for raw message schema objects
        function onMessageSchemaReceived(messageData) {
            // Update conversation view with latest messages
            if (conversationView)
                conversationView.updateModel(bridge.get_conversation());
        }

        function onRecordingStateChanged(is_recording) {
            state = is_recording ? "listening" : "processing";
            if (is_recording) {
                transcribedText = "";
                voiceInputArea.transcribedText = "";
            }
        }

        function onStatusChanged(newStatus) {
            console.log("QML: Status changed to:", newStatus);
            // Update timestamp for any status change to prevent timeout
            stateResetTimer.lastActionTimestamp = Date.now();

            // Map status to state
            if (newStatus.toLowerCase().includes("thinking")) {
                state = "thinking";
                stateResetTimer.toolExecutionActive = false;
            } else if (newStatus.toLowerCase().includes("tool") || newStatus.toLowerCase().includes("executing")) {
                state = "toolExecution";
                stateResetTimer.toolExecutionActive = true;
            } else if (newStatus.toLowerCase().includes("restoring_cache")) {
                state = "cacheRestoring";
                // Cache restoration is now handled separately and won't be reset by timer
            } else if (newStatus === "idle" || newStatus === "Ready") {
                state = "idle";
            } else if (newStatus.toLowerCase().includes("listening"))
                state = "listening";
            else if (newStatus.toLowerCase().includes("error"))
                state = "error";
        }

        function onRecordingError(errorMessage) {
            console.log("Recording Error: " + errorMessage);
            messageToast.showMessage("Error: " + errorMessage, 3000);
            state = "error";
            console.log("RecordingError: Reset all UI states due to error: " + errorMessage);
        }

        function onErrorReceived(content, eventId, timestamp) {
            console.log("Error event received: " + content);
            state = "error";
            // Update the conversation and show message toast
            if (bridge && bridge.ready) {
                conversationView.updateModel(bridge.get_conversation());
                conversationView.scrollToBottom();
                messageToast.showMessage("Error: " + content, 5000);
            }
        }

        function onErrorOccurred(errorMessage) {
            var displayDuration = Math.max(3000, Math.min(errorMessage.length * 75, 8000));
            messageToast.showMessage("Error: " + errorMessage, displayDuration);
            state = "error";
            // Force conversation view to update - ensure the error is displayed
            if (bridge && bridge.ready) {
                conversationView.updateModel(bridge.get_conversation());
                conversationView.scrollToBottom();
            }
            if (errorMessage.toLowerCase().includes("connect") || errorMessage.toLowerCase().includes("server") || errorMessage.toLowerCase().includes("timeout"))
                reconnectionTimer.start();
        }

        function onIsConnectedChanged(connected) {
            isServerConnected = connected;
            if (connected) {
                if (state === "disconnected")
                    state = "idle";
            } else {
                state = "disconnected";
            }
        }

        target: bridge
    }

    Timer {
        id: transcriptionTimer

        interval: 750
        repeat: false
        running: false
        onTriggered: {
            if (transcribedText && transcribedText.trim().length > 0 && bridge && bridge.ready) {
                bridge.submit_query(transcribedText.trim());
                transcribedText = "";
                voiceInputArea.transcribedText = "";
                // Update the action timestamp to track activity
                stateResetTimer.lastActionTimestamp = Date.now();
            } else {
                // Show error for empty message
                console.log("Empty transcription in timer, showing error state");
                // Show error state and message
                messageToast.showMessage("Error: Empty voice message", 3000);
                state = "error";
            }
        }
    }

    VoiceAssistantPageHeader {
        id: header

        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 60
        serverName: _serverName
        statusText: voiceAssistantPage.statusText
        isConnected: bridge && bridge.ready ? bridge.isConnected : false
        showStatusText: true
        Component.onCompleted: {
            // Add high contrast border for visibility
            var headerRect = findChild(header, "headerBackground");
            if (headerRect) {
                headerRect.border.width = 1;
                headerRect.border.color = ThemeManager.black;
            }
        }
        onServerSelectClicked: {
            previousFocusedItem = FocusManager.currentFocusItems[FocusManager.currentFocusIndex];
            // Show server list dialog instead of confirmation
            getServerListDialog().open();
        }
        onCloseAppClicked: {
            console.log("System shutdown requested...");
            // Any cleanup tasks before shutting down
            if (bridge && bridge.ready)
                console.log("Preparing for system shutdown...");
            else
                console.log("Failed to initiate system shutdown - bridge not available");
        }
        onShowToastMessage: function (message, duration) {
            if (messageToast)
                messageToast.showMessage(message, duration);
        }
        onInfoClicked: {
            // Store current focused item before opening dialog
            previousFocusedItem = FocusManager.currentFocusItems[FocusManager.currentFocusIndex];
            console.log("Opening InfoDialog, storing previous focus:", previousFocusedItem ? previousFocusedItem.objectName : "None");
            
            // Show info dialog with error handling
            var dialog = getInfoDialog();
            if (dialog) {
                dialog.open();
            } else {
                console.error("Failed to create InfoDialog");
                messageToast.showMessage("Error: Could not open info dialog", 3000);
            }
        }
    }

    // Lazy-loaded dialogs
    property var serverListDialog: null
    property var infoDialog: null
    
    function getServerListDialog() {
        if (!serverListDialog) {
            var component = Qt.createComponent("Components/ServerListDialog.qml");
            if (component.status === Component.Ready) {
                serverListDialog = component.createObject(voiceAssistantPage);
                
                serverListDialog.serverSelected.connect(function(serverPath, serverName) {
                    if (bridge && bridge.ready) {
                        // Set the selected server and connect to it
                        bridge.setServerPath(serverPath);
                        // This returns an error message if connection fails, or empty string on success
                        var connectionResult = bridge.connectToServer();
                        if (connectionResult) {
                            // Connection failed, show error message
                            console.error("Connection failed: " + connectionResult);
                            messageToast.showMessage("Connection failed: " + connectionResult, 5000);
                            state = "error";
                        } else {
                            // Short delay to ensure UI is updated first

                            // Connection successful, update server name
                            _serverName = serverName;
                            state = "idle";
                            // Get conversation if available
                            if (conversationView)
                                conversationView.updateModel(bridge.get_conversation());

                            // Move focus to voice button after successful server selection
                            if (voiceInputArea && voiceInputArea.voiceButton && voiceInputArea.voiceButton.navigable)
                                Qt.callLater(function () {
                                    FocusManager.setFocusToItem(voiceInputArea.voiceButton);
                                });
                        }
                    }
                    // Restore focus after dialog closes
                    focusTimer.isRestoreFocus = true;
                    focusTimer.start();
                });
                
                serverListDialog.dialogClosed.connect(function() {
                    // Reinitialize focus items in the parent page when dialog closes
                    Qt.callLater(function () {
                        collectFocusItems();
                        // Restore focus to a default item
                        if (voiceInputArea && voiceInputArea.voiceButton && voiceInputArea.voiceButton.navigable)
                            FocusManager.setFocusToItem(voiceInputArea.voiceButton);
                    });
                });
            } else {
                console.error("Failed to create ServerListDialog:", component.errorString());
            }
        }
        return serverListDialog;
    }

    function getInfoDialog() {
        if (!infoDialog) {
            var component = Qt.createComponent("Components/InfoDialog.qml");
            console.log("InfoDialog component status:", component.status);
            
            if (component.status === Component.Ready) {
                infoDialog = component.createObject(voiceAssistantPage);
                if (!infoDialog) {
                    console.error("Failed to create InfoDialog object");
                    return null;
                }
                
                infoDialog.dialogClosed.connect(function() {
                    // Reinitialize focus items in the parent page when dialog closes
                    Qt.callLater(function () {
                        console.log("InfoDialog closed, restoring focus...");
                        collectFocusItems();
                        
                        // Try to restore to previous focused item first
                        if (previousFocusedItem && previousFocusedItem.navigable) {
                            console.log("Restoring focus to previous item:", previousFocusedItem.objectName);
                            FocusManager.setFocusToItem(previousFocusedItem);
                        } else if (voiceInputArea && voiceInputArea.voiceButton && voiceInputArea.voiceButton.navigable) {
                            // Fallback to voice button
                            console.log("Restoring focus to voice button");
                            FocusManager.setFocusToItem(voiceInputArea.voiceButton);
                        } else if (focusableItems.length > 0) {
                            // Fallback to first focusable item
                            console.log("Restoring focus to first focusable item");
                            FocusManager.setFocusToItem(focusableItems[0]);
                        }
                        
                        // Clear the previous focused item
                        previousFocusedItem = null;
                    });
                });
            } else if (component.status === Component.Error) {
                console.error("Failed to create InfoDialog component:", component.errorString());
                return null;
            } else {
                console.log("InfoDialog component not ready, status:", component.status);
                return null;
            }
        }
        return infoDialog;
    }

    ConversationView {
        id: conversationView

        function onScrollModeChanged(active) {
            console.log("Scroll mode changed to: " + active);
            conversationScrollMode = active;
            // When entering scroll mode, we need to make sure the focus stays
            if (active)
                FocusManager.lockFocus = true;
            else
                FocusManager.lockFocus = false;
        }

        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: voiceInputArea.top
        anchors.bottomMargin: ThemeManager.spacingSmall
        anchors.leftMargin: ThemeManager.spacingSmall
        anchors.rightMargin: ThemeManager.spacingSmall
        anchors.topMargin: ThemeManager.spacingSmall
        Component.onCompleted: {
            if (bridge && bridge.ready)
                updateModel(bridge.get_conversation());
            else
                updateModel([]);
        }

        Connections {
            function onConversationChanged() {
                // Update timestamp to prevent timeout during conversation updates
                stateResetTimer.lastActionTimestamp = Date.now();
                conversationView.updateModel(bridge.get_conversation());
            // Let updateModel handle scrolling to prevent race conditions
            }

            function onMessageReceived(message, eventId, timestamp, status) {
                console.log("QML onMessageReceived:", status, eventId, message.substring(0, 50));
                if (status === "in_progress") {
                    // Update timestamp to prevent timeout during text streaming
                    stateResetTimer.lastActionTimestamp = Date.now();

                    // Get current conversation
                    var conversation = bridge.get_conversation();
                    // If this is the first chunk of a new message
                    if (conversation.length === 0 || !conversation[conversation.length - 1].includes(message)) {
                        // Add as a new message
                        conversation.push("[" + timestamp + "] Assistant: " + message);
                    } else {
                        // Update the last message by appending the new chunk
                        var lastMsg = conversation[conversation.length - 1];
                        var timestampPart = lastMsg.substring(0, lastMsg.indexOf("]") + 1);
                        var senderPart = "Assistant: ";
                        var existingContent = lastMsg.substring(lastMsg.indexOf(senderPart) + senderPart.length);
                        // Replace the last message with updated content
                        conversation[conversation.length - 1] = timestampPart + " " + senderPart + existingContent + message;
                    }
                    // Update the model and keep response in progress
                    conversationView.updateModel(conversation);
                    conversationView.setResponseInProgress(true);
                    // Let updateModel and setResponseInProgress handle scrolling
                } else if (status === "success") {
                    console.log("QML: Message complete, resetting UI state");
                    // Final message or end of streaming
                    // Reset UI state now that the response is complete
                    voiceAssistantPage.state = "idle";
                    // Final scroll to bottom after response completion
                    Qt.callLater(function () {
                        if (!conversationView.scrollModeActive) {
                            conversationView.scrollToBottom();
                        }
                    });
                    // Stop failsafe timer
                    stateResetTimer.stop();
                }
            }

            function onListeningStarted() {
                voiceAssistantPage.state = "listening";
            }

            function onListeningStopped() {
                voiceAssistantPage.state = "processing";
            }

            target: bridge && bridge.ready ? bridge : null
        }
    }

    MessageToast {
        id: messageToast

        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: voiceInputArea.top
        anchors.bottomMargin: ThemeManager.spacingNormal
        Component.onCompleted: {
            // Improve contrast for visibility
            var toastRect = findChild(messageToast, "toastBackground");
            if (toastRect) {
                toastRect.border.width = 1;
                toastRect.border.color = ThemeManager.black;
                toastRect.color = ThemeManager.backgroundColor;
            }
        }
    }

    VoiceInputArea {
        id: voiceInputArea

        property string transcribedText: ""

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 0
        isListening: voiceAssistantPage.isListening
        isProcessing: voiceAssistantPage.isProcessing
        isConnected: voiceAssistantPage.isServerConnected && serverName && serverName.length > 0 && serverName !== "No Server"
        showStatusHint: true
        onAppStateUpdated: function (newState) {
            console.log("VoiceInputArea state changed to: " + newState);
            // Map to appropriate state in the state machine
            if (newState === "listening") {
                if (voiceAssistantPage.state !== "listening")
                    voiceAssistantPage.state = "listening";
            } else if (newState === "processing") {
                if (voiceAssistantPage.state !== "processing")
                    voiceAssistantPage.state = "processing";
            } else if (newState === "thinking") {
                if (voiceAssistantPage.state !== "thinking")
                    voiceAssistantPage.state = "thinking";
            } else if (newState === "executing_tool") {
                if (voiceAssistantPage.state !== "toolExecution")
                    voiceAssistantPage.state = "toolExecution";
            } else if (newState === "restoring_cache") {
                if (voiceAssistantPage.state !== "cacheRestoring")
                    voiceAssistantPage.state = "cacheRestoring";
            } else if (newState === "error") {
                if (voiceAssistantPage.state !== "error")
                    voiceAssistantPage.state = "error";
            } else if (newState === "idle") {
                if (voiceAssistantPage.state !== "idle" && voiceAssistantPage.isServerConnected)
                    voiceAssistantPage.state = "idle";
            }
        }
        onVoiceToggled: function (listening) {
            // Prevent voice toggling during cache restoration
            if (voiceAssistantPage.state === "cacheRestoring") {
                console.log("Voice toggle ignored - cache is being restored");
                messageToast.showMessage("Please wait, cache restoration might take a few minutes...", 2000);
                return;
            }
            if (bridge && bridge.ready && bridge.isConnected && voiceAssistantPage.state !== "processing" && voiceAssistantPage.state !== "thinking" && voiceAssistantPage.state !== "toolExecution") {
                if (listening) {
                    bridge.startRecording();
                    voiceAssistantPage.state = "listening";
                } else {
                    bridge.stopAndTranscribe();
                    voiceAssistantPage.state = "processing";
                }
            }
        }
        onVoicePressed: function () {
            // Prevent voice press during cache restoration
            if (voiceAssistantPage.state === "cacheRestoring") {
                console.log("Voice press ignored - cache is being restored");
                messageToast.showMessage("Please wait, cache restoration might take a few minutes...", 2000);
                return;
            }
            if (bridge && bridge.ready && bridge.isConnected && voiceAssistantPage.state !== "processing" && voiceAssistantPage.state !== "thinking" && voiceAssistantPage.state !== "toolExecution") {
                bridge.startRecording();
                voiceAssistantPage.state = "listening";
            }
        }
        onVoiceReleased: function () {
            // Prevent voice release during cache restoration
            if (voiceAssistantPage.state === "cacheRestoring") {
                console.log("Voice release ignored - cache is being restored");
                return;
            }
            if (bridge && bridge.ready && bridge.isConnected && voiceAssistantPage.state === "listening") {
                bridge.stopAndTranscribe();
                voiceAssistantPage.state = "processing";
            }
        }
        onResetClicked: {
            // Show confirmation dialog, unless cache is restoring
            if (voiceAssistantPage.state === "cacheRestoring") {
                messageToast.showMessage("Cannot reset during cache restoration", 2000);
                return;
            }
            getRestartConfirmDialog().open();
        }
        onBatteryInfoRequested: function (message) {
            messageToast.showMessage(message, 3000);
        }
    }

    Timer {
        id: reconnectionTimer

        interval: 750
        repeat: false
        running: false
        onTriggered: {
            previousFocusedItem = FocusManager.currentFocusItems[FocusManager.currentFocusIndex];
            getConfirmServerChangeDialog().open();
        }
    }

    // Separate timer for handling reconnection process
    Timer {
        id: serverReconnectTimer

        interval: 2000
        repeat: false
        running: false
        onTriggered: {
            // Check connection state
            if (bridge && bridge.ready && bridge.isConnected) {
                messageToast.showMessage("Successfully reconnected to server", 3000);
                voiceAssistantPage.state = "idle";
            } else {
                messageToast.showMessage("Failed to reconnect to server", 3000);
                voiceAssistantPage.state = "disconnected";
            }
            // Update conversation view
            if (bridge && bridge.ready) {
                conversationView.updateModel(bridge.get_conversation());
                conversationView.scrollToBottom();
            }
            // Reset focus
            focusTimer.isRestoreFocus = true;
            focusTimer.start();
        }
    }

    Timer {
        id: responseEndTimer

        interval: 500
        repeat: false
        running: false
        onTriggered: {
            conversationView.setResponseInProgress(false);
        }
    }

    property var restartConfirmDialog: null
    
    function getRestartConfirmDialog() {
        if (!restartConfirmDialog) {
            var component = Qt.createComponent("Components/AppDialog.qml");
            if (component.status === Component.Ready) {
                restartConfirmDialog = component.createObject(voiceAssistantPage, {
                    "dialogTitle": "Reset Application",
                    "message": "Are you sure you want to reset the application?\nThis will clear your conversation and reconnect to the server.",
                    "standardButtonTypes": DialogButtonBox.Yes | DialogButtonBox.No,
                    "yesButtonText": "Reset",
                    "noButtonText": "Cancel",
                    "acceptButtonColor": ThemeManager.backgroundColor
                });
                
                restartConfirmDialog.accepted.connect(function() {
                    // Reset the application
                    restartApplication();
                });
            } else {
                console.error("Failed to create restart dialog:", component.errorString());
            }
        }
        return restartConfirmDialog;
    }

    property var confirmServerChangeDialog: null
    
    function getConfirmServerChangeDialog() {
        if (!confirmServerChangeDialog) {
            var component = Qt.createComponent("Components/AppDialog.qml");
            if (component.status === Component.Ready) {
                confirmServerChangeDialog = component.createObject(voiceAssistantPage, {
                    "dialogTitle": "Server Connection",
                    "message": "Server connection lost. Do you want to reconnect?",
                    "standardButtonTypes": DialogButtonBox.Yes | DialogButtonBox.No,
                    "yesButtonText": "Reconnect",
                    "noButtonText": "Cancel",
                    "acceptButtonColor": ThemeManager.backgroundColor
                });
                
                confirmServerChangeDialog.accepted.connect(function() {
                    // Use the shared reconnection function
                    reconnectToServer();
                });
                
                confirmServerChangeDialog.rejected.connect(function() {
                    // User chose not to reconnect
                    voiceAssistantPage.state = "disconnected";
                });
            } else {
                console.error("Failed to create server change dialog:", component.errorString());
            }
        }
        return confirmServerChangeDialog;
    }

    property var batteryWarningDialog: null
    
    function getBatteryWarningDialog() {
        if (!batteryWarningDialog) {
            var component = Qt.createComponent("Components/BatteryWarningDialog.qml");
            if (component.status === Component.Ready) {
                batteryWarningDialog = component.createObject(voiceAssistantPage);
                
                batteryWarningDialog.shutdownRequested.connect(function() {
                    console.log("Critical battery shutdown requested");
                    messageToast.showMessage("Shutting down due to critical battery...", 3000);

                    // Signal critical battery shutdown
                    if (bridge && bridge.ready) {
                        // Send BTN_POWER packet for coordinated shutdown
                        var success = bridge.sendPowerShutdownSignal();
                        if (!success) {
                            console.log("Warning: Failed to send power shutdown signal via UART");
                        }
                    }
                });
                
                batteryWarningDialog.acknowledged.connect(function() {
                    batteryWarningDialog.close();
                });
            } else {
                console.error("Failed to create battery warning dialog:", component.errorString());
            }
        }
        return batteryWarningDialog;
    }

    // Battery monitoring timer
    Timer {
        id: batteryMonitorTimer
        interval: 10000 // Check every 10 seconds
        repeat: true
        running: true

        property bool lowBatteryWarningShown: false
        property bool criticalBatteryWarningShown: false
        property bool temperatureWarningShown: false

        onTriggered: {
            if (bridge && bridge.ready) {
                var batteryInfo = bridge.getBatteryInfo();

                // Check for temperature warning (>55°C)
                if (batteryInfo.isTemperatureWarning) {
                    if (!temperatureWarningShown) {
                        console.log("Battery temperature warning: " + batteryInfo.temperature + "°C");
                        messageToast.showMessage("Battery temperature high: " + Math.round(batteryInfo.temperature) + "°C", 5000);
                        temperatureWarningShown = true;
                    }
                } else {
                    temperatureWarningShown = false;
                }

                // Check for critical battery (≤1%) - enhanced charging check
                if (batteryInfo.isCritical && !batteryInfo.isCharging && batteryInfo.current_ma <= 0) {
                    if (!criticalBatteryWarningShown) {
                        console.log("Critical battery detected: " + batteryInfo.capacity + "% (current: " + batteryInfo.current_ma + "mA)");
                        var dialog = getBatteryWarningDialog();
                        dialog.batteryLevel = batteryInfo.capacity;
                        dialog.isCritical = true;
                        dialog.isCharging = batteryInfo.isCharging;
                        dialog.open();
                        criticalBatteryWarningShown = true;

                        // Auto-shutdown after 30 seconds if not charging
                        criticalShutdownTimer.start();
                    }
                } else
                // Check for low battery (≤15%) - enhanced charging check
                if (batteryInfo.isLow && !batteryInfo.isCharging && batteryInfo.current_ma <= 0) {
                    if (!lowBatteryWarningShown && !criticalBatteryWarningShown) {
                        console.log("Low battery detected: " + batteryInfo.capacity + "% (current: " + batteryInfo.current_ma + "mA)");
                        var dialog = getBatteryWarningDialog();
                        dialog.batteryLevel = batteryInfo.capacity;
                        dialog.isCritical = false;
                        dialog.isCharging = batteryInfo.isCharging;
                        dialog.open();
                        lowBatteryWarningShown = true;
                    }
                } else
                // Reset warnings if charging or battery level improved
                if (batteryInfo.isCharging || batteryInfo.current_ma > 0 || batteryInfo.capacity > 20) {
                    lowBatteryWarningShown = false;
                    if (batteryInfo.capacity > 5) {
                        criticalBatteryWarningShown = false;
                        criticalShutdownTimer.stop();
                    }
                }
            }
        }
    }

    // Critical battery auto-shutdown timer
    Timer {
        id: criticalShutdownTimer
        interval: 30000
        repeat: false
        running: false

        onTriggered: {
            console.log("Auto-shutdown due to critical battery");
            messageToast.showMessage("Auto-shutdown: Critical battery level", 2000);

            if (bridge && bridge.ready) {
                // Send BTN_POWER packet for coordinated shutdown
                var success = bridge.sendPowerShutdownSignal();
                if (!success) {
                    console.log("Warning: Failed to send power shutdown signal via UART");
                }
            }
        }
    }

    // Cleanup lazy-loaded dialogs
    Component.onDestruction: {
        if (serverListDialog) {
            serverListDialog.destroy();
        }
        if (restartConfirmDialog) {
            restartConfirmDialog.destroy();
        }
        if (confirmServerChangeDialog) {
            confirmServerChangeDialog.destroy();
        }
        if (batteryWarningDialog) {
            batteryWarningDialog.destroy();
        }
    }
}
