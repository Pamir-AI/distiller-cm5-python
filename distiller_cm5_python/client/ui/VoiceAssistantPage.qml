import "Components"
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

PageBase {
    id: voiceAssistantPage
    
    pageName: "Voice Assistant"

    // Use property setter pattern to ensure component updates
    property string _serverName: "MCP Server"
    property string serverName: _serverName
    property bool isListening: false
    property bool isProcessing: false
    property string statusText: "Ready"
    property string inputBuffer: ""
    property var focusableItems: []
    property var previousFocusedItem: null
    // Add a property to store the full transcription result
    property string lastTranscription: ""

    signal selectNewServer()

    onServerNameChanged: {
        _serverName = serverName;
    }
    
    // Collect all focusable items on this page
    function collectFocusItems() {
        console.log("VoiceAssistantPage: Collecting focusable items");
        focusableItems = []
        
        // Add buttons from InputArea
        if (inputArea) {
            console.log("InputArea found, adding buttons");
            
            // Access buttons through the exposed properties
            if (inputArea.settingsButton && inputArea.settingsButton.navigable) {
                console.log("Adding settings button to focusable items");
                focusableItems.push(inputArea.settingsButton)
            }
            
            if (inputArea.voiceButton && inputArea.voiceButton.navigable) {
                console.log("Adding voice button to focusable items");
                focusableItems.push(inputArea.voiceButton)
            }
            
            // Send Button removed from focus list
            // if (inputArea.sendButton && inputArea.sendButton.navigable) {
            //     console.log("Adding send button to focusable items");
            //     focusableItems.push(inputArea.sendButton)
            // }
        } else {
            console.log("InputArea not found or not fully initialized yet");
        }
        
        // Add server select button in header if present
        if (header && header.serverSelectButton && header.serverSelectButton.navigable) {
            console.log("Adding server select button to focusable items");
            focusableItems.push(header.serverSelectButton)
        }
        
        console.log("Total focusable items: " + focusableItems.length);
        
        // Initialize focus manager with conversation view for scrolling
        FocusManager.initializeFocusItems(focusableItems, conversationView)
    }
    
    // Function to ensure input area buttons are focused if nothing else is
    function ensureFocusableItemsHaveFocus() {
        console.log("Ensuring something has focus");
        // If no focus or focus index is -1, reset focus to input area
        if (FocusManager.currentFocusIndex < 0 || FocusManager.currentFocusItems.length === 0) {
            console.log("Focus needs to be reset");
            // Re-collect focus items to ensure they're registered
            collectFocusItems();
            
            // Set focus to one of the input buttons
            if (inputArea && inputArea.voiceButton && inputArea.voiceButton.navigable) {
                console.log("Setting focus to voice button");
                FocusManager.setFocusToItem(inputArea.voiceButton);
            } else if (inputArea && inputArea.settingsButton && inputArea.settingsButton.navigable) {
                console.log("Setting focus to settings button");
                FocusManager.setFocusToItem(inputArea.settingsButton);
            } else if (focusableItems.length > 0) {
                console.log("Setting focus to first item in list");
                FocusManager.setFocusToItem(focusableItems[0]);
            }
        }
    }

    Component.onCompleted: {
        // Collect focusable items after component is fully loaded
        console.log("VoiceAssistantPage completed, scheduling focus collection");
        Qt.callLater(collectFocusItems);
    }

    // Add a timer to ensure focus items are collected after everything is fully loaded
    Timer {
        id: focusInitTimer
        interval: 500
        running: true
        repeat: false
        onTriggered: {
            console.log("Focus init timer triggered");
            collectFocusItems();
            
            // Set initial focus to voice button
            if (inputArea && inputArea.voiceButton && inputArea.voiceButton.navigable) {
                FocusManager.setFocusToItem(inputArea.voiceButton);
            }
        }
    }

    // Connect to bridge ready signal
    Connections {
        target: bridge
        
        function onBridgeReady() {
            // Initialize conversation when bridge is ready
            if (conversationView) {
                conversationView.updateModel(bridge.get_conversation());
            }
        }
    }

    // --- Connect to AppController for Whisper Signals/Slots ---
    Connections {
        target: AppController
        ignoreUnknownSignals: true // Good practice

        function onRecordingStateChanged(is_recording) {
            console.log("QML received recordingStateChanged:", is_recording)
            isListening = is_recording
            statusText = is_recording ? "Listening..." : "Ready"
            // Update voice button visual state (might need adjustment based on actual button implementation)
            if (inputArea && inputArea.voiceButton) {
                inputArea.voiceButton.checked = is_recording
                // Optionally change icon or style here too based on is_recording
                // e.g., inputArea.voiceButton.icon.source = is_recording ? "..." : "..."
            }
            if (is_recording) {
                // Clear previous transcription when starting new recording
                lastTranscription = ""
                inputBuffer = "" // Clear text input field when starting voice
            } else {
                 statusText = "Processing..." // Show processing after recording stops
            }
        }

        function onTranscriptionUpdate(transcription) {
            // console.log("QML received transcriptionUpdate:", transcription)
            // Append segment to the input buffer in real-time (optional)
            // inputBuffer = inputBuffer + transcription + " " 
            // Alternatively, update status or a dedicated field
            // statusText = "Transcribing: " + transcription
        }

        function onTranscriptionComplete(full_text) {
            console.log("QML received transcriptionComplete:", full_text)
            if (full_text === "[Transcription Error]") {
                 statusText = "Error during transcription."
                 // Show an error message to the user, e.g., using MessageToast
                 messageToast.showMessage("Transcription Failed", 2000)
                 inputBuffer = "" // Clear potentially partial input
            } else if (full_text.trim() !== "") {
                 lastTranscription = full_text
                 // inputBuffer = full_text // Don't put text in removed input field
                 statusText = "Sending..." 
                 // Optional: Automatically send the transcribed text
                 if (bridge && bridge.ready) {
                     console.log("Sending transcribed text:", full_text)
                     bridge.submit_query(full_text)
                 } else {
                     console.error("Bridge not ready, cannot send transcription")
                     statusText = "Error: Not Connected" // Update status
                     messageToast.showMessage("Error: Not connected", 2000)
                 }
                 // Note: isProcessing state will be reset by onMessageReceived from bridge
                 // or potentially after a timeout if send fails or no response comes.
            } else {
                 statusText = "Ready (No speech detected)" // Or just "Ready"
                 // inputBuffer = "" // No input buffer to clear
            }
             isProcessing = false // Ensure processing state is reset
        }
    }
    // --- End AppController Connections ---

    // Header area with server name and status
    VoiceAssistantPageHeader {
        id: header

        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 70 // Increased height to accommodate wrapping status text
        serverName: _serverName
        statusText: voiceAssistantPage.statusText
        isConnected: bridge && bridge.ready ? bridge.isConnected : false
        
        onServerSelectClicked: {
            // Store the currently focused item before showing dialog
            previousFocusedItem = FocusManager.currentFocusItems[FocusManager.currentFocusIndex];
            confirmServerChangeDialog.open();
        }
    }

    // Confirmation dialog for server change 
    AppDialog {
        id: confirmServerChangeDialog

        dialogTitle: "Change Server"
        message: "Are you sure you want to change servers? Current conversation will be lost."
        
        // Configure the standard buttons 
        standardButtonTypes: DialogButtonBox.Yes | DialogButtonBox.No
        
        // Button text customization
        yesButtonText: "Proceed"
        noButtonText: "Cancel"
        
        // Use accent color for the positive button
        acceptButtonColor: ThemeManager.accentColor
        
        onAccepted: {
            // Disconnect from current server
            if (bridge && bridge.ready) {
                bridge.disconnectFromServer();
            }
            // Go back to server selection
            voiceAssistantPage.selectNewServer();
        }
        
        onRejected: {
            // Restore focus to the previously focused item when canceling
            restoreFocusTimer.start();
        }
        
        // Handle dialog closure
        onClosed: {
            // If dialog is rejected (Cancel pressed), restore focus
            if (!visible && !accepted) {
                restoreFocusTimer.start();
            }
        }
    }

    // Conversation display area
    ConversationView {
        id: conversationView

        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: inputArea.top
        anchors.bottomMargin: 4 // Add a gap between conversation and input area
        anchors.margins: ThemeManager.spacingNormal

        // Force model refresh when conversation changes
        Component.onCompleted: {
            if (bridge && bridge.ready) {
                updateModel(bridge.get_conversation());
            } else {
                updateModel([]);
            }
        }

        Connections {
            target: bridge && bridge.ready ? bridge : null
            
            function onConversationChanged() {
                conversationView.updateModel(bridge.get_conversation());
            }
            
            function onMessageReceived(message, timestamp) {
                isProcessing = false;
                isListening = false;
                statusText = "Ready";
                
                // Explicitly clear and reset the input area
                inputBuffer = "";
                
                // Delay turning off response mode slightly to ensure the final message is rendered
                responseEndTimer.start();
            }
            
            function onListeningStarted() {
                isListening = true;
                statusText = "Listening...";
                messageToast.showMessage("Listening...", 1500);
            }
            
            function onListeningStopped() {
                isListening = false;
                statusText = "Processing...";
                isProcessing = true;
                // Set response in progress to lock scrolling
                conversationView.setResponseInProgress(true);
            }
            
            function onErrorOccurred(errorMessage) {
                // Log the error to console for developer debugging
                console.error("Error occurred in bridge: " + errorMessage);
                
                // Show error toast with appropriate duration based on message length
                var displayDuration = Math.max(3000, Math.min(errorMessage.length * 75, 8000));
                messageToast.showMessage("Error: " + errorMessage, displayDuration);
                
                // Update UI state
                isProcessing = false;
                isListening = false;
                statusText = "Ready";
                
                // Enable scrolling on error
                conversationView.setResponseInProgress(false);
                
                // If error is related to connection, suggest reconnecting
                if (errorMessage.toLowerCase().includes("connect") || 
                    errorMessage.toLowerCase().includes("server") ||
                    errorMessage.toLowerCase().includes("timeout")) {
                    // Show reconnection dialog after a brief delay
                    reconnectionTimer.start();
                }
            }
            
            function onStatusChanged(newStatus) {
                statusText = newStatus;
            }
        }
    }

    // Message toast
    MessageToast {
        id: messageToast

        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: inputArea.top
        anchors.bottomMargin: ThemeManager.spacingNormal
    }

    // Full input area with buttons row
    InputArea {
        id: inputArea
        
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 8
        
        isListening: voiceAssistantPage.isListening
        isProcessing: voiceAssistantPage.isProcessing
        
        onSettingsClicked: {
            // Navigate to the settings page using the application-defined function
            if (mainWindow && typeof mainWindow.pushSettingsPage === "function") {
                mainWindow.pushSettingsPage();
            }
        }

        // Connect the new InputArea signals to AppController slots
        onVoicePressed: {
            console.log("InputArea voicePressed signal received by page.")
            AppController.startRecording()
        }
        onVoiceReleased: {
            console.log("InputArea voiceReleased signal received by page.")
            AppController.stopAndTranscribe()
        }
    }
    
    // Reconnection suggestion timer
    Timer {
        id: reconnectionTimer
        
        interval: 500
        repeat: false
        running: false
        
        onTriggered: {
            // Save the current focus before showing dialog
            previousFocusedItem = FocusManager.currentFocusItems[FocusManager.currentFocusIndex];
            // Show reconnection dialog
            confirmServerChangeDialog.open();
        }
    }
    
    // Response end timer to delay turning off response in progress mode
    Timer {
        id: responseEndTimer
        
        interval: 300
        repeat: false
        running: false
        
        onTriggered: {
            // Turn off response in progress mode
            conversationView.setResponseInProgress(false);
        }
    }

    // Timer to restore focus after dialog is closed
    Timer {
        id: restoreFocusTimer
        interval: 50 // Short delay to ensure focus is set after dialog closes
        repeat: false
        running: false
        onTriggered: {
            if (previousFocusedItem) {
                FocusManager.setFocusToItem(previousFocusedItem);
            } else {
                // Fallback if previous item is lost
                ensureFocusableItemsHaveFocus(); 
            }
            previousFocusedItem = null; // Clear stored item
        }
    }

    // --- Key Handling ---
    focus: true // Ensure the page receives key events
    Keys.onPressed: (event) => {
        if (event.key === Qt.Key_Enter || event.key === Qt.Key_Return) {
            let currentItem = FocusManager.getCurrentFocusItem();
            if (currentItem === inputArea.voiceButton) {
                console.log("Enter pressed on voiceButton, intercepting default activation.");
                // We don't want Enter to toggle the voice button via FocusManager activation.
                // If keyboard push-to-talk is desired, logic would go here.
                // For now, just consume the event.
                event.accepted = true;
                // DO NOT CALL FocusManager.handleKeyPress(event) here
            } else {
                // Allow Enter to proceed for other elements (e.g., send button, future text inputs)
                // and let FocusManager handle standard activation if needed.
                console.log("Enter pressed on other item, allowing default handling.");
                event.accepted = false; // Explicitly allow propagation
                FocusManager.handleKeyPress(event); // Allow FocusManager to handle activation
            }
        } else {
            // Let FocusManager handle Up/Down/Other keys
            FocusManager.handleKeyPress(event);
        }
    }
    // --- End Key Handling ---
}

