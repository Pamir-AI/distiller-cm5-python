import QtQuick
import QtQuick.Controls

ScrollView {
    id: root

    property bool showEdgeEffects: false
    property bool showScrollIndicator: false
    property int wheelScrollLines: 3
    property int touchScrollSensitivity: 1
    property int keyNavigationSpeed: 40
    // Expose the scroll animation for external use but set duration to 0
    property alias scrollAnimation: scrollAnimation

    clip: true
    // Disable the internal keyboard handling since we'll handle it through FocusManager
    Keys.enabled: false
    contentWidth: availableWidth
    // Keyboard navigation support - direct movement without animation
    Keys.onPressed: function(event) {
        var contentItem = root.contentItem;
        if (event.key === Qt.Key_PageDown) {
            contentItem.contentY = Math.min(contentItem.contentY + root.height * 0.9, contentItem.contentHeight - root.height);
            event.accepted = true;
        } else if (event.key === Qt.Key_PageUp) {
            contentItem.contentY = Math.max(contentItem.contentY - root.height * 0.9, 0);
            event.accepted = true;
        } else if (event.key === Qt.Key_Home) {
            contentItem.contentY = 0;
            event.accepted = true;
        } else if (event.key === Qt.Key_End) {
            contentItem.contentY = contentItem.contentHeight - root.height;
            event.accepted = true;
        } else if (event.key === Qt.Key_Down) {
            contentItem.contentY = Math.min(contentItem.contentY + keyNavigationSpeed, contentItem.contentHeight - root.height);
            event.accepted = true;
        } else if (event.key === Qt.Key_Up) {
            contentItem.contentY = Math.max(contentItem.contentY - keyNavigationSpeed, 0);
            event.accepted = true;
        }
    }

    // Animation with zero duration for compatibility with code expecting the animation
    NumberAnimation {
        id: scrollAnimation

        target: root.contentItem
        property: "contentY"
        duration: 0
        easing.type: Easing.Linear
    }

    // Edge indicators - simplified to static elements
    Rectangle {
        id: topEdgeIndicator

        visible: showEdgeEffects && root.contentItem && root.contentItem.contentY <= 0
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 2
        color: ThemeManager.textColor
        opacity: 0.8
        z: 1
    }

    Rectangle {
        id: bottomEdgeIndicator

        visible: showEdgeEffects && root.contentItem && root.contentItem.contentHeight > root.height && (root.contentItem.contentY + root.height) >= root.contentItem.contentHeight
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 2
        color: ThemeManager.textColor
        opacity: 0.8
        z: 1
    }

    // Scroll indicator - simplified for e-ink display
    Rectangle {
        id: scrollPositionIndicator

        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.verticalCenter: parent.verticalCenter
        width: 40
        height: 40
        radius: width / 2
        color: ThemeManager.textColor
        visible: root.showScrollIndicator && root.contentItem.contentHeight > root.height * 1.5
        opacity: 0.7
        z: 10

        Text {
            anchors.centerIn: parent
            text: Math.round((root.contentItem.contentY / (root.contentItem.contentHeight - root.height)) * 100) + "%"
            color: ThemeManager.backgroundColor
            font.pixelSize: 12
            font.bold: true
            visible: root.contentItem.contentHeight > root.height
        }

    }

    ScrollBar.horizontal: ScrollBar {
        policy: ScrollBar.AlwaysOff
    }

    // Custom ScrollBar styling - simplified for e-ink
    ScrollBar.vertical: ScrollBar {
        id: verticalScrollBar

        anchors.right: parent.right
        anchors.rightMargin: 4
        policy: ScrollBar.AsNeeded
        // Static opacity for e-ink
        opacity: 0.6
        interactive: false // Disable interaction since we're removing mouse support
        // Make scrollbar wider for better visibility
        implicitWidth: 8

        contentItem: Rectangle {
            implicitWidth: 8
            radius: width / 2
            color: ThemeManager.textColor
        }

        background: Rectangle {
            implicitWidth: 6
            radius: width / 2
            color: ThemeManager.black
            opacity: 0.3
        }

    }

}
