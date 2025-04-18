import QtQuick 2.15
pragma Singleton

QtObject {
    // Subtle overlay for hover effects
    // Longer animation duration for e-ink
    // Standard button height

    id: themeManager

    // Theme mode property - controls which theme to use
    property bool darkMode: false
    // Dynamic color properties based on current theme
    readonly property color backgroundColor: darkMode ? "#000000" : "#FFFFFF"
    // Background: Black/White
    readonly property color textColor: darkMode ? "#FFFFFF" : "#000000"
    // Text: White/Black
    readonly property color buttonColor: darkMode ? "#333333" : "#EEEEEE"
    // Buttons: Dark gray/Light gray
    readonly property color accentColor: darkMode ? "#FFFFFF" : "#000000"
    // Accent: White/Black
    readonly property color borderColor: darkMode ? "#FFFFFF" : "#000000"
    // Borders: White/Black
    readonly property color placeholderTextColor: darkMode ? "#AAAAAA" : "#666666"
    // Placeholders: Light gray/Dark gray
    readonly property color headerColor: darkMode ? "#222222" : "#EEEEEE"
    // Headers: Dark gray/Light gray
    readonly property color secondaryTextColor: darkMode ? "#CCCCCC" : "#333333"
    // Secondary text: Light gray/Dark gray
    readonly property color tertiaryTextColor: darkMode ? "#999999" : "#666666"
    // Tertiary text: Gray
    readonly property color pressedColor: darkMode ? "#444444" : "#DDDDDD"
    // Pressed state: Dark gray/Light gray
    readonly property color highlightColor: darkMode ? "#333333" : "#F0F0F0"
    // Highlight: Dark gray/Light gray
    readonly property color subtleColor: darkMode ? Qt.rgba(1, 1, 1, 0.05) : Qt.rgba(0, 0, 0, 0.05)
    // Sizes and metrics
    readonly property real borderRadius: 6
    // Border radius for rectangles
    readonly property real borderWidth: 1
    // Border width
    readonly property real animationDuration: 500
    // Spacing
    readonly property real spacingSmall: 8
    readonly property real spacingNormal: 16
    readonly property real spacingLarge: 20
    readonly property real spacingTiny: 4
    // Component specific properties
    readonly property real buttonHeight: 44
    // Icon management - using more defined paths
    readonly property string basePath: "../../images/icons/"
    readonly property string lightIconPath: basePath
    readonly property string darkIconPath: basePath + "dark/"

    // Helper function to get theme-appropriate icon path
    function getIconPath(iconName) {
        if (darkMode)
            return darkIconPath + iconName;

        return lightIconPath + iconName;
    }

    // Function to toggle theme
    function toggleTheme() {
        darkMode = !darkMode;
    }

    // Function to set theme explicitly
    function setDarkMode(isDark) {
        darkMode = isDark;
    }

}
