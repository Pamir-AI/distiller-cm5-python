import Components 1.0
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

PageBase {
    id: settingsPage
    
    pageName: "Settings"

    // Signal to navigate back to the previous page
    signal backClicked()

    // Track navigable items
    property var focusableItems: []
    
    // Helper function to safely get config values with fallbacks
    function safeGetConfigValue(section, key, fallback) {
        if (bridge && bridge.ready) {
            var value = bridge.getConfigValue(section, key);
            return value !== "" ? value : fallback;
        }
        return fallback;
    }
    
    // Collect all focusable items on this page
    function collectFocusItems() {
        focusableItems = [];
        
        // Add header back button
        if (header && header.backButton && header.backButton.navigable) {
            focusableItems.push(header.backButton);
        }
        
        // Add header apply button
        if (header && header.applyButton && header.applyButton.navigable && header.applyButtonVisible) {
            focusableItems.push(header.applyButton);
        }
        
        // Add dark theme button
        if (darkModeButton && darkModeButton.navigable) {
            focusableItems.push(darkModeButton);
        }
        
        // Add network refresh button
        if (networkInfoSection && networkInfoSection.refreshButton && networkInfoSection.refreshButton.navigable) {
            focusableItems.push(networkInfoSection.refreshButton);
        }
        
        // Initialize focus with our FocusManager, passing the scroll view
        FocusManager.initializeFocusItems(focusableItems, settingsScrollView);
    }
    
    // Ensure focus is set to first item after initialization
    function setInitialFocus() {
        if (focusableItems.length > 0) {
            FocusManager.setFocusToItem(focusableItems[0]);
        }
    }
    
    Component.onCompleted: {
        // Collect focusable items after a short delay to ensure they're created
        Qt.callLater(function() {
            collectFocusItems();
            setInitialFocus();
        });
    }
    
    // Timer to ensure collection after full initialization
    Timer {
        id: initTimer
        interval: 300
        running: true
        repeat: false
        onTriggered: {
            collectFocusItems();
            setInitialFocus();
        }
    }
    
    // Connect to bridge ready signal
    Connections {
        target: bridge
        
        function onBridgeReady() {
            // Reset all components with updated config values when bridge becomes ready
            if (settingsPage.visible) {
                // Force update of all settings sections
                displaySettings.updateFromBridge();
            }
        }
    }

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
        
        // Configure apply button
        applyButtonVisible: anySettingsDirty() 
        
        onBackClicked: {
            settingsPage.backClicked();
        }
        
        onApplyClicked: {
            saveAllSettings();
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
        
        // Setting contentHeight explicitly for proper scrolling
        contentHeight: settingsColumn.height
        
        // Disable scroll position indicator
        showScrollIndicator: false
        
        // Content background for better visual clarity
        Rectangle {
            id: contentBackground
            width: settingsScrollView.width
            height: settingsColumn.height
            color: ThemeManager.transparentColor
            
            // Light background shading for scrollable area
            Rectangle {
                anchors.fill: parent
                color: ThemeManager.lightShadeColor
                visible: ThemeManager.darkMode ? false : true
                opacity: 0.5
            }
        }
        
        // Column of settings sections
        Column {
            id: settingsColumn
            // This ensures the column fills exactly the width of the ScrollView's content area
            width: settingsScrollView.width
            spacing: ThemeManager.spacingNormal
            
            // Enhanced Display Settings
            AppSection {
                id: displaySettings
                
                property bool isDirty: false
                property bool darkTheme: false
                property alias darkThemeButton: darkModeButton
                
                title: "DISPLAY SETTINGS"
                compact: true
                width: parent.width
                
                function updateFromBridge() {
                    if (bridge && bridge.ready) {
                        var savedTheme = bridge.getConfigValue("display", "dark_mode");
                        if (savedTheme !== "") {
                            darkTheme = (savedTheme === "true" || savedTheme === "True");
                            // Update the button text to reflect current state
                            if (darkModeButtonText) {
                                darkModeButtonText.text = darkTheme ? "ON" : "OFF";
                            }
                        }
                        isDirty = false;
                        updateApplyButtonVisibility();
                    }
                }
                
                function getConfig() {
                    return {
                        "dark_mode": darkTheme.toString()
                    };
                }
                
                ColumnLayout {
                    width: parent.width
                    spacing: ThemeManager.spacingLarge
                    
                    // Description text
                    Text {
                        text: "Choose a theme optimized for e-ink display"
                        font.pixelSize: FontManager.fontSizeNormal
                        font.family: FontManager.primaryFontFamily
                        color: ThemeManager.secondaryTextColor
                        Layout.fillWidth: true
                        Layout.bottomMargin: ThemeManager.spacingNormal
                        wrapMode: Text.WordWrap
                    }
                    
                    // Dark theme toggle
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ThemeManager.spacingLarge
                        
                        // Label
                        Text {
                            text: "DARK THEME"
                            font.pixelSize: FontManager.fontSizeNormal
                            font.family: FontManager.primaryFontFamily
                            color: ThemeManager.secondaryTextColor
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignVCenter
                        }
                        
                        // Dark theme button - implemented as a NavigableItem
                        NavigableItem {
                            id: darkModeButton
                            width: 80
                            height: 36
                            navigable: true
                            
                            // Set the clicked signal
                            onClicked: {
                                // Toggle dark theme
                                var newValue = !displaySettings.darkTheme;
                                displaySettings.darkTheme = newValue;
                                darkModeButtonText.text = newValue ? "ON" : "OFF";
                                ThemeManager.setDarkMode(newValue);
                                displaySettings.isDirty = true;
                                updateApplyButtonVisibility();
                            }
                            
                            // Visual rectangle
                            Rectangle {
                                anchors.fill: parent
                                radius: 4
                                color: parent.visualFocus ? ThemeManager.focusBackgroundColor : ThemeManager.buttonColor
                                border.width: parent.visualFocus ? 2 : 1
                                border.color: parent.visualFocus ? ThemeManager.focusBorderColor : ThemeManager.borderColor
                                
                                // Button text
                                Text {
                                    id: darkModeButtonText
                                    anchors.centerIn: parent
                                    text: displaySettings.darkTheme ? "ON" : "OFF"
                                    font.pixelSize: FontManager.fontSizeSmall
                                    font.family: FontManager.primaryFontFamily
                                    color: parent.parent.visualFocus ? ThemeManager.focusTextColor : ThemeManager.textColor
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                                
                                // Optional: touch/mouse handling
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: darkModeButton.clicked()
                                }
                            }
                        }
                    }
                }
            }
            
            // Network Information
            AppSection {
                id: networkInfoSection
                
                property alias refreshButton: ipRefreshButton

                title: "WI-FI INFORMATION"
                compact: true
                width: parent.width
                
                // Connect to bridge ready signal to update network info
                Connections {
                    target: bridge
                    
                    function onBridgeReady() {
                        // Update IP address when bridge is ready
                        if (wifiIpAddress) {
                            var ipAddress = bridge.getWifiIpAddress();
                            wifiIpAddress.ipAddress = ipAddress;
                            wifiIpAddress.text = ipAddress ? ipAddress : "Not available";
                        }
                    }
                }
                
                ColumnLayout {
                    width: parent.width
                    spacing: ThemeManager.spacingLarge
                    
                    // Description text
                    Text {
                        text: "View wifi details for this device"
                        font.pixelSize: FontManager.fontSizeNormal
                        font.family: FontManager.primaryFontFamily
                        color: ThemeManager.secondaryTextColor
                        Layout.fillWidth: true
                        Layout.bottomMargin: ThemeManager.spacingNormal
                        wrapMode: Text.WordWrap
                    }
                    
                    // WiFi IP Address section with refresh button
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ThemeManager.spacingNormal
                        
                        // Left column with label and value
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: ThemeManager.spacingSmall
                            
                            // WiFi IP Address Label
                            Text {
                                text: "IP ADDRESS"
                                font.pixelSize: FontManager.fontSizeNormal
                                font.family: FontManager.primaryFontFamily
                                color: ThemeManager.secondaryTextColor
                                Layout.fillWidth: true
                            }
                            
                            // WiFi IP Address Value
                            Text {
                                id: wifiIpAddress
                                property string ipAddress: ""
                                
                                Component.onCompleted: {
                                    if (bridge && bridge.ready) {
                                        ipAddress = bridge.getWifiIpAddress();
                                        text = ipAddress ? ipAddress : "Not available";
                                    } else {
                                        text = "Bridge not ready";
                                    }
                                }
                                
                                font.pixelSize: FontManager.fontSizeNormal
                                font.family: FontManager.primaryFontFamily
                                color: ThemeManager.textColor
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                                Layout.topMargin: 4
                            }
                        }
                        
                        // Refresh button
                        AppRoundButton {
                            id: ipRefreshButton
                            iconText: "↻"
                            width: 32
                            height: 32
                            showBorder: true
                            navigable: true
                            
                            onClicked: {
                                if (bridge && bridge.ready) {
                                    // Update the IP address display
                                    var newIpAddress = bridge.getWifiIpAddress();
                                    wifiIpAddress.ipAddress = newIpAddress;
                                    wifiIpAddress.text = newIpAddress ? newIpAddress : "Not available";
                                } else {
                                    wifiIpAddress.text = "Bridge not ready";
                                }
                            }
                        }
                    }
                }
            }
            
            // About Section
            AboutSection {
                id: aboutSection
                width: parent.width
            }
            
            // Final bottom spacing
            Item {
                width: parent.width
                height: ThemeManager.spacingLarge * 2
            }
        }
    }
    
    // Helper function to check if any settings are dirty
    function anySettingsDirty() {
        return displaySettings.isDirty;
    }
    
    // Update apply button visibility based on dirty state
    function updateApplyButtonVisibility() {
        header.applyButtonVisible = anySettingsDirty();
        collectFocusItems(); // Refresh focus items when visibility changes
    }
    
    // Save all settings
    function saveAllSettings() {
        if (bridge && bridge.ready) {
            // Display settings
            if (displaySettings.isDirty) {
                var displayConfig = displaySettings.getConfig();
                for (var key in displayConfig) {
                    bridge.setConfigValue("display", key, displayConfig[key]);
                }
            }
            
            // Save changes to config file
            bridge.saveConfig();
            
            // Reset dirty state
            displaySettings.isDirty = false;
            updateApplyButtonVisibility();
        }
    }
}

