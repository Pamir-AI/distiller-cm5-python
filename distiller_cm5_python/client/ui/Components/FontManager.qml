import QtQuick 2.15
pragma Singleton

QtObject {
    // Large headers

    id: fontManager

    // Font family - property is readwrite so it can be updated when a custom font is loaded
    property string primaryFontFamily: "JetBrainsMono Nerd Font"
    // Font sizes
    readonly property real fontSizeSmall: 12
    // Small text
    readonly property real fontSizeNormal: 14
    // Normal text
    readonly property real fontSizeMedium: 16
    // Medium text
    readonly property real fontSizeLarge: 18
    // Section headers
    readonly property real fontSizeXLarge: 20
    // Font weights
    readonly property int fontWeightNormal: Font.Normal
    readonly property int fontWeightBold: Font.Bold
    // Property to update font objects when primaryFontFamily changes
    property var normalFontTemplate: {
        "family": primaryFontFamily,
        "pixelSize": fontSizeNormal,
        "weight": fontWeightNormal
    }
    // Pre-defined font objects that update when primaryFontFamily changes
    property font normal: Qt.font(normalFontTemplate)
    property font normalBold: Qt.font({
        "family": primaryFontFamily,
        "pixelSize": fontSizeNormal,
        "weight": fontWeightBold
    })
    property font small: Qt.font({
        "family": primaryFontFamily,
        "pixelSize": fontSizeSmall,
        "weight": fontWeightNormal
    })
    property font smallBold: Qt.font({
        "family": primaryFontFamily,
        "pixelSize": fontSizeSmall,
        "weight": fontWeightBold
    })
    property font medium: Qt.font({
        "family": primaryFontFamily,
        "pixelSize": fontSizeMedium,
        "weight": fontWeightNormal
    })
    property font mediumBold: Qt.font({
        "family": primaryFontFamily,
        "pixelSize": fontSizeMedium,
        "weight": fontWeightBold
    })
    property font large: Qt.font({
        "family": primaryFontFamily,
        "pixelSize": fontSizeLarge,
        "weight": fontWeightNormal
    })
    property font largeBold: Qt.font({
        "family": primaryFontFamily,
        "pixelSize": fontSizeLarge,
        "weight": fontWeightBold
    })
    property font heading: Qt.font({
        "family": primaryFontFamily,
        "pixelSize": fontSizeLarge,
        "weight": fontWeightBold
    })
    property font title: Qt.font({
        "family": primaryFontFamily,
        "pixelSize": fontSizeXLarge,
        "weight": fontWeightBold
    })

    // Update all font objects when primaryFontFamily changes
    onPrimaryFontFamilyChanged: {
        normalFontTemplate.family = primaryFontFamily;
        normal = Qt.font(normalFontTemplate);
        normalBold = Qt.font({
            "family": primaryFontFamily,
            "pixelSize": fontSizeNormal,
            "weight": fontWeightBold
        });
        small = Qt.font({
            "family": primaryFontFamily,
            "pixelSize": fontSizeSmall,
            "weight": fontWeightNormal
        });
        smallBold = Qt.font({
            "family": primaryFontFamily,
            "pixelSize": fontSizeSmall,
            "weight": fontWeightBold
        });
        medium = Qt.font({
            "family": primaryFontFamily,
            "pixelSize": fontSizeMedium,
            "weight": fontWeightNormal
        });
        mediumBold = Qt.font({
            "family": primaryFontFamily,
            "pixelSize": fontSizeMedium,
            "weight": fontWeightBold
        });
        large = Qt.font({
            "family": primaryFontFamily,
            "pixelSize": fontSizeLarge,
            "weight": fontWeightNormal
        });
        largeBold = Qt.font({
            "family": primaryFontFamily,
            "pixelSize": fontSizeLarge,
            "weight": fontWeightBold
        });
        heading = Qt.font({
            "family": primaryFontFamily,
            "pixelSize": fontSizeLarge,
            "weight": fontWeightBold
        });
        title = Qt.font({
            "family": primaryFontFamily,
            "pixelSize": fontSizeXLarge,
            "weight": fontWeightBold
        });
    }
}
