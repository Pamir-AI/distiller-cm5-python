pragma Singleton
import QtQuick

QtObject {
    // Subtle overlay for hover effects
    // No animations for e-ink display
    // Standard button height
    // Text on accent background: Black/White
    // Lighter version of accent color
    // No animations for e-ink

    id: themeManager

    // Theme mode property - controls which theme to use (light = white bg, dark = black bg)
    property bool darkMode: false
    // Theme caching to reduce bridge calls
    property bool themeCached: false
    // Simplified black and white palette - no gradients
    readonly property color black: "#000000"
    readonly property color white: "#FFFFFF"
    readonly property color backgroundColor: darkMode ? black : white
    readonly property color textColor: darkMode ? white : black
    readonly property color transparentColor: "transparent"
    // Sizes and metrics
    readonly property real borderRadius: 6
    // Border radius for rectangles
    readonly property real borderWidth: 2
    // Border width
    readonly property real animationDuration: 0
    // Padding
    readonly property real paddingSmall: 4
    readonly property real paddingNormal: 8
    readonly property real paddingLarge: 12
    // Spacing
    readonly property real spacingSmall: 8
    readonly property real spacingNormal: 16
    readonly property real spacingLarge: 20
    readonly property real spacingTiny: 4
    // Component specific properties
    readonly property real buttonHeight: 36
    // Icon management - using more defined paths
    readonly property string basePath: "../../images/icons/"
    readonly property string lightIconPath: basePath
    readonly property string darkIconPath: basePath + "dark/"

    // Initialize theme from bridge settings
    function initializeTheme() {
        if (!themeCached && bridge && bridge.ready) {
            var savedTheme = bridge.getConfigValue("display", "dark_mode");
            if (savedTheme !== "")
                setDarkMode(savedTheme === "true" || savedTheme === "True");

            themeCached = true;
            return true;
        }
        return false;
    }

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
