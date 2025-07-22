import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

AppDialog {
    id: batteryWarningDialog
    
    property int batteryLevel: 15
    property bool isCritical: false
    property bool isCharging: false
    
    signal shutdownRequested()
    signal acknowledged()
    
    dialogTitle: isCritical ? "Critical Battery Warning" : "Low Battery Warning"
    
    message: {
        if (isCritical) {
            return "Battery level is critically low (" + batteryLevel + "%).\n\n" +
                   "The system will shut down automatically to prevent data loss.\n" +
                   (isCharging ? "Please ensure charger is connected properly." : "Please connect charger immediately.")
        } else {
            return "Battery level is low (" + batteryLevel + "%).\n\n" +
                   "Please connect your charger soon to avoid unexpected shutdown."
        }
    }
    
    standardButtonTypes: {
        if (isCritical) {
            return DialogButtonBox.Ok | DialogButtonBox.Cancel
        } else {
            return DialogButtonBox.Ok
        }
    }
    
    yesButtonText: isCritical ? "Shutdown Now" : "OK"
    noButtonText: "Cancel"
    
    acceptButtonColor: isCritical ? "#FF4444" : ThemeManager.backgroundColor
    
    onAccepted: {
        if (isCritical) {
            shutdownRequested();
        } else {
            acknowledged();
        }
    }
    
    onRejected: {
        if (isCritical) {
            acknowledged();  // Just close the dialog but don't shutdown
        }
    }
}