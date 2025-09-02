import QtQuick
import QtQuick.Layouts

NavigableItem {
    id: messageItem

    property string messageText: ""
    property bool isLastMessage: false
    property bool isResponding: false
    // Parse message components from string format "[timestamp] sender: content::type"
    readonly property string timestamp: messageText.indexOf("]") > 0 ? messageText.substring(1, messageText.indexOf("]")) : ""
    readonly property string remainder: messageText.indexOf("]") > 0 ? messageText.substring(messageText.indexOf("]") + 2) : messageText
    readonly property string sender: remainder.indexOf(":") > 0 ? remainder.substring(0, remainder.indexOf(":")) : ""
    // Extract message type if present (after ::)
    readonly property string contentWithType: remainder.indexOf(":") > 0 ? remainder.substring(remainder.indexOf(":") + 2) : remainder
    readonly property string messageType: contentWithType.lastIndexOf("::") > 0 ? contentWithType.substring(contentWithType.lastIndexOf("::") + 2) : "Message"
    readonly property string content: contentWithType.lastIndexOf("::") > 0 ? contentWithType.substring(0, contentWithType.lastIndexOf("::")) : contentWithType

    width: parent.width
    height: messageLayout.implicitHeight + ThemeManager.spacingNormal
    // Don't show the message if it's empty or only contains timestamp brackets
    visible: messageText !== "" && content.trim() !== ""

    // Background rectangle for message
    Rectangle {
        id: messageBackground
        anchors.fill: parent
        radius: ThemeManager.borderRadius
        color: messageItem.backgroundColor
        border.color: ThemeManager.black // Always black border for contrast
        border.width: ThemeManager.borderWidth
    }

    // Subtle highlight effect for the latest message during response generation
    // Only applied to the actual message rectangle, not extending beyond it
    Rectangle {
        id: highlightEffect

        anchors.fill: parent
        radius: messageBackground.radius
        color: isLastMessage && isResponding ? ThemeManager.black : ThemeManager.transparentColor // Solid black highlight instead of subtle color
        visible: isLastMessage && isResponding
        z: -1 // Behind text content
    }

    ColumnLayout {
        id: messageLayout

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: ThemeManager.spacingSmall
        spacing: ThemeManager.spacingTiny

        Text {
            text: sender
            font: FontManager.small
            color: messageItem.textColor
            Layout.fillWidth: true
            visible: sender !== ""
        }

        // Use our MarkdownText component
        MarkdownText {
            markdownText: content
            textFont: FontManager.normal
            textColor: messageItem.textColor
            Layout.fillWidth: true
            Layout.preferredHeight: implicitHeight
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: ThemeManager.spacingTiny / 2

            // Display the message type at the bottom left
            Text {
                text: messageType
                color: messageItem.textColor
                horizontalAlignment: Text.AlignLeft
                Layout.fillWidth: true
                visible: messageType !== ""

                font {
                    family: FontManager.small.family
                    pixelSize: FontManager.small.pixelSize
                    // Use bold for important message types
                    weight: {
                        switch (messageType.toLowerCase()) {
                        case "error":
                        case "warning":
                            return Font.Bold;
                        default:
                            return Font.Normal;
                        }
                    }
                    // Use italic for action-related types
                    italic: {
                        switch (messageType.toLowerCase()) {
                        case "action":
                        case "function":
                        case "observation":
                        case "plan":
                            return true;
                        default:
                            return false;
                        }
                    }
                }

            }

            // Display timestamp at the bottom right
            Text {
                text: timestamp
                font: FontManager.small
                color: messageItem.textColor
                horizontalAlignment: Text.AlignRight
                Layout.fillWidth: true
                visible: timestamp !== ""
            }

        }

    }

}
