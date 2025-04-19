# Three-Key Navigation System

This application has been refactored to support navigation using only three keys:
- Up
- Down
- Enter

## Navigation Framework

The application now uses a global focus management system that handles navigation between UI elements. This system is implemented in `FocusManager.qml` and works with all UI components that extend the `NavigableItem` base component.

## How to Navigate

### Basic Navigation
- **Up Key**: Move focus to the previous item in the navigation order
- **Down Key**: Move focus to the next item in the navigation order
- **Enter Key**: Activate the currently focused item (click buttons, toggle switches, etc.)

### Special Navigation Modes

#### Slider Mode
When a slider is focused:
1. Press **Enter** to enter slider adjustment mode
2. Use **Up** to increase value
3. Use **Down** to decrease value
4. Press **Enter** again to exit slider adjustment mode

## Components Supporting Three-Key Navigation

The following components have been updated to support three-key navigation:

- `AppButton`: Standard buttons
- `AppToggleSwitch`: Toggle switches
- `CustomSlider`: Value sliders
- `ServerGridCard`: Server selection cards

## Page Navigation

Each page in the application collects its focusable items when loaded and registers them with the FocusManager. The focus order follows a logical top-to-bottom layout, with navigation wrapping around from the last item to the first.

## Focus Indication

All focusable elements provide visual feedback when they have focus:
- Highlighted background color
- Border emphasis
- Text color changes

## Adding New Components

To make a new component work with the three-key navigation system:

1. Extend from `NavigableItem` instead of `Item` or other base components
2. Set the `navigable: true` property
3. Implement the `clicked()` signal for activation
4. For value adjustment components, implement `increaseValue()` and `decreaseValue()` functions

## Page Implementation

To make a page work with the navigation system:

1. Add a `focusableItems` property to store navigable elements
2. Implement a `collectFocusItems()` function that populates this array
3. Call `FocusManager.initializeFocusItems(focusableItems)` in this function
4. Make sure all interactive elements are included in the focusable items array 
