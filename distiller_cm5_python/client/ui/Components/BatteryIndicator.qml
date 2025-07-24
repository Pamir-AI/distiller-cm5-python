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
    property real currentMa: 0.0
    property bool isTemperatureWarning: false
    property string statusPattern: "solid_fill"
    property string statusText: "OK"

    // Make it navigable
    property bool navigable: true

    signal batteryClicked

    width: {
        var baseWidth = compact ? 80 : 96
        return isCharging ? baseWidth * 1.5 : baseWidth
    }
    height: compact ? 36 : 40

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
            currentMa = info.current_ma || 0.0;
            isTemperatureWarning = info.isTemperatureWarning || false;
            statusPattern = info.statusPattern || "solid_fill";
            statusText = info.statusText || "OK";
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
                font: compact ? FontManager.small : FontManager.normal
                color: ThemeManager.textColor
                anchors.verticalCenter: parent.verticalCenter
                renderType: Text.NativeRendering
            }

            // Charging indicator - enhanced with current_ma check
            Text {
                visible: isCharging && currentMa > 0
                text: "↯" // Simple lightning bolt that works in 1-bit
                font: compact ? FontManager.small : FontManager.medium
                color: ThemeManager.textColor
                anchors.verticalCenter: parent.verticalCenter
                renderType: Text.NativeRendering
                style: Text.Outline
                styleColor: ThemeManager.backgroundColor
            }

            // Simple battery icon - clean design for e-ink
            Rectangle {
                width: compact ? 28 : 36
                height: compact ? 16 : 20
                radius: 2
                border.width: 2
                border.color: ThemeManager.textColor
                color: ThemeManager.backgroundColor

                // Battery terminal (positive end)
                Rectangle {
                    width: 3
                    height: parent.height * 0.7
                    anchors.right: parent.right
                    anchors.rightMargin: -1
                    anchors.verticalCenter: parent.verticalCenter
                    color: ThemeManager.textColor
                    radius: 1
                }

                // Simple fill level indicator
                Rectangle {
                    width: Math.max(2, (parent.width - 6) * (batteryLevel / 100))
                    height: parent.height - 6
                    anchors.left: parent.left
                    anchors.leftMargin: 3
                    anchors.verticalCenter: parent.verticalCenter
                    color: ThemeManager.textColor
                    radius: 1
                }

                // Status text overlay - simple and readable
                Text {
                    visible: isCritical || isLow || isTemperatureWarning
                    text: {
                        if (isTemperatureWarning)
                            return "⚠";
                        if (isCritical)
                            return "!";
                        if (isLow)
                            return "L";
                        return "";
                    }
                    font: compact ? FontManager.small : FontManager.medium
                    color: ThemeManager.textColor
                    anchors.centerIn: parent
                    renderType: Text.NativeRendering
                    style: Text.Outline
                    styleColor: ThemeManager.backgroundColor
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
