import QtQuick 2.15
import QtQuick.Controls 2.15

TextField {
    id: root
    
    property bool isReadOnly: false
    
    color: ThemeManager.textColor
    placeholderTextColor: ThemeManager.secondaryTextColor
    selectionColor: ThemeManager.accentColor
    selectedTextColor: ThemeManager.backgroundColor
    font: FontManager.normal
    readOnly: isReadOnly
    
    background: Rectangle {
        color: ThemeManager.backgroundColor
        border.color: root.activeFocus ? ThemeManager.accentColor : ThemeManager.borderColor
        border.width: ThemeManager.borderWidth
        radius: ThemeManager.borderRadius
    }
} 