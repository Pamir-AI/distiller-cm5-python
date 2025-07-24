import QtQuick

AppButton {
    id: infoButton

    signal infoClicked

    width: ThemeManager.buttonHeight
    height: ThemeManager.buttonHeight
    isFlat: true
    buttonRadius: width / 2
    navigable: true

    onClicked: {
        infoButton.infoClicked();
    }

    // Info button icon with better visual design
    Rectangle {
        parent: infoButton
        anchors.fill: parent
        color: ThemeManager.backgroundColor

        // High contrast highlight for e-ink when focused
        Rectangle {
            visible: infoButton.visualFocus || infoButton.pressed || true
            anchors.fill: parent
            radius: width / 2
            color: infoButton.visualFocus ? ThemeManager.textColor : ThemeManager.backgroundColor
            border.width: ThemeManager.borderWidth
            border.color: ThemeManager.black
            antialiasing: true
        }

        // Info icon - using "i" character
        Text {
            text: ""
            font.pixelSize: parent.width * 0.4
            font.family: FontManager.primaryFontFamily
            font.bold: true
            color: infoButton.visualFocus ? ThemeManager.backgroundColor : ThemeManager.textColor
            anchors.centerIn: parent
            renderType: Text.NativeRendering
        }
    }
}
