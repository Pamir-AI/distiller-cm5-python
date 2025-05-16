import QtQuick

// Base component for items that can be navigated with Up/Down/Enter keys
Item {
    // Override in derived components
    // Override in derived components
    // Make the component ready for focus
    // Component.onCompleted: {
    //     if (navigable) {
    //         console.log("NavigableItem: Initialized with navigable=true");
    //     }
    // }
    // console.log("NavigableItem: Forcing focus");

    id: navigableItem

    // Navigation properties
    property bool navigable: true
    // Whether this item can be navigated to
    property bool visualFocus: activeFocus
    // Visual state
    property bool highlighted: visualFocus
    property color backgroundColor: highlighted ? ThemeManager.textColor : ThemeManager.backgroundColor
    property color textColor: highlighted ? ThemeManager.backgroundColor : ThemeManager.textColor
    // For sliders and other value adjustments
    property bool isAdjustable: false
    property real adjustmentStep: 0.1

    // Function that will be called when Enter is pressed on this item
    signal clicked()

    // Support for value adjustment (for sliders, etc.)
    function increaseValue() {
    }

    function decreaseValue() {
    }

    // Explicit key handling for this item
    Keys.onReturnPressed: function(event) {
        if (navigable) {
            // console.log("NavigableItem: Return key pressed on item");
            clicked();
            event.accepted = true;
        }
    }
    Keys.onEnterPressed: function(event) {
        if (navigable) {
            // console.log("NavigableItem: Enter key pressed on item");
            clicked();
            event.accepted = true;
        }
    }
    // Handle property changes
    onVisualFocusChanged: {
        // console.log("NavigableItem: visualFocus changed to: " + visualFocus + " for " + (parent ? parent.objectName || "unnamed" : "no parent"));
        if (visualFocus)
            forceActiveFocus();
    }
    // Handle focused state
    onActiveFocusChanged: {
        // console.log("NavigableItem: activeFocus changed to: " + activeFocus + " for " + (parent ? parent.objectName || "unnamed" : "no parent"));
    }

    // Static focus indicator optimized for e-ink
    Rectangle {
        id: focusIndicator

        anchors.fill: parent
        color: ThemeManager.transparentColor
        border.width: parent.visualFocus ? ThemeManager.borderWidth * 2 : 0 // Increased border width
        border.color: ThemeManager.textColor
        radius: parent.width
        visible: parent.visualFocus
        opacity: 1
    }

}
