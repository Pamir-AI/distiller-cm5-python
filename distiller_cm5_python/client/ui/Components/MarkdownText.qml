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

        // Style the markdown with CSS
        property string cssStyle: "
            h1, h2, h3, h4, h5, h6 { margin: 0.2em 0; }
            h1 { font-size: 1.4em; }
            h2 { font-size: 1.3em; }
            h3 { font-size: 1.2em; }
            h4 { font-size: 1.1em; }
            p { margin: 0.2em 0; }
            pre {
                background-color: rgba(0,0,0,0.05);
                padding: 0.3em;
                margin: 0.3em 0;
            }
            code {
                font-family: monospace;
                background-color: rgba(0,0,0,0.05);
                padding: 0.1em 0.2em;
            }
            blockquote {
                margin: 0.3em 0;
                padding-left: 0.5em;
                border-left: 2px solid " + markdownTextContainer.textColor + ";
                opacity: 0.8;
            }
            ul, ol { margin: 0.2em 0 0.2em 1em; padding: 0; }
            table {
                border-collapse: collapse;
                margin: 0.3em 0;
                width: 100%;
            }
            th, td {
                border: 1px solid rgba(0,0,0,0.2);
                padding: 0.2em;
            }
            th {
                font-weight: bold;
                background-color: rgba(0,0,0,0.05);
            }
            a {
                text-decoration: none;
                font-weight: bold;
                color: " + markdownTextContainer.textColor + ";
            }
            img {
                max-width: 100%;
                height: auto;
            }
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
