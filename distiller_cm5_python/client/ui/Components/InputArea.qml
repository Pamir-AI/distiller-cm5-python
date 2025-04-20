// import QtGraphicalEffects 1.15  // Commented out in case it's not available

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import Components 1.0

Rectangle {
    // No borders on the main rectangle

    id: inputArea

    // Simplified height since there's no text input
    height: 60 // Fixed height for buttons
    property bool isListening: false
    property bool isProcessing: false // Keep this for visual feedback on voice button?
    property bool compact: true // Keep or remove based on visual needs

    // Expose only remaining buttons
    property alias settingsButton: settingsButton
    property alias voiceButton: voiceButton
    // property alias sendButton: sendButton // Removed

    // signal textSubmitted(string text) // Removed
    signal settingsClicked()
    // Add signals for press/release
    signal voicePressed()
    signal voiceReleased()

    // function clearInput() { } // Removed
    // function getText() { return ""; } // Removed

    // Reset state might still be useful for voice button
    function resetState() {
        isProcessing = false;
    }

    color: ThemeManager.backgroundColor
    z: 10 // Ensure this is always on top

    // hintText Removed
    // listeningHint Removed (can be handled by statusText in parent page)

    // Simple Row layout for the remaining buttons
    RowLayout {
        id: buttonRowLayout

        anchors.fill: parent
        anchors.margins: 8
        spacing: 12

        // Consistent button size
        property int buttonSize: 40
        property int borderWidth: 2

        // Settings button (kept)
        RoundButton {
            id: settingsButton
            Layout.preferredWidth: buttonRowLayout.buttonSize
            Layout.preferredHeight: buttonRowLayout.buttonSize
            flat: true
            property bool navigable: true
            property bool isActiveItem: false
            onClicked: inputArea.settingsClicked()

            background: Rectangle {
                color: "transparent"
                antialiasing: true
                
                // Crisp focus border
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: settingsButton.isActiveItem ? 0 : -buttonRowLayout.borderWidth
                    color: "transparent"
                    border {
                        width: settingsButton.isActiveItem ? buttonRowLayout.borderWidth : 0
                        color: ThemeManager.accentColor
                    }
                    radius: width / 2
                    antialiasing: true
                    opacity: settingsButton.isActiveItem ? 1.0 : 0
                }
            }

            contentItem: Item {
                anchors.fill: parent
                
                // Simple hover highlight
                Rectangle {
                    visible: settingsButton.hovered || settingsButton.pressed
                    anchors.fill: parent
                    radius: width / 2
                    color: ThemeManager.buttonColor
                    opacity: 0.15
                    antialiasing: true
                }

                Text {
                    text: "⚙"  // Gear icon as text
                    font.pixelSize: parent.width / 2
                    font.family: FontManager.primaryFontFamily
                    color: ThemeManager.textColor
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    anchors.centerIn: parent
                    opacity: settingsButton.isActiveItem ? 1.0 : (settingsButton.hovered ? 1 : 0.7)
                }
            }
        }

        // Spacer to push voice button towards center/right
        Item {
           Layout.fillWidth: true
        }

        // Voice button (kept)
        RoundButton {
            id: voiceButton
            Layout.preferredWidth: buttonRowLayout.buttonSize
            Layout.preferredHeight: buttonRowLayout.buttonSize
            flat: true
            // checkable: true // Now handled by MouseArea
            property bool navigable: true
            property bool isActiveItem: false
            // checked: inputArea.isListening // State handled by parent page signal
            // onClicked: { inputArea.voiceToggled(checked); } // Handled by MouseArea

            // Connect the button's own signals to the InputArea signals
            onPressed: inputArea.voicePressed()
            onReleased: inputArea.voiceReleased()

            background: Rectangle {
                // color: voiceButton.checked ? ThemeManager.subtleColor : "transparent" // State handled by parent
                color: inputArea.isListening ? ThemeManager.subtleColor : "transparent"
                antialiasing: true
                
                // Crisp focus border
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: voiceButton.isActiveItem ? 0 : -buttonRowLayout.borderWidth
                    color: "transparent"
                    border {
                        width: voiceButton.isActiveItem ? buttonRowLayout.borderWidth : 0
                        color: ThemeManager.accentColor
                    }
                    radius: width / 2
                    antialiasing: true
                    opacity: voiceButton.isActiveItem ? 1.0 : 0
                }
            }

            contentItem: Item {
                anchors.fill: parent
                
                // Simple hover highlight
                Rectangle {
                    visible: voiceButton.hovered || voiceButton.pressed
                    anchors.fill: parent
                    radius: width / 2
                    color: ThemeManager.buttonColor
                    opacity: 0.15
                    antialiasing: true
                }

                OptimizedImage {
                    id: micIcon
                    source: {
                        // Simplified icon logic based on parent page state
                         if (inputArea.isListening) {
                             if (inputArea.isProcessing)
                                 // Maybe a different icon for processing after listening?
                                 return ThemeManager.darkMode ? "../images/icons/dark/microphone-filled.svg" : "../images/icons/microphone-filled.svg";
                             return ThemeManager.darkMode ? "../images/icons/dark/microphone-half.svg" : "../images/icons/microphone-half.svg"; // Listening icon
                         }
                         return ThemeManager.darkMode ? "../images/icons/dark/microphone-empty.svg" : "../images/icons/microphone-empty.svg"; // Idle icon
                    }
                    sourceSize.width: 22
                    sourceSize.height: 22
                    width: 22
                    height: 22
                    anchors.centerIn: parent
                    fillMode: Image.PreserveAspectFit
                    opacity: voiceButton.hovered ? 1 : 0.7 // Simplified opacity
                    fadeInDuration: 0
                    showPlaceholder: false
                }

                // Simple indicator for listening state
                Rectangle {
                    visible: inputArea.isListening && !inputArea.isProcessing // Use parent state
                    anchors.centerIn: parent
                    width: parent.width - 4
                    height: parent.height - 4
                    radius: width / 2
                    color: "transparent"
                    border.width: 1
                    border.color: ThemeManager.accentColor
                    opacity: 0.5
                    antialiasing: true
                }
            }
        }
        
        // Spacer
        Item { 
            Layout.fillWidth: true
        }
        
        // Send Button Removed

    }

}
