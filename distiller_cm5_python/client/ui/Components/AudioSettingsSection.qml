import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

AppSection {
    id: audioSettingsSection

    property alias volume: volumeSlider.value
    property bool isDirty: false

    signal volumeAdjusted(real value)
    signal configChanged()

    title: "AUDIO SETTINGS"
    compact: true
    navigable: true
    
    // Override to expose our navigable controls
    function getNavigableControls() {
        var controls = [];
        if (volumeSlider && volumeSlider.visible) {
            controls.push(volumeSlider);
        }
        return controls;
    }
    
    // Handle keyboard navigation
    Keys.onReturnPressed: {
        if (volumeSlider && volumeSlider.visible) {
            volumeSlider.forceActiveFocus();
        }
    }
    
    function updateFromBridge() {
        if (bridge && bridge.ready) {
            var savedVolume = bridge.getConfigValue("audio", "volume");
            if (savedVolume !== "") {
                volume = parseFloat(savedVolume);
            }
            isDirty = false;
        }
    }
    
    function getConfig() {
        return {
            "volume": volume.toString()
        };
    }

    ColumnLayout {
        width: parent.width
        spacing: ThemeManager.spacingNormal

        // Volume slider
        ColumnLayout {
            Layout.fillWidth: true
            spacing: ThemeManager.spacingNormal

            CustomSlider {
                id: volumeSlider
                Layout.fillWidth: true
                Layout.topMargin: 4
                Layout.bottomMargin: 4
                from: 0.0
                to: 1.0
                stepSize: 0.05
                value: 0.5
                label: "VOLUME"
                valueFormat: Math.round(value * 100) + "%"
                navigable: true
                
                onValueAdjusted: function(newValue) {
                    audioSettingsSection.volumeAdjusted(newValue);
                    audioSettingsSection.isDirty = true;
                    audioSettingsSection.configChanged();
                }
            }
        }
    }
}
