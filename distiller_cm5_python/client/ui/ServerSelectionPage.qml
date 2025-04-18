import "Components"
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

PageBase {
    id: serverSelectionPage
    
    pageName: "Server Selection"

    property var availableServers: []
    property bool isLoading: true
    property real cardSize: 200
    property real gridSpacing: 16

    signal serverSelected(string serverPath)

    // Add lifecycle logging
    onVisibleChanged: console.log("--- ServerSelectionPage visible changed: " + visible)
    onActiveFocusChanged: console.log("--- ServerSelectionPage activeFocus changed: " + activeFocus)

    Component.onCompleted: {
        console.log("--- ServerSelectionPage Component.onCompleted ---"); // Log completion
        // Call parent's onCompleted first
        // Use a small delay to ensure the component is fully constructed before requesting servers
        serverInitTimer.start();

        // Explicitly force focus when the page completes loading
        forceActiveFocus();
        console.log("--- ServerSelectionPage attempting forceActiveFocus() onCompleted ---");

        // Initial focus will be handled in onAvailableServersChanged or when page becomes active
    }
    
    // Prevent operations when being destroyed
    Component.onDestruction: {
        console.log("Server selection page being destroyed");
        // Stop any pending operations
        if (serverInitTimer.running)
            serverInitTimer.stop();
    }

    // Connect to the bridge signals
    Connections {
        function onAvailableServersChanged(servers) {
            console.log("--- ServerSelectionPage onAvailableServersChanged RECEIVED ---"); // Log signal reception
            console.log("Received servers: " + servers.length);
            availableServers = servers;
            isLoading = false;

            // Update focus after servers are loaded, using callLater for safety
            Qt.callLater(function() {
                if (serverSelectionPage.visible) { 
                    if (availableServers.length > 0) { 
                        console.log("Attempting to set focus on first list item (callLater, visible only)...");
                        serverListView.currentIndex = 0; // Set current index for ListView
                        // Ensure item exists and force focus on the list itself
                        if (serverListView.count > 0) { 
                           serverListView.forceActiveFocus(); 
                           positionViewAtIndex(0, ListView.Beginning); // Scroll to top
                           console.log("Focus hopefully set on ListView, index 0.");
                        } else {
                           console.log("ListView count is 0, cannot set focus");
                           // Fallback to refresh button if list view somehow empty
                           if (refreshButton.visible) refreshButton.forceActiveFocus();
                        }
                    } else if (refreshButton.visible) {
                        console.log("Attempting to set focus on refresh button (callLater)...");
                        // If no servers, focus the refresh button
                        refreshButton.forceActiveFocus();
                        console.log("Focus hopefully set on refresh button.");
                    }
                }
            });
        }

        target: bridge
    }

    // Timer to delay server loading to prevent component creation during destruction
    Timer {
        id: serverInitTimer

        interval: 100
        repeat: false
        running: false
        onTriggered: {
            if (serverSelectionPage.visible && serverSelectionPage.width > 0)
                bridge.getAvailableServers();
        }
    }

    // Loading indicator simplified for e-ink
    LoadingIndicator {
        anchors.fill: parent
        isLoading: serverSelectionPage.isLoading
        z: 10 // Ensure it's above other content
    }

    // Top margin padding area
    Item {
        id: topMargin
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: ThemeManager.spacingLarge // Add substantial top margin
    }

    // Header area
    MCPPageHeader {
        id: headerArea
        
        anchors.top: topMargin.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: implicitHeight
        z: 2 // Ensure header stays above content
        
        title: "SELECT MCP SERVER"
        subtitle: "Choose a server to connect to"
        compact: true
    }

    // Main content column
    ColumnLayout {
        id: contentColumn
        anchors.top: headerArea.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: footerArea.top
        anchors.topMargin: 1 // Connect with header
        anchors.leftMargin: ThemeManager.spacingSmall // Reduced left margin
        anchors.rightMargin: ThemeManager.spacingSmall // Reduced right margin
        anchors.bottomMargin: ThemeManager.spacingSmall
        spacing: ThemeManager.spacingLarge // Keep spacing between elements
        
        // Add top padding
        Item {
            width: parent.width
            height: ThemeManager.spacingSmall
        }
        
        // Empty state message for no servers
        MCPPageEmptyState {
            width: parent.width
            height: serverListView.height - ThemeManager.spacingLarge * 2
            visible: !serverSelectionPage.isLoading && availableServers.length === 0
            title: "NO SERVERS FOUND"
            message: "Please ensure MCP servers are available\nin the mcp_server directory"
            compact: true
        }
        
        // --- Add ListView for Servers --- 
        ListView {
            id: serverListView
            Layout.fillWidth: true
            Layout.fillHeight: true // Fill available vertical space in ColumnLayout
            visible: availableServers.length > 0
            
            model: availableServers
            clip: true // Important for scrolling
            focus: true // Allow the list itself to receive focus
            currentIndex: -1 // Keep track of focused item
            
            // Configure delegate (the card)
            delegate: ServerGridCard {
                width: serverListView.width // Card fills list width
                height: width * 0.3 // Make cards less tall
                serverName: modelData.name
                serverDescription: modelData.description || ""
                serverPath: modelData.path
                
                // Make card focusable within the list context
                focus: ListView.isCurrentItem
                // Ensure the list index updates when card gets focus directly (if ever needed)
                onActiveFocusChanged: {
                    if (activeFocus) {
                        serverListView.currentIndex = index;
                    }
                }
                
                onCardClicked: function(path) {
                    // Add a delay to allow e-ink display to refresh
                    clickTimer.serverPath = path
                    clickTimer.start()
                }
            }
            
            // Simplified Key Navigation
            Keys.onPressed: (event) => {
                console.log("--- serverListView Keys.onPressed received key: ", event.key, " currentIndex: ", currentIndex);
                if (event.key === Qt.Key_Up) {
                    if (currentIndex > 0) {
                        serverListView.decrementCurrentIndex();
                    } else {
                        // At first item, wrap around to refresh button
                        refreshButton.forceActiveFocus();
                        console.log("Focus moved to Refresh button (from list top - wrap)");
                    }
                    event.accepted = true;
                } else if (event.key === Qt.Key_Down) {
                    if (currentIndex < count - 1) {
                        serverListView.incrementCurrentIndex();
                    } else {
                        // At last item, move focus to refresh button
                        refreshButton.forceActiveFocus();
                        console.log("Focus moved to Refresh button (from list bottom)");
                    }
                    event.accepted = true;
                } else if (event.key === Qt.Key_Left || event.key === Qt.Key_Right) {
                    // Ignore Left/Right on the list itself
                    event.accepted = true; 
                } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Select) {
                    // Let the focused delegate (card) handle select/enter
                    event.accepted = false; 
                } else {
                    event.accepted = false; // Allow other keys (e.g., PageUp/Down for scrolling)
                }
                // Ensure the current item is visible after navigation
                if (event.accepted && currentIndex !== -1) {
                    positionViewAtIndex(currentIndex, ListView.Center);
                }
            }
        }
        // --- End ListView --- 

        // Add bottom padding
        Item {
            width: parent.width
            height: ThemeManager.spacingSmall
        }
    }

    // Footer area with refresh button and status text
    Rectangle {
        id: footerArea
        
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: footerLayout.height + ThemeManager.spacingNormal * 2
        color: ThemeManager.backgroundColor
        visible: !isLoading
        
        // Add a subtle top border
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: ThemeManager.borderColor
            opacity: 0.5
        }
        
        ColumnLayout {
            id: footerLayout
            
            anchors.centerIn: parent
            width: parent.width - ThemeManager.spacingLarge * 2
            spacing: ThemeManager.spacingSmall
            
            // Status text
            Text {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: serverSelectionPage.isLoading ? "Loading servers..." : (availableServers.length === 0 ? "No servers found" : "")
                color: ThemeManager.secondaryTextColor
                font: FontManager.small
                visible: serverSelectionPage.isLoading || availableServers.length === 0 // Only show when loading or no servers
            }
            
            // Refresh button
            AppButton {
                id: refreshButton
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: parent.width / 2
                Layout.preferredHeight: ThemeManager.buttonHeight * 0.7
                text: "Refresh"
                useFixedHeight: false
                onClicked: {
                    isLoading = true;
                    bridge.getAvailableServers();
                }
                // --- Focus and Key Handling for Button ---
                focus: true
                Keys.onPressed: (event) => {
                    if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Select) {
                        clicked(); // Trigger the button's action
                        event.accepted = true;
                    }
                    // Handle navigation back up to the list
                    if (event.key === Qt.Key_Up) {
                         if (serverListView.visible && serverListView.count > 0) {
                             // Try focusing the last item in the list
                             let lastIndex = serverListView.count - 1;
                             serverListView.currentIndex = lastIndex; // Set index
                             serverListView.forceActiveFocus(); // Focus the list view
                             positionViewAtIndex(lastIndex, ListView.End); // Scroll to bottom
                             console.log("Focus moved to ListView index: " + lastIndex + " (from refresh)");
                             event.accepted = true;
                         } else {
                            event.accepted = false; // Allow default if list not available
                         }
                    } else {
                        // **Handle navigation down (wrap) to the list**
                        if (event.key === Qt.Key_Down) {
                            if (serverListView.visible && serverListView.count > 0) {
                                // Wrap to the first item in the list
                                serverListView.currentIndex = 0; 
                                serverListView.forceActiveFocus(); 
                                serverListView.positionViewAtIndex(0, ListView.Beginning); 
                                console.log("Focus moved to ListView index: 0 (from refresh - wrap)");
                                event.accepted = true;
                            } else {
                                event.accepted = false; // Allow default if list not available
                            }
                        } else {
                            event.accepted = false; // Allow other keys to propagate if needed
                        }
                    }
                }
                // --- End Focus and Key Handling --- 
            }
        }
    }

    // Timer to allow e-ink display to refresh before navigation
    Timer {
        id: clickTimer

        property string serverPath: ""

        interval: 300
        repeat: false
        onTriggered: {
            console.log("Server selected: " + serverPath);
            serverSelected(serverPath);
        }
    }
}
