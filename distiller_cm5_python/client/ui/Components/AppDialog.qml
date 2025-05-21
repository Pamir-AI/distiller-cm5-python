import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: root

    // Basic properties
    property string dialogTitle: "Dialog"
    property string message: ""
    // Button configuration
    property int standardButtonTypes: DialogButtonBox.Ok | DialogButtonBox.Cancel
    property string okButtonText: "OK"
    property string cancelButtonText: "Cancel"
    property string yesButtonText: "Yes"
    property string noButtonText: "No"
    // Navigation system
    property var focusableItems: []
    // Button colors
    property color defaultButtonColor: ThemeManager.backgroundColor
    property color acceptButtonColor: ThemeManager.textColor
    property color focusButtonColor: ThemeManager.textColor
    // Store previous focus state
    property var previousFocusItems: []
    property int previousFocusIndex: -1

    // Collect all buttons for navigation
    function collectFocusableItems() {
        focusableItems = [];
        // Add visible buttons to focusable items
        var buttons = [okButton, yesButton, cancelButton, noButton];
        for (var i = 0; i < buttons.length; i++) {
            if (buttons[i] && buttons[i].visible)
                focusableItems.push(buttons[i]);

        }
        // Register with FocusManager but don't set initial focus
        if (focusableItems.length > 0)
            FocusManager.initializeFocusItems(focusableItems);

    }

    // Dialog setup
    title: dialogTitle
    modal: true
    anchors.centerIn: parent
    width: parent.width * 0.85
    height: contentColumn.implicitHeight + headerRect.height + footerRect.height + ThemeManager.spacingLarge * 2
    // Close on Escape key
    closePolicy: Popup.CloseOnEscape
    // Clean up focus when dialog closes
    onOpened: {
        // Store previous focus state
        previousFocusItems = FocusManager.currentFocusItems.slice();
        previousFocusIndex = FocusManager.currentFocusIndex;
        Qt.callLater(collectFocusableItems);
    }
    onClosed: {
        if (FocusManager) {
            // Use a timer to ensure dialog closing is complete
            // In case direct setting fails, find the nearest page's collectFocusItems function

            // Restore previous focus state
            if (previousFocusItems.length > 0 && previousFocusIndex >= 0 && previousFocusIndex < previousFocusItems.length)
                Qt.callLater(function() {
                // First reset focus manager state
                FocusManager.currentFocusItems = previousFocusItems;
                FocusManager.currentFocusIndex = previousFocusIndex;
                // Then set focus to the previous item
                if (previousFocusItems[previousFocusIndex] && previousFocusItems[previousFocusIndex].navigable)
                    FocusManager.setFocusToItem(previousFocusItems[previousFocusIndex]);
                else if (parent && parent.collectFocusItems)
                    parent.collectFocusItems();
            });
            else {
                // If no previous focus state, just clear the focus
                FocusManager.initializeFocusItems([]);
                // Find the nearest page's collectFocusItems function
                if (parent && parent.collectFocusItems)
                    Qt.callLater(function() {
                    parent.collectFocusItems();
                });

            }
        }
    }

    // Dialog background
    background: Rectangle {
        color: ThemeManager.backgroundColor
        radius: ThemeManager.borderRadius // Basic rounded corners
    }

    // Dialog header
    header: Rectangle {
        id: headerRect

        width: parent.width
        height: headerText.implicitHeight + ThemeManager.spacingNormal * 2
        color: ThemeManager.backgroundColor
        // Rounded corners for top portion only
        radius: ThemeManager.borderRadius

        // Only round the top corners
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: parent.radius + 1
            color: parent.color
        }

        Text {
            id: headerText

            anchors.centerIn: parent
            width: parent.width - ThemeManager.spacingLarge * 2
            text: dialogTitle
            font: FontManager.normalBold
            color: ThemeManager.textColor
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }

    }

    // Dialog content
    contentItem: ColumnLayout {
        id: contentColumn

        width: parent.width
        spacing: ThemeManager.spacingLarge

        Text {
            text: message
            color: ThemeManager.textColor
            font.pixelSize: FontManager.fontSizeNormal
            font.family: FontManager.primaryFontFamily
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            Layout.margins: ThemeManager.spacingLarge
            horizontalAlignment: Text.AlignHCenter
            visible: message !== ""
        }

    }

    // Dialog footer with buttons
    footer: Rectangle {
        id: footerRect

        width: parent.width
        height: buttonRow.height + ThemeManager.spacingLarge * 2
        color: ThemeManager.backgroundColor
        // Rounded corners for bottom portion only
        radius: ThemeManager.borderRadius

        // Only round the bottom corners
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: parent.radius + 1
            color: parent.color
        }

        // Simplified button row
        Row {
            id: buttonRow

            // Calculate number of visible buttons
            property int visibleCount: {
                var count = 0;
                if (standardButtonTypes & DialogButtonBox.Ok)
                    count++;

                if (standardButtonTypes & DialogButtonBox.Yes)
                    count++;

                if (standardButtonTypes & DialogButtonBox.Cancel)
                    count++;

                if (standardButtonTypes & DialogButtonBox.No)
                    count++;

                return count;
            }
            // Calculate width for each button
            property real buttonWidth: Math.min(120, (parent.width * 0.8 - (visibleCount - 1) * spacing) / Math.max(1, visibleCount))

            anchors.centerIn: parent
            spacing: ThemeManager.spacingNormal

            // OK button
            AppButton {
                id: okButton

                property bool navigable: true

                text: okButtonText
                visible: standardButtonTypes & DialogButtonBox.Ok
                width: buttonRow.buttonWidth
                height: ThemeManager.buttonHeight
                backgroundColor: visualFocus ? focusButtonColor : acceptButtonColor
                textColor: visualFocus ? ThemeManager.backgroundColor : ThemeManager.textColor
                onClicked: {
                    root.accept();
                    root.close();
                }
            }

            // Yes button
            AppButton {
                id: yesButton

                property bool navigable: true

                text: yesButtonText
                visible: standardButtonTypes & DialogButtonBox.Yes
                width: buttonRow.buttonWidth
                height: ThemeManager.buttonHeight
                backgroundColor: visualFocus ? focusButtonColor : acceptButtonColor
                textColor: visualFocus ? ThemeManager.backgroundColor : ThemeManager.textColor
                onClicked: {
                    root.accept();
                    root.close();
                }
            }

            // Cancel button
            AppButton {
                id: cancelButton

                property bool navigable: true

                text: cancelButtonText
                visible: standardButtonTypes & DialogButtonBox.Cancel
                width: buttonRow.buttonWidth
                height: ThemeManager.buttonHeight
                backgroundColor: visualFocus ? focusButtonColor : defaultButtonColor
                textColor: visualFocus ? ThemeManager.backgroundColor : ThemeManager.textColor
                onClicked: {
                    root.reject();
                    root.close();
                }
            }

            // No button
            AppButton {
                id: noButton

                property bool navigable: true

                text: noButtonText
                visible: standardButtonTypes & DialogButtonBox.No
                width: buttonRow.buttonWidth
                height: ThemeManager.buttonHeight
                backgroundColor: visualFocus ? focusButtonColor : defaultButtonColor
                textColor: visualFocus ? ThemeManager.backgroundColor : ThemeManager.textColor
                onClicked: {
                    root.reject();
                    root.close();
                }
            }

        }

    }

}
