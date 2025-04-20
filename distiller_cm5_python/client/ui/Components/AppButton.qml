import QtQuick 2.15
import QtQuick.Controls 2.15

NavigableItem {
    id: root
    
    property bool isFlat: false
    property bool useFixedHeight: true
    property string text: ""
    property color backgroundColor: getBackgroundColor()
    property color textColor: root.visualFocus ? 
                             (ThemeManager.darkMode ? "#000000" : "#FFFFFF") : 
                             (ThemeManager.textColor || "#000000")
    property int fontSize: FontManager.fontSizeSmall
    
    width: parent ? parent.width : implicitWidth
    height: useFixedHeight ? ThemeManager.buttonHeight : implicitHeight
    
    // Style properties
    Rectangle {
        id: backgroundRect
        anchors.fill: parent
        color: root.backgroundColor
        border.color: getBorderColor()
        border.width: root.visualFocus ? 2 : (isFlat ? 0 : ThemeManager.borderWidth)
        radius: ThemeManager.borderRadius
        
        function getBackgroundColor() {
            if (root.pressed)
                return ThemeManager.pressedColor;
            if (root.visualFocus)
                return ThemeManager.accentColor;
            if (root.hovered)
                return ThemeManager.highlightColor;
            return isFlat ? "transparent" : ThemeManager.buttonColor;
        }
        
        function getBorderColor() {
            if (root.visualFocus)
                return ThemeManager.accentColor;
            return isFlat ? "transparent" : ThemeManager.borderColor;
        }
    }
    
    Text {
        anchors.centerIn: parent
        text: root.text
        color: root.textColor
        font.pixelSize: root.fontSize
        font.family: FontManager.primaryFontFamily
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
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
    
    function getBackgroundColor() {
        if (root.pressed)
            return ThemeManager.pressedColor;
        if (root.visualFocus)
            return ThemeManager.accentColor;
        if (root.hovered)
            return ThemeManager.highlightColor;
        return isFlat ? "transparent" : ThemeManager.buttonColor;
    }
} 
