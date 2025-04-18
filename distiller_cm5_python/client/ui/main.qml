import "."
import Components 1.0
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15

ApplicationWindow {
    id: mainWindow

    // Navigation function
    function pushSettingsPage() {
        stackView.push(settingsPageComponent);
    }

    visible: true
    width: 256
    height: 384
    title: AppInfo.appName
    font: FontManager.normal
    // Update the FontManager primaryFontFamily and initialize theme when the app loads
    Component.onCompleted: {
        console.log("--- Main.qml Component.onCompleted START ---");
        if (jetBrainsMono.status == FontLoader.Ready)
            // Use the loaded font in the components
            FontManager.primaryFontFamily = jetBrainsMono.name;

        // Initialize theme from saved settings
        var savedTheme = bridge.getConfigValue("display", "dark_mode");
        if (savedTheme !== "") {
            ThemeManager.setDarkMode(savedTheme === "true" || savedTheme === "True");
            console.log("Theme initialized from settings: " + (ThemeManager.darkMode ? "Dark" : "Light"));
        } else {
            console.log("Using default theme (Light)");
        }
    }
    // Handle application shutdown
    onClosing: function(closeEvent) {
        closeEvent.accepted = false;
        bridge.shutdown();
    }

    // Custom font
    FontLoader {
        id: jetBrainsMono

        source: "fonts/JetBrainsMonoNerdFont-Regular.ttf"
        onStatusChanged: {
            if (status == FontLoader.Ready)
                console.log("JetBrains Mono font loaded successfully");

        }
    }

    // Main content area
    StackView {
        id: stackView

        anchors.fill: parent
        initialItem: serverSelectionComponent

        // Server Selection Page
        Component {
            id: serverSelectionComponent

            ServerSelectionPage {
                onServerSelected: function(serverPath) {
                    console.log("onServerSelected called with path: " + serverPath);
                    // Set the selected server and connect to it
                    bridge.setServerPath(serverPath);
                    // This returns the file-based name, which may not be correct
                    var initialServerName = bridge.connectToServer();
                    console.log("Connecting to server: " + initialServerName);
                    // Push the voice assistant page with a placeholder name
                    var voiceAssistantPage = stackView.push(voiceAssistantComponent);
                    // Use a timer to delay updating the server name until the connection is complete
                    var updateTimer = Qt.createQmlObject('import QtQuick 2.15; Timer {interval: 1000; repeat: false; running: true}', voiceAssistantPage);
                    updateTimer.triggered.connect(function() {
                        // Get the status message which should now contain the correct server name
                        var status = bridge.get_status();
                        console.log("Current status: " + status);
                        if (status.indexOf("Connected to") === 0) {
                            var extractedName = status.substring("Connected to ".length).trim();
                            if (extractedName) {
                                console.log("Setting server name to: " + extractedName);
                                voiceAssistantPage.serverName = extractedName;
                            }
                        }
                    });
                }
            }

        }

        // Voice Assistant Page
        Component {
            id: voiceAssistantComponent

            VoiceAssistantPage {
                onSelectNewServer: {
                    // Replace the current view with the server selection page
                    stackView.replace(serverSelectionComponent);
                    // Request servers again to refresh the list
                    bridge.getAvailableServers();
                }
            }

        }

        // Settings Page
        Component {
            id: settingsPageComponent

            SettingsPage {
                onBackClicked: {
                    stackView.pop();
                }
            }

        }

        // Simple fade transitions optimized for e-ink
        pushEnter: Transition {
            PropertyAnimation {
                property: "opacity"
                from: 0
                to: 1
                duration: ThemeManager.animationDuration
            }

        }

        pushExit: Transition {
            PropertyAnimation {
                property: "opacity"
                from: 1
                to: 0
                duration: ThemeManager.animationDuration
            }

        }

        popEnter: Transition {
            PropertyAnimation {
                property: "opacity"
                from: 0
                to: 1
                duration: ThemeManager.animationDuration
            }

        }

        popExit: Transition {
            PropertyAnimation {
                property: "opacity"
                from: 1
                to: 0
                duration: ThemeManager.animationDuration
            }

        }

    }

    // E-ink optimized splash screen - refined for better aesthetics
    Rectangle {
        id: splashScreen

        anchors.fill: parent
        color: ThemeManager.backgroundColor
        z: 1000

        // Create a container for better positioning
        Rectangle {
            id: splashContainer

            anchors.centerIn: parent
            width: parent.width * 0.8
            height: contentColumn.height
            color: "transparent"

            // Column layout for vertical alignment
            Column {
                id: contentColumn

                width: parent.width
                spacing: ThemeManager.spacingLarge

                // Logo with reduced size and nested in a nicely bordered container
                Rectangle {
                    id: logoContainer

                    width: 154
                    height: 154
                    color: ThemeManager.backgroundColor
                    border.color: ThemeManager.borderColor
                    border.width: ThemeManager.borderWidth
                    radius: width / 2
                    anchors.horizontalCenter: parent.horizontalCenter

                    Image {
                        id: logoImage

                        source: ThemeManager.darkMode ? "images/pamir_logo_white.webp" : "images/pamir_logo.webp"
                        width: 150
                        height: 150
                        anchors.centerIn: parent
                        fillMode: Image.PreserveAspectFit
                    }

                }

                // Improved typography
                Column {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: ThemeManager.spacingSmall

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: AppInfo.appName.split(" ")[0]
                        color: ThemeManager.textColor
                        font.pixelSize: FontManager.fontSizeXLarge
                        font.bold: true
                        font.family: FontManager.primaryFontFamily
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: AppInfo.appName.split(" ").slice(1).join(" ")
                        color: ThemeManager.secondaryTextColor
                        font.pixelSize: FontManager.fontSizeMedium
                        font.family: FontManager.primaryFontFamily
                    }

                    // Version information
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: AppInfo.shortVersionString
                        color: ThemeManager.tertiaryTextColor
                        font.pixelSize: FontManager.fontSizeSmall
                        font.family: FontManager.primaryFontFamily
                        topPadding: 4
                    }

                }

            }

        }

        // Simple loading indicator optimized for e-ink and Qt6
        Row {
            id: loadingIndicator

            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: ThemeManager.spacingLarge
            spacing: ThemeManager.spacingSmall

            // Use a Timer-based approach instead of SequentialAnimation for better compatibility
            Timer {
                id: dotTimer

                property int currentDot: 0

                interval: 400
                running: true
                repeat: true
                onTriggered: {
                    // Update the opacity of current dot and reset previous dot
                    var prevDot = (currentDot + 4) % 5;
                    loadingRepeater.itemAt(prevDot).opacity = 0.3;
                    loadingRepeater.itemAt(currentDot).opacity = 1;
                    // Move to next dot
                    currentDot = (currentDot + 1) % 5;
                }
            }

            // Static loading dots
            Repeater {
                id: loadingRepeater

                model: 5

                Rectangle {
                    width: 6
                    height: 6
                    radius: 3
                    color: ThemeManager.textColor
                    opacity: 0.3
                }

            }

        }

        // Start fade out after a longer delay to give e-ink time to render
        Timer {
            interval: 3000
            running: true
            onTriggered: {
                splashFadeOut.start();
            }
        }

        // Simple fade out with longer duration for e-ink
        NumberAnimation on opacity {
            id: splashFadeOut

            from: 1
            to: 0
            duration: ThemeManager.animationDuration * 2
            running: false
            onFinished: {
                splashScreen.visible = false;
            }
        }

    }

    // Debug console overlay (press F12 to toggle)
    Rectangle {
        id: debugConsole

        anchors.fill: parent
        color: ThemeManager.backgroundColor
        opacity: 0.95
        visible: false
        z: 2000

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ThemeManager.spacingNormal

            RowLayout {
                Layout.fillWidth: true

                Text {
                    text: "Debug Console"
                    color: ThemeManager.textColor
                    font.pixelSize: FontManager.fontSizeLarge
                    font.bold: true
                }

                Item {
                    Layout.fillWidth: true
                }

                Text {
                    text: "Press F12 to hide"
                    color: ThemeManager.tertiaryTextColor
                    font.pixelSize: FontManager.fontSizeNormal
                }

            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: ThemeManager.backgroundColor
                border.color: ThemeManager.borderColor
                border.width: ThemeManager.borderWidth

                AppScrollView {
                    id: logScrollView

                    anchors.fill: parent
                    anchors.margins: ThemeManager.spacingNormal
                    contentHeight: logTextArea.implicitHeight
                    showEdgeEffects: true

                    TextArea {
                        id: logTextArea

                        function append(message) {
                            text = text + message + "\n";
                            // Auto-scroll to bottom
                            cursorPosition = text.length;
                        }

                        readOnly: true
                        wrapMode: TextEdit.Wrap
                        color: ThemeManager.textColor
                        background: null
                        // Sample logs
                        text: "Application starting...\n"
                    }

                }

            }

        }

    }

    // Create a signal handler for console.log that the text area can connect to
    QtObject {
        id: consoleHelper

        signal logMessage(string message)

        Component.onCompleted: {
            // Override the console.log function
            console.log = function(message) {
                consoleHelper.logMessage(message);
            };
        }
    }

    // Connect the debug console text area to the log helper
    Connections {
        function onLogMessage(message) {
            if (logTextArea)
                logTextArea.append(message);

        }

        target: consoleHelper
    }

    // Handle F12 key to toggle debug console
    Item {
        id: f12HandlerItem
        anchors.fill: parent
        focus: false
        
        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_F12) {
                debugConsole.visible = !debugConsole.visible;
                if (debugConsole.visible) {
                   logScrollView.forceActiveFocus();
                } else {
                    if (stackView.currentItem) {
                        stackView.currentItem.forceActiveFocus();
                    }
                }
                event.accepted = true;
            } else {
                event.accepted = false;
            }
        }
    }

    // Background
    background: Rectangle {
        color: ThemeManager.backgroundColor
    }

}
