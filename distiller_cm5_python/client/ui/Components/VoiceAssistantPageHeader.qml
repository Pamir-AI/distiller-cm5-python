import QtQuick
import QtQuick.Controls

Rectangle {
    id: header

    property string serverName: "NO SERVER"
    property string statusText: "Ready"
    property bool isConnected: false
    property bool showStatusText: false
    property bool wifiConnected: false
    property string ipAddress: ""
    property string wifiName: ""
    property alias serverSelectButton: serverSelectBtn
    // Keep the alias but point to a dummy item to prevent runtime errors
    property alias darkModeButton: dummyDarkModeBtn
    property alias closeButton: closeBtn
    property alias statusButton: statusBtn
    // System stats properties
    property var systemStats: {
        "cpu": "N/A",
        "ram": "N/A",
        "temp": "N/A",
        "llm": "Local"
    }

    signal serverSelectClicked
    // Keep the signal to prevent errors
    signal darkModeClicked
    signal closeAppClicked
    signal showToastMessage(string message, int duration)

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
        if (bridge && bridge.ready) {
            systemStats = bridge.getSystemStats();
            // Also update WiFi status when updating stats
            updateWifiStatus();
        }
    }

    color: ThemeManager.backgroundColor
    Component.onCompleted: {
        updateWifiStatus();
        updateSystemStats();
    }

    // Dummy invisible item to satisfy the darkModeButton alias
    Item {
        id: dummyDarkModeBtn

        property bool navigable: false

        visible: false
    }

    // Shadow effect for the header
    Rectangle {
        anchors.top: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 2
        color: ThemeManager.black
    }

    // Server selection button - centered with reduced width
    AppButton {
        id: serverSelectBtn

        width: 120
        height: ThemeManager.buttonHeight
        anchors.left: parent.left
        anchors.leftMargin: ThemeManager.spacingSmall
        anchors.verticalCenter: parent.verticalCenter
        navigable: true
        isFlat: false
        text: "" // Set empty text since we're using custom content

        onClicked: {
            if (statsPopup.visible)
                statsPopup.close();

            header.serverSelectClicked();
        }

        // Custom content using a child Column instead of contentItem
        Column {
            anchors.fill: parent
            anchors.leftMargin: ThemeManager.spacingSmall
            anchors.rightMargin: ThemeManager.spacingSmall
            anchors.topMargin: ThemeManager.spacingTiny
            anchors.bottomMargin: ThemeManager.spacingTiny
            spacing: ThemeManager.spacingTiny / 4

            // Server name - left aligned
            Text {
                width: parent.width
                height: parent.height / 2
                horizontalAlignment: Text.AlignLeft
                text: isConnected && serverName && serverName !== "NO SERVER" ? serverName : "SELECT SERVER"
                font: FontManager.small
                color: serverSelectBtn.visualFocus ? ThemeManager.backgroundColor : ThemeManager.textColor
                elide: Text.ElideRight
                renderType: Text.NativeRendering
            }

            // Status text - left aligned, smaller font
            Text {
                width: parent.width
                height: parent.height / 2
                horizontalAlignment: Text.AlignLeft
                text: statusText
                // visible: isConnected && serverName && serverName !== "NO SERVER"
                font: FontManager.tiny
                color: serverSelectBtn.visualFocus ? ThemeManager.backgroundColor : ThemeManager.textColor
                elide: Text.ElideRight
                renderType: Text.NativeRendering
            }
        }
    }

    // System Status button
    AppButton {
        id: statusBtn

        width: ThemeManager.buttonHeight
        height: ThemeManager.buttonHeight
        anchors.right: closeBtn.left
        anchors.rightMargin: ThemeManager.spacingSmall
        anchors.verticalCenter: parent.verticalCenter
        navigable: true
        isFlat: true
        buttonRadius: width / 2

        onClicked: {
            if (statsPopup.visible) {
                statsPopup.close();
                statusBtn.forceActiveFocus();
            } else {
                updateSystemStats();
                statsPopup.open();
            }
        }

        // Status button icon
        Rectangle {
            parent: statusBtn
            anchors.fill: parent
            color: ThemeManager.backgroundColor

            // High contrast highlight for e-ink when focused
            Rectangle {
                visible: statusBtn.visualFocus || statusBtn.pressed || true
                anchors.fill: parent
                radius: width / 2
                color: statusBtn.visualFocus ? ThemeManager.textColor : ThemeManager.backgroundColor
                border.width: ThemeManager.borderWidth
                border.color: ThemeManager.black
                antialiasing: true
            }

            Text {
                text: ""
                font.pixelSize: parent.width * 0.5
                font.family: FontManager.primaryFontFamily
                color: statusBtn.visualFocus ? ThemeManager.backgroundColor : ThemeManager.textColor
                anchors.centerIn: parent
                renderType: Text.NativeRendering
            }
        }
    }

    // System stats popup
    Popup {
        id: statsPopup

        x: Math.max(0, parent.width / 2 - width / 2) // Center horizontally
        y: header.height
        width: parent.width
        height: parent.parent.height * 0.7 // Cover most of the conversation area height
        padding: ThemeManager.spacingSmall
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: ThemeManager.backgroundColor
        }

        contentItem: Item {
            Column {
                id: statsColumn

                anchors.fill: parent
                spacing: ThemeManager.spacingSmall

                // System Stats Section
                Rectangle {
                    width: parent.width
                    height: systemStatsColumn.height + ThemeManager.spacingSmall * 2
                    color: ThemeManager.backgroundColor
                    border.width: ThemeManager.borderWidth
                    border.color: ThemeManager.black
                    radius: ThemeManager.borderRadius

                    Column {
                        id: systemStatsColumn

                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: ThemeManager.spacingSmall
                        spacing: ThemeManager.spacingSmall

                        Row {
                            width: parent.width
                            spacing: ThemeManager.spacingSmall

                            Text {
                                text: "CPU:"
                                font: FontManager.small
                                color: ThemeManager.textColor
                                width: parent.width * 0.2
                                horizontalAlignment: Text.AlignLeft
                                renderType: Text.NativeRendering
                            }

                            Text {
                                text: systemStats.cpu || "N/A"
                                font: FontManager.small
                                color: ThemeManager.textColor
                                width: parent.width * 0.7
                                horizontalAlignment: Text.AlignLeft
                                elide: Text.ElideRight
                                renderType: Text.NativeRendering
                            }
                        }

                        Row {
                            width: parent.width
                            spacing: ThemeManager.spacingSmall

                            Text {
                                text: "RAM:"
                                font: FontManager.small
                                color: ThemeManager.textColor
                                width: parent.width * 0.2
                                horizontalAlignment: Text.AlignLeft
                                renderType: Text.NativeRendering
                            }

                            Text {
                                text: systemStats.ram || "N/A"
                                font: FontManager.small
                                color: ThemeManager.textColor
                                width: parent.width * 0.7
                                horizontalAlignment: Text.AlignLeft
                                elide: Text.ElideRight
                                renderType: Text.NativeRendering
                            }
                        }

                        Row {
                            width: parent.width
                            spacing: ThemeManager.spacingSmall

                            Text {
                                text: "Temp:"
                                font: FontManager.small
                                color: ThemeManager.textColor
                                width: parent.width * 0.2
                                horizontalAlignment: Text.AlignLeft
                                renderType: Text.NativeRendering
                            }

                            Text {
                                text: systemStats.temp || "N/A"
                                font: FontManager.small
                                color: ThemeManager.textColor
                                width: parent.width * 0.7
                                horizontalAlignment: Text.AlignLeft
                                elide: Text.ElideRight
                                renderType: Text.NativeRendering
                            }
                        }

                        Row {
                            width: parent.width
                            spacing: ThemeManager.spacingSmall

                            Text {
                                text: "LLM:"
                                font: FontManager.small
                                color: ThemeManager.textColor
                                width: parent.width * 0.2
                                horizontalAlignment: Text.AlignLeft
                                renderType: Text.NativeRendering
                            }

                            Text {
                                text: systemStats.llm || "Local"
                                font: FontManager.small
                                color: ThemeManager.textColor
                                width: parent.width * 0.7
                                horizontalAlignment: Text.AlignLeft
                                elide: Text.ElideRight
                                renderType: Text.NativeRendering
                            }
                        }
                    }
                }

                // Network Info Section
                Rectangle {
                    width: parent.width
                    height: networkColumn.height + ThemeManager.spacingSmall * 2
                    color: ThemeManager.backgroundColor
                    border.width: ThemeManager.borderWidth
                    border.color: ThemeManager.black
                    radius: ThemeManager.borderRadius

                    Column {
                        id: networkColumn

                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: ThemeManager.spacingSmall
                        spacing: ThemeManager.spacingSmall

                        Row {
                            width: parent.width
                            spacing: ThemeManager.spacingSmall

                            Text {
                                text: "WiFi:"
                                font: FontManager.small
                                color: ThemeManager.textColor
                                width: parent.width * 0.2
                                horizontalAlignment: Text.AlignLeft
                                renderType: Text.NativeRendering
                            }

                            Text {
                                text: wifiConnected ? "Connected" : "Not Connected"
                                font: FontManager.small
                                color: ThemeManager.textColor
                                width: parent.width * 0.7
                                horizontalAlignment: Text.AlignLeft
                                elide: Text.ElideRight
                                renderType: Text.NativeRendering
                            }
                        }

                        Row {
                            width: parent.width
                            spacing: ThemeManager.spacingSmall
                            visible: wifiConnected && wifiName.length > 0

                            Text {
                                text: "SSID:"
                                font: FontManager.small
                                color: ThemeManager.textColor
                                width: parent.width * 0.2
                                horizontalAlignment: Text.AlignLeft
                                renderType: Text.NativeRendering
                            }

                            Text {
                                text: wifiName
                                font: FontManager.small
                                color: ThemeManager.textColor
                                width: parent.width * 0.7
                                horizontalAlignment: Text.AlignLeft
                                elide: Text.ElideRight
                                renderType: Text.NativeRendering
                            }
                        }

                        Row {
                            width: parent.width
                            spacing: ThemeManager.spacingSmall
                            visible: wifiConnected && ipAddress.length > 0

                            Text {
                                text: "IP:"
                                font: FontManager.small
                                color: ThemeManager.textColor
                                width: parent.width * 0.2
                                horizontalAlignment: Text.AlignLeft
                                renderType: Text.NativeRendering
                            }

                            Text {
                                text: ipAddress
                                font: FontManager.small
                                color: ThemeManager.textColor
                                width: parent.width * 0.7
                                horizontalAlignment: Text.AlignLeft
                                elide: Text.ElideRight
                                renderType: Text.NativeRendering
                            }
                        }
                    }
                }
            }
        }
    }

    // Close application button
    AppButton {
        id: closeBtn

        width: ThemeManager.buttonHeight
        height: ThemeManager.buttonHeight
        anchors.right: parent.right
        anchors.rightMargin: ThemeManager.spacingSmall
        anchors.verticalCenter: parent.verticalCenter
        navigable: true
        isFlat: true
        buttonRadius: width / 2
        onClicked: {
            if (statsPopup.visible)
                statsPopup.close();

            shutdownConfirmDialog.open();
        }

        // Shutdown button icon
        Rectangle {
            parent: closeBtn
            anchors.fill: parent
            color: ThemeManager.backgroundColor

            // High contrast highlight for e-ink when focused
            Rectangle {
                visible: closeBtn.visualFocus || closeBtn.pressed || true
                anchors.fill: parent
                radius: width / 2
                color: closeBtn.visualFocus ? ThemeManager.textColor : ThemeManager.backgroundColor
                border.width: ThemeManager.borderWidth
                border.color: ThemeManager.black
                antialiasing: true
            }

            Text {
                text: "" // Power/Shutdown icon
                font.pixelSize: parent.width * 0.3
                font.family: FontManager.primaryFontFamily
                color: closeBtn.visualFocus ? ThemeManager.backgroundColor : ThemeManager.textColor
                anchors.centerIn: parent
            }
        }
    }

    // Close app timer - simple delay before closing
    Timer {
        id: closeAppTimer

        interval: 2000 // 2 second delay before closing
        repeat: false
        running: false
        onTriggered: {
            if (bridge && bridge.ready) {
                // Signal app shutdown via UART
                header.closeAppClicked();
                // Then execute system shutdown
                bridge.executeSystemCommand("shutdown now");
            }
        }
    }

    // Shutdown confirmation dialog
    AppDialog {
        id: shutdownConfirmDialog

        dialogTitle: "System Shutdown"
        message: "Are you sure you want to shut down the system?"
        standardButtonTypes: DialogButtonBox.Yes | DialogButtonBox.No
        yesButtonText: "Proceed"
        noButtonText: "Cancel"
        acceptButtonColor: ThemeManager.backgroundColor
        onAccepted: {
            // Close the dialog
            shutdownConfirmDialog.close();
            // Show shutdown message
            header.showToastMessage("Shutting down...", 5000);
            // Start the timer to delay closing
            closeAppTimer.start();
        }
        onRejected: {
            shutdownConfirmDialog.close();
        }
    }
}
