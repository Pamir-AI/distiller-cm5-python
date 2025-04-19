import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

NavigableItem {
    id: root
    
    property bool checked: false
    property bool value: checked
    
    signal valueToggled(bool newValue)
    signal toggled()
    
    Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
    Layout.preferredHeight: 28
    Layout.preferredWidth: 52
    
    function toggle() {
        checked = !checked
        toggled()
    }
    
    onCheckedChanged: {
        // Prevent signal loops by only emitting the signal if the checked state
        // is different from the property value
        if (value !== checked) {
            valueToggled(checked);
        }
    }
    
    onValueChanged: {
        // Update the checked state to match the value property
        if (checked !== value) {
            checked = value;
        }
    }
    
    // Handle Enter key press
    Keys.onReturnPressed: function() {
        toggle()
    }
    
    Rectangle {
        id: toggleBackground
        width: 52
        height: 28
        anchors.centerIn: parent
        radius: height / 2
        color: root.checked ? ThemeManager.accentColor : ThemeManager.backgroundColor
        border.color: root.visualFocus ? ThemeManager.accentColor : ThemeManager.borderColor
        border.width: root.visualFocus ? 2 : ThemeManager.borderWidth

        Rectangle {
            id: toggleHandle
            x: root.checked ? parent.width - width - (root.visualFocus ? 4 : 2) : (root.visualFocus ? 4 : 2)
            y: root.visualFocus ? 4 : 2
            width: parent.height - (root.visualFocus ? 8 : 4)
            height: parent.height - (root.visualFocus ? 8 : 4)
            radius: height / 2
            color: ThemeManager.backgroundColor
            border.color: root.visualFocus ? ThemeManager.accentColor : ThemeManager.borderColor
            border.width: root.visualFocus ? 2 : ThemeManager.borderWidth

            Behavior on x {
                NumberAnimation {
                    duration: ThemeManager.animationDuration / 2
                }
            }
        }
    }
    
    // Mouse area to handle clicks
    MouseArea {
        anchors.fill: parent
        onClicked: {
            root.toggle()
            root.forceActiveFocus()
        }
    }
} 
