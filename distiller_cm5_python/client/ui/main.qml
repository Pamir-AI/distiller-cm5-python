import Components 1.0
import QtQuick
import QtQuick.Controls
import QtQuick.Window

ApplicationWindow {
    id: mainWindow

    // Cache for theme setting to avoid repeated bridge calls
    property bool themeCached: false
    property bool cachedDarkMode: false

    visible: true
    width: 240
    height: 416
    title: AppInfo.appName
    font: FontManager.normal
    flags: Qt.Window | Qt.MaximizeUsingFullscreenGeometryHint

    // Update the FontManager primaryFontFamily when the app loads
    Component.onCompleted: {
        // Use the configured font in the components
        if (configuredFont.status == FontLoader.Ready) {
            FontManager.primaryFontFamily = configuredFont.name;
            console.log("Primary font set to:", configuredFont.name);
        } else {
            console.log("Using fallback font as primary font couldn't be loaded");
        }
        // Set initial focus to key handler
        keyHandler.forceActiveFocus();
    }
    // Handle application shutdown
    onClosing: function (closeEvent) {
        // No bridge available or not ready, just accept the close event
        closeEvent.accepted = false;
        if (bridge && bridge.ready)
            bridge.shutdownApplication(false);
        else
            closeEvent.accepted = true;
    }

    // Dedicated key handler that stays on top of everything
    FocusScope {
        id: keyHandler

        anchors.fill: parent
        focus: true
        z: 2000 // Make sure it's above everything else
        Component.onCompleted: {
            forceActiveFocus();
        }

        // Use this Item to capture all key events
        Item {
            anchors.fill: parent
            focus: true
            Keys.onPressed: function (event) {
                // Log the currently focused item
                console.log("Key Pressed:", event.key, " | Current Focus:", FocusManager.currentItem ? FocusManager.currentItem.objectName : "None", " | Scroll Mode:", FocusManager.scrollModeActive);
                // Only handle navigation keys - UP, DOWN, and ENTER
                if (event.key === Qt.Key_Down) {
                    event.accepted = true;
                    FocusManager.moveFocusDown();
                } else if (event.key === Qt.Key_Up) {
                    event.accepted = true;
                    FocusManager.moveFocusUp();
                } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                    event.accepted = true;
                    // If in scroll mode, exit it with ENTER key
                    if (FocusManager.scrollModeActive) {
                        FocusManager.exitScrollMode();
                        if (FocusManager.scrollTargetItem) {
                            // Force update the property first
                            FocusManager.scrollTargetItem.scrollModeActive = false;
                            // Then trigger the signal if available
                            if (FocusManager.scrollTargetItem.scrollModeChanged)
                                FocusManager.scrollTargetItem.scrollModeChanged(false);

                            // Force a UI update by using a short timer
                            exitScrollModeTimer.start();
                        }
                    } else {
                        // Normal enter key handling
                        FocusManager.handleEnterKey();
                    }
                }
            }
            // Explicitly grab focus whenever anything else tries to take it
            onActiveFocusChanged: {
                if (!activeFocus)
                    forceActiveFocus();
            }
        }

        // Timer for focus management
        Timer {
            interval: 500
            running: true
            repeat: true
            onTriggered: {
                if (!keyHandler.activeFocus)
                    keyHandler.forceActiveFocus();
            }
        }
    }

    // Timer to ensure the UI is updated when exiting scroll mode
    Timer {
        id: exitScrollModeTimer

        interval: 10
        repeat: false
        onTriggered: {
            // Force additional update for any target that might still be in scroll mode
            if (FocusManager.scrollTargetItem)
                FocusManager.scrollTargetItem.scrollModeActive = false;
        }
    }

    // Connect to the bridge ready signal
    Connections {
        function onBridgeReady() {
            // Use the ThemeManager's centralized theme caching
            ThemeManager.initializeTheme();
        }

        target: bridge
    }

    // Custom font from configuration
    FontLoader {
        id: configuredFont

        // Get font path directly from display_config.py via a bridge property
        property string fontPath: {
            if (bridge && bridge.ready) {
                var path = bridge.getPrimaryFontPath();
                // Check if path is relative and convert if needed
                if (path && !path.startsWith("/") && !path.startsWith("file:///") && !path.startsWith("qrc:///"))
                    return path;

                return path;
            }
            return "fonts/MonoramaNerdFont-Medium.ttf";
        }

        source: fontPath
        onStatusChanged: {
            if (status == FontLoader.Ready)
                console.log("Font loaded successfully:", source);
            else if (status == FontLoader.Error)
                console.error("Failed to load font:", source);
        }
    }

    // Keep the JetBrains font as a fallback
    FontLoader {
        id: jetBrainsMono

        source: "fonts/JetBrainsMonoNerdFont-Regular.ttf"
        onStatusChanged: {
            if (status == FontLoader.Ready)
                console.log("JetBrains Mono font loaded successfully");
            else if (status == FontLoader.Error)
                console.error("Failed to load JetBrains Mono font");
        }
    }

    // Main content - single VoiceAssistantPage
    VoiceAssistantPage {
        id: voiceAssistantPage

        anchors.fill: parent
        Component.onCompleted: {
            if (typeof collectFocusItems === "function")
                collectFocusItems();

            // Ensure key handler has focus
            keyHandler.forceActiveFocus();
        }
    }

    // Global toast message for application-wide errors
    MessageToast {
        id: globalToast

        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 100
        z: 1001 // Above everything
    }

    // Handle global bridge errors
    Connections {
        function onErrorOccurred(errorMessage) {
            // Show global error messages only for severe errors
            if (errorMessage.toLowerCase().includes("critical") || errorMessage.toLowerCase().includes("fatal") || errorMessage.toLowerCase().includes("restart"))
                globalToast.showMessage("Error: " + errorMessage, 5000);
        }

        target: bridge
    }

    // Place the background image as the first child so it is always at the back
    OptimizedImage {
        id: backgroundImage

        source: "images/idle-frame.png"
        anchors.fill: parent
        fillMode: Image.Stretch
        opacity: 1 // Full opacity, no transparency
        z: -1

        onStatusChanged: {
            console.log("Background image status:", status, "source:", source);
        }
    }

    // Header area 
    Rectangle {
        id: headerAreaOverlay

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 50
        color: ThemeManager.backgroundColor
        opacity: 1
        z: -0.5
        // Add border around the entire rectangle
        border.width: ThemeManager.borderWidth
        border.color: ThemeManager.black
    }
}
