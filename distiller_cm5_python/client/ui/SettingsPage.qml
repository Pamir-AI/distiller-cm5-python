import Components 1.0
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

PageBase {
    id: settingsPage
    
    pageName: "Settings"

    // Signal to navigate back to the previous page
    signal backClicked()

    width: parent ? parent.width : 0
    height: parent ? parent.height : 0

    // White background for e-ink display
    Rectangle {
        anchors.fill: parent
        color: ThemeManager.backgroundColor
    }

    // Use the SettingsHeader component
    SettingsHeader {
        id: header

        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 60 // Adjusted height without subtitle
        z: 2 // Ensure header stays above content
        showApplyButton: false // Hide the apply button from header
        onBackClicked: {
            settingsPage.backClicked();
        }
    }

    // Use AppScrollView instead of standard ScrollView
    AppScrollView {
        id: settingsScrollView
        
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.topMargin: 1 // Connect with header
        anchors.leftMargin: ThemeManager.spacingSmall // Reduced left margin
        anchors.rightMargin: ThemeManager.spacingSmall // Reduced right margin
        anchors.bottomMargin: applyButtonContainer.height + ThemeManager.spacingNormal // Make room for the floating button
        
        // Setting contentHeight explicitly for proper scrolling
        contentHeight: settingsColumn.height
        
        // Disable scroll position indicator
        showScrollIndicator: false
        
        // Content background for better visual clarity
        Rectangle {
            id: contentBackground
            width: settingsScrollView.width
            height: settingsColumn.height
            color: "transparent"
            
            // Light background shading for scrollable area
            Rectangle {
                anchors.fill: parent
                color: Qt.darker(ThemeManager.backgroundColor, 1.02) // Very subtle darkening
                visible: ThemeManager.darkMode ? false : true
                opacity: 0.5
            }
        }
        
        // Column of settings sections
        Column {
            id: settingsColumn
            // This ensures the column fills exactly the width of the ScrollView's content area
            width: settingsScrollView.width
            spacing: 0 // We're using the section's bottom margin for spacing
            
            // Add top padding
            Item {
                width: parent.width
                height: ThemeManager.spacingNormal
            }
            
            // LLM Settings Section - make wider
            LlmSettingsSection {
                width: parent.width - ThemeManager.spacingSmall * 2 // Wider width
                anchors.horizontalCenter: parent.horizontalCenter
                bottomMargin: ThemeManager.spacingNormal
                serverUrl: bridge.getConfigValue("llm", "server_url")
                enableStreaming: bridge.getConfigValue("llm", "streaming") === "True"
                onServerUrlEdited: function(url) {
                    bridge.setConfigValue("llm", "server_url", url);
                }
                onStreamingToggled: function(enabled) {
                    bridge.setConfigValue("llm", "streaming", enabled.toString());
                }
            }
            
            // Audio Settings Section
            AudioSettingsSection {
                width: parent.width - ThemeManager.spacingSmall * 2 // Wider width
                anchors.horizontalCenter: parent.horizontalCenter
                bottomMargin: ThemeManager.spacingNormal
                volume: parseFloat(bridge.getConfigValue("audio", "volume"))
                onVolumeAdjusted: function(value) {
                    bridge.setConfigValue("audio", "volume", value.toString());
                }
            }
            
            // Display Settings Section
            DisplaySettingsSection {
                width: parent.width - ThemeManager.spacingSmall * 2 // Wider width
                anchors.horizontalCenter: parent.horizontalCenter
                bottomMargin: ThemeManager.spacingNormal
                darkTheme: ThemeManager.darkMode
                Component.onCompleted: {
                    // Initialize from stored setting if available
                    var savedTheme = bridge.getConfigValue("display", "dark_mode");
                    if (savedTheme !== "") {
                        darkTheme = (savedTheme === "true" || savedTheme === "True");
                        ThemeManager.setDarkMode(darkTheme);
                    }
                }
                onDarkThemeToggled: function(enabled) {
                    ThemeManager.setDarkMode(enabled);
                    bridge.setConfigValue("display", "dark_mode", enabled.toString());
                }
            }
            
            // Developer Settings Section
            DeveloperSettingsSection {
                width: parent.width - ThemeManager.spacingSmall * 2 // Wider width
                anchors.horizontalCenter: parent.horizontalCenter
                bottomMargin: ThemeManager.spacingNormal
                debugMode: bridge.getConfigValue("logging", "level") === "DEBUG"
                onDebugModeToggled: function(enabled) {
                    bridge.setConfigValue("logging", "level", enabled ? "DEBUG" : "INFO");
                }
            }
            
            // Network Information Section
            NetworkInfoSection {
                width: parent.width - ThemeManager.spacingSmall * 2 // Wider width
                anchors.horizontalCenter: parent.horizontalCenter
                bottomMargin: ThemeManager.spacingNormal
            }
            
            // About Section
            AboutSection {
                width: parent.width - ThemeManager.spacingSmall * 2 // Wider width
                anchors.horizontalCenter: parent.horizontalCenter
                bottomMargin: ThemeManager.spacingNormal
            }
            
            // Add some bottom padding
            Item {
                width: parent.width
                height: ThemeManager.spacingLarge
            }
        }
    }
    
    // Floating Apply button container
    Rectangle {
        id: applyButtonContainer
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: ThemeManager.buttonHeight + ThemeManager.spacingNormal
        color: ThemeManager.backgroundColor
        z: 2 // Ensure it stays above content
        
        // Subtle top shadow
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: ThemeManager.borderColor
            opacity: 0.5
        }
        
        // Apply button
        AppButton {
            id: applyButton
            anchors.centerIn: parent
            width: 120 // Fixed width for consistency
            height: ThemeManager.buttonHeight * 0.7
            text: "Apply"
            useFixedHeight: false
            
            onClicked: {
                bridge.saveConfigToFile();
                bridge.applyConfig();
            }
        }
    }
}
