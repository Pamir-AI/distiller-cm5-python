import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: delegateItem

    property bool isCurrentItem: false
    property string serverName: ""
    property string serverDescription: ""
    property string serverPath: ""
    property bool compact: true

    signal itemClicked(string path)

    width: parent.width
    height: contentLayout.height + ThemeManager.spacingSmall * 2
    radius: ThemeManager.borderRadius
    color: ThemeManager.backgroundColor
    border.color: ThemeManager.borderColor
    border.width: ThemeManager.borderWidth

    // Server selection indication - simpler for e-ink
    Rectangle {
        id: selectionIndicator

        anchors.fill: parent
        radius: ThemeManager.borderRadius
        color: ThemeManager.buttonColor
        opacity: delegateItem.isCurrentItem ? 0.5 : 0
    }

    // Server display with proper padding
    RowLayout {
        id: contentLayout

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.margins: compact ? ThemeManager.spacingSmall : ThemeManager.spacingNormal
        spacing: ThemeManager.spacingSmall

        ColumnLayout {
            Layout.fillWidth: true
            spacing: compact ? 2 : ThemeManager.spacingSmall

            Text {
                text: serverName.toUpperCase()
                font: compact ? FontManager.normal : FontManager.heading
                color: ThemeManager.textColor
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                elide: Text.ElideRight
                maximumLineCount: 1
            }

            Text {
                text: serverDescription || ""
                font: FontManager.small
                color: ThemeManager.secondaryTextColor
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                elide: Text.ElideRight
                maximumLineCount: compact ? 1 : 2
                visible: text.length > 0
            }
        }

        // Use AppRoundButton instead of text
        AppRoundButton {
            iconText: "⏎" // Enter symbol
            Layout.alignment: Qt.AlignVCenter
            useHoverEffect: false
            onClicked: {
                delegateItem.itemClicked(serverPath);
            }
        }
    }

    // Click and hover behavior - simpler for e-ink
    MouseArea {
        id: mouseArea

        anchors.fill: parent
        hoverEnabled: true
        onEntered: {
            if (!delegateItem.isCurrentItem)
                selectionIndicator.opacity = 0.3;
        }
        onExited: {
            if (!delegateItem.isCurrentItem)
                selectionIndicator.opacity = 0;
        }
        onClicked: {
            itemClicked(serverPath);
            // Prevent too rapid clicks by disabling the area briefly
            mouseArea.enabled = false;
            mouseReenableTimer.start();
        }

        Timer {
            id: mouseReenableTimer

            interval: ThemeManager.animationDuration
            onTriggered: mouseArea.enabled = true
        }
    }
}
