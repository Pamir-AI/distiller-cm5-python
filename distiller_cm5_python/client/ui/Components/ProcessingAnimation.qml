import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: processingAnimation
    color: "transparent"
    
    property bool isActive: false
    property int dotCount: 5
    property int updateInterval: 200
    
    signal stopRequested()
    
    // Animation timer for updating the dots
    Timer {
        id: updateTimer
        interval: updateInterval
        repeat: true
        running: isActive
        onTriggered: {
            // Update dot sizes
            for (let i = 0; i < dotRepeater.count; i++) {
                var wavePos = (i / dotCount) * 2 * Math.PI;
                var phase = (updateTimer.counter * 0.2) % (2 * Math.PI);
                var sizeFactor = Math.sin(wavePos + phase) * 0.5 + 0.5;
                dotRepeater.itemAt(i).width = maxDotSize * sizeFactor;
                dotRepeater.itemAt(i).height = maxDotSize * sizeFactor;
            }
            updateTimer.counter += 1;
        }
        
        property int counter: 0
    }
    
    // Size calculation property
    property real maxDotSize: Math.min(animationContainer.height * 0.3, animationContainer.width / (dotCount * 2))
    
    // Container for visualizer and stop button
    Item {
        id: mainContainer
        anchors.fill: parent
        
        // Visualizer container
        Item {
            id: animationContainer
            anchors.fill: parent
            anchors.bottomMargin: 50 // Make room for button
            
            // Use Row for simpler dot layout
            Row {
                anchors.centerIn: parent
                spacing: parent.width / (dotCount + 1) - maxDotSize
                
                // Create dots using repeater
                Repeater {
                    id: dotRepeater
                    model: dotCount
                    
                    Rectangle {
                        id: dot
                        width: maxDotSize * (0.5 + (index % 3) * 0.2)
                        height: width
                        radius: width / 2
                        color: ThemeManager.darkMode ? "#FFFFFF" : "#000000"
                        
                        // Center dots vertically
                        anchors.verticalCenter: parent ? parent.verticalCenter : undefined
                    }
                }
            }
        }
        
        // Pause/Stop button - centered below the animation
        Rectangle {
            id: stopButton
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 8
            width: 100
            height: 38
            radius: 19
            color: stopButtonMouseArea.pressed ? ThemeManager.pressedColor : (stopButtonMouseArea.containsMouse ? ThemeManager.subtleColor : ThemeManager.backgroundColor)
            border.color: ThemeManager.borderColor
            border.width: ThemeManager.borderWidth
            
            Text {
                anchors.centerIn: parent
                text: "STOP"
                font.pixelSize: FontManager.fontSizeNormal
                font.family: FontManager.primaryFontFamily
                font.bold: true
                color: ThemeManager.textColor
            }
            
            // Pulse animation to draw attention to the button
            SequentialAnimation {
                id: pulseAnimation
                running: isActive
                loops: Animation.Infinite
                
                NumberAnimation {
                    target: stopButton
                    property: "scale"
                    from: 1.0
                    to: 1.05
                    duration: 800
                    easing.type: Easing.InOutQuad
                }
                
                NumberAnimation {
                    target: stopButton
                    property: "scale"
                    from: 1.05
                    to: 1.0
                    duration: 800
                    easing.type: Easing.InOutQuad
                }
            }
            
            MouseArea {
                id: stopButtonMouseArea
                anchors.fill: parent
                hoverEnabled: true
                onClicked: {
                    console.log("Stop button clicked, emitting stopRequested signal");
                    processingAnimation.stopRequested();
                }
            }
        }
    }
} 