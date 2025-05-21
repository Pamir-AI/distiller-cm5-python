import QtQuick
pragma Singleton

QtObject {
    id: appInfo

    // Version information
    readonly property string versionNumber: "0.1"
    readonly property string versionType: "alpha"
    readonly property string fullVersion: versionNumber + "-" + versionType
    // App name and branding
    readonly property string appName: "PamirAI Assistant"
    readonly property string companyName: "PamirAI Incorporated."
    readonly property string copyrightYear: "2025"
    readonly property string copyright: "© " + copyrightYear + " " + companyName
    // Display strings
    readonly property string versionString: appName + " v" + fullVersion
    readonly property string shortVersionString: "v" + fullVersion
}
