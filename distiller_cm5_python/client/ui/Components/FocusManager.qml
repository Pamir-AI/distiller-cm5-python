import QtQml 2.15
pragma Singleton

// Focus management for 3-button navigation
QtObject {
    id: focusManagerSingleton

    property var currentFocusItems: []
    property int currentFocusIndex: -1
    property var currentScrollView: null
    property bool scrollModeActive: false
    property var scrollTargetItem: null
    property bool lockFocus: false
    property int scrollStep: 60

    // Signal when focus changes
    signal focusChanged(var focusedItem)
    
    function setItemFocus(item, value) {
        if (item && typeof item.visualFocus !== 'undefined') {
            item.visualFocus = value;
        }
    }

    function clearFocus() {
        for (var i = 0; i < currentFocusItems.length; i++) {
            setItemFocus(currentFocusItems[i], false);
        }
    }

    function initializeFocusItems(items, scrollView) {
        currentFocusItems = items.slice();
        currentFocusIndex = items.length > 0 ? 0 : -1;
        currentScrollView = scrollView || null;
        
        if (currentFocusIndex >= 0 && currentFocusItems[currentFocusIndex]) {
            setItemFocus(currentFocusItems[currentFocusIndex], true);
            setFocusToItem(currentFocusItems[currentFocusIndex]);
        }
    }

    function setFocusToItem(item) {
        if (!item) return;
        var foundIndex = -1;
        for (var i = 0; i < currentFocusItems.length; i++) {
            if (currentFocusItems[i] === item) {
                foundIndex = i;
                break;
            }
        }
        if (foundIndex === -1) return;
        for (var j = 0; j < currentFocusItems.length; j++) {
            setItemFocus(currentFocusItems[j], false);
        }
        
        currentFocusIndex = foundIndex;
        setItemFocus(item, true);
        if (item.forceActiveFocus && typeof item.forceActiveFocus === "function") {
            item.forceActiveFocus();
        }
        focusChanged(item);
    }

    function enterScrollMode(item) {
        if (!item) return;
        scrollModeActive = true;
        scrollTargetItem = item;
    }

    function exitScrollMode() {
        if (scrollTargetItem) {
            scrollTargetItem.scrollModeActive = false;
            if (scrollTargetItem.scrollModeChanged) {
                scrollTargetItem.scrollModeChanged(false);
            }
            scrollTargetItem = null;
        }
        scrollModeActive = false;
    }

    function moveFocusUp() {
        if (scrollModeActive && scrollTargetItem) {
            if (scrollTargetItem.contentY !== undefined) {
                var newY = Math.max(0, scrollTargetItem.contentY - scrollStep);
                scrollTargetItem.contentY = newY;
            }
            return;
        }
        if (currentFocusItems.length === 0) return;
        
        if (currentFocusIndex > 0) {
            currentFocusIndex--;
        } else {
            currentFocusIndex = currentFocusItems.length - 1;
        }
        setFocusToItem(currentFocusItems[currentFocusIndex]);
    }

    function moveFocusDown() {
        if (scrollModeActive && scrollTargetItem) {
            if (scrollTargetItem.contentY !== undefined) {
                var maxY = Math.max(0, scrollTargetItem.contentHeight - scrollTargetItem.height);
                var newY = Math.min(maxY, scrollTargetItem.contentY + scrollStep);
                scrollTargetItem.contentY = newY;
            }
            return;
        }
        if (currentFocusItems.length === 0) return;
        
        if (currentFocusIndex < currentFocusItems.length - 1) {
            currentFocusIndex++;
        } else {
            currentFocusIndex = 0;
        }
        setFocusToItem(currentFocusItems[currentFocusIndex]);
    }

    function handleEnterKey() {
        if (currentFocusItems.length === 0 || currentFocusIndex < 0) return;
        
        var item = currentFocusItems[currentFocusIndex];
        if (!item) return;
        if (item.objectName === "conversationView" || (item.navigable && item.scrollModeActive !== undefined)) {
            if (!scrollModeActive) {
                enterScrollMode(item);
                if (item.scrollModeChanged) {
                    item.scrollModeActive = true;
                    item.scrollModeChanged(true);
                }
            }
            return;
        }
        if (item.activate && typeof item.activate === "function") {
            item.activate();
        } else if (item.clicked && typeof item.clicked === "function") {
            item.clicked();
        } else if (item.toggle && typeof item.toggle === "function") {
            item.toggle();
        }
    }

    function handleEnterKeyPress() {
        if (currentFocusItems.length === 0 || currentFocusIndex < 0) return;
        
        var item = currentFocusItems[currentFocusIndex];
        if (!item) return;
        
        if (item.onKeyPress && typeof item.onKeyPress === "function") {
            item.onKeyPress();
        } else {
            handleEnterKey();
        }
    }
    
    function handleEnterKeyRelease() {
        if (currentFocusItems.length === 0 || currentFocusIndex < 0) return;
        
        var item = currentFocusItems[currentFocusIndex];
        if (!item) return;
        
        if (item.onKeyRelease && typeof item.onKeyRelease === "function") {
            item.onKeyRelease();
        }
    }
}
