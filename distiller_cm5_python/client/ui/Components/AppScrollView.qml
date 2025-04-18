import QtQuick 2.15
import QtQuick.Controls 2.15

ScrollView {
    id: root
    
    property bool showEdgeEffects: true
    property bool showScrollIndicator: true
    property int wheelScrollLines: 3
    property int touchScrollSensitivity: 1
    property int keyNavigationSpeed: 40
    
    clip: true
    
    ScrollBar.horizontal: ScrollBar {
        policy: ScrollBar.AlwaysOff
    }
    
    contentWidth: availableWidth
    
    // Improve scroll behavior for wheel events
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.NoButton // Don't steal clicks from children
        propagateComposedEvents: true // Allow events to pass through
        
        // Optimize wheel scrolling speed for e-ink
        onWheel: function(wheel) {
            // Adjust contentY directly for smoother scrolling
            if (wheel.angleDelta.y !== 0) {
                var delta = wheel.angleDelta.y > 0 ? -wheelScrollLines * 20 : wheelScrollLines * 20;
                var newContentY = Math.max(0, Math.min(root.contentHeight - root.height, root.contentItem.contentY + delta));
                
                // Apply scrolling with easing for smoother motion
                scrollAnimation.stop();
                scrollAnimation.from = root.contentItem.contentY;
                scrollAnimation.to = newContentY;
                scrollAnimation.start();
            }
            wheel.accepted = true;
        }
    }
    
    // Animation for smoother scrolling
    NumberAnimation {
        id: scrollAnimation
        target: root.contentItem
        property: "contentY"
        duration: 150
        easing.type: Easing.OutCubic
    }
    
    // Custom ScrollBar styling
    ScrollBar.vertical: ScrollBar {
        id: verticalScrollBar
        anchors.right: parent.right
        anchors.rightMargin: 4
        policy: ScrollBar.AsNeeded
        
        // Keep partially visible even when inactive for better usability
        opacity: active || hovered ? 0.9 : 0.4
        interactive: true
        
        // Make scrollbar wider for better touch targets
        implicitWidth: 8
        
        Behavior on opacity {
            NumberAnimation { duration: 200 }
        }
        
        contentItem: Rectangle {
            implicitWidth: 8
            radius: width / 2
            color: ThemeManager.accentColor
        }
        
        background: Rectangle {
            implicitWidth: 6
            radius: width / 2
            color: Qt.rgba(0, 0, 0, 0.1)
            opacity: 0.3
        }
    }
    
    // Keyboard navigation support
    Keys.onPressed: function(event) {
        var contentItem = root.contentItem;
        let handled = false;
        
        if (event.key === Qt.Key_PageDown) {
            var newY = Math.min(contentItem.contentY + root.height * 0.9, contentItem.contentHeight - root.height);
            scrollAnimation.stop();
            scrollAnimation.from = contentItem.contentY;
            scrollAnimation.to = newY;
            scrollAnimation.start();
            handled = true;
        } else if (event.key === Qt.Key_PageUp) {
            var newY = Math.max(contentItem.contentY - root.height * 0.9, 0);
            scrollAnimation.stop();
            scrollAnimation.from = contentItem.contentY;
            scrollAnimation.to = newY;
            scrollAnimation.start();
            handled = true;
        } else if (event.key === Qt.Key_Home) {
            scrollAnimation.stop();
            scrollAnimation.from = contentItem.contentY;
            scrollAnimation.to = 0;
            scrollAnimation.start();
            handled = true;
        } else if (event.key === Qt.Key_End) {
            scrollAnimation.stop();
            scrollAnimation.from = contentItem.contentY;
            scrollAnimation.to = contentItem.contentHeight - root.height;
            scrollAnimation.start();
            handled = true;
        } else if (event.key === Qt.Key_Down) {
            // --- Let Down key propagate for page navigation --- 
            console.log("--- AppScrollView ignoring Key_Down ---");
            handled = false; 
        } else if (event.key === Qt.Key_Up) {
            // --- Let Up key propagate for page navigation --- 
            console.log("--- AppScrollView ignoring Key_Up ---");
            handled = false; 
        }
        
        event.accepted = handled;
    }
    
    // Visual feedback for edge bounces
    Rectangle {
        id: topEdgeIndicator
        
        visible: showEdgeEffects
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 2
        color: ThemeManager.accentColor
        // Check if we're at the top edge
        opacity: root.contentItem && root.contentItem.contentY <= 0 ? 0.8 : 0
        z: 1
        
        Behavior on opacity {
            NumberAnimation {
                duration: 200
            }
        }
    }
    
    Rectangle {
        id: bottomEdgeIndicator
        
        visible: showEdgeEffects
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 2
        color: ThemeManager.accentColor
        // Check if we're at the bottom edge
        opacity: root.contentItem && 
                root.contentItem.contentHeight > root.height &&
                (root.contentItem.contentY + root.height) >= root.contentItem.contentHeight ? 0.8 : 0
        z: 1
        
        Behavior on opacity {
            NumberAnimation {
                duration: 200
            }
        }
    }
    
    // Scroll indicator for user feedback
    Rectangle {
        id: scrollPositionIndicator
        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.verticalCenter: parent.verticalCenter
        width: 40
        height: 40
        radius: width / 2
        color: ThemeManager.accentColor
        opacity: 0
        z: 10
        visible: root.showScrollIndicator
        
        Text {
            anchors.centerIn: parent
            text: Math.round((root.contentItem.contentY / (root.contentItem.contentHeight - root.height)) * 100) + "%"
            color: "white"
            font.pixelSize: 12
            font.bold: true
            visible: root.contentItem.contentHeight > root.height
        }
        
        // Show indicator during fast scrolling
        states: State {
            name: "visible"
            when: scrollAnimation.running && root.contentItem.contentHeight > root.height * 1.5
            PropertyChanges {
                target: scrollPositionIndicator
                opacity: 0.7
            }
        }
        
        transitions: Transition {
            from: "*"
            to: "*"
            NumberAnimation {
                properties: "opacity"
                duration: 200
            }
        }
    }
} 
