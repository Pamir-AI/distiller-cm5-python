import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

NavigableItem {
    id: root
    
    property string serverName: ""
    property string serverDescription: ""
    property string serverPath: ""
    property bool isEmpty: false
    
    signal cardClicked(string path)
    
    // Send clicked signal on Enter key press
    Keys.onReturnPressed: function() {
        clicked()
    }
    
    onClicked: {
        if (!isEmpty) {
            cardClicked(serverPath)
        }
    }
    
    Rectangle {
        id: cardBackground
        anchors.fill: parent
        color: root.visualFocus ? ThemeManager.accentColor : ThemeManager.backgroundColor
        radius: ThemeManager.borderRadius
        border.width: root.visualFocus ? 2 : ThemeManager.borderWidth
        border.color: root.visualFocus ? ThemeManager.accentColor : ThemeManager.borderColor
        
        // Inner content layout for the server card
        Column {
            id: contentLayout
            anchors.fill: parent
            anchors.margins: ThemeManager.spacingNormal
            spacing: ThemeManager.spacingSmall
            
            // Server icon 
            Rectangle {
                id: serverIcon
                width: parent.width * 0.4
                height: width
                radius: width / 2
                color: "transparent"
                border.width: 1
                border.color: root.visualFocus ? "white" : ThemeManager.borderColor
                anchors.horizontalCenter: parent.horizontalCenter
                
                // Server initial in the center of the icon
                Text {
                    text: serverName.charAt(0).toUpperCase()
                    anchors.centerIn: parent
                    font.pixelSize: parent.width * 0.6
                    font.family: FontManager.primaryFontFamily
                    color: root.visualFocus ? "white" : ThemeManager.textColor
                }
            }
            
            // Server name
            Text {
                text: serverName
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: FontManager.fontSizeNormal
                font.family: FontManager.primaryFontFamily
                color: root.visualFocus ? "white" : ThemeManager.textColor
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
            }
            
            // Server description (if available)
            Text {
                visible: serverDescription
                text: serverDescription
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: FontManager.fontSizeSmall
                font.family: FontManager.primaryFontFamily
                color: root.visualFocus ? "white" : ThemeManager.secondaryTextColor
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
            }
        }
    }
    
    // Mouse area to handle clicks
    MouseArea {
        anchors.fill: parent
        onClicked: {
            root.forceActiveFocus()
            root.clicked()
        }
    }
}
