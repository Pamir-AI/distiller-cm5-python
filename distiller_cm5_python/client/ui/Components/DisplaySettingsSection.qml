import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

AppSection {
    id: displaySettingsSection

    property alias darkTheme: darkThemeItem.toggleValue

    signal darkThemeToggled(bool enabled)

    title: "DISPLAY SETTINGS"
    compact: true
    
    ColumnLayout {
        width: parent.width
        spacing: ThemeManager.spacingLarge

        // Description text for e-ink optimization
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
        SettingItem {
            id: darkThemeItem
            label: "DARK THEME"
            toggleValue: darkTheme
            onToggleChanged: function(newValue) {
                displaySettingsSection.darkThemeToggled(newValue)
            }
        }
    }
}
