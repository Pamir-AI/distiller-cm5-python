import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: busyIndicator

    property bool isLoading: true

    width: 80
    height: 80
    radius: 40
    color: ThemeManager.backgroundColor
    border.color: ThemeManager.borderColor
    border.width: ThemeManager.borderWidth
    visible: isLoading

    Text {
        id: loadingText

        anchors.centerIn: parent
        text: "Loading"
        font: FontManager.heading
        color: ThemeManager.textColor

        // Simple opacity animation that works better on e-ink
        SequentialAnimation on opacity {
            running: busyIndicator.isLoading
            loops: Animation.Infinite

            NumberAnimation {
                from: 1
                to: 0.3
                duration: ThemeManager.animationDuration
            }

            NumberAnimation {
                from: 0.3
                to: 1
                duration: ThemeManager.animationDuration
            }

        }

    }

}
