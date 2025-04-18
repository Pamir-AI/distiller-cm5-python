import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

FocusScope {
    id: pageBase
    
    // Common properties
    property string pageName: ""
    property bool usesThemeManager: true
    
    // Size properties
    width: parent ? parent.width : 0
    height: parent ? parent.height : 0
    
    // Initialize theme if needed
    Component.onCompleted: {
        if (usesThemeManager) {
            var savedTheme = bridge.getConfigValue("display", "dark_mode");
            if (savedTheme !== "") {
                ThemeManager.setDarkMode(savedTheme === "true" || savedTheme === "True");
            }
        }
    }
    
    // Background rectangle
    Rectangle {
        id: background
        
        anchors.fill: parent
        color: ThemeManager.backgroundColor
    }
} 