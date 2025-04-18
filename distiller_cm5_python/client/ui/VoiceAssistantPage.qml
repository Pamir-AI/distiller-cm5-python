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
    
    signal selectNewServer()

    onServerNameChanged: {
        _serverName = serverName;
    }

    // === Focus Navigation Order ===
    // 1. header.backButton
    // 2. conversationView
    // 3. inputArea.voiceButton
    // (Wraps around)
    property list<Item> focusOrder: [header.backButtonAlias, conversationView, inputArea.voiceButtonAlias]
    property int currentFocusItemIndex: -1

    // --- Function to handle focus cycling --- 
    function cycleFocus(direction) {
        if (focusOrder.length > 0) {
            let nextIndex = (currentFocusItemIndex + direction + focusOrder.length) % focusOrder.length;
            if (focusOrder[nextIndex] && typeof focusOrder[nextIndex].forceActiveFocus === 'function') { 
                focusOrder[nextIndex].forceActiveFocus();
                currentFocusItemIndex = nextIndex;
                console.log("VoiceAssistantPage: Focus cycled to item index", currentFocusItemIndex);
            } else {
                console.warn("VoiceAssistantPage: Could not cycle focus, target item invalid at index", nextIndex);
            }
        }
    }

    Component.onCompleted: {
        // Set initial focus (e.g., on the voice button - now index 2)
        if (focusOrder.length > 2) { // Check if items exist
            currentFocusItemIndex = 2; // Start on voiceButton (index 2)
            Qt.callLater(function() { // Use callLater for safety
                 if (focusOrder[currentFocusItemIndex]) {
                    focusOrder[currentFocusItemIndex].forceActiveFocus();
                    console.log("VoiceAssistantPage: Initial focus set on item index", currentFocusItemIndex);
                 }
            });
        }
    }

    // --- Restore page-level Keys.onPressed handler --- 
    Keys.onPressed: (event) => {
        let handled = false;
        let direction = 0;
        let currentItem = focusOrder.length > 0 && currentFocusItemIndex >= 0 ? focusOrder[currentFocusItemIndex] : null;

        // --- Determine action based on key and focused item --- 
        if (event.key === Qt.Key_Up) {
            direction = -1;
            if (currentItem === conversationView) {
                // Scroll Up
                conversationView.contentY = Math.max(0, conversationView.contentY - 50); // Scroll by 50 pixels
                console.log("VoiceAssistantPage: Scrolled ConversationView UP");
                handled = true;
            } else {
                // Cycle focus
                cycleFocus(direction);
                handled = true;
            }
        } else if (event.key === Qt.Key_Down) {
            direction = 1;
            if (currentItem === conversationView) {
                // Scroll Down
                conversationView.contentY = Math.min(conversationView.contentHeight - conversationView.height, conversationView.contentY + 50); // Scroll by 50 pixels
                console.log("VoiceAssistantPage: Scrolled ConversationView DOWN");
                handled = true;
            } else {
                 // Cycle focus
                cycleFocus(direction);
                handled = true;
            }
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Select) {
            if (currentItem && currentItem !== conversationView && typeof currentItem.clicked === 'function') {
                // Activate Button
                console.log("VoiceAssistantPage: Activating item index", currentFocusItemIndex);
                currentItem.clicked();
                handled = true;
            } else if (currentItem === conversationView) {
                 // Do nothing when Select is pressed on ConversationView
                console.log("VoiceAssistantPage: Select ignored on ConversationView");
                handled = true; 
            } else {
                console.log("VoiceAssistantPage: Select key ignored, no valid button focused.");
                // Optional: Add feedback if Select is pressed with no valid target?
                handled = false;
            }
        }

        // --- Original focus cycling logic (now within Up/Down handling or unused) ---
        // if (handled) {
        //     cycleFocus(direction); // Use the helper function
        // }

        event.accepted = handled;
    }
    // --- End Restore --- 

    // Header area with server name and status
    VoiceAssistantPageHeader {
        id: header

        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 70 // Increased height to accommodate wrapping status text
        serverName: _serverName
        statusText: voiceAssistantPage.statusText
        isConnected: bridge.isConnected
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
            bridge.disconnectFromServer();
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
        // Simple model using direct string array
        model: bridge.get_conversation()

        // Force model refresh when conversation changes
        Connections {
            function onConversationChanged() {
                conversationView.updateModel(bridge.get_conversation());
            }

            target: bridge
        }
    }

    // Message toast
    MessageToast {
        id: messageToast

        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: inputArea.top
        anchors.bottomMargin: ThemeManager.spacingNormal
    }

    // Input area
    InputArea {
        id: inputArea

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 8
        z: 2 // Ensure input area is above other elements
        isListening: voiceAssistantPage.isListening
        isProcessing: voiceAssistantPage.isProcessing
        compact: false
        onTextSubmitted: function(messageText) {
            statusText = "Processing...";
            isProcessing = true;
            // Set response in progress to lock scrolling
            conversationView.setResponseInProgress(true);
            bridge.submit_query(messageText);
        }
        onVoiceToggled: function(listening) {
            if (listening) {
                isListening = true;
                statusText = "Listening...";
                bridge.start_listening();
            } else {
                isListening = false;
                statusText = "Processing...";
                isProcessing = true;
                // Set response in progress to lock scrolling
                conversationView.setResponseInProgress(true);
                bridge.stop_listening();
            }
        }
    }

    // Connect to bridge signals
    Connections {
        target: bridge
        
        function onMessageReceived(message, timestamp) {
            isProcessing = false;
            isListening = false;
            statusText = "Ready";
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
        
        function onResponseStopped() {
            isProcessing = false;
            statusText = "Ready";
            // Enable scrolling when response is stopped
            conversationView.setResponseInProgress(false);
            
            // Force update the input area to ensure it's usable
            inputArea.isProcessing = false;
            
            messageToast.showMessage("Response stopped", 1500);
        }

        function onErrorOccurred(errorMessage) {
            messageToast.showMessage("Error: " + errorMessage, 3000);
            isProcessing = false;
            isListening = false;
            statusText = "Ready";
            // Enable scrolling on error
            conversationView.setResponseInProgress(false);
        }

        function onStatusChanged(newStatus) {
            statusText = newStatus;
            // Update isProcessing based on status
            // Consider processing/streaming as 'processing' states
            isProcessing = (newStatus === "Processing query..." || newStatus === "Streaming response...");
            // Ensure scrolling is enabled if we transition out of processing/streaming
            if (!isProcessing) {
                conversationView.setResponseInProgress(false);
            }
        }
    }

    // Timer to delay disabling response mode to ensure UI is updated
    Timer {
        id: responseEndTimer

        interval: 500 // Half-second delay
        repeat: false
        onTriggered: {
            // Response complete, enable scrolling again
            conversationView.setResponseInProgress(false);
        }
    }
}
