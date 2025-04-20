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
    
    // Dedicated key handler that stays on top of everything
    FocusScope {
        id: keyHandler
        
        anchors.fill: parent
        focus: true
        z: 2000 // Make sure it's above everything else
        
        // Use this Item to capture all key events
        Item {
            anchors.fill: parent
            focus: true
            
            Keys.onPressed: function(event) {
                console.log("Key pressed: " + event.key);
                
                // Handle navigation keys
                if (event.key === Qt.Key_Up) {
                    console.log("Key UP pressed");
                    FocusManager.moveFocusUp();
                    event.accepted = true;
                }
                else if (event.key === Qt.Key_Down) {
                    console.log("Key DOWN pressed");
                    FocusManager.moveFocusDown();
                    event.accepted = true;
                }
                else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                    console.log("Key ENTER/RETURN pressed");
                    FocusManager.handleEnterKey();
                    event.accepted = true;
                }
            }
            
            // Explicitly grab focus whenever anything else tries to take it
            onActiveFocusChanged: {
                if (!activeFocus) {
                    console.log("Key handler lost focus - reclaiming");
                    forceActiveFocus();
                }
            }
        }
        
        Component.onCompleted: {
            console.log("Key handler initialized");
            forceActiveFocus();
        }
        
        // Timer to periodically ensure key handler has focus
        Timer {
            interval: 200
            running: true
            repeat: true
            onTriggered: {
                if (!keyHandler.activeFocus) {
                    console.log("Key handler regaining focus");
                    keyHandler.forceActiveFocus();
                }
            }
        }
    }
    
    // Connect to the bridge ready signal
    Connections {
        target: bridge
        
        function onBridgeReady() {
            console.log("Bridge is now ready!")
            
            // Initialize theme from saved settings once bridge is ready
            var savedTheme = bridge.getConfigValue("display", "dark_mode");
            if (savedTheme !== "") {
                ThemeManager.setDarkMode(savedTheme === "true" || savedTheme === "True");
                console.log("Theme initialized from settings: " + (ThemeManager.darkMode ? "Dark" : "Light"));
            } else {
                console.log("Using default theme (Light)");
            }
        }
    }
    
    // Update the FontManager primaryFontFamily when the app loads
    Component.onCompleted: {
        if (jetBrainsMono.status == FontLoader.Ready) {
            // Use the loaded font in the components
            FontManager.primaryFontFamily = jetBrainsMono.name;
        }
        console.log("Application window initialized")
        
        // Set initial focus to key handler
        keyHandler.forceActiveFocus()
    }
    
    // Handle application shutdown
    onClosing: function(closeEvent) {
        closeEvent.accepted = false;
        if (bridge && bridge.ready) {
            bridge.shutdown();
        } else {
            // No bridge available or not ready, just accept the close event
            closeEvent.accepted = true;
        }
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

    // Main content area - full width since we removed the navigation buttons
    StackView {
        id: stackView

        anchors.fill: parent
        initialItem: serverSelectionComponent
        
        // Set focus to the new current item when it changes
        onCurrentItemChanged: {
            if (currentItem) {
                console.log("StackView current item changed");
                Qt.callLater(function() {
                    // Reset focus to the key handler when changing pages
                    console.log("Resetting focus to key handler");
                    keyHandler.forceActiveFocus();
                    
                    // Initialize focusable items on the current page
                    if (currentItem.collectFocusItems) {
                        console.log("Collecting focusable items on current page");
                        try {
                            currentItem.collectFocusItems();
                            
                            // Ensure the key handler gets focus after a small delay
                            focusTimer.restart();
                        } catch (e) {
                            console.error("Error collecting focus items: " + e);
                        }
                    } else {
                        console.log("Current page does not have collectFocusItems method");
                    }
                });
            }
        }
        
        // Timer to ensure focus returns to key handler
        Timer {
            id: focusTimer
            interval: 100
            repeat: false
            onTriggered: {
                console.log("Focus timer triggered - forcing focus to key handler");
                keyHandler.forceActiveFocus();
            }
        }

        // Server Selection Page
        Component {
            id: serverSelectionComponent

            ServerSelectionPage {
                onServerSelected: function(serverPath) {
                    console.log("onServerSelected called with path: " + serverPath);
                    if (!bridge.ready) {
                        console.error("Bridge not ready, cannot connect to server");
                        // Display an error message to the user
                        globalToast.showMessage("Error: Application not fully initialized. Please restart.", 5000);
                        return;
                    }
                    
                    // Set the selected server and connect to it
                    bridge.setServerPath(serverPath);
                    
                    // This returns an error message if connection fails, or empty string on success
                    var connectionResult = bridge.connectToServer();
                    
                    if (connectionResult) {
                        // Connection failed, show error message
                        console.error("Connection failed: " + connectionResult);
                        globalToast.showMessage("Connection failed: " + connectionResult, 5000);
                        return;
                    }
                    
                    console.log("Connecting to server...");
                    
                    // Push the voice assistant page with a placeholder name
                    var voiceAssistantPage = stackView.push(voiceAssistantComponent);
                    
                    // Create and start the server name update timer
                    var serverNameUpdateTimer = serverNameUpdateTimerComponent.createObject(voiceAssistantPage, {
                        "targetPage": voiceAssistantPage
                    });
                    serverNameUpdateTimer.start();
                }
            }
        }
        
        // Timer component for updating server name
        Component {
            id: serverNameUpdateTimerComponent
            
            Timer {
                property var targetPage
                
                interval: 1000
                repeat: false
                running: false
                
                onTriggered: {
                    if (!bridge.ready) {
                        console.error("Bridge not ready in timer, cannot update server name");
                        destroy();
                        return;
                    }
                    
                    // Get the status message which should now contain the correct server name
                    var status = bridge.get_status();
                    console.log("Current status: " + status);
                    if (status.indexOf("Connected to") === 0) {
                        var extractedName = status.substring("Connected to ".length).trim();
                        if (extractedName) {
                            console.log("Setting server name to: " + extractedName);
                            targetPage.serverName = extractedName;
                        }
                    }
                    
                    // Destroy the timer after use
                    destroy();
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
                    if (bridge.ready) {
                        bridge.getAvailableServers();
                    }
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

                    OptimizedImage {
                        id: logoImage

                        source: ThemeManager.darkMode ? "images/pamir_logo_white.webp" : "images/pamir_logo.webp"
                        width: 150
                        height: 150
                        anchors.centerIn: parent
                        fillMode: Image.PreserveAspectFit
                        sourceSize.width: 300
                        sourceSize.height: 300
                        fadeInDuration: 300
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

    // Log messages to debug console
    Connections {
        target: console
        
        // Need a signal handler that matches console signals
        function onMessageLogged(message) {
            if (logTextArea)
                logTextArea.append(message);
        }
    }

    // Create a signal handler for console.log that the text area can connect to
    QtObject {
        id: consoleHelper

        signal logMessage(string message)

        Component.onCompleted: {
            // Override the console.log function
            var originalLog = console.log;
            console.log = function(message) {
                // Call the original log function
                originalLog.call(console, message);
                // Emit our custom signal
                consoleHelper.logMessage(message);
            };
        }
    }
    
    // Connect the debug console text area to the log helper
    Connections {
        target: consoleHelper
        
        function onLogMessage(message) {
            if (logTextArea)
                logTextArea.append(message);
        }
    }

    // Handle F12 key to toggle debug console
    Item {
        anchors.fill: parent
        focus: true
        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_F12) {
                debugConsole.visible = !debugConsole.visible;
                event.accepted = true;
            }
        }
    }

    // Background
    background: Rectangle {
        color: ThemeManager.backgroundColor
    }

    // Global toast message for application-wide errors
    MessageToast {
        id: globalToast
        
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 100
        z: 1001 // Above everything, including the splash screen
    }
    
    // Handle global bridge errors
    Connections {
        target: bridge
        
        function onErrorOccurred(errorMessage) {
            // Log all errors to console for debugging
            console.error("Bridge error: " + errorMessage);
            
            // Show global error messages only for severe errors
            if (errorMessage.toLowerCase().includes("critical") || 
                errorMessage.toLowerCase().includes("fatal") ||
                errorMessage.toLowerCase().includes("restart")) {
                globalToast.showMessage("Error: " + errorMessage, 5000);
            }
        }
    }
}

