import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: messageItem

    property string messageText: ""
    property bool compact: false
    property bool isLastMessage: false
    property bool isResponding: false
    // Parse message components from string format "[timestamp] sender: content"
    readonly property string timestamp: messageText.indexOf("]") > 0 ? messageText.substring(1, messageText.indexOf("]")) : ""
    readonly property string remainder: messageText.indexOf("]") > 0 ? messageText.substring(messageText.indexOf("]") + 2) : messageText
    readonly property string sender: remainder.indexOf(":") > 0 ? remainder.substring(0, remainder.indexOf(":")) : ""
    readonly property string content: remainder.indexOf(":") > 0 ? remainder.substring(remainder.indexOf(":") + 2) : remainder

    width: parent.width
    height: messageLayout.implicitHeight + (compact ? ThemeManager.spacingNormal : ThemeManager.spacingLarge)
    radius: ThemeManager.borderRadius
    color: ThemeManager.backgroundColor
    border.color: ThemeManager.borderColor
    border.width: ThemeManager.borderWidth
    // Don't show the message if it's empty or only contains timestamp brackets
    visible: messageText !== "" && content.trim() !== ""

    // Subtle highlight effect for the latest message during response generation
    // Only applied to the actual message rectangle, not extending beyond it
    Rectangle {
        id: highlightEffect

        anchors.fill: parent
        radius: parent.radius
        color: isLastMessage && isResponding ? ThemeManager.highlightColor : parent.color
        visible: isLastMessage && isResponding
        z: -1 // Behind text content
    }

    ColumnLayout {
        id: messageLayout

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: compact ? (ThemeManager.spacingSmall || 4) : (ThemeManager.spacingNormal || 8)
        spacing: compact ? (ThemeManager.spacingTiny || 2) : (ThemeManager.spacingSmall || 4)

        Text {
            text: sender
            font: compact ? FontManager.small : FontManager.normal
            color: ThemeManager.textColor
            Layout.fillWidth: true
            visible: sender !== ""
        }

        Text {
            text: content
            font: compact ? FontManager.normal : FontManager.medium
            color: ThemeManager.textColor
            wrapMode: Text.WordWrap
            lineHeight: compact ? 1.1 : 1.2
            Layout.fillWidth: true
        }

        Text {
            text: timestamp
            font: FontManager.small
            color: ThemeManager.secondaryTextColor
            horizontalAlignment: Text.AlignRight
            Layout.fillWidth: true
            Layout.topMargin: compact ? 1 : ThemeManager.spacingTiny
            visible: timestamp !== ""
        }

    }

}
