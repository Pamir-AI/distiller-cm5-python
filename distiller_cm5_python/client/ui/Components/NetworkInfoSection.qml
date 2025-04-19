import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

AppSection {
    id: networkInfoSection

    title: "WI-FI INFORMATION"
    compact: true
    
    // Connect to bridge ready signal
    Connections {
        target: bridge
        
        function onBridgeReady() {
            // Update IP address when bridge is ready
            if (wifiIpAddress) {
                var ipAddress = bridge.getWifiIpAddress();
                wifiIpAddress.ipAddress = ipAddress;
                wifiIpAddress.text = ipAddress ? ipAddress : "Not available";
                console.log("WiFi IP Address:", ipAddress);
            }
        }
    }
    
    ColumnLayout {
        width: parent.width
        spacing: ThemeManager.spacingLarge // Increased spacing for consistency with other sections

        // Description text
        Text {
            text: "View wifi details for this device"
            font.pixelSize: FontManager.fontSizeNormal
            font.family: FontManager.primaryFontFamily
            color: ThemeManager.secondaryTextColor
            Layout.fillWidth: true
            Layout.bottomMargin: ThemeManager.spacingNormal
            wrapMode: Text.WordWrap
        }

        // WiFi IP Address section with refresh button
        RowLayout {
            Layout.fillWidth: true
            spacing: ThemeManager.spacingNormal

            // Left column with label and value
            ColumnLayout {
                Layout.fillWidth: true
                spacing: ThemeManager.spacingSmall

                // WiFi IP Address Label
                Text {
                    text: "IP ADDRESS"
                    font.pixelSize: FontManager.fontSizeNormal
                    font.family: FontManager.primaryFontFamily
                    color: ThemeManager.secondaryTextColor
                    Layout.fillWidth: true
                }

                // WiFi IP Address Value
                Text {
                    id: wifiIpAddress
                    property string ipAddress: ""

                    Component.onCompleted: {
                        if (bridge && bridge.ready) {
                            ipAddress = bridge.getWifiIpAddress();
                            text = ipAddress ? ipAddress : "Not available";
                            console.log("WiFi IP Address:", ipAddress);
                        } else {
                            text = "Bridge not ready";
                            console.log("Bridge not ready, waiting for initialization");
                        }
                    }

                    font.pixelSize: FontManager.fontSizeNormal
                    font.family: FontManager.primaryFontFamily
                    color: ThemeManager.textColor
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                }
            }

            // Minimal refresh button with spacing
            Item {
                Layout.preferredWidth: 48  // Increased from 32 to 48 for more spacing
                Layout.preferredHeight: 32
                Layout.alignment: Qt.AlignBottom

                AppRoundButton {
                    id: refreshButton
                    iconText: "↻"
                    width: 32
                    height: 32
                    anchors.left: parent.left  // Left align within the 48px wide container
                    showBorder: true  // Enable border around the button

                    onClicked: {
                        if (bridge && bridge.ready) {
                            // Update the IP address display
                            var newIpAddress = bridge.getWifiIpAddress();
                            wifiIpAddress.ipAddress = newIpAddress;
                            wifiIpAddress.text = newIpAddress ? newIpAddress : "Not available";
                        } else {
                            wifiIpAddress.text = "Bridge not ready";
                            console.log("Bridge not ready, cannot refresh WiFi IP address");
                        }
                    }
                }
            }
        }
    }
}
