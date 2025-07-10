import QtQuick

ListView {
    id: conversationView

    // Properties for state tracking - simplified
    property bool responseInProgress: false
    // Track if a response is being generated
    property bool navigable: true
    // Make focusable for keyboard navigation
    property bool visualFocus: false
    // For focus management
    property bool scrollModeActive: false
    // Track if scroll mode is active
    // Expose scrolling animation for FocusManager
    property alias scrollAnimation: smoothScrollAnimation

    // Signal to notify when scroll mode changes
    signal scrollModeChanged(bool active)

    // Update function for external callers
    function setResponseInProgress(inProgress) {
        responseInProgress = inProgress;
        
        // Only auto-scroll if we're not in scroll mode and starting a response
        if (inProgress && !scrollModeActive) {
            Qt.callLater(function() {
                if (!scrollModeActive) {
                    positionViewAtEnd();
                }
            });
        }
    }

    // Force scroll to bottom immediately
    function scrollToBottom() {
        positionViewAtEnd();
    }
    
    // Reset scroll position if it gets stuck
    function resetScrollPosition() {
        if (contentHeight <= height) {
            contentY = 0;
        } else {
            // Ensure we're within valid bounds
            var maxScrollY = Math.max(0, contentHeight - height);
            if (contentY > maxScrollY) {
                contentY = maxScrollY;
            } else if (contentY < 0) {
                contentY = 0;
            }
        }
        console.log("Reset scroll position - contentY=" + contentY + ", contentHeight=" + contentHeight + ", height=" + height);
    }
    
    // Navigate to top of conversation
    function scrollToTop() {
        contentY = 0;
    }
    
    // Navigate to specific position with bounds checking
    function scrollToPosition(targetY) {
        var maxScrollY = Math.max(0, contentHeight - height);
        contentY = Math.min(Math.max(targetY, 0), maxScrollY);
    }

    // Method to update the model and scroll to bottom conditionally
    function updateModel(newModel) {
        // Record current position state
        var wasAtEnd = atYEnd;
        var wasInScrollMode = scrollModeActive;
        
        // Update model
        model = newModel;
        
        // Only auto-scroll if we're not in scroll mode and were at the end
        if (!wasInScrollMode && (responseInProgress || wasAtEnd)) {
            // Use a small delay to prevent racing with other scroll operations
            Qt.callLater(function() {
                if (!scrollModeActive) {
                    positionViewAtEnd();
                }
            });
        }
    }

    objectName: "conversationView"
    focus: visualFocus
    clip: true
    spacing: ThemeManager.spacingSmall
    interactive: true
    boundsBehavior: Flickable.StopAtBounds
    // Use ListView's built-in positioning features
    onContentHeightChanged: {
        if (!scrollModeActive && (responseInProgress || atYEnd)) {
            Qt.callLater(function() {
                if (!scrollModeActive) {
                    positionViewAtEnd();
                }
            });
        }
    }
    // Automatically scroll to the end when model changes during a response
    onModelChanged: {
        if (!scrollModeActive && (responseInProgress || atYEnd || count === 0)) {
            Qt.callLater(function() {
                if (!scrollModeActive) {
                    positionViewAtEnd();
                }
            });
        }
    }
    // Simplified scroll mode handling
    onScrollModeActiveChanged: {
        activeScrollModeInstructions.visible = scrollModeActive;
    }
    // Add keyboard handling for scroll mode with message-based scrolling
    Keys.onPressed: function(event) {
        if (scrollModeActive) {
            // Calculate scroll amount based on message content and screen size
            var averageMessageHeight = count > 0 ? (contentHeight / count) : height * 0.3;
            var minScrollAmount = Math.max(50, height * 0.2); // Minimum 50px or 20% of screen
            var maxScrollAmount = height * 0.8; // Maximum 80% of screen
            
            // Use message-based scrolling for better navigation
            var scrollAmount = Math.min(Math.max(averageMessageHeight * 0.8, minScrollAmount), maxScrollAmount);
            
            // For very long content, use larger scroll amounts
            if (contentHeight > height * 4) {
                scrollAmount = height * 0.6; // 60% of screen for long conversations
            }
            
            // Ensure minimum effective scroll amount
            if (scrollAmount < minScrollAmount) {
                scrollAmount = minScrollAmount;
            }
            
            if (event.key === Qt.Key_Down) {
                // Scroll down with proper bounds protection
                var maxScrollY = Math.max(0, contentHeight - height);
                var newContentY = Math.min(contentY + scrollAmount, maxScrollY);
                console.log("Scrolling down: contentY=" + contentY + " -> " + newContentY + ", maxScrollY=" + maxScrollY + ", scrollAmount=" + scrollAmount);
                contentY = newContentY;
                event.accepted = true;
            } else if (event.key === Qt.Key_Up) {
                // Scroll up with proper bounds protection
                var newContentY = Math.max(contentY - scrollAmount, 0);
                console.log("Scrolling up: contentY=" + contentY + " -> " + newContentY + ", scrollAmount=" + scrollAmount);
                contentY = newContentY;
                event.accepted = true;
            } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                // Exit scroll mode
                console.log("Exiting scroll mode");
                FocusManager.exitScrollMode();
                scrollModeChanged(false);
                event.accepted = true;
            }
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            // Enter scroll mode if there's content to scroll
            if (contentHeight > height) {
                console.log("Entering scroll mode - contentHeight=" + contentHeight + ", height=" + height + ", contentY=" + contentY);
                resetScrollPosition(); // Ensure we start with a valid scroll position
                FocusManager.enterScrollMode();
                scrollModeChanged(true);
                event.accepted = true;
            }
        }
    }

    // Animation with zero duration for compatibility with code expecting the animation
    NumberAnimation {
        id: smoothScrollAnimation

        target: conversationView
        property: "contentY"
        duration: 0 // No animation for e-ink
        easing.type: Easing.Linear
    }

    // Visual instruction when in focus but not in scroll mode
    Rectangle {
        id: scrollModeInstructions

        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: ThemeManager.spacingNormal
        height: scrollModeText.height + ThemeManager.spacingLarge
        width: scrollModeText.width + ThemeManager.spacingSmall * 3
        color: ThemeManager.textColor
        border.width: ThemeManager.borderWidth
        border.color: ThemeManager.textColor
        radius: ThemeManager.borderRadius
        visible: visualFocus && !scrollModeActive && conversationView.contentHeight > conversationView.height
        z: 2

        Text {
            id: scrollModeText

            anchors.centerIn: parent
            text: "Press Enter to enable scroll mode"
            color: ThemeManager.backgroundColor
            font: FontManager.small
        }

    }

    // Visual instruction when in scroll mode
    Rectangle {
        id: activeScrollModeInstructions

        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: ThemeManager.spacingNormal
        height: activeScrollModeText.height + ThemeManager.spacingLarge
        width: activeScrollModeText.width + ThemeManager.spacingSmall * 3
        color: ThemeManager.textColor
        border.width: ThemeManager.borderWidth
        border.color: ThemeManager.textColor
        radius: ThemeManager.borderRadius
        visible: scrollModeActive
        z: 2

        Text {
            id: activeScrollModeText

            anchors.centerIn: parent
            text: "Use ↑/↓ to scroll, Enter to exit"
            color: ThemeManager.backgroundColor
            font: FontManager.small
        }

    }

    // Delegate for message items
    delegate: MessageItem {
        width: ListView.view.width
        messageText: typeof modelData === "string" ? modelData : ""
        isLastMessage: index === conversationView.count - 1
        isResponding: conversationView.responseInProgress && index === conversationView.count - 1
    }

}
