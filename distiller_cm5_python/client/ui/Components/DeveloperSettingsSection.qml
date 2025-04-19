import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

AppSection {
    id: developerSettingsSection

    property alias debugMode: debugModeItem.toggleValue
    property bool isDirty: false

    signal debugModeToggled(bool enabled)
    signal configChanged()

    title: "DEVELOPER SETTINGS"
    compact: true
    navigable: true
    
    function updateFromBridge() {
        if (bridge && bridge.ready) {
            var loggingLevel = bridge.getConfigValue("logging", "level");
            debugMode = (loggingLevel === "DEBUG");
            isDirty = false;
        }
    }
    
    function getConfig() {
        return {
            "level": debugMode ? "DEBUG" : "INFO"
        };
    }

    ColumnLayout {
        width: parent.width
        spacing: ThemeManager.spacingLarge

        // Description text for debug mode
        Text {
            text: "Enable advanced debugging options"
            font.pixelSize: FontManager.fontSizeNormal
            font.family: FontManager.primaryFontFamily
            color: ThemeManager.secondaryTextColor
            Layout.fillWidth: true
            Layout.bottomMargin: ThemeManager.spacingNormal
            wrapMode: Text.WordWrap
        }

        // Debug mode toggle
        SettingItem {
            id: debugModeItem
            label: "DEBUG MODE"
            toggleValue: debugMode
            onUserToggled: function(newValue) {
                developerSettingsSection.debugModeToggled(newValue);
                developerSettingsSection.isDirty = true;
                developerSettingsSection.configChanged();
            }
        }
    }
} 