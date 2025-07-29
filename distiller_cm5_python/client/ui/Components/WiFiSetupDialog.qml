import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

Rectangle {
    id: wifiSetupDialog

    property bool isVisible: false
    property var focusableItems: []
    property string currentState: "idle"
    property string statusMessage: ""
    property string hotspotSSID: ""
    property string hotspotPassword: ""
    property string hotspotIP: "192.168.4.1"
    property string connectedNetwork: ""
    property string connectedIP: ""
    property string errorMessage: ""
    property bool scrollModeActive: false

    // Timing properties for smooth UX
    property bool showHotspotInstructions: false
    property bool showSuccessMessage: false

    signal dialogClosed
    signal scrollModeChanged(bool active)

    // Timer for hotspot setup delay
    Timer {
        id: hotspotSetupTimer
        interval: 3000 // 3 seconds delay
        running: false
        repeat: false
        onTriggered: {
            showHotspotInstructions = true;
        }
    }

    // Timer for success message delay
    Timer {
        id: successDelayTimer
        interval: 2000 // 2 seconds delay
        running: false
        repeat: false
        onTriggered: {
            showSuccessMessage = true;
        }
    }

    function collectFocusItems() {
        focusableItems = [];

        // Add content list view for navigation if visible
        if (contentListView && contentListView.visible) {
            contentListView.objectName = "ContentListView";
            focusableItems.push(contentListView);
        }

        // Add stop/close button if visible
        if (stopButton && stopButton.visible && stopButton.navigable) {
            stopButton.objectName = "StopButton";
            focusableItems.push(stopButton);
        }

        if (closeButton && closeButton.visible && closeButton.navigable) {
            closeButton.objectName = "CloseButton";
            focusableItems.push(closeButton);
        }

        // Initialize focus with our FocusManager, passing contentListView as the scroll view
        FocusManager.initializeFocusItems(focusableItems, contentListView);
        // Set focus to first item if available
        if (focusableItems.length > 0)
            FocusManager.setFocusToItem(focusableItems[0]);
    }

    // Open the dialog
    function open() {
        isVisible = true;
        visible = true;

        // Start WiFi setup process
        if (bridge && bridge.wifiSetupBridge) {
            bridge.wifiSetupBridge.startWiFiSetup();
        }

        // Initialize focus items after the dialog becomes visible
        Qt.callLater(function () {
            collectFocusItems();
            // Set focus to the dialog itself for key handling
            wifiSetupDialog.forceActiveFocus();
        });
    }

    // Close the dialog
    function close() {
        isVisible = false;
        visible = false;

        // Stop WiFi setup process
        if (bridge && bridge.wifiSetupBridge) {
            bridge.wifiSetupBridge.stopWiFiSetup();
        }

        // Clear focus from all dialog items before closing
        FocusManager.clearFocus();

        // Notify parent about dialog closing so it can restore its focus items
        dialogClosed();

        // Force the parent to reinitialize its focus items
        if (parent && typeof parent.collectFocusItems === "function") {
            Qt.callLater(parent.collectFocusItems);
        }
    }

    anchors.fill: parent
    color: ThemeManager.textColor
    visible: false
    z: 1000 // Set a very high z value to appear above all other content
    focus: isVisible

    // Handle key events for the dialog
    Keys.onPressed: function(event) {
        // Use standard FocusManager key handling
        if (event.key === Qt.Key_Up) {
            FocusManager.moveFocusUp();
            event.accepted = true;
        } else if (event.key === Qt.Key_Down) {
            FocusManager.moveFocusDown();
            event.accepted = true;
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            // Activate the currently focused item
            var currentItem = FocusManager.currentFocusItems[FocusManager.currentFocusIndex];
            if (currentItem && currentItem.activate) {
                currentItem.activate();
                event.accepted = true;
            } else if (currentItem && currentItem.clicked) {
                currentItem.clicked();
                event.accepted = true;
            }
        }
    }

    Component.onCompleted: {
        // Connect to WiFi setup bridge signals
        if (bridge && bridge.wifiSetupBridge) {
            bridge.wifiSetupBridge.setupStateChanged.connect(function (state) {
                currentState = state;

                // Handle timing for smooth UX
                if (state === "hotspot_active") {
                    showHotspotInstructions = false;
                    hotspotSetupTimer.start();
                } else if (state === "success") {
                    showSuccessMessage = false;
                    successDelayTimer.start();
                } else {
                    // Reset timers for other states
                    hotspotSetupTimer.stop();
                    successDelayTimer.stop();
                    showHotspotInstructions = false;
                    showSuccessMessage = false;
                }

                collectFocusItems(); // Update focus items when state changes
            });

            bridge.wifiSetupBridge.setupMessageChanged.connect(function (message) {
                statusMessage = message;
            });

            bridge.wifiSetupBridge.hotspotInfoChanged.connect(function (ssid, password, ip) {
                hotspotSSID = ssid;
                hotspotPassword = password;
                hotspotIP = ip;
            });

            bridge.wifiSetupBridge.networkConnected.connect(function (ssid, ip) {
                connectedNetwork = ssid;
                connectedIP = ip;
            });

            bridge.wifiSetupBridge.errorOccurred.connect(function (error) {
                errorMessage = error;
            });
        }
    }

    // Connect to FocusManager to handle focus changes
    Connections {
        target: FocusManager
        function onCurrentFocusIndexChanged() {
            // Update visual focus for all items
            if (FocusManager.currentFocusItems.length > 0) {
                var currentItem = FocusManager.currentFocusItems[FocusManager.currentFocusIndex];
                console.log("WiFiSetupDialog focus changed to:", currentItem ? currentItem.objectName : "null");
                
                // Update content list view focus
                if (contentListView) {
                    contentListView.visualFocus = (currentItem === contentListView);
                }
            }
        }
    }

    // Dialog content
    Rectangle {
        id: dialogContent

        width: parent.width
        height: parent.height
        anchors.centerIn: parent
        color: ThemeManager.backgroundColor

        // Dialog header
        Rectangle {
            id: dialogHeader

            width: parent.width
            height: 40
            color: ThemeManager.backgroundColor
            radius: ThemeManager.borderRadius

            // Header title - centered
            Text {
                anchors.centerIn: parent
                text: "WiFi Setup"
                font.pixelSize: FontManager.fontSizeSmall
                font.family: FontManager.primaryFontFamily
                color: ThemeManager.textColor
                elide: Text.ElideRight
            }

            // Stop/Close button - positioned at right
            AppButton {
                id: stopButton

                width: 30
                height: 30
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.rightMargin: ThemeManager.spacingTiny
                text: currentState === "success" || currentState === "error" ? "×" : "󰓛"
                fontSize: FontManager.fontSizeSmall
                navigable: true
                isFlat: true
                buttonRadius: width / 2
                z: 10
                visible: currentState !== "idle"
                onClicked: {
                    if (currentState === "success" || currentState === "error") {
                        wifiSetupDialog.close();
                    } else {
                        // Stop the setup process
                        if (bridge && bridge.wifiSetupBridge) {
                            bridge.wifiSetupBridge.stopWiFiSetup();
                        }
                        wifiSetupDialog.close();
                    }
                }
            }

            // Close button for completed states
            AppButton {
                id: closeButton

                width: 30
                height: 30
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.rightMargin: ThemeManager.spacingTiny
                text: "×"
                fontSize: FontManager.fontSizeSmall
                navigable: true
                isFlat: true
                buttonRadius: width / 2
                z: 10
                visible: currentState === "success" || currentState === "error"
                onClicked: wifiSetupDialog.close()
            }
        }

        // Main content area with ListView
        ListView {
            id: contentListView

            property bool navigable: true
            property bool visualFocus: false
            property bool scrollModeActive: false
            
            // Signal for scroll mode changes
            signal scrollModeChanged(bool active)

            anchors.top: dialogHeader.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: ThemeManager.spacingSmall
            anchors.bottomMargin: 40  // Add 40px bottom space

            focus: visualFocus
            clip: true
            spacing: ThemeManager.spacingNormal
            interactive: true
            boundsBehavior: Flickable.StopAtBounds

            // Update visual focus based on FocusManager
            Connections {
                target: FocusManager
                function onCurrentFocusIndexChanged() {
                    var currentItem = FocusManager.currentFocusItems[FocusManager.currentFocusIndex];
                    contentListView.visualFocus = (currentItem === contentListView);
                }
            }

            // Function to activate this item (required for NavigableItem pattern)
            function activate() {
                if (contentHeight > height) {
                    FocusManager.enterScrollMode(contentListView);
                    scrollModeActive = true;
                    scrollModeChanged(true);
                }
            }
            
            // Connect to own scroll mode changes
            onScrollModeActiveChanged: {
                wifiSetupDialog.scrollModeActive = scrollModeActive;
                wifiSetupDialog.scrollModeChanged(scrollModeActive);
                
                // Lock focus when entering scroll mode
                if (scrollModeActive) {
                    FocusManager.lockFocus = true;
                } else {
                    FocusManager.lockFocus = false;
                }
                
                console.log("WiFiSetupDialog contentListView scroll mode changed to:", scrollModeActive);
            }

            // Create a simple model with the content items
            model: ListModel {
                id: contentModel
                ListElement { itemType: "status" }
                ListElement { itemType: "content" }
            }

            // Keys are handled by the parent dialog now

            delegate: Item {
                width: ListView.view.width
                height: childrenRect.height

                Column {
                    width: parent.width
                    spacing: ThemeManager.spacingNormal

                    // Status message
                    Rectangle {
                        width: parent.width
                        height: statusSection.height + ThemeManager.spacingSmall * 2
                        color: ThemeManager.backgroundColor
                        border.width: ThemeManager.borderWidth
                        border.color: ThemeManager.black
                        radius: ThemeManager.borderRadius
                        visible: model.itemType === "status"

                        Column {
                            id: statusSection

                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: ThemeManager.spacingSmall
                            spacing: ThemeManager.spacingTiny

                            Text {
                                text: "STATUS"
                                font: FontManager.smallBold
                                color: ThemeManager.textColor
                                renderType: Text.NativeRendering
                            }

                            Text {
                                width: parent.width
                                text: statusMessage || "Ready to start WiFi setup"
                                font: FontManager.small
                                color: ThemeManager.textColor
                                wrapMode: Text.WordWrap
                                renderType: Text.NativeRendering
                            }
                        }
                    }

                    // State-specific content
                    Loader {
                        width: parent.width
                        visible: model.itemType === "content"
                        sourceComponent: {
                            switch (currentState) {
                            case "hotspot_active":
                                return showHotspotInstructions ? hotspotInstructionsComponent : setupProgressComponent;
                            case "connecting":
                                return connectingComponent;
                            case "success":
                                return showSuccessMessage ? successComponent : connectingProgressComponent;
                            case "error":
                                return errorComponent;
                            default:
                                return initialComponent;
                            }
                        }
                    }
                }
            }
        }

        // Visual instruction when in focus but not in scroll mode
        Rectangle {
            id: scrollModeInstructions

            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: ThemeManager.spacingNormal
            height: scrollModeText.height + ThemeManager.spacingSmall * 2
            width: Math.min(scrollModeText.implicitWidth + ThemeManager.spacingNormal * 2, parent.width - ThemeManager.spacingSmall * 2)
            color: ThemeManager.textColor
            border.width: ThemeManager.borderWidth
            border.color: ThemeManager.textColor
            radius: ThemeManager.borderRadius
            visible: contentListView.visualFocus && !contentListView.scrollModeActive && contentListView.contentHeight > contentListView.height && contentListView.visible
            z: 2

            Text {
                id: scrollModeText

                anchors.centerIn: parent
                anchors.margins: ThemeManager.spacingSmall
                text: "Press Enter to enable scroll mode"
                color: ThemeManager.backgroundColor
                font: FontManager.small
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }
        }

        // Visual instruction when in scroll mode
        Rectangle {
            id: activeScrollModeInstructions

            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: ThemeManager.spacingNormal
            height: activeScrollModeText.height + ThemeManager.spacingSmall * 2
            width: Math.min(activeScrollModeText.implicitWidth + ThemeManager.spacingNormal * 2, parent.width - ThemeManager.spacingSmall * 2)
            color: ThemeManager.textColor
            border.width: ThemeManager.borderWidth
            border.color: ThemeManager.textColor
            radius: ThemeManager.borderRadius
            visible: contentListView.scrollModeActive
            z: 2

            Text {
                id: activeScrollModeText

                anchors.centerIn: parent
                anchors.margins: ThemeManager.spacingSmall
                text: "Use ↑/↓ to scroll, Enter to exit"
                color: ThemeManager.backgroundColor
                font: FontManager.small
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }

    // State-specific components
    Component {
        id: initialComponent

        Column {
            spacing: ThemeManager.spacingNormal

            Rectangle {
                width: parent.width
                height: initialInstructions.height + ThemeManager.spacingSmall * 2
                color: ThemeManager.backgroundColor
                border.width: ThemeManager.borderWidth
                border.color: ThemeManager.black
                radius: ThemeManager.borderRadius

                Column {
                    id: initialInstructions

                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: ThemeManager.spacingSmall
                    spacing: ThemeManager.spacingTiny

                    Text {
                        text: "INSTRUCTIONS"
                        font: FontManager.smallBold
                        color: ThemeManager.textColor
                        renderType: Text.NativeRendering
                    }

                    Text {
                        width: parent.width
                        text: "WiFi setup will create a temporary hotspot that you can connect to from another device (phone, laptop) to configure the network settings."
                        font: FontManager.small
                        color: ThemeManager.textColor
                        wrapMode: Text.WordWrap
                        renderType: Text.NativeRendering
                    }
                }
            }
        }
    }

    Component {
        id: hotspotInstructionsComponent

        Column {
            spacing: ThemeManager.spacingNormal

            // Hotspot connection info
            Rectangle {
                width: parent.width
                height: hotspotInfo.height + ThemeManager.spacingSmall * 2
                color: ThemeManager.backgroundColor
                border.width: ThemeManager.borderWidth
                border.color: ThemeManager.black
                radius: ThemeManager.borderRadius

                Column {
                    id: hotspotInfo

                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: ThemeManager.spacingSmall
                    spacing: ThemeManager.spacingTiny

                    Text {
                        text: "CONNECT TO HOTSPOT"
                        font: FontManager.smallBold
                        color: ThemeManager.textColor
                        renderType: Text.NativeRendering
                    }

                    Row {
                        width: parent.width
                        spacing: ThemeManager.spacingSmall

                        Text {
                            text: "Network:"
                            font: FontManager.small
                            color: ThemeManager.textColor
                            renderType: Text.NativeRendering
                        }

                        Text {
                            text: hotspotSSID || "Distiller-Setup"
                            font: FontManager.small
                            color: ThemeManager.textColor
                            renderType: Text.NativeRendering
                            width: parent.width - 80 // Reserve space for "Network:" label
                            wrapMode: Text.WordWrap
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: ThemeManager.spacingSmall

                        Text {
                            text: "Password:"
                            font: FontManager.small
                            color: ThemeManager.textColor
                            renderType: Text.NativeRendering
                        }

                        Text {
                            text: hotspotPassword
                            font: FontManager.smallBold
                            color: ThemeManager.textColor
                            renderType: Text.NativeRendering
                        }
                    }
                }
            }

            // QR Code section
            Rectangle {
                width: parent.width
                height: qrCodeInfo.height + ThemeManager.spacingSmall * 2
                color: ThemeManager.backgroundColor
                border.width: ThemeManager.borderWidth
                border.color: ThemeManager.black
                radius: ThemeManager.borderRadius
                visible: bridge && bridge.wifiSetupBridge && bridge.wifiSetupBridge.qrCodeData !== ""

                Column {
                    id: qrCodeInfo

                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: ThemeManager.spacingSmall
                    spacing: ThemeManager.spacingSmall

                    Text {
                        text: "SCAN QR CODE"
                        font: FontManager.smallBold
                        color: ThemeManager.textColor
                        renderType: Text.NativeRendering
                    }

                    Text {
                        width: parent.width
                        text: "Scan this QR code with your phone's camera to quickly connect to the WiFi hotspot:"
                        font: FontManager.small
                        color: ThemeManager.textColor
                        wrapMode: Text.WordWrap
                        renderType: Text.NativeRendering
                    }

                    // QR Code Image
                    Item {
                        width: parent.width
                        height: qrCodeImage.visible ? 120 : 0

                        Image {
                            id: qrCodeImage
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: 100
                            height: 100
                            fillMode: Image.PreserveAspectFit
                            smooth: false  // Keep crisp for QR codes
                            source: bridge && bridge.wifiSetupBridge ? bridge.wifiSetupBridge.qrCodeData : ""
                            visible: source !== ""

                            Rectangle {
                                anchors.fill: parent
                                color: "transparent"
                                border.width: 1
                                border.color: ThemeManager.black
                                z: -1
                            }
                        }
                    }
                }
            }

            // Web interface info
            Rectangle {
                width: parent.width
                height: webInfo.height + ThemeManager.spacingSmall * 2
                color: ThemeManager.backgroundColor
                border.width: ThemeManager.borderWidth
                border.color: ThemeManager.black
                radius: ThemeManager.borderRadius

                Column {
                    id: webInfo

                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: ThemeManager.spacingSmall
                    spacing: ThemeManager.spacingTiny

                    Text {
                        text: "OPEN WEB BROWSER"
                        font: FontManager.smallBold
                        color: ThemeManager.textColor
                        renderType: Text.NativeRendering
                    }

                    Text {
                        width: parent.width
                        text: "After connecting to the hotspot, open a web browser and go to:"
                        font: FontManager.small
                        color: ThemeManager.textColor
                        wrapMode: Text.WordWrap
                        renderType: Text.NativeRendering
                    }

                    Text {
                        text: `http://${hotspotIP}:8080`
                        font: FontManager.smallBold
                        color: ThemeManager.textColor
                        renderType: Text.NativeRendering
                    }

                    Text {
                        width: parent.width
                        text: "Use the web interface to select your WiFi network and enter the password."
                        font: FontManager.small
                        color: ThemeManager.textColor
                        wrapMode: Text.WordWrap
                        renderType: Text.NativeRendering
                    }
                }
            }
        }
    }

    Component {
        id: connectingComponent

        Rectangle {
            width: parent.width
            height: connectingInfo.height + ThemeManager.spacingSmall * 2
            color: ThemeManager.backgroundColor
            border.width: ThemeManager.borderWidth
            border.color: ThemeManager.black
            radius: ThemeManager.borderRadius

            Column {
                id: connectingInfo

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: ThemeManager.spacingSmall
                spacing: ThemeManager.spacingTiny

                Text {
                    text: "CONNECTING"
                    font: FontManager.smallBold
                    color: ThemeManager.textColor
                    renderType: Text.NativeRendering
                }

                Text {
                    width: parent.width
                    text: statusMessage || "Attempting to connect to the selected network..."
                    font: FontManager.small
                    color: ThemeManager.textColor
                    wrapMode: Text.WordWrap
                    renderType: Text.NativeRendering
                }
            }
        }
    }

    Component {
        id: successComponent

        Column {
            spacing: ThemeManager.spacingNormal

            Rectangle {
                width: parent.width
                height: successInfo.height + ThemeManager.spacingSmall * 2
                color: ThemeManager.backgroundColor
                border.width: ThemeManager.borderWidth
                border.color: ThemeManager.black
                radius: ThemeManager.borderRadius

                Column {
                    id: successInfo

                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: ThemeManager.spacingSmall
                    spacing: ThemeManager.spacingTiny

                    Text {
                        text: "SUCCESS"
                        font: FontManager.smallBold
                        color: ThemeManager.textColor
                        renderType: Text.NativeRendering
                    }

                    Text {
                        width: parent.width
                        text: statusMessage.includes("Connected") ? `Connected to: ${connectedNetwork}` : `Successfully connected to: ${connectedNetwork}`
                        font: FontManager.smallBold
                        color: ThemeManager.textColor
                        wrapMode: Text.WordWrap
                        renderType: Text.NativeRendering
                    }

                    Row {
                        width: parent.width
                        spacing: ThemeManager.spacingSmall

                        Text {
                            text: "IP Address:"
                            font: FontManager.small
                            color: ThemeManager.textColor
                            renderType: Text.NativeRendering
                        }

                        Text {
                            text: connectedIP
                            font: FontManager.smallBold
                            color: ThemeManager.textColor
                            renderType: Text.NativeRendering
                        }
                    }

                    Text {
                        width: parent.width
                        text: statusMessage.includes("Connected") ? "Web interface is available for network management. You can access it from any device on the network." : "WiFi setup is complete. Web interface is now available for network management."
                        font: FontManager.small
                        color: ThemeManager.textColor
                        wrapMode: Text.WordWrap
                        renderType: Text.NativeRendering
                    }

                    // Web interface access info
                    Text {
                        width: parent.width
                        text: `Web Interface: http://${connectedIP}:8080`
                        font: FontManager.smallBold
                        color: ThemeManager.textColor
                        wrapMode: Text.WordWrap
                        renderType: Text.NativeRendering
                        topPadding: ThemeManager.spacingTiny
                    }
                }
            }
        }
    }

    Component {
        id: errorComponent

        Rectangle {
            width: parent.width
            height: errorInfo.height + ThemeManager.spacingSmall * 2
            color: ThemeManager.backgroundColor
            border.width: ThemeManager.borderWidth
            border.color: ThemeManager.black
            radius: ThemeManager.borderRadius

            Column {
                id: errorInfo

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: ThemeManager.spacingSmall
                spacing: ThemeManager.spacingTiny

                Text {
                    text: "ERROR"
                    font: FontManager.smallBold
                    color: ThemeManager.textColor
                    renderType: Text.NativeRendering
                }

                Text {
                    width: parent.width
                    text: errorMessage || "An error occurred during WiFi setup."
                    font: FontManager.small
                    color: ThemeManager.textColor
                    wrapMode: Text.WordWrap
                    renderType: Text.NativeRendering
                }

                Text {
                    width: parent.width
                    text: "You can try again by closing this dialog and starting a new setup."
                    font: FontManager.small
                    color: ThemeManager.textColor
                    wrapMode: Text.WordWrap
                    renderType: Text.NativeRendering
                }
            }
        }
    }

    Component {
        id: setupProgressComponent

        Rectangle {
            width: parent.width
            height: setupProgress.height + ThemeManager.spacingSmall * 2
            color: ThemeManager.backgroundColor
            border.width: ThemeManager.borderWidth
            border.color: ThemeManager.black
            radius: ThemeManager.borderRadius

            Column {
                id: setupProgress

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: ThemeManager.spacingSmall
                spacing: ThemeManager.spacingTiny

                Text {
                    text: "SETTING UP HOTSPOT"
                    font: FontManager.smallBold
                    color: ThemeManager.textColor
                    renderType: Text.NativeRendering
                }

                Text {
                    width: parent.width
                    text: "Creating WiFi hotspot and starting web server. Please wait..."
                    font: FontManager.small
                    color: ThemeManager.textColor
                    wrapMode: Text.WordWrap
                    renderType: Text.NativeRendering
                }
            }
        }
    }

    Component {
        id: connectingProgressComponent

        Rectangle {
            width: parent.width
            height: connectionProgress.height + ThemeManager.spacingSmall * 2
            color: ThemeManager.backgroundColor
            border.width: ThemeManager.borderWidth
            border.color: ThemeManager.black
            radius: ThemeManager.borderRadius

            Column {
                id: connectionProgress

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: ThemeManager.spacingSmall
                spacing: ThemeManager.spacingTiny

                Text {
                    text: "FINALIZING CONNECTION"
                    font: FontManager.smallBold
                    color: ThemeManager.textColor
                    renderType: Text.NativeRendering
                }

                Text {
                    width: parent.width
                    text: "Connection successful. Starting services and verifying network stability..."
                    font: FontManager.small
                    color: ThemeManager.textColor
                    wrapMode: Text.WordWrap
                    renderType: Text.NativeRendering
                }
            }
        }
    }
}
