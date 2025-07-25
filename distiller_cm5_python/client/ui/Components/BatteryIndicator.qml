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
    property string statusPattern: "empty"
    property string statusText: "UNK"

    // Make it navigable
    property bool navigable: true

    width: {
        var baseWidth = compact ? 80 : 96;
        return isCharging ? baseWidth * 1.5 : baseWidth;
    }
    height: compact ? ThemeManager.buttonHeight : ThemeManager.buttonHeight * 1.2;

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
            statusPattern = info.statusPattern || "empty";
            statusText = info.statusText || "UNK";
        }
    }

    // Main battery display container
    Row {
        anchors.centerIn: parent
        spacing: compact ? ThemeManager.spacingTiny : ThemeManager.spacingSmall

        // Battery percentage text - 1-bit colors only
        Text {
            visible: showPercentage
            text: batteryLevel + "%"
            font: compact ? FontManager.small : FontManager.normal
            color: ThemeManager.textColor
            anchors.verticalCenter: parent.verticalCenter
            renderType: Text.NativeRendering
        }

        // Status indicator text - displayed beside percentage for better visibility
        Text {
            visible: isCritical || isLow || isTemperatureWarning
            text: {
                if (isTemperatureWarning)
                    return "󰼩";
                if (isCritical)
                    return "";
                if (isLow)
                    return "󰗖";
                return "";
            }
            font: compact ? FontManager.small : FontManager.medium
            color: ThemeManager.textColor
            anchors.verticalCenter: parent.verticalCenter
            renderType: Text.NativeRendering
        }

        // Charging indicator - monochrome lightning bolt for e-ink
        Text {
            visible: isCharging && currentMa > 0
            text: "⚡"
            font: compact ? FontManager.small : FontManager.medium
            color: ThemeManager.textColor
            anchors.verticalCenter: parent.verticalCenter
            renderType: Text.NativeRendering
        }

        // Simple battery icon
        Rectangle {
            width: compact ? 28 : ThemeManager.buttonHeight
            height: compact ? 16 : ThemeManager.buttonHeight / 2
            radius: ThemeManager.borderRadius / 3
            border.width: ThemeManager.borderWidth
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
