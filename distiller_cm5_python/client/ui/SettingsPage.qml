import Components 1.0
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

PageBase {
    id: settingsPage
    
    pageName: "Settings"

    // Signal to navigate back to the previous page
    signal backClicked()

    // Track currently focused section
    property var focusableItems: []
    property var allFocusableItems: [] // Contains both sections and their internal controls
    
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
        console.log("SettingsPage: Collecting focusable items");
        focusableItems = []
        allFocusableItems = []
        
        // Add header back button
        if (header && header.backButton && header.backButton.navigable) {
            console.log("SettingsPage: Adding back button");
            focusableItems.push(header.backButton)
            allFocusableItems.push(header.backButton)
        }
        
        // Add settings sections' focusable items
        var sections = settingsColumn.getSettingSections()
        console.log("SettingsPage: Found " + sections.length + " settings sections");
        
        for (var i = 0; i < sections.length; i++) {
            var section = sections[i]
            if (section.visible && section.navigable) {
                console.log("SettingsPage: Adding section: " + section.title);
                focusableItems.push(section)
                allFocusableItems.push(section)
                
                // If the section has internal controls, collect them too
                if (section.getNavigableControls && typeof section.getNavigableControls === "function") {
                    var controls = section.getNavigableControls();
                    for (var j = 0; j < controls.length; j++) {
                        if (controls[j] && controls[j].navigable) {
                            console.log("SettingsPage: Adding control from " + section.title);
                            allFocusableItems.push(controls[j]);
                        }
                    }
                }
            }
        }
        
        // Add apply button
        if (applyButton && applyButton.navigable) {
            console.log("SettingsPage: Adding apply button");
            focusableItems.push(applyButton)
            allFocusableItems.push(applyButton)
        }
        
        console.log("SettingsPage: Total focusable sections: " + focusableItems.length);
        console.log("SettingsPage: Total focusable items including controls: " + allFocusableItems.length);
        
        // Initialize focus with our FocusManager, passing the scroll view
        FocusManager.initializeFocusItems(focusableItems, settingsScrollView)
    }
    
    Component.onCompleted: {
        // Collect focusable items after a short delay to ensure they're created
        console.log("SettingsPage: Component completed");
        Qt.callLater(collectFocusItems)
    }
    
    // Timer to ensure collection after full initialization
    Timer {
        id: initTimer
        interval: 200
        running: true
        repeat: false
        onTriggered: {
            collectFocusItems();
        }
    }
    
    // Connect to bridge ready signal
    Connections {
        target: bridge
        
        function onBridgeReady() {
            // Reset all components with updated config values when bridge becomes ready
            if (settingsPage.visible) {
                // Force update of all settings sections
                // This will cause them to read current values from the bridge
                settingsColumn.forceUpdate();
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
        anchors.bottom: applyButton.top
        anchors.topMargin: 1 // Connect with header
        anchors.leftMargin: ThemeManager.spacingSmall // Reduced left margin
        anchors.rightMargin: ThemeManager.spacingSmall // Reduced right margin
        anchors.bottomMargin: ThemeManager.spacingNormal // Make room for the apply button
        
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
            
            // Function to force update of all children
            function forceUpdate() {
                for (var i = 0; i < children.length; i++) {
                    var child = children[i];
                    if (child && typeof child.updateFromBridge === "function") {
                        child.updateFromBridge();
                    }
                }
            }
            
            // Get all setting sections for navigation
            function getSettingSections() {
                var sections = [];
                for (var i = 0; i < children.length; i++) {
                    var child = children[i];
                    if (child && typeof child.updateFromBridge === "function") {
                        sections.push(child);
                    }
                }
                return sections;
            }
            
            // Display Settings
            DisplaySettingsSection {
                id: displaySettings
                width: parent.width
                navigable: true
                
                onConfigChanged: {
                    applyButton.dirty = true;
                }
                
                // Must manually apply changes for dark mode since it's not persisted yet
                onDarkThemeToggled: function(enabled) {
                    ThemeManager.setDarkMode(enabled);
                }
            }
            
            // Audio Settings (simplified)
            AudioSettingsSection {
                id: audioSettings
                width: parent.width
                navigable: true
                
                onConfigChanged: {
                    applyButton.dirty = true;
                }
            }
            
            // LLM Settings
            LlmSettingsSection {
                id: llmSettings
                width: parent.width 
                navigable: true
                
                onConfigChanged: {
                    applyButton.dirty = true;
                }
            }
            
            // Developer Settings
            DeveloperSettingsSection {
                id: developerSettings
                width: parent.width
                navigable: true
                
                onConfigChanged: {
                    applyButton.dirty = true;
                }
            }
            
            // Network Information
            NetworkInfoSection {
                id: networkInfoSection
                width: parent.width
                navigable: true
            }
            
            // About Section
            AboutSection {
                id: aboutSection
                width: parent.width
                navigable: true
            }
            
            // Final bottom spacing
            Item {
                width: parent.width
                height: ThemeManager.spacingLarge * 2
            }
        }
    }
    
    // Apply button (fixed to bottom)
    AppButton {
        id: applyButton
        text: "Apply Changes"
        property bool dirty: false
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom  
        anchors.bottomMargin: ThemeManager.spacingNormal
        width: Math.min(parent.width - ThemeManager.spacingLarge * 2, 220)
        visible: dirty
        navigable: true
        
        onClicked: {
            // Collect settings from all sections
            if (bridge && bridge.ready) {
                // Display settings
                if (displaySettings.isDirty) {
                    var displayConfig = displaySettings.getConfig();
                    for (var key in displayConfig) {
                        bridge.setConfigValue("display", key, displayConfig[key]);
                    }
                }
                
                // Audio settings
                if (audioSettings.isDirty) {
                    var audioConfig = audioSettings.getConfig();
                    for (var key in audioConfig) {
                        bridge.setConfigValue("audio", key, audioConfig[key]);
                    }
                }
                
                // LLM settings
                if (llmSettings.isDirty) {
                    var llmConfig = llmSettings.getConfig();
                    for (var key in llmConfig) {
                        bridge.setConfigValue("llm", key, llmConfig[key]);
                    }
                }
                
                // Developer settings
                if (developerSettings.isDirty) {
                    var devConfig = developerSettings.getConfig();
                    for (var key in devConfig) {
                        bridge.setConfigValue("developer", key, devConfig[key]);
                    }
                }
                
                // Save changes to config file
                bridge.saveConfig();
                
                // Reset dirty state
                applyButton.dirty = false;
                displaySettings.isDirty = false;
                audioSettings.isDirty = false;
                llmSettings.isDirty = false;
                developerSettings.isDirty = false;
            }
        }
    }
}

