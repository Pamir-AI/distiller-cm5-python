import QtQuick

NavigableItem {
    id: root

    property bool isFlat: false
    property bool useFixedHeight: true
    property string text: ""
    property color backgroundColor: root.visualFocus ? ThemeManager.textColor : ThemeManager.backgroundColor
    property color textColor: root.visualFocus ? ThemeManager.backgroundColor : ThemeManager.textColor
    property color black: ThemeManager.black
    property int fontSize: FontManager.fontSizeNormal
    property int buttonRadius: ThemeManager.borderRadius
    // Define standalone pressed property for visual states
    property bool pressed: false

    width: parent ? parent.width : implicitWidth
    height: useFixedHeight ? ThemeManager.buttonHeight : implicitHeight
    // Add keyboard handling for Enter/Return
    Keys.onReturnPressed: function() {
        clicked();
    }

    // Style properties
    Rectangle {
        id: backgroundRect

        anchors.fill: parent
        color: root.backgroundColor
        border.color: ThemeManager.black
        border.width: root.visualFocus ? ThemeManager.borderWidth * 2 : ThemeManager.borderWidth // Always show border for better visibility on E-Ink
        radius: buttonRadius
    }

    Text {
        anchors.centerIn: parent
        text: root.text
        color: root.textColor
        font.pixelSize: root.fontSize
        font.family: FontManager.primaryFontFamily
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

}
