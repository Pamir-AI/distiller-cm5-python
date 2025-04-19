import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Dialog {
    id: root
    
    property string dialogTitle: "Dialog"
    property string message: ""
    property var customContent: null
    
    // Properties to customize the DialogButtonBox
    property int standardButtonTypes: DialogButtonBox.Ok | DialogButtonBox.Cancel | DialogButtonBox.Help | DialogButtonBox.Reset
    property Component customDelegate: defaultButtonDelegate
    
    // Button text customization
    property string okButtonText: "OK"
    property string cancelButtonText: "Cancel"
    property string yesButtonText: "Yes"
    property string noButtonText: "No"
    property string helpButtonText: "Help"
    property string resetButtonText: "Reset"
    property string secondaryActionText: "Secondary Action"
    property bool showSecondaryAction: standardButtonTypes & DialogButtonBox.Help
    
    // Navigation properties
    property var dialogButtons: []
    property int currentButtonIndex: -1
    
    // Style customization
    property color positiveButtonColor: ThemeManager.accentColor
    property color neutralButtonColor: ThemeManager.buttonColor
    
    // Custom signals with unique names to avoid conflicts with built-in signals
    signal okButtonClicked()
    signal cancelButtonClicked()
    signal helpButtonClicked()
    signal resetButtonClicked()
    signal secondaryButtonClicked()
    
    title: dialogTitle
    modal: true
    anchors.centerIn: parent
    width: parent.width * 0.85
    height: Math.min(parent.height * 0.7, customContentHeight + customHeaderHeight + customFooterHeight + ThemeManager.spacingLarge * 2)
    
    // Close on Escape
    closePolicy: Popup.CloseOnEscape
    
    // Properties for height calculation - renamed to avoid conflicts
    property real customContentHeight: contentColumn.implicitHeight
    property real customHeaderHeight: headerRect.height
    property real customFooterHeight: buttonLayout.height
    
    // Function to collect all buttons and register them with FocusManager
    function collectFocusItems() {
        console.log("AppDialog: Collecting focusable buttons");
        dialogButtons = [];
        
        // Add buttons based on visibility and if they're defined
        if (okButton && okButton.visible) {
            dialogButtons.push(okButton);
        }
        
        if (yesButton && yesButton.visible) {
            dialogButtons.push(yesButton);
        }
        
        if (cancelButton && cancelButton.visible) {
            dialogButtons.push(cancelButton);
        }
        
        if (noButton && noButton.visible) {
            dialogButtons.push(noButton);
        }
        
        if (helpButton && helpButton.visible) {
            dialogButtons.push(helpButton);
        }
        
        if (resetButton && resetButton.visible) {
            dialogButtons.push(resetButton);
        }
        
        if (secondaryButton && secondaryButton.visible) {
            dialogButtons.push(secondaryButton);
        }
        
        // Initialize the focus manager with our buttons
        if (dialogButtons.length > 0) {
            console.log("AppDialog: Registering " + dialogButtons.length + " buttons with FocusManager");
            FocusManager.initializeFocusItems(dialogButtons);
            
            // Focus the primary action button by default
            if (okButton && okButton.visible) {
                FocusManager.setFocusToItem(okButton);
            } else if (yesButton && yesButton.visible) {
                FocusManager.setFocusToItem(yesButton);
            }
        }
    }
    
    // Register with the focus manager when opened
    onOpened: {
        Qt.callLater(collectFocusItems);
    }
    
    // Reset focus when closing
    onClosed: {
        if (FocusManager) {
            FocusManager.initializeFocusItems([]);
        }
    }
    
    // Default button delegate component using AppButton
    Component {
        id: defaultButtonDelegate
        
        AppButton {
            isFlat: false
            
            // Set background color based on button role
            property color backgroundColor: {
                if (parent.DialogButtonBox.buttonRole === DialogButtonBox.AcceptRole ||
                    parent.DialogButtonBox.buttonRole === DialogButtonBox.YesRole) {
                    return parent.down ? Qt.darker(positiveButtonColor, 1.1) : positiveButtonColor
                } else {
                    return parent.down ? ThemeManager.pressedColor : neutralButtonColor
                }
            }
            
            // Set text color based on button role
            property color buttonTextColor: {
                if (parent.DialogButtonBox.buttonRole === DialogButtonBox.AcceptRole ||
                    parent.DialogButtonBox.buttonRole === DialogButtonBox.YesRole) {
                    return ThemeManager.backgroundColor
                } else {
                    return ThemeManager.textColor
                }
            }
        }
    }
    
    // Background
    background: Rectangle {
        color: ThemeManager.backgroundColor
        border.color: ThemeManager.borderColor
        border.width: ThemeManager.borderWidth
        radius: ThemeManager.borderRadius
    }
    
    // Header with title
    header: Rectangle {
        id: headerRect
        width: parent.width
        height: headerLayout.implicitHeight + ThemeManager.spacingNormal * 2
        color: ThemeManager.headerColor
        
        RowLayout {
            id: headerLayout
            anchors.fill: parent
            anchors.margins: ThemeManager.spacingNormal
            
            Text {
                text: dialogTitle
                font: FontManager.normalBold
                color: ThemeManager.textColor
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
            
            // Close button
            AppRoundButton {
                text: "✕"
                flat: true
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
                onClicked: root.close()
            }
        }
    }
    
    // Content
    contentItem: ColumnLayout {
        id: contentColumn
        width: parent.width
        spacing: ThemeManager.spacingLarge
        
        // Message
        Text {
            text: message
            color: ThemeManager.textColor
            font.pixelSize: FontManager.fontSizeNormal
            font.family: FontManager.primaryFontFamily
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            Layout.margins: ThemeManager.spacingLarge
            visible: message !== ""
        }
        
        // Custom content (optional)
        Item {
            id: customContentContainer
            Layout.fillWidth: true
            Layout.preferredHeight: customContent ? customContent.height : 0
            Layout.margins: ThemeManager.spacingLarge
            visible: customContent !== null
            
            Component.onCompleted: {
                if (customContent) {
                    customContent.parent = customContentContainer;
                    customContent.anchors.fill = customContentContainer;
                }
            }
        }
    }
    
    // Footer with AppButtons instead of DialogButtonBox
    footer: Item {
        width: parent ? parent.width : implicitWidth
        height: buttonLayout.height + ThemeManager.spacingLarge * 2
        
        Rectangle {
            anchors.fill: parent
            color: ThemeManager.backgroundColor
        }
        
        // Count visible buttons for layout decisions
        property bool hasSingleButton: {
            let count = 0;
            if (standardButtonTypes & DialogButtonBox.Ok) count++;
            if (standardButtonTypes & DialogButtonBox.Yes) count++;
            if (standardButtonTypes & DialogButtonBox.Cancel) count++;
            if (standardButtonTypes & DialogButtonBox.No) count++;
            if (standardButtonTypes & DialogButtonBox.Help && !showSecondaryAction) count++;
            if (standardButtonTypes & DialogButtonBox.Reset) count++;
            if (showSecondaryAction) count++;
            return count === 1;
        }
        
        // Center container for single buttons
        Item {
            anchors.centerIn: parent
            width: parent.width * 0.6
            height: parent.height
            visible: parent.hasSingleButton
            
            // OK button (centered when it's the only button)
            AppButton {
                anchors.centerIn: parent
                text: okButtonText
                visible: standardButtonTypes & DialogButtonBox.Ok
                width: 120
                height: ThemeManager.buttonHeight
                backgroundColor: parent.down ? Qt.darker(positiveButtonColor, 1.1) : positiveButtonColor
                textColor: ThemeManager.backgroundColor
                navigable: true
                
                onClicked: {
                    root.close();
                    root.accept();
                    okButtonClicked();
                }
            }
        }
        
        // Row layout for multiple buttons
        RowLayout {
            id: buttonLayout
            width: parent.width
            anchors.centerIn: parent
            spacing: ThemeManager.spacingNormal
            visible: !parent.hasSingleButton
            layoutDirection: Qt.RightToLeft  // Right-aligned buttons
            
            // OK button (right-aligned when multiple buttons are present)
            AppButton {
                id: okButton
                text: okButtonText
                visible: standardButtonTypes & DialogButtonBox.Ok
                Layout.preferredWidth: 100
                backgroundColor: okButton.down ? Qt.darker(positiveButtonColor, 1.1) : positiveButtonColor
                textColor: ThemeManager.backgroundColor
                navigable: true
                
                onClicked: {
                    root.close();
                    root.accept();
                    okButtonClicked();
                }
            }
            
            // Yes button
            AppButton {
                id: yesButton
                text: yesButtonText
                visible: standardButtonTypes & DialogButtonBox.Yes
                Layout.preferredWidth: 100
                backgroundColor: yesButton.down ? Qt.darker(positiveButtonColor, 1.1) : positiveButtonColor
                textColor: ThemeManager.backgroundColor
                navigable: true
                
                onClicked: {
                    root.close();
                    root.accept();
                    okButtonClicked();
                }
            }
            
            // Cancel button
            AppButton {
                id: cancelButton
                text: cancelButtonText
                visible: standardButtonTypes & DialogButtonBox.Cancel
                Layout.preferredWidth: 100
                navigable: true
                
                onClicked: {
                    root.close();
                    root.reject();
                }
            }
            
            // No button
            AppButton {
                id: noButton
                text: noButtonText
                visible: standardButtonTypes & DialogButtonBox.No
                Layout.preferredWidth: 100
                navigable: true
                
                onClicked: {
                    root.close();
                    root.reject();
                }
            }
            
            // Help button
            AppButton {
                id: helpButton
                text: helpButtonText
                visible: standardButtonTypes & DialogButtonBox.Help
                Layout.preferredWidth: 100
                navigable: true
                
                onClicked: {
                    helpButtonClicked();
                }
            }
            
            // Reset button
            AppButton {
                id: resetButton
                text: resetButtonText
                visible: standardButtonTypes & DialogButtonBox.Reset
                Layout.preferredWidth: 100
                navigable: true
                
                onClicked: {
                    resetButtonClicked();
                }
            }
            
            // Secondary action button
            AppButton {
                id: secondaryButton
                text: secondaryActionText
                visible: showSecondaryAction
                Layout.preferredWidth: 150
                navigable: true
                
                onClicked: {
                    secondaryButtonClicked();
                }
            }
        }
    }
} 
