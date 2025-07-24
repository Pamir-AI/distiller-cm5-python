/**
 * Enhanced WiFi Setup Interface
 * Modern implementation with improved error handling and user experience
 */

class WiFiSetup {
  constructor() {
    this.statusCard = document.getElementById("status-card");
    this.statusInfo = document.getElementById("status-info");
    this.ssidInput = document.getElementById("ssid-input");
    this.passwordInput = document.getElementById("password-input");
    this.connectBtn = document.getElementById("connect-btn");
    this.alertContainer = document.getElementById("alert-container");

    this.init();
  }

  init() {
    if (this.connectBtn) {
      this.connectBtn.addEventListener("click", () => this.connectToNetwork());
    }

    // Show initial disconnected state
    this.updateStatusDisplay({ connected: false });

    // Add input validation
    this.setupInputValidation();
  }

  setupInputValidation() {
    if (this.ssidInput) {
      this.ssidInput.addEventListener(
        "input",
        CommonUtils.debounce((e) => {
          const validation = CommonUtils.validateSSID(e.target.value);
          this.showInputValidation(e.target, validation);
        }, 300)
      );
    }
  }

  showInputValidation(input, validation) {
    // Remove existing validation messages
    const existingMessage = input.parentElement.querySelector(
      ".validation-message"
    );
    if (existingMessage) {
      existingMessage.remove();
    }

    if (!validation.isValid && input.value.length > 0) {
      const message = document.createElement("div");
      message.className = "validation-message";
      message.style.cssText = `
        color: #dc3545;
        font-size: 10px;
        margin-top: 4px;
        font-family: "MartianMono", monospace;
      `;
      message.textContent = validation.message;
      input.parentElement.appendChild(message);
    }
  }

  // Enhanced status checking method
  async checkStatus() {
    try {
      const status = await CommonUtils.apiRequest("/api/status");
      this.updateStatusDisplay(status);
      return status;
    } catch (error) {
      console.error("Status check failed:", error);
      CommonUtils.showNotification(
        "Failed to check connection status",
        "error"
      );
      return null;
    }
  }

  updateStatusDisplay(status) {
    if (!this.statusCard || !this.statusInfo) return;

    if (status.connected) {
      this.statusCard.className = "status-card";
      this.statusInfo.innerHTML = `
        <div class="detail-row">
          <span class="detail-label">Network:</span>
          <span class="detail-value">${status.ssid || "N/A"}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">IP Address:</span>
          <span class="detail-value">${status.ip_address || "N/A"}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Interface:</span>
          <span class="detail-value">${status.interface || "N/A"}</span>
        </div>
      `;
    } else {
      this.statusCard.className = "status-card disconnected";
      this.statusInfo.innerHTML = `
        <div class="status-message">Ready to connect to WiFi network</div>
        <div class="instruction-detail">Enter network credentials below to get started</div>
      `;
    }
  }

  async connectToNetwork() {
    if (!this.ssidInput || !this.connectBtn) {
      console.error("Required elements not found");
      return;
    }

    const ssid = this.ssidInput.value.trim();
    const password = this.passwordInput ? this.passwordInput.value : "";

    // Validate SSID
    const validation = CommonUtils.validateSSID(ssid);
    if (!validation.isValid) {
      this.showAlert(validation.message, "error");
      return;
    }

    // Show loading state
    CommonUtils.showLoading(this.connectBtn, "Connecting...");

    try {
      // Initiate the connection
      const connectResponse = await CommonUtils.apiRequest("/api/connect", {
        method: "POST",
        body: JSON.stringify({ ssid: ssid, password: password }),
      });

      // Show connection status information
      this.showConnectionStatus(ssid);
    } catch (error) {
      console.error("Connection process failed:", error);
      this.showAlert(`Connection failed: ${error.message}`, "error");
    } finally {
      // Reset button state
      CommonUtils.hideLoading(this.connectBtn);
    }
  }

  showConnectionStatus(ssid) {
    const message = `
      <strong>Connection initiated to ${ssid}</strong><br><br>
      The device is now connecting to your WiFi network. This process may take a few moments.<br><br>
      <strong>What happens next:</strong><br>
      • The device will connect to your network<br>
      • You can check the connection status at any time<br>
      • If successful, access your device using its new IP address<br><br>
      <strong>To check status:</strong> Visit the <a href="/status" style="color: #000; text-decoration: underline;">Status Page</a>
    `;

    this.showAlert(message, "info");

    // Auto-check status after a delay
    setTimeout(() => {
      this.checkStatus();
    }, 3000);
  }

  showAlert(message, type) {
    if (!this.alertContainer) {
      // Fallback to common notification system
      CommonUtils.showNotification(message, type);
      return;
    }

    const alertClass = `alert-${type}`;
    const alertHtml = `
      <div class="alert ${alertClass}">
        ${message}
        <button class="notification-close" onclick="this.parentElement.remove()" style="
          float: right;
          background: none;
          border: none;
          font-family: 'MartianMono', monospace;
          font-size: 12px;
          cursor: pointer;
          margin-left: 10px;
        ">[×]</button>
      </div>
    `;

    this.alertContainer.innerHTML = alertHtml;

    // Auto-remove alerts
    const timeout = type === "info" ? 15000 : 5000;
    setTimeout(() => {
      if (this.alertContainer.innerHTML.includes(alertClass)) {
        this.alertContainer.innerHTML = "";
      }
    }, timeout);
  }

  // Method to refresh network list (if supported)
  async refreshNetworks() {
    try {
      const networks = await CommonUtils.apiRequest("/api/networks");
      if (networks && networks.length > 0) {
        CommonUtils.showNotification(
          `Found ${networks.length} networks`,
          "success"
        );
        // Trigger page refresh to show new networks
        setTimeout(() => window.location.reload(), 1000);
      } else {
        CommonUtils.showNotification("No networks found", "warning");
      }
    } catch (error) {
      console.error("Failed to refresh networks:", error);
      CommonUtils.showNotification("Failed to refresh network list", "error");
    }
  }

  // Method to check if device is online
  async checkConnectivity() {
    try {
      // Try to reach a simple endpoint
      await CommonUtils.apiRequest("/api/ping");
      return true;
    } catch (error) {
      return false;
    }
  }
}

// Initialize the WiFi setup interface when the page loads
CommonUtils.onReady(function () {
  window.wifiSetup = new WiFiSetup();

  // Add global keyboard shortcuts
  document.addEventListener("keydown", function (e) {
    // Escape key to clear alerts
    if (e.key === "Escape") {
      const alerts = document.querySelectorAll(".alert, .notification");
      alerts.forEach((alert) => alert.remove());
    }

    // Enter key in SSID field to focus password field
    if (e.key === "Enter" && e.target.id === "ssid-input") {
      const passwordInput = document.getElementById("password-input");
      if (passwordInput) {
        e.preventDefault();
        passwordInput.focus();
      }
    }
  });

  // Add refresh button functionality if present
  const refreshBtn = document.getElementById("refresh-networks");
  if (refreshBtn && window.wifiSetup) {
    refreshBtn.addEventListener("click", () => {
      window.wifiSetup.refreshNetworks();
    });
  }
});
