import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: header

    // --- Expose internal button for external focus management ---
    property alias backButtonAlias: backButton
    // --- End exposed alias --- 

    property string serverName: "MCP Server"
    property string statusText: "Ready"
    property bool isConnected: false
    property bool compact: true

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
        AppRoundButton {
            id: backButton
            objectName: "headerBackButton"
            
            Layout.preferredWidth: 32
            Layout.preferredHeight: 32
            Layout.alignment: Qt.AlignVCenter
            
            flat: true
            focus: true
            
            Keys.onPressed: (event) => {
                if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Select) {
                    clicked(); 
                    event.accepted = true;
                } else {
                    event.accepted = false;
                }
            }
            
            contentItem: Text {
                text: "←"
                font.pixelSize: FontManager.fontSizeLarge
                color: ThemeManager.accentColor
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            
            onClicked: header.serverSelectClicked()
            
            ToolTip {
                visible: parent.hovered
                text: "Change server"
                delay: 500
            }
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
            
                ToolTip {
                    visible: statusTextItem.truncated && statusTextItem.hovered
                    text: statusText
                    delay: 500
                }
            }
        }
    }
}
