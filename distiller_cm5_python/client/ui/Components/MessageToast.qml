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

    width: messageText.width + ThemeManager.spacingLarge * 2
    height: messageText.height + ThemeManager.spacingLarge
    radius: ThemeManager.borderRadius
    color: ThemeManager.backgroundColor
    border.color: ThemeManager.borderColor
    border.width: ThemeManager.borderWidth
    opacity: 0
    visible: opacity > 0

    Text {
        id: messageText

        anchors.centerIn: parent
        font: FontManager.normal
        color: ThemeManager.textColor
        text: ""
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
