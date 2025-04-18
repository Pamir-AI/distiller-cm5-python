import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

// A common base header that can be extended by specialized headers
Rectangle {
    id: commonHeader

    // Common properties
    property string title: ""
    property bool showBackButton: false
    property bool showActionButton: false
    property string actionButtonText: "Apply"

    // Common signals
    signal backClicked()
    signal actionClicked()

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

        // Back button (optional)
        AppRoundButton {
            id: backButton
            
            Layout.preferredWidth: 32
            Layout.preferredHeight: 32
            Layout.alignment: Qt.AlignVCenter
            
            visible: showBackButton
            flat: true
            
            contentItem: Text {
                text: "←"
                font.pixelSize: FontManager.fontSizeLarge
                color: ThemeManager.accentColor
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            
            onClicked: commonHeader.backClicked()
        }

        // Title text
        Text {
            id: titleText
            
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            
            text: title
            font: FontManager.medium
            color: ThemeManager.textColor
            elide: Text.ElideRight
        }

        // Action button (optional)
        AppButton {
            id: actionButton
            
            Layout.preferredHeight: 30
            Layout.alignment: Qt.AlignVCenter
            
            visible: showActionButton
            text: actionButtonText
            
            onClicked: commonHeader.actionClicked()
        }
    }
} 