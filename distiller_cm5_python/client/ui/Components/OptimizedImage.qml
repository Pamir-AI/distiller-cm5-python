import QtQuick 2.15

// Optimized image component with performance enhancements
Image {
    id: optimizedImage

    // Default properties optimized for performance
    asynchronous: true
    cache: true
    mipmap: smooth
    smooth: true

    // Properties for fade-in effect
    property bool fadeInEffect: true
    property int fadeInDuration: 250

    // Optional error handling
    property string fallbackSource: ""
    property bool showPlaceholder: true

    // Internal state
    readonly property bool isLoading: status === Image.Loading
    readonly property bool hasError: status === Image.Error
    readonly property bool isReady: status === Image.Ready

    // Automatically handle fallback source on error
    onStatusChanged: {
        if (status === Image.Error && fallbackSource !== "") {
            console.warn("Image failed to load: " + source + ", using fallback");
            source = fallbackSource;
        }
    }

    // Fade-in effect when image is loaded
    opacity: fadeInEffect ? (isReady ? 1.0 : 0.3) : 1.0
    Behavior on opacity {
        enabled: optimizedImage.fadeInEffect
        NumberAnimation {
            duration: optimizedImage.fadeInDuration
        }
    }

    // Placeholder rectangle shown during loading or on error
    Rectangle {
        anchors.fill: parent
        visible: optimizedImage.showPlaceholder && (optimizedImage.isLoading || (optimizedImage.hasError && optimizedImage.fallbackSource === ""))
        color: "transparent"
        border.color: ThemeManager.borderColor
        border.width: 1
        radius: 4

        // Loading indicator or error symbol
        Text {
            anchors.centerIn: parent
            text: optimizedImage.hasError ? "!" : "..."
            color: ThemeManager.tertiaryTextColor
            font.pixelSize: Math.min(parent.width, parent.height) * 0.2
        }
    }
}
