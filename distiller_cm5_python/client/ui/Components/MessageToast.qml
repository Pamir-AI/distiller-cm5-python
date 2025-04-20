import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: messageToast

    function showMessage(message, duration) {
        messageText.text = message;
        opacity = 1;
        fadeTimer.interval = duration || 3000;
        fadeTimer.restart();
    }

    // Fixed width based on parent only, breaking the binding loop
    width: parent.width * 0.8
    height: messageText.implicitHeight + ThemeManager.spacingNormal
    radius: ThemeManager.borderRadius
    color: ThemeManager.backgroundColor
    border.color: ThemeManager.borderColor
    border.width: ThemeManager.borderWidth
    opacity: 0
    visible: opacity > 0

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

    NumberAnimation {
        id: fadeAnimation

        target: messageToast
        property: "opacity"
        duration: 500
        from: 1
        to: 0
        running: false
    }

    Timer {
        id: fadeTimer

        interval: 3000
        onTriggered: fadeAnimation.start()
    }
}
