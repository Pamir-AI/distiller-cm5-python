import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

NavigableItem {
    id: root

    property string title: "Section"
    property bool collapsible: false
    property bool collapsed: false
    property bool showBorder: true
    property bool compact: true
    property int contentMargins: ThemeManager.spacingNormal * 1.25

    // Add bottom margin for better visual separation
    property int bottomMargin: ThemeManager.spacingNormal

    height: headerContainer.height + (collapsed ? 0 : contentArea.height) + bottomMargin
    implicitHeight: height
    
    // Visual feedback for focused state
    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.width: root.visualFocus ? 2 : 0
        border.color: ThemeManager.accentColor
        visible: root.visualFocus
        opacity: 0.8
        radius: ThemeManager.borderRadius
        z: 1
    }

    // Background rectangle for entire section
    Rectangle {
        id: sectionBackground
        anchors.fill: parent
        anchors.bottomMargin: bottomMargin
        color: "transparent"

        // Add subtle shadow for better visual separation (optional)
        Rectangle {
            id: shadowEffect
            anchors.fill: parent
            anchors.topMargin: -1
            anchors.leftMargin: -1
            anchors.rightMargin: -1
            anchors.bottomMargin: 2
            color: "transparent"
            border.color: Qt.rgba(0, 0, 0, 0.05)
            border.width: 1
            radius: ThemeManager.borderRadius + 1
            z: -1
            visible: showBorder
        }
    }

    // Section header
    Rectangle {
        id: headerContainer

        width: parent.width
        height: headerRow.height + (compact ? ThemeManager.spacingNormal * 1.25 : ThemeManager.spacingNormal * 1.5)
        color: root.visualFocus ? Qt.lighter(ThemeManager.headerColor, 1.1) : ThemeManager.headerColor
        border.color: showBorder ? ThemeManager.borderColor : "transparent"
        border.width: showBorder ? ThemeManager.borderWidth : 0
        radius: ThemeManager.borderRadius

        Row {
            id: headerRow

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: contentMargins
            anchors.rightMargin: contentMargins
            spacing: ThemeManager.spacingSmall

            Text {
                id: sectionTitle

                width: collapsible ? parent.width - collapseIcon.width - ThemeManager.spacingSmall : parent.width
                height: contentHeight
                text: title
                color: ThemeManager.textColor
                font.pixelSize: compact ? FontManager.fontSizeMedium : FontManager.fontSizeLarge
                font.family: FontManager.primaryFontFamily
                font.bold: true
                elide: Text.ElideRight
                opacity: root.visualFocus ? 1.0 : 0.9
            }

            Text {
                id: collapseIcon

                visible: collapsible
                width: visible ? implicitWidth : 0
                text: collapsed ? "+" : "-"
                color: ThemeManager.textColor
                font.pixelSize: FontManager.fontSizeLarge
                font.family: FontManager.primaryFontFamily
                font.bold: true
            }
        }

        MouseArea {
            anchors.fill: parent
            enabled: collapsible
            onClicked: {
                if (collapsible) {
                    collapsed = !collapsed;
                }
            }
        }
    }

    // Content area
    Rectangle {
        id: contentArea

        anchors.top: headerContainer.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        // No top margin since we're using a continuous look
        height: contentContainer.height + contentMargins * 2
        visible: !collapsed
        opacity: collapsed ? 0 : 1

        color: ThemeManager.backgroundColor
        border.color: showBorder ? ThemeManager.borderColor : "transparent"
        border.width: showBorder ? ThemeManager.borderWidth : 0
        // Only round the bottom corners
        radius: ThemeManager.borderRadius

        // Special treatment for top edges to connect with header
        Rectangle {
            id: connectionRect
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 4
            color: parent.color

            // Top-left overlap rectangle (hide top-left rounded corner)
            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                width: parent.parent.radius * 2
                height: parent.height
                color: parent.color
            }

            // Top-right overlap rectangle (hide top-right rounded corner)
            Rectangle {
                anchors.right: parent.right
                anchors.top: parent.top
                width: parent.parent.radius * 2
                height: parent.height
                color: parent.color
            }
        }

        Behavior on opacity {
            NumberAnimation {
                duration: ThemeManager.animationDuration / 2
            }
        }

        // This is the actual content container where child items will be placed
        Item {
            id: contentContainer

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: contentMargins
            height: childrenRect.height

            // Child items are placed here with the default layout
        }
    }
    
    // Function to get navigable controls - to be implemented by children
    function getNavigableControls() {
        return [];
    }
    
    // Handle activating this section
    onClicked: {
        console.log("AppSection: " + title + " clicked");
        
        // Try to focus the first control in this section
        var controls = getNavigableControls();
        if (controls.length > 0) {
            console.log("AppSection: Focusing first control in " + title);
            controls[0].forceActiveFocus();
        } else if (collapsible) {
            collapsed = !collapsed;
        }
    }

    // This states that any child items added to this component should be parented to contentContainer
    default property alias content: contentContainer.data
}
