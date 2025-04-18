import QtQuick 2.15
import QtQuick.Controls 2.15

Text {
    id: statusText

    property bool isLoading: false
    property int itemCount: 0

    color: ThemeManager.textColor
    font: FontManager.normal
    horizontalAlignment: Text.AlignHCenter
    width: parent.width
    padding: ThemeManager.spacingSmall
    text: isLoading ? "Loading servers..." : (itemCount > 0 ? "Found " + itemCount + " servers" : "No servers found")
}
