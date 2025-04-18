import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

AppSection {
    id: llmSettingsSection

    property alias serverUrl: serverUrlInput.text
    property alias enableStreaming: streamingItem.toggleValue

    signal serverUrlEdited(string url)
    signal streamingToggled(bool enabled)

    title: "LLM SETTINGS"
    compact: true

    ColumnLayout {
        width: parent.width
        spacing: ThemeManager.spacingLarge

        // Server URL
        ColumnLayout {
            Layout.fillWidth: true
            spacing: ThemeManager.spacingNormal

            Text {
                text: "SERVER URL"
                font.pixelSize: FontManager.fontSizeNormal
                font.family: FontManager.primaryFontFamily
                color: ThemeManager.secondaryTextColor
            }

            Rectangle {
                id: urlInputContainer
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(48, serverUrlInput.implicitHeight + 16)
                radius: ThemeManager.borderRadius
                color: ThemeManager.backgroundColor
                border.color: serverUrlInput.activeFocus ? ThemeManager.accentColor : ThemeManager.borderColor
                border.width: ThemeManager.borderWidth
                
                TextEdit {
                    id: serverUrlInput
                    anchors.fill: parent
                    anchors.margins: 8
                    font: FontManager.normal
                    color: ThemeManager.textColor
                    wrapMode: TextEdit.Wrap
                    selectByMouse: true
                    verticalAlignment: TextEdit.AlignVCenter
                    
                    onTextChanged: {
                        var contentHeight = serverUrlInput.contentHeight
                        urlInputContainer.height = Math.max(48, contentHeight + 16)
                        llmSettingsSection.serverUrlEdited(text)
                    }
                }
            }
        }

        // Streaming toggle
        SettingItem {
            id: streamingItem
            label: "ENABLE STREAMING"
            toggleValue: enableStreaming
            onToggleChanged: function(newValue) {
                llmSettingsSection.streamingToggled(newValue)
            }
        }
    }
}
