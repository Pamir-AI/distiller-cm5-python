import QtQuick

Rectangle {
    id: messageToast

    function showMessage(message, duration) {
        messageText.text = message;
        visible = true;
        opacity = 1;
        fadeTimer.interval = duration || 3000;
        fadeTimer.restart();
    }

    objectName: "toastBackground"
    // Fixed width based on parent only, breaking the binding loop
    width: parent.width * 0.8
    height: messageText.implicitHeight + ThemeManager.spacingNormal
    radius: ThemeManager.borderRadius
    color: ThemeManager.backgroundColor
    border.color: ThemeManager.black
    border.width: ThemeManager.borderWidth
    visible: false

    Text {
        id: messageText

        anchors.centerIn: parent
        font.pixelSize: FontManager.fontSizeSmall
        font.family: FontManager.primaryFontFamily
        color: ThemeManager.textColor
        text: ""
        width: parent.width - ThemeManager.spacingNormal * 2
        wrapMode: Text.WordWrap
        horizontalAlignment: Text.AlignCenter
    }

    // Timer to hide message
    Timer {
        id: fadeTimer

        interval: 3000
        onTriggered: {
            messageToast.visible = false;
        }
    }

}
