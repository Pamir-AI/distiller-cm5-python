import QtQuick

Item {
    id: pageBase

    // Common properties
    property string pageName: ""
    property bool usesThemeManager: true

    // Size properties
    width: parent ? parent.width : 0
    height: parent ? parent.height : 0
    // Initialize component
    Component.onCompleted: {
        // If bridge is already ready, initialize immediately
        if (usesThemeManager && bridge && bridge.ready)
            ThemeManager.initializeTheme();

    }

    // Connect to bridge ready signal if page uses the theme manager
    Connections {
        function onBridgeReady() {
            // Use ThemeManager's centralized theme caching
            if (usesThemeManager)
                ThemeManager.initializeTheme();

        }

        target: usesThemeManager ? bridge : null
    }

    // Background rectangle
    Rectangle {
        id: background

        anchors.fill: parent
        color: ThemeManager.transparentColor
    }

}
