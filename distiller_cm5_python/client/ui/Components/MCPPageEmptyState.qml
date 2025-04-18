import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Column {
    id: emptyState

    property string title: "No items found"
    property string message: "Please check and try again"
    property bool compact: false

    spacing: ThemeManager.spacingSmall
    width: parent.width

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width
        text: title.toUpperCase()
        color: ThemeManager.textColor
        font: compact ? FontManager.normal : FontManager.heading
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.Wrap
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width
        text: message
        color: ThemeManager.secondaryTextColor
        font: compact ? FontManager.small : FontManager.normal
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.Wrap
    }

}
