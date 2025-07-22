import QtQuick
import QtQuick.Controls

NavigableItem {
    id: batteryIndicator

    property int batteryLevel: 100
    property bool isCharging: false
    property bool isLow: false
    property bool isCritical: false
    property bool showPercentage: true
    property bool compact: false

    // Make it navigable
    property bool navigable: true

    signal batteryClicked

    width: compact ? 64 : 80
    height: compact ? 25 : 35

    // Override NavigableItem's clicked signal
    onClicked: batteryIndicator.batteryClicked()

    // Activation function for focus manager
    function activate() {
        batteryClicked();
    }

    // Update battery info from battery monitor
    function updateBatteryInfo() {
        if (bridge && bridge.ready && typeof bridge.getBatteryInfo === "function") {
            var info = bridge.getBatteryInfo();
            batteryLevel = info.capacity || 100;
            isCharging = info.isCharging || false;
            isLow = info.isLow || false;
            isCritical = info.isCritical || false;
        }
    }

    // Main battery display container
    Rectangle {
        anchors.fill: parent
        color: "transparent"

        Row {
            anchors.centerIn: parent
            spacing: compact ? 6 : 8

            // Battery percentage text - 1-bit colors only (moved to first position)
            Text {
                visible: showPercentage
                text: batteryLevel + "%"
                font: compact ? FontManager.tiny : FontManager.small
                color: ThemeManager.textColor
                anchors.verticalCenter: parent.verticalCenter
                renderType: Text.NativeRendering
            }

            // Charging indicator - simplified for 1-bit
            Text {
                visible: isCharging
                text: "↯" // Simple lightning bolt that works in 1-bit
                font: compact ? FontManager.tiny : FontManager.small
                color: ThemeManager.textColor
                anchors.verticalCenter: parent.verticalCenter
                renderType: Text.NativeRendering
            }

            // Battery Icon - simplified for 1-bit display (moved to second position)
            Rectangle {
                width: compact ? 16 : 20
                height: compact ? 10 : 12
                radius: 1
                border.width: 2  // Thickened border
                border.color: ThemeManager.textColor
                color: ThemeManager.backgroundColor

                // Battery terminal (positive end)
                Rectangle {
                    width: 2
                    height: parent.height * 0.6
                    anchors.right: parent.right
                    anchors.rightMargin: -1
                    anchors.verticalCenter: parent.verticalCenter
                    color: ThemeManager.textColor
                    radius: 1
                }

                // Battery fill level - using patterns for 1-bit display
                Rectangle {
                    id: batteryFill
                    width: Math.max(2, (parent.width - 4) * (batteryLevel / 100))
                    height: parent.height - 4
                    anchors.left: parent.left
                    anchors.leftMargin: 2
                    anchors.verticalCenter: parent.verticalCenter
                    radius: 1

                    // Use solid fill or pattern based on battery state
                    color: {
                        if (isCritical) {
                            // Solid black for critical (will flash)
                            return ThemeManager.textColor;
                        } else if (isLow) {
                            // Diagonal stripes pattern for low battery
                            return ThemeManager.textColor;
                        } else {
                            // Normal fill
                            return ThemeManager.textColor;
                        }
                    }
                }

                // Low battery warning pattern - using cross-hatch
                Rectangle {
                    visible: isLow && !isCritical
                    anchors.fill: batteryFill
                    color: "transparent"
                    border.width: 2  // Thickened border
                    border.color: ThemeManager.textColor
                    radius: batteryFill.radius
                }
            }
        }
    }

    // Update battery info periodically
    Timer {
        id: batteryUpdateTimer
        interval: 5000 // Update every 5 seconds
        repeat: true
        running: true
        triggeredOnStart: true
        onTriggered: updateBatteryInfo()
    }

    Component.onCompleted: {
        updateBatteryInfo();
    }
}
