import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

AppSection {
    id: developerSettingsSection

    property alias debugMode: debugModeItem.toggleValue

    signal debugModeToggled(bool enabled)

    title: "DEVELOPER SETTINGS"
    compact: true
    
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
            onToggleChanged: function(newValue) {
                developerSettingsSection.debugModeToggled(newValue)
            }
        }
    }
} 