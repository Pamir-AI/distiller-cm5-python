pragma Singleton

import QtQuick 2.15

// FocusManager provides application-wide focus management
// enabling navigation with just Up, Down, and Enter keys
QtObject {
    id: focusManager
    
    // Current navigation mode
    property int currentMode: FocusManager.normalMode
    
    // Navigation modes
    readonly property int normalMode: 0     // Standard navigation between focusable items
    readonly property int sliderMode: 1     // Adjusting slider values
    readonly property int textInputMode: 2  // Text input editing
    
    // Focus navigation arrays for different contexts
    property var currentFocusItems: []      // Current array of focusable items
    property int currentFocusIndex: -1      // Index of currently focused item
    
    // Current scroll view - can be set by pages to enable scroll support
    property var currentScrollView: null
    
    // Scroll step size
    property int scrollStep: 40
    
    // Signal when focus changes 
    signal focusChanged(var focusedItem)
    
    // Initialize/update the array of focusable items
    function initializeFocusItems(items, scrollView) {
        console.log("FocusManager: Initializing focus items, count: " + items.length);
        currentFocusItems = items.slice() // Make a copy of the array
        currentFocusIndex = items.length > 0 ? 0 : -1
        
        // Store the scroll view reference if provided
        if (scrollView) {
            currentScrollView = scrollView;
            console.log("FocusManager: Registered scroll view for combined navigation");
        } else {
            currentScrollView = null;
        }
        
        // Set initial focus
        if (currentFocusIndex >= 0 && currentFocusItems[currentFocusIndex]) {
            console.log("FocusManager: Setting initial focus to item at index " + currentFocusIndex);
            currentFocusItems[currentFocusIndex].isActiveItem = true;
            setFocusToItem(currentFocusItems[currentFocusIndex]);
        }
    }
    
    // Focus on a specific item and update indices
    function setFocusToItem(item) {
        if (!item) {
            console.error("FocusManager: Attempted to focus on null item");
            return;
        }
        
        // Find the item's index
        let foundIndex = -1;
        for (var i = 0; i < currentFocusItems.length; i++) {
            if (currentFocusItems[i] === item) {
                foundIndex = i;
                break;
            }
        }
        
        if (foundIndex === -1) {
            console.error("FocusManager: Item not found in focusable items list");
            return;
        }
        
        // Reset active state on all items
        for (var j = 0; j < currentFocusItems.length; j++) {
            if (currentFocusItems[j]) {
                currentFocusItems[j].isActiveItem = false;
            }
        }
        
        // Update current index and set active state
        currentFocusIndex = foundIndex;
        item.isActiveItem = true;
        
        // If we have a scroll view, try to ensure this item is visible
        if (currentScrollView && item.parent) {
            ensureItemVisible(item);
        }
        
        // Set focus to the item
        console.log("FocusManager: Setting focus to item at index " + currentFocusIndex);
        item.forceActiveFocus();
        focusChanged(item);
    }
    
    // Ensure an item is visible within the scroll view
    function ensureItemVisible(item) {
        if (!currentScrollView || !item) return;
        
        try {
            // Get item position relative to the scrollview's content
            var itemGlobalPos = item.mapToItem(currentScrollView.contentItem, 0, 0);
            var itemY = itemGlobalPos.y;
            var itemHeight = item.height;
            
            // Calculate visible range of the scroll view
            var scrollViewY = currentScrollView.contentItem.contentY;
            var scrollViewHeight = currentScrollView.height;
            var viewBottom = scrollViewY + scrollViewHeight;
            
            console.log("Item position: " + itemY + ", height: " + itemHeight);
            console.log("Scroll view position: " + scrollViewY + ", height: " + scrollViewHeight);
            
            // Check if item is outside the visible area
            if (itemY < scrollViewY) {
                // Item is above visible area, scroll up
                scrollToPosition(itemY);
            } else if ((itemY + itemHeight) > viewBottom) {
                // Item is below visible area, scroll down
                scrollToPosition(itemY + itemHeight - scrollViewHeight);
            }
        } catch (e) {
            console.error("Error ensuring item visibility: " + e);
        }
    }
    
    // Scroll to a specific position
    function scrollToPosition(yPos) {
        if (!currentScrollView) return;
        
        try {
            // Make sure we don't exceed content bounds
            var maxY = Math.max(0, currentScrollView.contentItem.contentHeight - currentScrollView.height);
            var targetY = Math.max(0, Math.min(maxY, yPos));
            
            // Use animation for smooth scrolling
            if (currentScrollView.scrollAnimation) {
                currentScrollView.scrollAnimation.stop();
                currentScrollView.scrollAnimation.from = currentScrollView.contentItem.contentY;
                currentScrollView.scrollAnimation.to = targetY;
                currentScrollView.scrollAnimation.start();
            } else {
                currentScrollView.contentItem.contentY = targetY;
            }
        } catch (e) {
            console.error("Error scrolling to position: " + e);
        }
    }
    
    // Move focus up
    function moveFocusUp() {
        console.log("FocusManager: Moving focus up, current index: " + currentFocusIndex);
        if (currentMode === sliderMode) {
            // In slider mode, increase the value
            if (currentFocusItems[currentFocusIndex] && currentFocusItems[currentFocusIndex].increaseValue) {
                currentFocusItems[currentFocusIndex].increaseValue();
            }
            return;
        }
        
        // Make sure we have focusable items before proceeding
        if (currentFocusItems.length === 0) {
            console.log("FocusManager: No focusable items available");
            // If we have a scroll view but no focusable items, just scroll
            if (currentScrollView) {
                scrollUp();
            }
            return;
        }
        
        // Priority #1: Navigate to previous item first (if not at first item)
        if (currentFocusIndex > 0) {
            currentFocusIndex--;
            setFocusToItem(currentFocusItems[currentFocusIndex]);
            return;
        }
        
        // Priority #2: If at first item, try to scroll if not at top
        if (currentScrollView && currentScrollView.contentItem.contentY > 0) {
            scrollUp();
            return;
        }
        
        // Priority #3: If at first item and top of scroll, wrap to last item
        currentFocusIndex = currentFocusItems.length - 1;
        setFocusToItem(currentFocusItems[currentFocusIndex]);
    }
    
    // Helper function to scroll up
    function scrollUp() {
        if (!currentScrollView) return;
        
        var newY = Math.max(0, currentScrollView.contentItem.contentY - scrollStep);
        if (currentScrollView.scrollAnimation) {
            currentScrollView.scrollAnimation.stop();
            currentScrollView.scrollAnimation.from = currentScrollView.contentItem.contentY;
            currentScrollView.scrollAnimation.to = newY;
            currentScrollView.scrollAnimation.start();
        } else {
            currentScrollView.contentItem.contentY = newY;
        }
    }
    
    // Move focus down
    function moveFocusDown() {
        console.log("FocusManager: Moving focus down, current index: " + currentFocusIndex);
        if (currentMode === sliderMode) {
            // In slider mode, decrease the value
            if (currentFocusItems[currentFocusIndex] && currentFocusItems[currentFocusIndex].decreaseValue) {
                currentFocusItems[currentFocusIndex].decreaseValue();
            }
            return;
        }
        
        // Make sure we have focusable items before proceeding
        if (currentFocusItems.length === 0) {
            console.log("FocusManager: No focusable items available");
            // If we have a scroll view but no focusable items, just scroll
            if (currentScrollView) {
                scrollDown();
            }
            return;
        }
        
        // Priority #1: Navigate to next item first (if not at last item)
        if (currentFocusIndex < currentFocusItems.length - 1) {
            currentFocusIndex++;
            setFocusToItem(currentFocusItems[currentFocusIndex]);
            return;
        }
        
        // Priority #2: If at last item, try to scroll if not at bottom
        if (currentScrollView) {
            var maxY = Math.max(0, currentScrollView.contentItem.contentHeight - currentScrollView.height);
            if (currentScrollView.contentItem.contentY < maxY) {
                scrollDown();
                return;
            }
        }
        
        // Priority #3: If at last item and bottom of scroll, wrap to first item
        currentFocusIndex = 0;
        setFocusToItem(currentFocusItems[currentFocusIndex]);
    }
    
    // Helper function to scroll down
    function scrollDown() {
        if (!currentScrollView) return;
        
        var maxY = Math.max(0, currentScrollView.contentItem.contentHeight - currentScrollView.height);
        var newY = Math.min(maxY, currentScrollView.contentItem.contentY + scrollStep);
        if (currentScrollView.scrollAnimation) {
            currentScrollView.scrollAnimation.stop();
            currentScrollView.scrollAnimation.from = currentScrollView.contentItem.contentY;
            currentScrollView.scrollAnimation.to = newY;
            currentScrollView.scrollAnimation.start();
        } else {
            currentScrollView.contentItem.contentY = newY;
        }
    }
    
    // Switch to slider adjustment mode
    function enterSliderMode() {
        currentMode = sliderMode;
    }
    
    // Switch to text input mode
    function enterTextInputMode() {
        currentMode = textInputMode;
    }
    
    // Return to normal navigation mode
    function exitSpecialMode() {
        currentMode = normalMode;
    }
    
    // Handle Enter key press based on current mode
    function handleEnterKey() {
        console.log("FocusManager: Handling Enter key, current index: " + currentFocusIndex);
        if (currentFocusItems.length === 0 || currentFocusIndex < 0) {
            console.log("FocusManager: No item focused");
            return;
        }
        
        var item = currentFocusItems[currentFocusIndex];
        if (!item) {
            console.error("FocusManager: Focused item is null");
            return;
        }
        
        if (currentMode === normalMode) {
            // Normal mode - activate the current item
            console.log("FocusManager: Activating item");
            if (item.clicked && typeof item.clicked === "function") {
                item.clicked();
            } else if (item.toggle && typeof item.toggle === "function") {
                item.toggle();
            } else if (item.activated && typeof item.activated === "function") {
                item.activated();
            }
        } else if (currentMode === sliderMode) {
            // Exit slider mode
            console.log("FocusManager: Exiting slider mode");
            exitSpecialMode();
        }
    }
} 
