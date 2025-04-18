import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

AppSection {
    id: aboutSection

    title: "About"
    compact: true

    ColumnLayout {
        width: parent.width
        spacing: ThemeManager.spacingNormal

        // App logo/icon (placeholder rectangle, replace with actual logo if available)
        Rectangle {
            id: logoPlaceholder

            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 80
            Layout.preferredHeight: 80
            Layout.topMargin: ThemeManager.spacingNormal
            Layout.bottomMargin: ThemeManager.spacingNormal
            radius: 12
            color: ThemeManager.accentColor
            opacity: 0.9

            Text {
                anchors.centerIn: parent
                text: "P" // First letter of Pamir
                font.pixelSize: 40
                font.bold: true
                font.family: FontManager.primaryFontFamily
                color: "white"
            }
        }

        // Version info with larger text
        Text {
            id: versionInfo

            Layout.fillWidth: true
            Layout.alignment: Qt.AlignHCenter
            Layout.leftMargin: ThemeManager.spacingLarge
            Layout.rightMargin: ThemeManager.spacingLarge
            color: ThemeManager.textColor
            text: AppInfo.versionString
            font.pixelSize: FontManager.fontSizeLarge
            font.family: FontManager.primaryFontFamily
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            elide: Text.ElideNone
        }

        // Separator line
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            Layout.topMargin: ThemeManager.spacingNormal
            Layout.bottomMargin: ThemeManager.spacingNormal
            Layout.leftMargin: ThemeManager.spacingLarge * 2
            Layout.rightMargin: ThemeManager.spacingLarge * 2
            color: ThemeManager.borderColor
        }

        // Copyright info
        Text {
            id: copyrightInfo

            Layout.fillWidth: true
            Layout.leftMargin: ThemeManager.spacingLarge
            Layout.rightMargin: ThemeManager.spacingLarge
            Layout.bottomMargin: ThemeManager.spacingNormal
            color: ThemeManager.secondaryTextColor
            text: AppInfo.copyright
            font.pixelSize: FontManager.fontSizeNormal
            font.family: FontManager.primaryFontFamily
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            elide: Text.ElideNone
        }
    }
}
