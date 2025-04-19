import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: header
    
    property bool showApplyButton: true
    property alias backButton: backBtn
    
    signal backClicked()
    signal applyClicked()
    
    color: ThemeManager.headerColor
    
    AppButton {
        id: backBtn
        text: "←"
        anchors.left: parent.left
        anchors.leftMargin: ThemeManager.spacingNormal
        anchors.verticalCenter: parent.verticalCenter
        width: 40
        height: 32
        navigable: true
        
        onClicked: {
            header.backClicked();
        }
    }
    
    Text {
        text: "SETTINGS"
        font.pixelSize: FontManager.fontSizeLarge
        font.family: FontManager.primaryFontFamily
        anchors.centerIn: parent
        color: ThemeManager.textColor
    }
}
