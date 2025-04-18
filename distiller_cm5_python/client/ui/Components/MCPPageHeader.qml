import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: headerArea

    property string title: "Title"
    property string subtitle: "Subtitle"
    property bool compact: false

    implicitHeight: headerColumn.height

    // Fixed header to avoid recalculation during scrolling
    Column {
        id: headerColumn

        width: parent.width
        spacing: compact ? 0 : ThemeManager.spacingSmall

        Text {
            width: parent.width
            text: title.toUpperCase()
            font: FontManager.title
            color: ThemeManager.textColor
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            elide: Text.ElideRight
            padding: compact ? ThemeManager.spacingSmall / 2 : ThemeManager.spacingSmall
        }

        Text {
            width: parent.width
            text: subtitle
            font: compact ? FontManager.small : FontManager.medium
            color: ThemeManager.secondaryTextColor
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            elide: Text.ElideRight
            padding: compact ? ThemeManager.spacingSmall / 2 : ThemeManager.spacingSmall
            bottomPadding: compact ? ThemeManager.spacingSmall / 2 : ThemeManager.spacingNormal
            visible: text.length > 0
        }

    }

}
