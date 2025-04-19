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
            
            if (inputArea.sendButton && inputArea.sendButton.navigable) {
                console.log("Adding send button to focusable items");
                focusableItems.push(inputArea.sendButton)
            }
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
        
        // Hide secondary action
        showSecondaryAction: false
        
        // Use accent color for the positive button
        positiveButtonColor: ThemeManager.accentColor
        
        onAccepted: {
            // Disconnect from current server
            if (bridge && bridge.ready) {
                bridge.disconnectFromServer();
            }
            // Go back to server selection
            voiceAssistantPage.selectNewServer();
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
        
        onTextSubmitted: function(text) {
            if (bridge && bridge.ready && bridge.isConnected && !isProcessing) {
                inputBuffer = text;
                if (bridge.sendTextMessage(text)) {
                    isProcessing = true;
                    statusText = "Processing...";
                    // Set response in progress to lock scrolling
                    conversationView.setResponseInProgress(true);
                }
            }
        }
        
        onVoiceToggled: function(listening) {
            if (bridge && bridge.ready && bridge.isConnected && !isProcessing) {
                if (listening) {
                    bridge.startListening();
                } else {
                    bridge.stopListening();
                }
            }
        }
        
        onSettingsClicked: {
            // Navigate to the settings page using the application-defined function
            if (mainWindow && typeof mainWindow.pushSettingsPage === "function") {
                mainWindow.pushSettingsPage();
            }
        }
    }
    
    // Reconnection suggestion timer
    Timer {
        id: reconnectionTimer
        
        interval: 500
        repeat: false
        running: false
        
        onTriggered: {
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
}

