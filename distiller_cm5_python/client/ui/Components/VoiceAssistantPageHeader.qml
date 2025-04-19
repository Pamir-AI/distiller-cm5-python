import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: header

    property string serverName: "MCP Server"
    property string statusText: "Ready"
    property bool isConnected: false
    property bool compact: true
    property alias serverSelectButton: backButton

    signal serverSelectClicked()

    color: ThemeManager.headerColor
    border.width: 0
    border.color: ThemeManager.borderColor
    
    // Shadow effect for the header
    Rectangle {
        anchors.top: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: ThemeManager.borderColor
        opacity: 0.5
    }

    // Layout for header components
    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: ThemeManager.spacingNormal
        anchors.rightMargin: ThemeManager.spacingNormal
        spacing: ThemeManager.spacingNormal

        // Back button (server select)
        AppButton {
            id: backButton
            
            Layout.preferredWidth: 40
            Layout.preferredHeight: 32
            Layout.alignment: Qt.AlignVCenter
            
            text: "←"
            navigable: true
            
            onClicked: header.serverSelectClicked()
        }

        // Server name and status column
        ColumnLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            spacing: compact ? 2 : 6

            RowLayout {
                spacing: compact ? 4 : ThemeManager.spacingSmall
                Layout.fillWidth: true

                Text {
                    text: serverName.toUpperCase()
                    font: compact ? FontManager.normal : FontManager.title
                    color: ThemeManager.textColor
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }

                ServerStatusIndicator {
                    Layout.alignment: Qt.AlignVCenter
                    isConnected: header.isConnected
                    width: compact ? 12 : 16
                    height: compact ? 12 : 16
                }
            }

            Text {
                id: statusTextItem
                text: statusText
                font: compact ? FontManager.small : FontManager.normal
                color: ThemeManager.secondaryTextColor
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                elide: Text.ElideRight
                maximumLineCount: 2
                clip: true
                
                property bool hovered: false
                property bool truncated: (elide === Text.ElideRight) && (text.length > 0) && (paintedWidth < implicitWidth)
            
                ToolTip {
                    visible: statusTextItem.truncated && statusTextItem.hovered
                    text: statusText
                    delay: 500
                }
                
                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    onEntered: statusTextItem.hovered = true
                    onExited: statusTextItem.hovered = false
                }
            }
        }
    }
}
