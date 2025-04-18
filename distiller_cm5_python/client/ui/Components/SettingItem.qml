import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

RowLayout {
    id: root
    
    property string label: "SETTING"
    property bool showToggle: true
    property bool toggleValue: false
    property real rowHeight: 48
    
    // Rename signal to avoid conflict with auto-generated toggleValueChanged signal
    signal toggleChanged(bool newValue)
    
    Layout.fillWidth: true
    Layout.preferredHeight: rowHeight
    spacing: ThemeManager.spacingLarge
    Layout.topMargin: ThemeManager.spacingNormal
    
    // Label
    Text {
        text: label
        font.pixelSize: FontManager.fontSizeNormal
        font.family: FontManager.primaryFontFamily
        color: ThemeManager.secondaryTextColor
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignVCenter
    }
    
    // Toggle switch (visible only when showToggle is true)
    AppToggleSwitch {
        visible: showToggle
        value: toggleValue
        onValueToggled: function(newValue) {
            root.toggleChanged(newValue)
        }
    }
    
    // Default property alias to allow inserting custom content
    default property alias content: customContent.data
    
    // Container for custom content (used when toggle is hidden)
    Item {
        id: customContent
        visible: !showToggle
        Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
    }
} 