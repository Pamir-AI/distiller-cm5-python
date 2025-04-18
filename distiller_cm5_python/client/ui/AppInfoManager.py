from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal

class AppInfoManager(QObject):
    """
    Python counterpart to the AppInfo QML singleton.
    Provides the same properties for use in Python code.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Version information
        self._version_number = "0.1"
        self._version_type = "alpha"
        self._full_version = self._version_number + "-" + self._version_type
        
        # App name and branding
        self._app_name = "PamirAI Assistant"
        self._company_name = "PamirAI Inc"
        self._copyright_year = "2025"
        self._copyright = "© " + self._copyright_year + " " + self._company_name
        
        # Display strings
        self._version_string = self._app_name + " v" + self._full_version
        self._short_version_string = "v" + self._full_version
    
    @pyqtProperty(str, constant=True)
    def versionNumber(self):
        return self._version_number
        
    @pyqtProperty(str, constant=True)
    def versionType(self):
        return self._version_type
        
    @pyqtProperty(str, constant=True)
    def fullVersion(self):
        return self._full_version
        
    @pyqtProperty(str, constant=True)
    def appName(self):
        return self._app_name
        
    @pyqtProperty(str, constant=True)
    def companyName(self):
        return self._company_name
        
    @pyqtProperty(str, constant=True)
    def copyrightYear(self):
        return self._copyright_year
        
    @pyqtProperty(str, constant=True)
    def copyright(self):
        return self._copyright
        
    @pyqtProperty(str, constant=True)
    def versionString(self):
        return self._version_string
        
    @pyqtProperty(str, constant=True)
    def shortVersionString(self):
        return self._short_version_string 
