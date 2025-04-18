import QtQuick 2.15
import QtQuick.Controls 2.15

RoundButton {
    id: root
    
    property string iconText: ""
    property real iconOpacity: 0.7
    property real hoverOpacity: 1.0
    property bool useHoverEffect: true
    property bool showBorder: false
    
    width: 36
    height: 36
    flat: true
    
    // Make focusable
    focus: true
    
    // Add logging for focus state changes
    onActiveFocusChanged: console.log("--- AppRoundButton [" + objectName + "] activeFocus changed: " + activeFocus) // Use objectName if set, or just log generic message
    onFocusChanged: console.log("--- AppRoundButton [" + objectName + "] focus changed: " + focus)
    
    // Handle Enter/Select key
    Keys.onPressed: (event) => {
        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Select) {
            clicked(); 
            event.accepted = true;
        } else {
            event.accepted = false; // Allow other keys (like arrows) to propagate
        }
    }
    
    background: Rectangle {
        color: root.checked ? ThemeManager.subtleColor 
             : root.pressed ? ThemeManager.pressedColor 
             : "transparent"
        border.width: root.activeFocus ? 4 : 0
        border.color: root.activeFocus ? "red" : "transparent"
        radius: width / 2
    }
    
    contentItem: Text {
        text: root.iconText
        font: FontManager.heading
        color: ThemeManager.textColor
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        opacity: (useHoverEffect && root.hovered) ? hoverOpacity : iconOpacity
        
        Behavior on opacity {
            NumberAnimation {
                duration: 150
            }
        }
    }
} 