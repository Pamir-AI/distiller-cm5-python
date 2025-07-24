/**
 * Common JavaScript functionality for Distiller CM5 WiFi Setup Interface
 * Provides shared utilities and functions across all pages
 */

class CommonUtils {
  /**
   * Show a temporary notification message
   * @param {string} message - The message to display
   * @param {string} type - Type of notification: 'success', 'error', 'info', 'warning'
   * @param {number} duration - Duration in milliseconds (default: 5000)
   */
  static showNotification(message, type = "info", duration = 5000) {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll(".notification");
    existingNotifications.forEach((n) => n.remove());

    // Create notification element
    const notification = document.createElement("div");
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
      <div class="notification-content">
        ${message}
        <button class="notification-close" onclick="this.parentElement.parentElement.remove()">[×]</button>
      </div>
    `;

    // Add styles if not already added
    if (!document.getElementById("notification-styles")) {
      const styles = document.createElement("style");
      styles.id = "notification-styles";
      styles.innerHTML = `
        .notification {
          position: fixed;
          top: 20px;
          right: 20px;
          max-width: 400px;
          background: #ffffff;
          border: 2px solid #000000;
          padding: 15px;
          font-family: "MartianMono", monospace;
          font-size: 12px;
          z-index: 1000;
          animation: slideIn 0.3s ease;
        }
        .notification-success { border-color: #28a745; }
        .notification-error { border-color: #dc3545; }
        .notification-warning { border-color: #ffc107; }
        .notification-info { border-color: #007bff; }
        .notification-content {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 10px;
        }
        .notification-close {
          background: none;
          border: none;
          font-family: "MartianMono", monospace;
          font-size: 12px;
          cursor: pointer;
          padding: 0;
          margin-left: 10px;
          flex-shrink: 0;
        }
        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        @media (max-width: 600px) {
          .notification {
            top: 10px;
            right: 10px;
            left: 10px;
            max-width: none;
          }
        }
      `;
      document.head.appendChild(styles);
    }

    // Add to page
    document.body.appendChild(notification);

    // Auto-remove after duration
    if (duration > 0) {
      setTimeout(() => {
        if (notification.parentElement) {
          notification.remove();
        }
      }, duration);
    }
  }

  /**
   * Make an API request with proper error handling
   * @param {string} url - API endpoint
   * @param {Object} options - Fetch options
   * @returns {Promise<Object>} - Response data
   */
  static async apiRequest(url, options = {}) {
    try {
      const response = await fetch(url, {
        headers: {
          "Content-Type": "application/json",
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed: ${url}`, error);
      throw error;
    }
  }

  /**
   * Format device information for display
   * @param {Object} info - Device info object
   * @returns {string} - Formatted string
   */
  static formatDeviceInfo(info) {
    const parts = [];
    if (info.ssid) parts.push(`Network: ${info.ssid}`);
    if (info.ip_address) parts.push(`IP: ${info.ip_address}`);
    if (info.interface) parts.push(`Interface: ${info.interface}`);
    return parts.join(" • ");
  }

  /**
   * Show loading state on an element
   * @param {HTMLElement} element - Element to show loading on
   * @param {string} loadingText - Text to display while loading
   */
  static showLoading(element, loadingText = "Loading...") {
    element.dataset.originalText = element.textContent;
    element.textContent = loadingText;
    element.disabled = true;
    element.classList.add("loading");
  }

  /**
   * Hide loading state on an element
   * @param {HTMLElement} element - Element to hide loading from
   */
  static hideLoading(element) {
    if (element.dataset.originalText) {
      element.textContent = element.dataset.originalText;
      delete element.dataset.originalText;
    }
    element.disabled = false;
    element.classList.remove("loading");
  }

  /**
   * Validate SSID format
   * @param {string} ssid - Network SSID to validate
   * @returns {Object} - Validation result with isValid and message
   */
  static validateSSID(ssid) {
    if (!ssid || ssid.trim().length === 0) {
      return { isValid: false, message: "Network name is required" };
    }

    if (ssid.length > 32) {
      return {
        isValid: false,
        message: "Network name must be 32 characters or less",
      };
    }

    // Check for invalid characters (basic check)
    if (ssid.includes("\0")) {
      return {
        isValid: false,
        message: "Network name contains invalid characters",
      };
    }

    return { isValid: true, message: "" };
  }

  /**
   * Add event listeners when DOM is ready
   * @param {Function} callback - Function to call when DOM is ready
   */
  static onReady(callback) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback);
    } else {
      callback();
    }
  }

  /**
   * Throttle function execution
   * @param {Function} func - Function to throttle
   * @param {number} limit - Time limit in milliseconds
   * @returns {Function} - Throttled function
   */
  static throttle(func, limit) {
    let inThrottle;
    return function () {
      const args = arguments;
      const context = this;
      if (!inThrottle) {
        func.apply(context, args);
        inThrottle = true;
        setTimeout(() => (inThrottle = false), limit);
      }
    };
  }

  /**
   * Debounce function execution
   * @param {Function} func - Function to debounce
   * @param {number} delay - Delay in milliseconds
   * @returns {Function} - Debounced function
   */
  static debounce(func, delay) {
    let timeoutId;
    return function () {
      const args = arguments;
      const context = this;
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func.apply(context, args), delay);
    };
  }

  /**
   * Smart status poller with adaptive intervals
   * Polls more frequently during transitions, less frequently when stable
   */
  static createStatusPoller(statusCallback, options = {}) {
    const defaults = {
      fastInterval: 2000, // Fast polling during transitions (2s)
      slowInterval: 10000, // Slow polling when stable (10s)
      maxRetries: 3, // Max consecutive failures before backing off
      backoffMultiplier: 2, // Multiplier for backoff intervals
    };
    const config = { ...defaults, ...options };

    let currentInterval = config.fastInterval;
    let consecutiveErrors = 0;
    let lastState = null;
    let timeoutId = null;
    let isRunning = false;

    const poll = async () => {
      if (!isRunning) return;

      try {
        const status = await CommonUtils.apiRequest("/api/status");
        consecutiveErrors = 0; // Reset error count on success

        // Determine if we should use fast or slow polling
        const isTransitioning =
          status.current_state === "connecting" ||
          status.current_state === "initializing" ||
          (status.connected && status.current_state !== "connected");

        // Check if state changed
        const stateChanged =
          lastState && lastState.current_state !== status.current_state;

        if (isTransitioning || stateChanged) {
          currentInterval = config.fastInterval;
          console.log("Fast polling: state transitioning or changed");
        } else {
          currentInterval = config.slowInterval;
        }

        // Special handling for successful connection
        if (
          status.connected &&
          status.current_state === "connected" &&
          lastState &&
          lastState.current_state === "connecting"
        ) {
          console.log("Connection completed - checking mDNS redirection");
          // Give a few seconds for mDNS to stabilize, then check if we should redirect
          setTimeout(() => {
            if (
              status.mdns_url &&
              window.location.hostname !== new URL(status.mdns_url).hostname
            ) {
              console.log("Redirecting to mDNS URL:", status.mdns_url);
              window.location.href = status.mdns_url + "/status";
            }
          }, 5000);
        }

        lastState = status;

        // Call the status callback
        if (statusCallback) {
          statusCallback(status);
        }
      } catch (error) {
        consecutiveErrors++;
        console.error("Status polling error:", error);

        // Apply exponential backoff on repeated failures
        if (consecutiveErrors >= config.maxRetries) {
          currentInterval =
            config.slowInterval *
            Math.pow(
              config.backoffMultiplier,
              consecutiveErrors - config.maxRetries,
            );
          console.log(
            `Backing off polling due to errors, interval: ${currentInterval}ms`,
          );
        }

        // Notify about connection issues
        if (consecutiveErrors === config.maxRetries) {
          CommonUtils.showNotification(
            "Connection issues detected, checking less frequently",
            "warning",
          );
        }
      }

      // Schedule next poll
      if (isRunning) {
        timeoutId = setTimeout(poll, currentInterval);
      }
    };

    return {
      start() {
        if (isRunning) return;
        isRunning = true;
        console.log("Starting status poller");
        poll(); // Start immediately
      },

      stop() {
        isRunning = false;
        if (timeoutId) {
          clearTimeout(timeoutId);
          timeoutId = null;
        }
        console.log("Stopped status poller");
      },

      isRunning() {
        return isRunning;
      },
    };
  }
}

// Make CommonUtils available globally
window.CommonUtils = CommonUtils;

// Auto-start status polling on status-related pages
CommonUtils.onReady(() => {
  // Only auto-start on status or connecting pages
  if (
    window.location.pathname.includes("/status") ||
    document.body.classList.contains("status-page") ||
    document.getElementById("status-container")
  ) {
    // Create and start status poller
    window.statusPoller = CommonUtils.createStatusPoller((status) => {
      // Update page content if status update function exists
      if (window.updateStatus && typeof window.updateStatus === "function") {
        window.updateStatus(status);
      }

      // Handle redirection for successful connections
      if (
        status.connected &&
        status.current_state === "connected" &&
        status.mdns_url
      ) {
        const currentHost = window.location.hostname;
        const mdnsHost = new URL(status.mdns_url).hostname;

        if (currentHost !== mdnsHost && !currentHost.endsWith(".local")) {
          console.log("Connection complete - should redirect to mDNS URL");
          // Show notification about redirection
          CommonUtils.showNotification(
            "Connection successful! Redirecting to device URL...",
            "success",
            3000,
          );

          // Redirect after a brief delay
          setTimeout(() => {
            window.location.href = status.mdns_url + window.location.pathname;
          }, 3000);
        }
      }
    });

    window.statusPoller.start();

    // Stop polling when leaving the page
    window.addEventListener("beforeunload", () => {
      if (window.statusPoller) {
        window.statusPoller.stop();
      }
    });
  }
});
