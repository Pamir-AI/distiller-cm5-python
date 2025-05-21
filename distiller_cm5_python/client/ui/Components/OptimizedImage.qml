import QtQuick

// Optimized image component with performance enhancements for e-ink
Image {
    id: optimizedImage

    // Properties for fade-in effect (disabled for e-ink)
    property bool fadeInEffect: false
    property int fadeInDuration: 0
    // Optional error handling
    property string fallbackSource: ""
    property bool showPlaceholder: true
    // Internal state
    readonly property bool isLoading: status === Image.Loading
    readonly property bool hasError: status === Image.Error
    readonly property bool isReady: status === Image.Ready

    // Default properties optimized for performance
    asynchronous: true
    cache: true
    smooth: true
    mipmap: smooth

    // Use the sourceClipRect property for better performance
    sourceClipRect: Qt.rect(0, 0, sourceSize.width, sourceSize.height)

    // Automatically handle fallback source on error
    onStatusChanged: {
        if (status === Image.Error && fallbackSource !== "") {
            console.warn("Image failed to load: " + source + ", using fallback");
            source = fallbackSource;
        }
    }
    // No fade-in effect for e-ink display
    opacity: 1

    // Placeholder rectangle shown during loading or on error
    Rectangle {
        anchors.fill: parent
        visible: optimizedImage.showPlaceholder && (optimizedImage.isLoading || (optimizedImage.hasError && optimizedImage.fallbackSource === ""))
        color: ThemeManager.transparentColor
        border.color: ThemeManager.black
        border.width: ThemeManager.borderWidth
        radius: ThemeManager.borderRadius

        // Loading indicator or error symbol
        Text {
            anchors.centerIn: parent
            text: optimizedImage.hasError ? "!" : "..."
            color: ThemeManager.textColor
            font.pixelSize: Math.min(parent.width, parent.height) * 0.2
        }
    }
}
