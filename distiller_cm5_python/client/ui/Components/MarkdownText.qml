import QtQuick

// Use Item as container to handle the background
Item {
    id: markdownTextContainer

    // Properties
    property string markdownText: ""
    property font textFont: FontManager.normal
    property color textColor: ThemeManager.textColor

    // Make the container fill its parent
    implicitWidth: markdownTextEdit.implicitWidth
    implicitHeight: markdownTextEdit.implicitHeight

    // Background rectangle (instead of setting background property)
    Rectangle {
        anchors.fill: parent
        color: ThemeManager.transparentColor
        border.color: ThemeManager.transparentColor
    }

    // The actual TextEdit
    TextEdit {
        id: markdownTextEdit

        // Lightweight CSS for embedded performance
        property string cssStyle: "
            h1, h2, h3, h4, h5, h6 { margin: 0.1em 0; }
            h1 { font-size: 1.3em; }
            h2 { font-size: 1.2em; }
            h3 { font-size: 1.1em; }
            p { margin: 0.1em 0; }
            pre { padding: 0.2em; margin: 0.2em 0; }
            code { font-family: monospace; }
            blockquote { margin: 0.2em 0; padding-left: 0.3em; }
            ul, ol { margin: 0.1em 0 0.1em 0.8em; }
        "

        // Fill the container
        anchors.fill: parent
        // Configuration
        text: markdownTextContainer.markdownText
        textFormat: TextEdit.MarkdownText
        readOnly: true
        wrapMode: TextEdit.Wrap
        selectByMouse: true
        selectByKeyboard: false
        // Styling
        font: markdownTextContainer.textFont
        color: markdownTextContainer.textColor
        // Set the CSS style sheet
        Component.onCompleted: {
            textDocument.defaultStyleSheet = cssStyle;
        }

        // Make background transparent
        Rectangle {
            z: -1
            anchors.fill: parent
            color: ThemeManager.transparentColor
        }

    }

}
