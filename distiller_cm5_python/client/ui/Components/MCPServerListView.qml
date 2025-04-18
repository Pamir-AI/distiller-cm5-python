import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: listContainer

    property var model: []

    signal serverSelected(string path)

    color: "transparent"
    Component.onCompleted: {
        // Give focus to ListView for keyboard navigation
        serverListView.forceActiveFocus();
    }

    // Empty state message directly in the container
    MCPPageEmptyState {
        anchors.centerIn: parent
        visible: model.length === 0
        title: "NO SERVERS FOUND"
        message: "Please ensure MCP servers are available\nin the mcp_server directory"
        compact: true
    }

    ListView {
        // Increased cache for smoother scrolling

        id: serverListView

        // Custom flick behavior
        property real lastY: 0
        property bool atBoundary: false
        // Overscroll protection
        property bool preventEdgeUpdate: false

        anchors.fill: parent
        anchors.leftMargin: ThemeManager.spacingSmall / 2
        anchors.rightMargin: ThemeManager.spacingSmall / 2
        spacing: 4 // Reduced spacing between items
        clip: true
        model: listContainer.model
        // Edge behavior fixes
        boundsMovement: Flickable.StopAtBounds
        // Prevent movement beyond edges
        boundsBehavior: Flickable.StopAtBounds
        // Stop completely at bounds
        flickDeceleration: 2000
        // Faster deceleration to stop more quickly at edges
        maximumFlickVelocity: 800
        // Lower maximum velocity for more control
        flickableDirection: Flickable.VerticalFlick
        // Only allow vertical flicking
        cacheBuffer: 400
        onDraggingChanged: {
            if (dragging)
                lastY = contentY;

        }
        onFlickStarted: {
            // Detect if we're at a boundary when flick starts
            atBoundary = (contentY <= 0 || (contentY + height >= contentHeight));
            // If at boundary, reduce the flick velocity
            if (atBoundary)
                // Reduce vertical velocity by 70% if at boundary
                verticalVelocity *= 0.3;

        }
        onMovementStarted: {
            // Monitor if we're at the edge
            preventEdgeUpdate = (contentY <= 0 || (contentY + height >= contentHeight));
        }
        onMovementEnded: {
            preventEdgeUpdate = false;
        }
        onContentYChanged: {
            // Clamp content position to avoid overscroll artifacts
            if (!preventEdgeUpdate) {
                if (contentY < 0)
                    contentY = 0;
                else if (contentHeight > height && contentY > contentHeight - height)
                    contentY = contentHeight - height;
            }
        }
        // Improved physics for e-ink display
        interactive: true
        highlightMoveDuration: 400
        highlightResizeDuration: 0
        highlightFollowsCurrentItem: true
        // Add keyboard navigation for accessibility
        Keys.onUpPressed: decrementCurrentIndex()
        Keys.onDownPressed: incrementCurrentIndex()
        Keys.onReturnPressed: {
            if (currentIndex >= 0 && currentIndex < count)
                listContainer.serverSelected(model[currentIndex].path);

        }

        // Visual ScrollIndicator optimized for e-ink
        ScrollIndicator {
            id: scrollIndicator

            anchors.right: parent.right
            anchors.rightMargin: 2
            anchors.top: parent.top
            anchors.topMargin: 2
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 2
            active: serverListView.moving || serverListView.dragging

            // Thicker handle for easier visibility on e-ink
            contentItem: Rectangle {
                implicitWidth: 4
                implicitHeight: 100
                color: ThemeManager.accentColor
                opacity: scrollIndicator.active ? 0.8 : 0.5
            }

        }

        // Delegate with key navigation
        delegate: MCPServerListItem {
            width: serverListView.width
            isCurrentItem: ListView.isCurrentItem
            serverName: modelData.name
            serverDescription: modelData.description || ""
            serverPath: modelData.path
            onItemClicked: function(path) {
                serverListView.currentIndex = index;
                listContainer.serverSelected(path);
            }
        }

    }

}
