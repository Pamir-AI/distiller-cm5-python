// import QtGraphicalEffects 1.15  // Commented out in case it's not available

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import Components 1.0

Rectangle {
    // No borders on the main rectangle

    id: inputArea
    objectName: "inputAreaRoot"

    // --- Re-add missing alias --- 
    property alias voiceButtonAlias: voiceButton
    // --- End re-add ---

    // Dynamic height based on text content with min/max constraints
    property int minHeight: 80
    property int maxHeight: 160
    property bool isListening: false
    property bool isProcessing: false
    property bool compact: true

    signal textSubmitted(string text)
    signal voiceToggled(bool listening)

    color: ThemeManager.backgroundColor
    height: Math.min(maxHeight, Math.max(minHeight, inputLayout.implicitHeight + 20))
    z: 10 // Ensure this is always on top

    // Hint text that appears above the input field
    Text {
        id: hintText

        visible: !isListening && (textInput.text.length > 30 || textInput.text.indexOf("\n") >= 0)
        anchors.right: parent.right
        anchors.bottom: inputLayout.top
        anchors.rightMargin: 12
        anchors.bottomMargin: 2
        text: "Shift+Enter for new line"
        font.pixelSize: 10
        color: ThemeManager.textColor
        opacity: 0.6

        // Add a subtle background to improve visibility
        Rectangle {
            z: -1
            anchors.fill: parent
            anchors.margins: -3
            color: ThemeManager.backgroundColor
            opacity: 0.8
            radius: 3
        }

    }

    // Listening hint that appears during microphone input
    Text {
        id: listeningHint

        visible: isListening
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: inputLayout.top
        anchors.bottomMargin: 2
        text: "Listening..."
        font.pixelSize: FontManager.fontSizeNormal
        font.family: FontManager.primaryFontFamily
        color: ThemeManager.textColor
        opacity: 0.9

        // Add a subtle background to improve visibility
        Rectangle {
            z: -1
            anchors.fill: parent
            anchors.margins: -6
            color: ThemeManager.backgroundColor
            opacity: 0.8
            radius: 3
        }

    }

    // Simple grid layout with fixed proportions
    GridLayout {
        id: inputLayout

        anchors.fill: parent
        anchors.margins: 8
        rowSpacing: 4
        columnSpacing: 4
        columns: 1
        rows: 2

        // Input field - simple rectangle with text area
        Rectangle {
            id: inputField

            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 36
            color: ThemeManager.backgroundColor
            border.color: isListening ? "transparent" : ThemeManager.borderColor
            border.width: isListening ? 0 : ThemeManager.borderWidth
            radius: ThemeManager.borderRadius

            // Stack content that switches between text area and visualizer
            Item {
                anchors.fill: parent

                // Text input scroll view
                AppScrollView {
                    id: scrollView
                    objectName: "inputScrollView"
                    enabled: !inputArea.isListening && !inputArea.isProcessing

                    anchors.fill: parent
                    anchors.margins: 0
                    visible: !isListening && !isProcessing
                    showEdgeEffects: false
                    contentHeight: textInput.implicitHeight

                    TextArea {
                        id: textInput

                        anchors.fill: parent
                        anchors.margins: 4
                        wrapMode: TextArea.Wrap
                        font: FontManager.normal
                        color: ThemeManager.textColor
                        placeholderText: "Type your message here..."
                        placeholderTextColor: ThemeManager.secondaryTextColor
                        background: null
                        // Allow vertical growth but limit it
                        onTextChanged: {
                            // Update implicitHeight when text changes
                            inputArea.implicitHeight = Math.min(inputArea.maxHeight, Math.max(inputArea.minHeight, inputLayout.implicitHeight + 20));
                        }
                        Keys.onPressed: (event) => {
                            if (event.key === Qt.Key_Up || event.key === Qt.Key_Down) {
                                // Don't let TextArea consume Up/Down arrow keys
                                event.accepted = false;
                            } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                                 if (event.modifiers & Qt.ShiftModifier) {
                                     // Allow shift+return for line breaks
                                     event.accepted = false;
                                 } else if (text.trim() !== "") {
                                     sendButton.clicked();
                                     event.accepted = true;
                                 } else {
                                     // Prevent Enter on empty text from doing anything or propagating
                                     event.accepted = true; 
                                 }
                            } else {
                                 // Let other keys behave normally within the text area
                                 event.accepted = false;
                            }
                        }
                    }
                }

                // Audio visualizer component
                AudioVisualizer {
                    id: audioVisualizer
                    objectName: "inputAudioVisualizer"

                    anchors.fill: parent
                    anchors.margins: 4
                    visible: isListening
                    isActive: isListening
                }
            }
        }

        // Minimalist button row
        Item {
            id: buttonRow

            Layout.fillWidth: true
            Layout.preferredHeight: 36

            Row {
                id: leftButtonsRow

                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8

                // Voice button
                AppRoundButton {
                    id: voiceButton
                    objectName: "inputVoiceButton"

                    width: 36
                    height: 36
                    flat: true
                    checkable: true
                    checked: inputArea.isListening
                    onClicked: {
                        inputArea.voiceToggled(checked);
                    }

                    contentItem: Item {
                        anchors.fill: parent

                        Image {
                            id: micIcon

                            source: {
                                if (!voiceButton.enabled)
                                    return ThemeManager.darkMode ? "../images/icons/dark/microphone-empty.svg" : "../images/icons/microphone-empty.svg";

                                if (voiceButton.checked) {
                                    if (inputArea.isProcessing)
                                        return ThemeManager.darkMode ? "../images/icons/dark/microphone-filled.svg" : "../images/icons/microphone-filled.svg";

                                    return ThemeManager.darkMode ? "../images/icons/dark/microphone-half.svg" : "../images/icons/microphone-half.svg";
                                }
                                return ThemeManager.darkMode ? "../images/icons/dark/microphone-empty.svg" : "../images/icons/microphone-empty.svg";
                            }
                            sourceSize.width: 20
                            sourceSize.height: 20
                            width: 20
                            height: 20
                            anchors.centerIn: parent
                            fillMode: Image.PreserveAspectFit
                            opacity: voiceButton.checked ? 1 : (voiceButton.hovered ? 0.9 : 0.7)

                            Behavior on opacity {
                                NumberAnimation {
                                    duration: 150
                                }

                            }

                        }

                        // Subtle pulse animation for listening state
                        Rectangle {
                            visible: voiceButton.checked && !inputArea.isProcessing
                            anchors.centerIn: parent
                            width: parent.width
                            height: parent.height
                            radius: width / 2
                            color: ThemeManager.subtleColor
                            scale: pulseAnimation.running ? 1 : 0.8
                            opacity: pulseAnimation.running ? 0.3 : 0

                            SequentialAnimation {
                                id: pulseAnimation

                                loops: Animation.Infinite
                                running: voiceButton.checked && !inputArea.isProcessing

                                ParallelAnimation {
                                    NumberAnimation {
                                        target: micIcon
                                        property: "opacity"
                                        from: 0.8
                                        to: 1
                                        duration: 1000
                                        easing.type: Easing.InOutQuad
                                    }

                                    NumberAnimation {
                                        target: micIcon.parent
                                        property: "scale"
                                        from: 0.95
                                        to: 1.05
                                        duration: 1000
                                        easing.type: Easing.InOutQuad
                                    }

                                }

                                ParallelAnimation {
                                    NumberAnimation {
                                        target: micIcon
                                        property: "opacity"
                                        from: 1
                                        to: 0.8
                                        duration: 1000
                                        easing.type: Easing.InOutQuad
                                    }

                                    NumberAnimation {
                                        target: micIcon.parent
                                        property: "scale"
                                        from: 1.05
                                        to: 0.95
                                        duration: 1000
                                        easing.type: Easing.InOutQuad
                                    }

                                }

                            }

                        }

                    }

                }

            }

            // Send button
            RoundButton {
                id: sendButton

                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: 36
                height: 36
                flat: true
                enabled: textInput.text.trim() !== "" && !isProcessing
                
                onClicked: {
                    if (textInput.text.trim() !== "") {
                        // Trigger send animation
                        sendAnimation.start();
                        
                        // Small delay before actual submission to see animation
                        sendTimer.start();
                    }
                }

                background: Rectangle {
                    color: !parent.enabled ? "transparent" : (parent.pressed ? ThemeManager.pressedColor : "transparent")
                    border.width: 0
                    radius: width / 2
                }

                contentItem: Item {
                    anchors.fill: parent

                    Rectangle {
                        visible: sendButton.enabled && (sendButton.hovered || sendButton.pressed)
                        anchors.fill: parent
                        radius: width / 2
                        color: ThemeManager.buttonColor
                        opacity: 0.15
                    }

                    Image {
                        id: sendButtonIcon
                        source: ThemeManager.darkMode ? "../images/icons/dark/arrow_right.svg" : "../images/icons/arrow_right.svg"
                        sourceSize.width: 20
                        sourceSize.height: 20
                        width: 20
                        height: 20
                        anchors.centerIn: parent
                        fillMode: Image.PreserveAspectFit
                        opacity: parent.parent.enabled ? (sendButton.hovered ? 1 : 0.7) : 0.3

                        Behavior on opacity {
                            NumberAnimation {
                                duration: 150
                            }
                        }
                        
                        // Send button animation
                        SequentialAnimation {
                            id: sendAnimation
                            
                            ParallelAnimation {
                                NumberAnimation {
                                    target: sendButtonIcon
                                    property: "scale"
                                    from: 1.0
                                    to: 0.5
                                    duration: 100
                                    easing.type: Easing.InQuad
                                }
                                
                                NumberAnimation {
                                    target: sendButtonIcon
                                    property: "opacity"
                                    from: 1.0
                                    to: 0.5
                                    duration: 100
                                    easing.type: Easing.InQuad
                                }
                            }
                            
                            ParallelAnimation {
                                NumberAnimation {
                                    target: sendButtonIcon
                                    property: "scale"
                                    from: 0.5
                                    to: 1.2
                                    duration: 150
                                    easing.type: Easing.OutBack
                                }
                                
                                NumberAnimation {
                                    target: sendButtonIcon
                                    property: "opacity"
                                    from: 0.5
                                    to: 1.0
                                    duration: 150
                                    easing.type: Easing.OutQuad
                                }
                            }
                            
                            PauseAnimation {
                                duration: 50
                            }
                            
                            NumberAnimation {
                                target: sendButtonIcon
                                property: "scale"
                                from: 1.2
                                to: 1.0
                                duration: 100
                                easing.type: Easing.OutQuad
                            }
                        }
                    }
                }
            }

        }

    }

    // Timer to delay submission slightly to show animation
    Timer {
        id: sendTimer
        interval: 250
        repeat: false
        onTriggered: {
            if (textInput.text.trim() !== "") {
                inputArea.textSubmitted(textInput.text.trim());
                textInput.clear();
            }
        }
    }

    Behavior on height {
        NumberAnimation {
            duration: 100
            easing.type: Easing.OutQuad
        }

    }

}
