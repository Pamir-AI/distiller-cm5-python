import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

AppHeader {
    id: settingsHeader

    property bool showApplyButton: true

    signal applyClicked()

    title: "SETTINGS"
    showBackButton: true
    showActionButton: showApplyButton
    actionButtonText: "APPLY"
    
    onActionClicked: settingsHeader.applyClicked()
}
