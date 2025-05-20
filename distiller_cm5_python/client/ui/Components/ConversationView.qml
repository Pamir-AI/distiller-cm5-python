import QtQuick
import QtQuick.Layouts

ListView {
    id: conversationView

    // Core properties
    property bool responseInProgress: false
    property bool navigable: true
    property bool visualFocus: false
    property bool scrollModeActive: false
    property alias scrollAnimation: smoothScrollAnimation
    property int currentMessageIndex: -1
    property var messagePaginationInfo: ({})
    property int currentPaginationPage: 0

    // Signal for scroll mode changes
    signal scrollModeChanged(bool active)

    // Set response progress and scroll to bottom when needed
    function setResponseInProgress(inProgress) {
        responseInProgress = inProgress;
        if (inProgress)
            positionViewAtEnd();
    }

    // Force scroll to bottom
    function scrollToBottom() {
        positionViewAtEnd();
    }

    // Update model and handle scrolling
    function updateModel(newModel) {
        var wasAtEnd = atYEnd;
        model = newModel;
        if (responseInProgress || wasAtEnd)
            positionViewAtEnd();
        // Reset pagination info
        messagePaginationInfo = {};
        currentPaginationPage = 0;
    }

    // Calculate pagination for large messages
    function calculateMessagePagination() {
        messagePaginationInfo = {};
        for (var i = 0; i < count; i++) {
            var item = itemAtIndex(i);
            if (item && item.height > height * 0.8) {
                // If message is larger than 80% of visible area
                var pages = Math.ceil(item.height / (height * 0.8));
                messagePaginationInfo[i] = pages;
            }
        }
    }

    // Navigate to next message or page
    function navigateDown() {
        // Already at the last message and page, do nothing
        if (currentMessageIndex >= count - 1 && currentPaginationPage >= (messagePaginationInfo[currentMessageIndex] || 0) - 1) {
            return;
        }

        // Has pagination and not at last page
        if (messagePaginationInfo[currentMessageIndex] && currentPaginationPage < messagePaginationInfo[currentMessageIndex] - 1) {
            // Next page within same message
            currentPaginationPage++;
            var item = itemAtIndex(currentMessageIndex);
            if (item) {
                var pageSize = height * 0.8;
                var targetY = item.y + (currentPaginationPage * pageSize);
                contentY = Math.min(targetY, contentHeight - height);
            }
        } else {
            // Next message
            currentPaginationPage = 0;
            currentMessageIndex = Math.min(currentMessageIndex + 1, count - 1);
            positionViewAtIndex(currentMessageIndex, 0);
        }
    }

    // Navigate to previous message or page
    function navigateUp() {
        // Already at first message and page, do nothing
        if (currentMessageIndex <= 0 && currentPaginationPage <= 0) {
            return;
        }

        // On a paginated message and not at first page
        if (currentPaginationPage > 0) {
            // Previous page within same message
            currentPaginationPage--;
            var item = itemAtIndex(currentMessageIndex);
            if (item) {
                var pageSize = height * 0.8;
                var targetY = item.y + (currentPaginationPage * pageSize);
                contentY = Math.min(targetY, contentHeight - height);
            }
        } else {
            // Previous message
            currentMessageIndex = Math.max(currentMessageIndex - 1, 0);
            currentPaginationPage = 0;
            positionViewAtIndex(currentMessageIndex, 0);
        }
    }

    // ListView configuration
    objectName: "conversationView"
    focus: visualFocus
    clip: true
    spacing: ThemeManager.spacingSmall
    interactive: true
    boundsBehavior: Flickable.StopAtBounds

    // Auto-scroll handling
    onContentHeightChanged: {
        if (responseInProgress || atYEnd)
            positionViewAtEnd();
        Qt.callLater(calculateMessagePagination);
    }

    onModelChanged: {
        if (responseInProgress || atYEnd || count === 0)
            positionViewAtEnd();
        currentMessageIndex = -1;
        currentPaginationPage = 0;
    }

    // Scroll mode handling
    onScrollModeActiveChanged: {
        activeScrollModeInstructions.visible = scrollModeActive;
        if (scrollModeActive && currentMessageIndex === -1 && count > 0) {
            // Initialize to last message
            currentMessageIndex = count - 1;
            positionViewAtIndex(currentMessageIndex, 0);
        } else if (!scrollModeActive) {
            // Reset when exiting
            currentMessageIndex = -1;
            currentPaginationPage = 0;
        }
    }

    // Key navigation handling
    Keys.onPressed: function (event) {
        if (scrollModeActive) {
            if (event.key === Qt.Key_Down) {
                navigateDown();
                event.accepted = true;
            } else if (event.key === Qt.Key_Up) {
                navigateUp();
                event.accepted = true;
            } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                // Exit scroll mode
                FocusManager.exitScrollMode();
                scrollModeChanged(false);
                event.accepted = true;
            }
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            // Enter scroll mode if needed
            if (contentHeight > height) {
                FocusManager.enterScrollMode();
                scrollModeChanged(true);
                event.accepted = true;
            }
        }
    }

    // Zero-duration animation for compatibility
    NumberAnimation {
        id: smoothScrollAnimation
        target: conversationView
        property: "contentY"
        duration: 0 // No animation for e-ink
        easing.type: Easing.Linear
    }

    // Entry scroll instruction
    Rectangle {
        id: scrollModeInstructions
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: ThemeManager.spacingNormal
        width: parent.width
        height: scrollInstructionLayout.height + ThemeManager.spacingLarge
        color: ThemeManager.textColor
        border.width: ThemeManager.borderWidth
        border.color: ThemeManager.textColor
        radius: ThemeManager.borderRadius
        visible: visualFocus && !scrollModeActive && conversationView.contentHeight > conversationView.height
        z: 2

        ColumnLayout {
            id: scrollInstructionLayout
            anchors.centerIn: parent
            width: parent.width - ThemeManager.spacingNormal * 2
            spacing: 0

            Text {
                id: scrollModeText
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignHCenter
                text: "Press Enter to enable scroll mode"
                color: ThemeManager.backgroundColor
                font: FontManager.small
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideNone
                maximumLineCount: 2
            }
        }
    }

    // Active scroll instruction
    Rectangle {
        id: activeScrollModeInstructions
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: ThemeManager.spacingNormal
        width: parent.width
        height: activescrollInstructionLayout.height + ThemeManager.spacingLarge
        color: ThemeManager.textColor
        border.width: ThemeManager.borderWidth
        border.color: ThemeManager.textColor
        radius: ThemeManager.borderRadius
        visible: scrollModeActive
        z: 2

        ColumnLayout {
            id: activescrollInstructionLayout
            anchors.centerIn: parent
            width: parent.width - ThemeManager.spacingNormal * 2
            spacing: 0

            Text {
                id: activeScrollModeText
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignHCenter
                text: {
                    if (messagePaginationInfo[currentMessageIndex] && messagePaginationInfo[currentMessageIndex] > 1) {
                        return "Message " + (currentMessageIndex + 1) + "/" + count + " (Page " + (currentPaginationPage + 1) + "/" + messagePaginationInfo[currentMessageIndex] + "), Enter to exit";
                    } else {
                        return "Message " + (currentMessageIndex + 1) + "/" + count + ", Enter to exit";
                    }
                }
                color: ThemeManager.backgroundColor
                font: FontManager.small
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideNone
                maximumLineCount: 2
            }
        }
    }

    // Message item delegate
    delegate: MessageItem {
        id: delegateItem
        width: ListView.view.width
        messageText: typeof modelData === "string" ? modelData : ""
        isLastMessage: index === conversationView.count - 1
        isResponding: conversationView.responseInProgress && index === conversationView.count - 1
        navigable: !conversationView.scrollModeActive

        // Current message highlight
        Rectangle {
            anchors.fill: parent
            visible: conversationView.scrollModeActive && conversationView.currentMessageIndex === index
            color: ThemeManager.transparentColor
            border.color: ThemeManager.textColor
            border.width: 2
            radius: ThemeManager.borderRadius
        }

        onClicked: {
            if (!conversationView.scrollModeActive) {
                conversationView.positionViewAtIndex(index, 0);
            }
        }
    }

    Component.onCompleted: {
        Qt.callLater(calculateMessagePagination);
    }
}
