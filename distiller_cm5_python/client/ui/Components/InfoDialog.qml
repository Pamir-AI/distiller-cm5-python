import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

Rectangle {
    id: infoDialog

    property bool isLoading: false
    property var focusableItems: []
    property bool wifiConnected: false
    property string ipAddress: ""  
    property string wifiName: ""
    property bool showSystemStats: bridge && bridge.ready ? bridge.getShowSystemStats() : true
    property var systemStats: {
        "cpu": "N/A",
        "ram": "N/A", 
        "temp": "N/A",
        "llm": "Local"
    }
    
    // WiFi Setup Dialog (lazy loaded)
    property var wifiSetupDialog: null

    signal dialogClosed()

    // Enable key handling for the dialog
    focus: visible
    Keys.enabled: visible

    // Key handling for navigation
    Keys.onPressed: function(event) {
        console.log("InfoDialog Key Pressed:", event.key, "| Current Focus:", FocusManager.currentFocusIndex);
        
        if (event.key === Qt.Key_Up) {
            FocusManager.navigateUp();
            event.accepted = true;
        } else if (event.key === Qt.Key_Down) {
            FocusManager.navigateDown();
            event.accepted = true;
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            // Activate current focused item
            if (FocusManager.currentFocusIndex >= 0 && FocusManager.currentFocusItems.length > 0) {
                var currentItem = FocusManager.currentFocusItems[FocusManager.currentFocusIndex];
                if (currentItem && typeof currentItem.clicked === "function") {
                    currentItem.clicked();
                } else if (currentItem && currentItem.onClicked) {
                    currentItem.onClicked();
                }
            }
            event.accepted = true;
        } else if (event.key === Qt.Key_Escape || event.key === Qt.Key_Back) {
            infoDialog.close();
            event.accepted = true;
        }
    }

    function collectFocusItems() {
        focusableItems = [];
        // Add refresh button first
        if (refreshButton && refreshButton.navigable) {
            refreshButton.objectName = "RefreshButton";
            focusableItems.push(refreshButton);
        }
        // Add WiFi setup button
        if (wifiSetupButton && wifiSetupButton.navigable) {
            wifiSetupButton.objectName = "WiFiSetupButton";
            focusableItems.push(wifiSetupButton);
        }
        // Add close button
        if (closeButton && closeButton.navigable) {
            closeButton.objectName = "CloseButton";
            focusableItems.push(closeButton);
        }
        
        // Initialize focus with our FocusManager
        FocusManager.initializeFocusItems(focusableItems);
        // Set focus to first item if available
        if (focusableItems.length > 0)
            FocusManager.setFocusToItem(focusableItems[0]);
    }
    
    function getWifiSetupDialog() {
        if (!wifiSetupDialog) {
            var component = Qt.createComponent("WiFiSetupDialog.qml");
            if (component.status === Component.Ready) {
                wifiSetupDialog = component.createObject(infoDialog);
                // Connect dialog closed signal to restore focus
                wifiSetupDialog.dialogClosed.connect(function() {
                    Qt.callLater(collectFocusItems);
                    infoDialog.forceActiveFocus();
                });
            } else {
                console.error("Error creating WiFiSetupDialog:", component.errorString());
            }
        }
        return wifiSetupDialog;
    }

    // Update WiFi status from bridge
    function updateWifiStatus() {
        if (bridge && bridge.ready) {
            var ipAddr = bridge.getWifiIpAddress();
            wifiConnected = ipAddr && ipAddr !== "No network IP found" && !ipAddr.includes("Error");
            ipAddress = wifiConnected ? ipAddr : "";
            // Get WiFi name if available from the bridge
            if (wifiConnected && bridge.getWifiName)
                wifiName = bridge.getWifiName();
            else
                wifiName = "";
        } else {
            wifiConnected = false;
            ipAddress = "";
            wifiName = "";
        }
    }

    // Update system stats from bridge
    function updateSystemStats() {
        if (bridge && bridge.ready && showSystemStats) {
            systemStats = bridge.getSystemStats();
            // Also update WiFi status when updating stats
            updateWifiStatus();
        }
    }

    // Open the dialog
    function open() {
        visible = true;
        isLoading = true;
        updateSystemStats();
        isLoading = false;
        
        // Initialize focus items after the dialog becomes visible
        Qt.callLater(function() {
            collectFocusItems();
            // Set focus to the dialog itself for key handling
            infoDialog.forceActiveFocus();
        });
    }

    // Close the dialog
    function close() {
        visible = false;
        
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
    
    Component.onCompleted: {
        // Initialize data but don't set focus until dialog is opened
        updateWifiStatus();
        updateSystemStats();
    }

    // Connect to FocusManager to handle focus changes
    Connections {
        function onCurrentFocusIndexChanged() {
            // Handle focus changes if needed
        }
        target: FocusManager
    }

    // Dialog content
    Rectangle {
        id: dialogContent

        width: parent.width
        height: parent.height
        anchors.centerIn: parent
        color: ThemeManager.backgroundColor

        // Dialog header - more compact
        Rectangle {
            id: dialogHeader

            width: parent.width
            height: 40
            color: ThemeManager.backgroundColor
            radius: ThemeManager.borderRadius

            // Refresh button - smaller and positioned at left
            AppButton {
                id: refreshButton

                width: 30
                height: 30
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: ThemeManager.spacingTiny
                text: "↻"
                fontSize: FontManager.fontSizeSmall
                navigable: true
                isFlat: true
                buttonRadius: width / 2
                z: 10
                onClicked: {
                    if (bridge && bridge.ready) {
                        isLoading = true;
                        updateSystemStats();
                        isLoading = false;
                    } else {
                        messageToast.showMessage("Error: Application not fully initialized", 3000);
                    }
                }
            }

            // Header title - smaller and centered
            Text {
                anchors.centerIn: parent
                width: parent.width - refreshButton.width - closeButton.width - 20
                horizontalAlignment: Text.AlignHCenter
                text: "System Info"
                font.pixelSize: FontManager.fontSizeSmall
                font.family: FontManager.primaryFontFamily
                color: ThemeManager.textColor
                elide: Text.ElideRight
            }

            // Close button - smaller and positioned at right
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
                onClicked: infoDialog.close()
            }
        }

        // Loading indicator
        LoadingIndicator {
            anchors.fill: parent
            isLoading: infoDialog.isLoading
            z: 5
        }

        // Organized compact system info content
        Column {
            id: infoColumn
            
            anchors.top: dialogHeader.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: footerArea.top
            anchors.margins: ThemeManager.spacingSmall
            spacing: ThemeManager.spacingSmall
            visible: !isLoading

            property var batteryInfo: bridge && bridge.ready ? bridge.getBatteryInfo() : {}

            // Battery Section
            Rectangle {
                width: parent.width
                height: batterySection.height + ThemeManager.spacingSmall * 2
                color: ThemeManager.backgroundColor
                border.width: ThemeManager.borderWidth
                border.color: ThemeManager.black
                radius: ThemeManager.borderRadius

                Column {
                    id: batterySection
                    
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: ThemeManager.spacingSmall
                    spacing: ThemeManager.spacingTiny

                    Text {
                        text: "BATTERY"
                        font.pixelSize: FontManager.fontSizeSmall
                        font.family: FontManager.primaryFontFamily
                        font.bold: true
                        color: ThemeManager.textColor
                        renderType: Text.NativeRendering
                    }

                    Row {
                        width: parent.width
                        spacing: ThemeManager.spacingSmall

                        Text {
                            text: (infoColumn.batteryInfo.capacity || 100) + "%" + 
                                  (infoColumn.batteryInfo.isCritical ? " !!!" : infoColumn.batteryInfo.isLow ? " !" : "")
                            font: FontManager.small
                            color: ThemeManager.textColor
                            renderType: Text.NativeRendering
                        }

                        Text {
                            text: (infoColumn.batteryInfo.voltage || 0).toFixed(2) + "V"
                            font: FontManager.small
                            color: ThemeManager.textColor
                            renderType: Text.NativeRendering
                        }

                        Text {
                            text: (infoColumn.batteryInfo.temperature || 0).toFixed(0) + "°C"
                            font: FontManager.small
                            color: ThemeManager.textColor
                            renderType: Text.NativeRendering
                        }
                    }
                }
            }

            // System Section
            Rectangle {
                width: parent.width
                height: systemSection.height + ThemeManager.spacingSmall * 2
                color: ThemeManager.backgroundColor
                border.width: ThemeManager.borderWidth
                border.color: ThemeManager.black
                radius: ThemeManager.borderRadius

                Column {
                    id: systemSection
                    
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: ThemeManager.spacingSmall
                    spacing: ThemeManager.spacingTiny

                    Text {
                        text: "SYSTEM"
                        font.pixelSize: FontManager.fontSizeSmall
                        font.family: FontManager.primaryFontFamily
                        font.bold: true
                        color: ThemeManager.textColor
                        renderType: Text.NativeRendering
                    }

                    Row {
                        width: parent.width
                        spacing: ThemeManager.spacingSmall

                        Text {
                            text: "CPU: " + (systemStats.cpu || "N/A")
                            font: FontManager.small
                            color: ThemeManager.textColor
                            renderType: Text.NativeRendering
                        }

                        Text {
                            text: "RAM: " + (systemStats.ram || "N/A")
                            font: FontManager.small
                            color: ThemeManager.textColor
                            renderType: Text.NativeRendering
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: ThemeManager.spacingSmall

                        Text {
                            text: "Temp: " + (systemStats.temp || "N/A")
                            font: FontManager.small
                            color: ThemeManager.textColor
                            renderType: Text.NativeRendering
                        }

                        Text {
                            text: "LLM: " + (systemStats.llm || "Local")
                            font: FontManager.small
                            color: ThemeManager.textColor
                            renderType: Text.NativeRendering
                        }
                    }
                }
            }

            // Network Section
            Rectangle {
                width: parent.width
                height: networkSection.height + ThemeManager.spacingSmall * 2
                color: ThemeManager.backgroundColor
                border.width: ThemeManager.borderWidth
                border.color: ThemeManager.black
                radius: ThemeManager.borderRadius

                Column {
                    id: networkSection
                    
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: ThemeManager.spacingSmall
                    spacing: ThemeManager.spacingTiny

                    Text {
                        text: "NETWORK"
                        font.pixelSize: FontManager.fontSizeSmall
                        font.family: FontManager.primaryFontFamily
                        font.bold: true
                        color: ThemeManager.textColor
                        renderType: Text.NativeRendering
                    }

                    Text {
                        width: parent.width
                        text: wifiConnected ? "WiFi: Connected" : "WiFi: Disconnected"
                        font: FontManager.small
                        color: ThemeManager.textColor
                        elide: Text.ElideRight
                        renderType: Text.NativeRendering
                    }

                    Text {
                        width: parent.width
                        text: wifiConnected && wifiName ? "SSID: " + wifiName : ""
                        font: FontManager.small
                        color: ThemeManager.textColor
                        elide: Text.ElideRight
                        renderType: Text.NativeRendering
                        visible: text.length > 0
                    }

                    Text {
                        width: parent.width
                        text: wifiConnected && ipAddress ? "IP: " + ipAddress : ""
                        font: FontManager.small
                        color: ThemeManager.textColor
                        elide: Text.ElideRight
                        renderType: Text.NativeRendering
                        visible: text.length > 0
                    }
                }
            }
        }

        // WiFi Setup Button
        Rectangle {
            id: wifiSetupArea

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: footerArea.top
            height: 45
            color: ThemeManager.backgroundColor
            
            AppButton {
                id: wifiSetupButton
                
                width: parent.width - ThemeManager.spacingMedium * 2
                height: ThemeManager.buttonHeight
                anchors.centerIn: parent
                isFlat: true
                navigable: true
                buttonRadius: width / 2
                fontSize: FontManager.fontSizeSmall
                
                onClicked: {
                    getWifiSetupDialog().open();
                }

                Rectangle {
                    parent: infoButton
                    anchors.fill: parent
                    color: ThemeManager.backgroundColor

                    // High contrast highlight for e-ink when focused
                    Rectangle {
                        visible: infoButton.visualFocus || infoButton.pressed || true
                        anchors.fill: parent
                        radius: width / 2
                        color: infoButton.visualFocus ? ThemeManager.textColor : ThemeManager.backgroundColor
                        border.width: ThemeManager.borderWidth
                        border.color: ThemeManager.black
                        antialiasing: true
                    }

                    // Wifi setup icon
                    Text {
                        text: "󱚾  setup"
                        font.pixelSize: parent.width * 0.4
                        font.family: FontManager.primaryFontFamily
                        font.bold: true
                        color: infoButton.visualFocus ? ThemeManager.backgroundColor : ThemeManager.textColor
                        anchors.centerIn: parent
                        renderType: Text.NativeRendering
                    }
                }
            }
        }

        // Footer area - minimal spacing
        Rectangle {
            id: footerArea

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: ThemeManager.spacingTiny
            color: ThemeManager.backgroundColor
        }
    }

    // Toast message
    MessageToast {
        id: messageToast

        anchors.centerIn: parent
        z: 100
    }
}