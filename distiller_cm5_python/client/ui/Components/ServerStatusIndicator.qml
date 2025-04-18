import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: statusIndicator

    property bool isConnected: false

    width: 12
    height: 12
    radius: width / 2
    color: ThemeManager.backgroundColor
    border.color: ThemeManager.borderColor
    border.width: ThemeManager.borderWidth

    Rectangle {
        id: indicator

        anchors.centerIn: parent
        width: parent.width / 2
        height: parent.height / 2
        radius: width / 2
        color: statusIndicator.isConnected ? ThemeManager.accentColor : ThemeManager.tertiaryTextColor

        SequentialAnimation {
            loops: Animation.Infinite
            running: statusIndicator.isConnected

            NumberAnimation {
                target: indicator
                property: "opacity"
                from: 1
                to: 0.3
                duration: 2000
            }

            NumberAnimation {
                target: indicator
                property: "opacity"
                from: 0.3
                to: 1
                duration: 2000
            }

        }

    }

}
