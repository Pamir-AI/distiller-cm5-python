import QtQuick

Rectangle {
    // Dynamic hint text based on state
    // Any external components connecting to stateChanged can now connect to onAppStateChanged

    id: voiceInputArea

    // Properties
    property bool isListening: false
    property bool isProcessing: false
    property bool isConnected: true // Add new property for connection status
    property string transcribedText: ""
    property bool showStatusHint: true // Enable status hint by default
    // State management - define possible states
    property string appState: "idle"
    // Possible values: "idle", "listening", "processing", "thinking", "executing_tool", "restoring_cache", "error"
    property string stateHint: getStateHint()
    // Expose button as property
    property alias voiceButton: voiceButton
    property alias resetButton: resetButton
    // Flag to track cache restore state specifically
    property bool cacheRestoring: appState === "restoring_cache"

    // Signals
    signal voiceToggled(bool listening)
    signal voicePressed()
    signal voiceReleased()
    signal resetClicked() // New signal for reset button
    signal appStateUpdated(string newState) // Renamed signal to avoid conflict with appStateChanged

    // Get appropriate hint text for current state
    function getStateHint() {
        if (!isConnected)
            return "Not connected";

        switch (appState) {
        case "idle":
            return "Tap to speak";
        case "listening":
            return "Listening...";
        case "processing":
            return "Processing audio...";
        case "thinking":
            return "Thinking...";
        case "executing_tool":
            return "Executing tool...";
        case "restoring_cache":
            return "Restoring cache...";
        case "error":
            return "Error - try again";
        default:
            return "Ready";
        }
    }

    // Set the app state and emit signal
    function setAppState(newState) {
        // Block state changes from restoring_cache to anything other than idle or error
        if (appState === "restoring_cache" && newState !== "idle" && newState !== "error" && newState !== "restoring_cache") {
            console.log("VoiceInputArea: Blocked state change from restoring_cache to " + newState);
            return ;
        }
        if (appState !== newState) {
            console.log("VoiceInputArea: State changing from " + appState + " to " + newState);
            appState = newState;
            stateHint = getStateHint();
            // Update legacy state properties for backward compatibility
            isListening = (newState === "listening");
            isProcessing = (newState === "processing" || newState === "thinking" || newState === "executing_tool" || newState === "restoring_cache");
            // If transitioning to idle, ensure button is enabled
            if (newState === "idle" && voiceButton) {
                voiceButton.enabled = isConnected;
                voiceButton.checked = false;
                resetButton.enabled = true;
            } else if (newState === "listening" && voiceButton) {
                voiceButton.checked = true;
                voiceButton.enabled = true;
                resetButton.enabled = false;
            } else if (newState === "processing" || newState === "thinking" || newState === "executing_tool") {
                if (voiceButton) {
                    voiceButton.checked = false;
                    voiceButton.enabled = false; // Disable during any processing state
                }
                resetButton.enabled = false;
            } else if (newState === "restoring_cache") {
                // Special handling for cache restoration - disable ALL buttons
                if (voiceButton) {
                    voiceButton.checked = false;
                    voiceButton.enabled = false; // Explicitly disable during cache restoration
                }
                resetButton.enabled = false;
                // Show appropriate hint text with stronger visibility
                stateHint = "Restoring cache...";
            } else if (newState === "error") {
                // Show error state
                if (voiceButton) {
                    voiceButton.checked = false;
                    voiceButton.enabled = isConnected;
                }
                resetButton.enabled = true;
            }
            // Signal app state change
            appStateUpdated(newState);
        }
    }

    // Functions to manage state
    function resetState() {
        console.log("VoiceInputArea: Resetting state");
        setAppState("idle");
        transcribedText = "";
        // Reset button states
        if (voiceButton) {
            voiceButton.checked = false;
            voiceButton.enabled = isConnected;
        }
        resetButton.enabled = true;
        // Force status update
        stateHint = getStateHint();
    }

    // Move to thinking state (for external calls)
    function setThinkingState() {
        setAppState("thinking");
    }

    // Move to tool execution state (for external calls)
    function setToolExecutionState() {
        setAppState("executing_tool");
    }

    // Set error state (for external calls)
    function setErrorState() {
        setAppState("error");
        // Automatically reset to idle after showing error briefly
        errorResetTimer.start();
    }

    // Connect to the automatically generated property change signal
    onAppStateChanged: {
        console.log("App state changed to: " + appState);
    }
    // Set the main container properties
    color: ThemeManager.backgroundColor
    height: transcribedText.trim().length > 0 ? 100 : 70
    z: 10 // Ensure this is always on top
    // Watch for changes to legacy properties and update state accordingly (for backward compatibility)
    onIsListeningChanged: {
        if (isListening && appState !== "listening")
            setAppState("listening");
        else if (!isListening && appState === "listening")
            setAppState("idle");
    }
    onIsProcessingChanged: {
        if (isProcessing && appState === "idle")
            setAppState("processing");
        else if (!isProcessing && (appState === "processing" || appState === "thinking" || appState === "executing_tool"))
            setAppState("idle");
    }
    onVoiceReleased: function() {
        // Double-check cache restoration state
        if (appState === "restoring_cache") {
            console.log("Voice release blocked - cache is being restored");
            return ;
        }
        if (bridge && bridge.ready && bridge.isConnected && isListening) {
            // First set state to processing explicitly
            setAppState("processing");
            // Trigger e-ink update *after* state changes are applied but before the blocking call
            if (typeof AppController !== 'undefined' && AppController.triggerEinkUpdate) {
                console.log("VoiceInputArea: Forcing e-ink update after setAppState('processing')");
                AppController.triggerEinkUpdate();
            }
            // Then call the bridge method after a minimal delay to allow UI event processing (including e-ink)
            Qt.callLater(function() {
                console.log("VoiceInputArea.onVoiceReleased: Calling bridge.stopAndTranscribe() after delay");
                bridge.stopAndTranscribe();
            });
        }
    }

    // Straight rectangle to fill the rest of the area without rounded bottom
    Rectangle {
        id: bottomFill

        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        color: ThemeManager.backgroundColor
    }

    // Timer to automatically reset from error state to idle
    Timer {
        id: errorResetTimer

        interval: 2000 // Show error state for 2 seconds
        repeat: false
        running: false
        onTriggered: {
            resetState();
        }
    }

    // Hint text that shows when any button is in focus
    Text {
        id: staticHintText

        anchors.top: parent.top
        anchors.topMargin: 8 // Reduced top margin
        anchors.horizontalCenter: parent.horizontalCenter
        text: {
            // Dynamic text based on which button has focus
            if (voiceButton.visualFocus)
                return voiceInputArea.stateHint;
            else if (resetButton.visualFocus)
                return "Reset App";
            else
                return "";
        }
        font.pixelSize: FontManager.fontSizeSmall
        font.family: FontManager.primaryFontFamily
        color: ThemeManager.textColor
        horizontalAlignment: Text.AlignHCenter
        z: 20 // Make sure it appears above everything
        // Show hint text whenever the app is not idle, or if a button has focus (and hint is enabled)
        visible: showStatusHint && (appState !== "idle" || (voiceButton.visualFocus || resetButton.visualFocus))
    }

    // Transcribed text display
    Rectangle {
        id: transcribedTextDisplay

        visible: transcribedText.trim().length > 0
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: staticHintText.bottom
        anchors.topMargin: 5 // Reduced top margin
        anchors.margins: 6 // Reduced margins
        height: transcribedTextLabel.contentHeight + 8 // Reduced height
        color: ThemeManager.backgroundColor
        border.width: ThemeManager.borderWidth
        border.color: ThemeManager.black // Always black border for contrast
        radius: ThemeManager.borderRadius
        z: 20 // Above the background rectangles

        Text {
            id: transcribedTextLabel

            anchors.fill: parent
            anchors.margins: 4 // Reduced margins
            text: transcribedText
            font.pixelSize: FontManager.fontSizeNormal
            font.family: FontManager.primaryFontFamily
            color: ThemeManager.textColor
            wrapMode: Text.WordWrap
            elide: Text.ElideRight
            maximumLineCount: 1
        }

    }

    // Button layout
    Item {
        id: buttonRow

        // Consistent button size - smaller for better layout
        property int borderWidth: ThemeManager.borderWidth

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 5 // Reduced margins for tighter fit
        height: ThemeManager.buttonHeight
        z: 20 // Above background rectangles

        Row {
            anchors.centerIn: parent
            spacing: ThemeManager.spacingLarge * 0.8 // Slightly reduced spacing for tighter fit

            // 1st button: Voice/Mic button in the center position
            AppButton {
                // This allows the binding to checked: voiceInputArea.isListening to work
                // We don't force the checked state here to let the binding handle it

                id: voiceButton

                property bool navigable: isConnected // Only navigable when connected
                property bool visualFocus: false
                property bool checked: voiceInputArea.isListening

                // Activate when Enter is pressed via FocusManager
                function activate() {
                    // Block activation during cache restoration
                    if (voiceInputArea.appState === "restoring_cache") {
                        console.log("VoiceButton.activate(): Blocked during cache restoration");
                        if (checked)
                            checked = false;

                        return ;
                    }
                    // Only allow activation when connected and not processing
                    if (!isConnected || voiceInputArea.appState === "processing" || voiceInputArea.appState === "thinking" || voiceInputArea.appState === "executing_tool")
                        return ;

                    // When activating with Enter key
                    if (!isListening) {
                        // Start listening
                        console.log("VoiceButton.activate(): Starting listening");
                        voiceInputArea.voicePressed();
                        setAppState("listening");
                    } else {
                        // Stop listening
                        console.log("VoiceButton.activate(): Stopping listening");
                        voiceInputArea.voiceReleased();
                        setAppState("processing");
                    }
                }

                width: ThemeManager.buttonHeight
                height: ThemeManager.buttonHeight
                isFlat: true
                // Disable button when not connected or when processing/thinking/executing/restoring cache
                enabled: (isConnected && voiceInputArea.appState !== "processing" && voiceInputArea.appState !== "thinking" && voiceInputArea.appState !== "executing_tool") || voiceInputArea.appState !== "restoring_cache"
                onClicked: {
                    if (voiceInputArea.appState === "restoring_cache") {
                        console.log("Voice button clicked during cache restoration - ignoring");
                        checked = false; // Ensure unchecked state
                        enabled = false; // Explicitly disable
                        return ;
                    }
                    // Only allow interaction when connected and not in any processing state
                    if (!isConnected || voiceInputArea.appState === "processing" || voiceInputArea.appState === "thinking" || voiceInputArea.appState === "executing_tool" || voiceInputArea.appState === "restoring_cache")
                        return ;

                    // Toggle listening state
                    console.log("VoiceButton.onClicked(), current state: " + checked);
                    if (!isListening) {
                        // Start listening
                        voiceInputArea.voicePressed();
                        setAppState("listening");
                    } else {
                        // Stop listening
                        voiceInputArea.voiceReleased();
                        setAppState("processing");
                    }
                }
                // Handle key press/release for Enter/Return
                Keys.onPressed: function(event) {
                    // Check if we're processing before handling key
                    if (!isConnected || voiceInputArea.appState === "processing" || voiceInputArea.appState === "thinking" || voiceInputArea.appState === "executing_tool") {
                        event.accepted = true;
                        return ;
                    }
                    if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                        event.accepted = true;
                        if (!isListening) {
                            // Start listening
                            voiceInputArea.voicePressed();
                            setAppState("listening");
                        }
                    }
                }
                Keys.onReleased: function(event) {
                    // Check if we're processing before handling key
                    if (!isConnected || (voiceInputArea.appState !== "listening" && voiceInputArea.appState !== "idle")) {
                        event.accepted = true;
                        return ;
                    }
                    if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                        if (isListening) {
                            // Stop listening
                            voiceInputArea.voiceReleased();
                            setAppState("processing");
                        }
                    }
                }
                backgroundColor: ThemeManager.backgroundColor // Solid color based on theme
                buttonRadius: width / 2

                // Voice icon content needs custom handling
                Rectangle {
                    // Clear custom styling from AppButton
                    parent: voiceButton
                    anchors.fill: parent
                    color: ThemeManager.backgroundColor

                    // High contrast highlight for e-ink when focused
                    Rectangle {
                        visible: voiceButton.visualFocus || voiceButton.pressed || true // Always visible
                        anchors.fill: parent
                        radius: width / 2
                        color: voiceButton.visualFocus ? ThemeManager.textColor : ThemeManager.backgroundColor
                        border.width: ThemeManager.borderWidth
                        border.color: ThemeManager.black
                        antialiasing: true
                    }

                    Text {
                        // Disabled microphone icon

                        id: micIcon

                        text: {
                            // If not connected, show "disabled" icon
                            if (!isConnected)
                                return "󱙱";

                            // Use the new state system for determining icon
                            switch (voiceInputArea.appState) {
                            case "listening":
                                return "󰍬"; // Listening
                            case "processing":
                            case "thinking":
                            case "executing_tool":
                                return "󰍯"; // Processing
                            case "restoring_cache":
                                return "󰃨"; // Cache/loading icon
                            case "error":
                                return "󱦉"; // Error symbol (warning icon)
                            default:
                                // idle
                                return "󰍮";
                            }
                        }
                        rightPadding: (!isConnected || voiceInputArea.appState === "restoring_cache") ? 4 : 0
                        anchors.centerIn: parent
                        font.pixelSize: parent.width * 0.45 // Slightly smaller for cleaner look
                        // Color based on connection state and focus state
                        color: voiceButton.visualFocus ? ThemeManager.backgroundColor : ThemeManager.textColor
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }

                }

            }

            // 2nd button: Reset button
            AppButton {
                id: resetButton

                property bool navigable: true
                property bool visualFocus: false

                objectName: "resetButton"
                width: ThemeManager.buttonHeight
                height: ThemeManager.buttonHeight
                isFlat: true
                buttonRadius: width / 2
                onClicked: voiceInputArea.resetClicked()

                // Reset icon content needs custom handling
                Rectangle {
                    // Clear custom styling from AppButton
                    parent: resetButton
                    anchors.fill: parent
                    color: ThemeManager.backgroundColor

                    // High contrast highlight for e-ink when focused
                    Rectangle {
                        visible: resetButton.visualFocus || resetButton.pressed || true // Always visible
                        anchors.fill: parent
                        radius: width / 2
                        color: resetButton.visualFocus ? ThemeManager.textColor : ThemeManager.backgroundColor
                        border.width: ThemeManager.borderWidth
                        border.color: ThemeManager.black
                        antialiasing: true
                    }

                    Text {
                        text: "↻" // Reset icon as text
                        font.pixelSize: parent.width * 0.5
                        font.family: FontManager.primaryFontFamily
                        color: resetButton.visualFocus ? ThemeManager.backgroundColor : ThemeManager.textColor
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        anchors.centerIn: parent
                    }

                }

            }

        }

    }

    Behavior on height {
        NumberAnimation {
            duration: 100
        }

    }

}
