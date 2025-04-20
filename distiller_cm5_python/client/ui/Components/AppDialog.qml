import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

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
    property color defaultButtonColor: ThemeManager.buttonColor
    property color acceptButtonColor: ThemeManager.accentColor
    property color focusButtonColor: ThemeManager.darkMode ? 
                                    ThemeManager.darkAccentColor : 
                                    ThemeManager.lightAccentColor
    
    // Dialog setup
    title: dialogTitle
    modal: true
    anchors.centerIn: parent
    width: parent.width * 0.85
    height: contentColumn.implicitHeight + headerRect.height + footerRect.height + ThemeManager.spacingLarge * 2
    
    // Close on Escape key
    closePolicy: Popup.CloseOnEscape
    
    // Collect all buttons for navigation
    function collectFocusableItems() {
        focusableItems = [];
        
        // Add visible buttons to focusable items
        var buttons = [okButton, yesButton, cancelButton, noButton];
        for (var i = 0; i < buttons.length; i++) {
            if (buttons[i] && buttons[i].visible) {
                focusableItems.push(buttons[i]);
            }
        }
        
        // Register with FocusManager but don't set initial focus
        if (focusableItems.length > 0) {
            FocusManager.initializeFocusItems(focusableItems);
        }
    }
    
    // Clean up focus when dialog closes
    onOpened: {
        Qt.callLater(collectFocusableItems);
    }
    
    onClosed: {
        if (FocusManager) {
            FocusManager.initializeFocusItems([]);
        }
    }
    
    // Dialog background
    background: Rectangle {
        color: ThemeManager.backgroundColor
        border.color: ThemeManager.borderColor
        border.width: ThemeManager.borderWidth
        radius: ThemeManager.borderRadius
    }
    
    // Dialog header
    header: Rectangle {
        id: headerRect
        width: parent.width
        height: headerText.implicitHeight + ThemeManager.spacingNormal * 2
        color: ThemeManager.headerColor
        
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
        
        // Simplified button row
        Row {
            id: buttonRow
            anchors.centerIn: parent
            spacing: ThemeManager.spacingNormal
            
            // Calculate number of visible buttons
            property int visibleCount: {
                var count = 0;
                if (standardButtonTypes & DialogButtonBox.Ok) count++;
                if (standardButtonTypes & DialogButtonBox.Yes) count++;
                if (standardButtonTypes & DialogButtonBox.Cancel) count++;
                if (standardButtonTypes & DialogButtonBox.No) count++;
                return count;
            }
            
            // Calculate width for each button
            property real buttonWidth: Math.min(120, (parent.width * 0.8 - (visibleCount - 1) * spacing) / Math.max(1, visibleCount))
            
            // OK button
            AppButton {
                id: okButton
                text: okButtonText
                visible: standardButtonTypes & DialogButtonBox.Ok
                width: buttonRow.buttonWidth
                height: ThemeManager.buttonHeight
                backgroundColor: isActiveItem ? focusButtonColor : acceptButtonColor
                textColor: isActiveItem && !ThemeManager.darkMode ? 
                          ThemeManager.textColor : ThemeManager.backgroundColor
                property bool navigable: true
                
                onClicked: {
                    root.accept();
                    root.close();
                }
            }
            
            // Yes button
            AppButton {
                id: yesButton
                text: yesButtonText
                visible: standardButtonTypes & DialogButtonBox.Yes
                width: buttonRow.buttonWidth
                height: ThemeManager.buttonHeight
                backgroundColor: isActiveItem ? focusButtonColor : acceptButtonColor
                textColor: isActiveItem && !ThemeManager.darkMode ? 
                          ThemeManager.textColor : ThemeManager.backgroundColor
                property bool navigable: true
                
                onClicked: {
                    root.accept();
                    root.close();
                }
            }
            
            // Cancel button
            AppButton {
                id: cancelButton
                text: cancelButtonText
                visible: standardButtonTypes & DialogButtonBox.Cancel
                width: buttonRow.buttonWidth
                height: ThemeManager.buttonHeight
                backgroundColor: isActiveItem ? focusButtonColor : defaultButtonColor
                textColor: ThemeManager.textColor
                property bool navigable: true
                
                onClicked: {
                    root.reject();
                    root.close();
                }
            }
            
            // No button
            AppButton {
                id: noButton
                text: noButtonText
                visible: standardButtonTypes & DialogButtonBox.No
                width: buttonRow.buttonWidth
                height: ThemeManager.buttonHeight
                backgroundColor: isActiveItem ? focusButtonColor : defaultButtonColor
                textColor: ThemeManager.textColor
                property bool navigable: true
                
                onClicked: {
                    root.reject();
                    root.close();
                }
            }
        }
    }
} 
