import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

AppSection {
    id: audioSettingsSection

    property alias volume: volumeSlider.value

    signal volumeAdjusted(real value)

    title: "AUDIO SETTINGS"
    compact: true

    ColumnLayout {
        width: parent.width
        spacing: ThemeManager.spacingNormal

        // Volume slider
        ColumnLayout {
            Layout.fillWidth: true
            spacing: ThemeManager.spacingNormal

            Text {
                text: "VOLUME (" + Math.round(volumeSlider.value * 100) + "%)"
                font.pixelSize: FontManager.fontSizeNormal
                font.family: FontManager.primaryFontFamily
                color: ThemeManager.secondaryTextColor
                Layout.bottomMargin: 8
            }

            Slider {
                id: volumeSlider

                Layout.fillWidth: true
                Layout.topMargin: 4
                Layout.bottomMargin: 4
                from: 0
                to: 1
                stepSize: 0.05
                onMoved: {
                    audioSettingsSection.volumeAdjusted(value);
                }

                background: Rectangle {
                    x: volumeSlider.leftPadding
                    y: volumeSlider.topPadding + volumeSlider.availableHeight / 2 - height / 2
                    width: volumeSlider.availableWidth
                    height: 6
                    radius: 3
                    color: ThemeManager.buttonColor
                    border.color: ThemeManager.borderColor
                    border.width: ThemeManager.borderWidth

                    Rectangle {
                        width: volumeSlider.visualPosition * parent.width
                        height: parent.height
                        color: ThemeManager.accentColor
                        radius: 3
                    }
                }

                handle: Rectangle {
                    x: volumeSlider.leftPadding + volumeSlider.visualPosition * (volumeSlider.availableWidth - width)
                    y: volumeSlider.topPadding + volumeSlider.availableHeight / 2 - height / 2
                    width: 20
                    height: 20
                    radius: 10
                    color: volumeSlider.pressed ? ThemeManager.buttonColor : ThemeManager.backgroundColor
                    border.color: ThemeManager.borderColor
                    border.width: ThemeManager.borderWidth
                }
            }
        }
    }
}
