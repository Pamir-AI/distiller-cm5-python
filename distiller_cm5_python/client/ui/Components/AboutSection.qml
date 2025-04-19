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

        // App logo image that changes based on theme
        OptimizedImage {
            id: logoImage
            
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 100
            Layout.preferredHeight: 100
            Layout.topMargin: ThemeManager.spacingNormal
            Layout.bottomMargin: ThemeManager.spacingNormal
            
            source: ThemeManager.darkMode ? "../images/pamir_logo_white.webp" : "../images/pamir_logo.webp"
            fillMode: Image.PreserveAspectFit
            sourceSize.width: 200
            sourceSize.height: 200
            
            // Set fadeInDuration to match the theme animation duration
            fadeInDuration: ThemeManager.animationDuration
            
            // Add a smooth transition when theme changes
            Behavior on source {
                PropertyAnimation {
                    target: logoImage
                    property: "opacity"
                    from: 0.8
                    to: 1.0
                    duration: ThemeManager.animationDuration
                }
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
