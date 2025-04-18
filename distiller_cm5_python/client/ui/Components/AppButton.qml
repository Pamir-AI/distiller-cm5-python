import QtQuick 2.15
import QtQuick.Controls 2.15

Button {
    id: root
    
    property bool isFlat: false
    property bool useFixedHeight: true
    
    width: parent ? parent.width : implicitWidth
    height: useFixedHeight ? ThemeManager.buttonHeight : implicitHeight
    
    // Style properties
    background: Rectangle {
        color: root.down ? ThemeManager.pressedColor 
             : root.hovered ? ThemeManager.highlightColor 
             : (isFlat ? "transparent" : ThemeManager.backgroundColor)
        border.color: root.activeFocus ? ThemeManager.highlightColor : (isFlat ? "transparent" : ThemeManager.borderColor)
        border.width: root.activeFocus ? 4 : (isFlat ? 0 : ThemeManager.borderWidth)
        radius: ThemeManager.borderRadius
    }
    
    contentItem: Text {
        text: root.text
        color: ThemeManager.textColor
        font.pixelSize: FontManager.fontSizeNormal
        font.family: FontManager.primaryFontFamily
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
} 