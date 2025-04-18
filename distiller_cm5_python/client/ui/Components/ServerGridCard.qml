import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: cardContainer

    property string serverName: ""
    property string serverDescription: ""
    property string serverPath: ""

    signal cardClicked(string path)

    width: 200
    height: 200

    // Add logging for focus state changes
    onFocusChanged: console.log("--- ServerGridCard [" + serverName + "] focus changed: " + focus)
    onActiveFocusChanged: console.log("--- ServerGridCard [" + serverName + "] activeFocus changed: " + activeFocus)

    // Handle key presses when the card has focus
    Keys.onPressed: (event) => {
        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Select) {
            cardContainer.cardClicked(cardContainer.serverPath);
            event.accepted = true; // Accept Select/Enter
        } else if (event.key === Qt.Key_Up || event.key === Qt.Key_Down || event.key === Qt.Key_Left || event.key === Qt.Key_Right) {
            // **Important**: Don't accept arrow keys here; let the parent grid handle navigation.
            event.accepted = false;
        } else {
            // Decide how to handle other keys. For now, let them propagate.
            event.accepted = false; 
        }
    }

    // Drop shadow effect (subtle for e-ink displays)
    Rectangle {
        id: shadow
        anchors.fill: card
        anchors.margins: -2
        radius: card.radius + 2
        color: "transparent"
        border.color: ThemeManager.subtleColor
        border.width: 2
        z: 0
    }

    // Main card rectangle
    Rectangle {
        id: card
        anchors.fill: parent
        radius: 12 // More rounded corners
        color: ThemeManager.backgroundColor
        // -- Change border based on activeFocus for high contrast --
        border.color: cardContainer.activeFocus ? ThemeManager.highlightColor : ThemeManager.borderColor
        border.width: cardContainer.activeFocus ? 4 : ThemeManager.borderWidth // Use thicker border for focus
        z: 1

        // Card content
        Item {
            id: cardContent
            anchors.fill: parent
            anchors.margins: ThemeManager.spacingNormal / 2

            // Center content to ensure server name visibility
            ColumnLayout {
                id: contentLayout
                anchors.fill: parent
                spacing: 0  // Removed spacing

                // Server name container with guaranteed spacing
                Rectangle {
                    id: nameContainer
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.margins: 0  // Removed margins
                    color: "transparent" // No background

                    // Background rectangle for server name
                    Rectangle {
                        id: nameBackground
                        anchors.fill: parent
                        color: ThemeManager.darkMode ? ThemeManager.buttonColor : ThemeManager.highlightColor
                        radius: ThemeManager.borderRadius
                        border.width: 0
                    }

                    // Server name text with improved visibility
                    Text {
                        id: nameText
                        anchors.centerIn: parent
                        width: parent.width - (ThemeManager.spacingSmall * 2) // Reduced margins on sides
                        height: parent.height - (ThemeManager.spacingSmall * 2) // Allow more vertical space
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        text: cardContainer.serverName.toUpperCase()
                        font {
                            pixelSize: FontManager.fontSizeNormal
                            family: FontManager.primaryFontFamily
                            weight: FontManager.fontWeightBold
                        }
                        color: ThemeManager.textColor
                        elide: Text.ElideNone // Prevent truncation
                        maximumLineCount: 5 // Increased max lines for longer names
                        wrapMode: Text.Wrap // Better handling of long words
                        // Scale down text if needed
                        fontSizeMode: Text.Fit // Changed to Fit to scale in both directions
                        minimumPixelSize: 8 // Slightly lower minimum size to fit more text
                    }
                }
            }
        }
    }
}
