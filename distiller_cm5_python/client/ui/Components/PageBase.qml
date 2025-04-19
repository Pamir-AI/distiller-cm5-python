import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: pageBase
    
    // Common properties
    property string pageName: ""
    property bool usesThemeManager: true
    
    // Size properties
    width: parent ? parent.width : 0
    height: parent ? parent.height : 0
    
    // Connect to bridge ready signal if page uses the theme manager
    Connections {
        target: usesThemeManager ? bridge : null
        
        function onBridgeReady() {
            // Initialize theme when bridge is ready
            var savedTheme = bridge.getConfigValue("display", "dark_mode");
            if (savedTheme !== "") {
                ThemeManager.setDarkMode(savedTheme === "true" || savedTheme === "True");
            }
        }
    }
    
    // Initialize component
    Component.onCompleted: {
        // If bridge is already ready, initialize immediately
        if (usesThemeManager && bridge && bridge.ready) {
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