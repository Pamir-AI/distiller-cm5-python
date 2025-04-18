import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: audioVisualizer

    property bool isActive: false
    property int barCount: 5
    property int updateInterval: 150 // Slower updates for e-ink
    // Store the bar heights
    property var barHeights: []

    width: parent.width
    height: parent.height
    color: "transparent"
    Component.onCompleted: {
        // Initialize bar heights
        for (let i = 0; i < barCount; i++) {
            barHeights.push(0.3 + (i % 3) * 0.2); // Different initial heights
        }
    }

    // Animation timer for updating the visualizer
    Timer {
        id: updateTimer

        interval: updateInterval
        repeat: true
        running: isActive
        onTriggered: {
            // Update heights of bars randomly when active
            for (let i = 0; i < barCount; i++) {
                barHeights[i] = Math.random() * 0.7 + 0.3; // Range: 0.3 to 1.0
            }
            canvas.requestPaint();
        }
    }

    // Container for visualizer and text
    Item {
        anchors.centerIn: parent
        width: parent.width * 0.9
        height: parent.height * 0.8

        // Use Canvas for better e-ink performance
        Canvas {
            id: canvas

            anchors.fill: parent
            onPaint: {
                var ctx = getContext("2d");
                ctx.clearRect(0, 0, width, height);
                var barWidth = width / (barCount * 2 - 1);
                var spacing = barWidth;
                // Draw bars
                ctx.fillStyle = ThemeManager.darkMode ? "#FFFFFF" : "#000000";
                for (let i = 0; i < barCount; i++) {
                    var barHeight = height * barHeights[i] * 0.6; // Keep heights reasonable
                    var x = i * (barWidth + spacing);
                    var y = (height - barHeight) / 2;
                    // Draw rounded rectangles for bars
                    ctx.beginPath();
                    var radius = 3;
                    ctx.moveTo(x + radius, y);
                    ctx.lineTo(x + barWidth - radius, y);
                    ctx.arcTo(x + barWidth, y, x + barWidth, y + radius, radius);
                    ctx.lineTo(x + barWidth, y + barHeight - radius);
                    ctx.arcTo(x + barWidth, y + barHeight, x + barWidth - radius, y + barHeight, radius);
                    ctx.lineTo(x + radius, y + barHeight);
                    ctx.arcTo(x, y + barHeight, x, y + barHeight - radius, radius);
                    ctx.lineTo(x, y + radius);
                    ctx.arcTo(x, y, x + radius, y, radius);
                    ctx.fill();
                }
            }
        }

    }

}
