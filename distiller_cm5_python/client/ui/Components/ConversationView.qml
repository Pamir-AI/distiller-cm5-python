import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ListView {
    id: conversationView
    objectName: "conversationViewList"

    // Add border to indicate focus/scroll mode
    border.width: activeFocus ? 2 : 0 // Show border only when focused
    border.color: ThemeManager.highlightColor // Use highlight color for focus border

    // Properties to track user scrolling and state
    property bool userScrolling: false
    property bool atBottom: true
    property real lastContentY: 0
    property real lastContentHeight: 0
    property bool responseInProgress: false // Track if a response is being generated

    // Update function for external callers
    function setResponseInProgress(inProgress) {
        responseInProgress = inProgress;
        if (inProgress) {
            // Force scroll to bottom when response starts
            positionViewAtEnd();
            atBottom = true;
        }
    }

    // Function to determine if view is at the bottom
    function checkIfAtBottom() {
        // Consider at bottom if within 50 pixels of the end
        var viewEnd = contentY + height;
        var tolerance = 50;
        atBottom = (contentHeight - viewEnd) < tolerance;
    }

    // Method to update the model and scroll to bottom conditionally
    function updateModel(newModel) {
        var wasAtBottom = atBottom;
        model = newModel;
        // Always scroll to bottom during response or if we were already at the bottom
        if (responseInProgress || wasAtBottom)
            Qt.callLater(positionViewAtEnd);
    }

    clip: true
    spacing: ThemeManager.spacingSmall
    // Always enable interaction
    interactive: true
    // Track when view is at the bottom
    onContentYChanged: {
        // Only check when not user scrolling to avoid unnecessary calculations
        if (!userScrolling)
            checkIfAtBottom();
    }
    // Track when user is manually scrolling
    onMovementStarted: {
        // If response is in progress, force scroll to bottom
        if (responseInProgress) {
            positionViewAtEnd();
        } else {
            // Normal scrolling behavior
            userScrolling = true;
            lastContentY = contentY;
        }
    }
    onMovementEnded: {
        userScrolling = false;
        checkIfAtBottom();
    }
    // For auto-scrolling when content changes
    onContentHeightChanged: {
        // Always scroll to bottom when response is in progress
        // or if we were already at the bottom, or this is the first content
        if (responseInProgress || atBottom || lastContentHeight === 0)
            Qt.callLater(positionViewAtEnd);

        lastContentHeight = contentHeight;
    }
    // Enable caching for better performance
    cacheBuffer: 1000

    // Add a scroll-to-bottom button
    AppRoundButton {
        id: scrollToBottomButton
        
        width: 32
        height: 32
        iconText: "↓"
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: ThemeManager.spacingSmall
        visible: !atBottom && contentHeight > height && !responseInProgress
        z: 1 // Ensure it's above content
        
        onClicked: {
            conversationView.positionViewAtEnd();
            atBottom = true;
        }
    }

    // Delegate for message items
    delegate: MessageItem {
        width: ListView.view.width
        messageText: typeof modelData === "string" ? modelData : ""
        compact: true
        isLastMessage: index === conversationView.count - 1
        isResponding: conversationView.responseInProgress && index === conversationView.count - 1
    }

    focus: true
    onActiveFocusChanged: console.log("--- ConversationView activeFocus changed: " + activeFocus)
    
    // --- Temporarily comment out key handler to test propagation ---
    // Keys.onPressed: (event) => {
    //     if (event.key === Qt.Key_Up || event.key === Qt.Key_Down) {
    //         // Ignore Up/Down keys to allow page-level navigation
    //         console.log("--- ConversationView ignored key: ", event.key);
    //         event.accepted = false; 
    //     } else {
    //         // Allow other keys (like PageUp/Down for default scrolling) to work
    //         event.accepted = false; 
    //     }
    // }
    // --- End temporary comment out ---
}
