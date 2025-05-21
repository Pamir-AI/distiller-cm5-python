import QtQuick

Rectangle {
    id: busyIndicator

    property bool isLoading: true

    width: 80
    height: 80
    radius: 40
    color: ThemeManager.backgroundColor
    border.color: ThemeManager.black
    border.width: ThemeManager.borderWidth
    visible: isLoading

    Text {
        id: loadingText

        anchors.centerIn: parent
        text: "Loading"
        font: FontManager.heading
        color: ThemeManager.textColor
    }

}
