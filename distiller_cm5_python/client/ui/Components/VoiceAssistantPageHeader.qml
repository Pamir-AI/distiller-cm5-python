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
    property alias infoButton: infoBtn

    signal serverSelectClicked
    // Keep the signal to prevent errors
    signal darkModeClicked
    signal closeAppClicked
    signal showToastMessage(string message, int duration)
    signal infoClicked()

    color: ThemeManager.backgroundColor

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

    // Info button
    InfoButton {
        id: infoBtn

        anchors.right: closeBtn.left
        anchors.rightMargin: ThemeManager.spacingSmall
        anchors.verticalCenter: parent.verticalCenter
        
        onInfoClicked: {
            header.infoClicked();
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
                // Execute pre-shutdown command and send initial BTN_POWER packet
                var success = bridge.sendPowerShutdownSignal();
                if (!success) {
                    console.log("Warning: Failed to send power shutdown signal via UART");
                }
                // Signal the closeAppClicked for any UI cleanup
                header.closeAppClicked();
                
                // Close the main window - this will trigger the same onClosing handler
                // that works when manually closing the application
                var mainWin = header.Window.window;
                if (mainWin) {
                    console.log("Closing main window programmatically");
                    mainWin.close();
                } else {
                    // Fallback to bridge shutdown if main window not accessible
                    console.log("Main window not accessible, using bridge shutdown");
                    bridge.shutdownApplication(false);
                }
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
