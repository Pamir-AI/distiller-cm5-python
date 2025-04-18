import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Switch {
    id: root
    
    property bool value: checked
    
    signal valueToggled(bool newValue)
    
    Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
    Layout.preferredHeight: 28
    Layout.preferredWidth: 52
    
    checked: value
    
    onToggled: {
        valueToggled(checked)
    }
    
    indicator: Rectangle {
        implicitWidth: 52
        implicitHeight: 28
        x: root.leftPadding
        y: parent.height / 2 - height / 2
        radius: height / 2
        color: root.checked ? ThemeManager.accentColor : ThemeManager.backgroundColor
        border.color: ThemeManager.borderColor
        border.width: ThemeManager.borderWidth

        Rectangle {
            x: root.checked ? parent.width - width - ThemeManager.borderWidth * 2 : ThemeManager.borderWidth * 2
            y: ThemeManager.borderWidth * 2
            width: parent.height - ThemeManager.borderWidth * 4
            height: parent.height - ThemeManager.borderWidth * 4
            radius: height / 2
            color: ThemeManager.backgroundColor
            border.color: ThemeManager.borderColor
            border.width: ThemeManager.borderWidth

            Behavior on x {
                NumberAnimation {
                    duration: ThemeManager.animationDuration / 2
                }
            }
        }
    }
} 
