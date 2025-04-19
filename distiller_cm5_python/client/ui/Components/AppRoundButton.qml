import QtQuick 2.15
import QtQuick.Controls 2.15

NavigableItem {
    id: root
    
    property string iconText: ""
    property string text: ""
    property real iconOpacity: 0.7
    property real hoverOpacity: 1.0
    property bool useHoverEffect: true
    property bool showBorder: false
    property bool flat: true
    property bool checked: false
    
    width: 36
    height: 36
    
    Rectangle {
        id: backgroundRect
        anchors.fill: parent
        color: root.checked ? ThemeManager.subtleColor 
             : root.pressed ? ThemeManager.pressedColor 
             : root.visualFocus ? ThemeManager.accentColor
             : "transparent"
        border.width: showBorder || root.visualFocus ? ThemeManager.borderWidth : 0
        border.color: root.visualFocus ? ThemeManager.accentColor : (showBorder ? ThemeManager.borderColor : "transparent")
        radius: width / 2
    }
    
    Text {
        id: textItem
        text: root.iconText || root.text
        font: FontManager.heading
        color: root.visualFocus ? "white" : ThemeManager.textColor
        anchors.centerIn: parent
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        opacity: (useHoverEffect && root.hovered) ? hoverOpacity : iconOpacity
        
        Behavior on opacity {
            NumberAnimation {
                duration: 150
            }
        }
    }
    
    // Mouse area to handle clicks
    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        
        property bool pressed: false
        
        onClicked: {
            root.clicked()
        }
        
        onPressed: {
            pressed = true
        }
        
        onReleased: {
            pressed = false
        }
    }
    
    // Add keyboard handling for Enter/Return
    Keys.onReturnPressed: function() {
        clicked();
    }
    
    property bool hovered: mouseArea.containsMouse
    property bool pressed: mouseArea.pressed
} 