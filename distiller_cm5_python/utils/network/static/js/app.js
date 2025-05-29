// DOM Elements
const connectFormView = document.getElementById('connectFormView');
const connectForm = document.getElementById('connectForm');
const ssidInput = document.getElementById('ssid');
const passwordInput = document.getElementById('password');
const statusMessage = document.getElementById('statusMessage');
const connectingMessage = document.getElementById('connectingMessage');
const connectionStatus = document.getElementById('connectionStatus');
const connectedSsid = document.getElementById('connectedSsid');
const ipAddress = document.getElementById('ipAddress');

// Show/hide views
function showConnectForm() {
    connectFormView.classList.remove('hidden');
    connectingMessage.classList.add('hidden');
}

function showConnecting() {
    connectFormView.classList.add('hidden');
    connectingMessage.classList.remove('hidden');
}

// Show status message
function showStatus(message, isError = false) {
    statusMessage.textContent = message;
    statusMessage.classList.remove('hidden', 'success', 'error');
    statusMessage.classList.add(isError ? 'error' : 'success');
    
    // Hide after 5 seconds
    setTimeout(() => {
        statusMessage.classList.add('hidden');
    }, 5000);
}

// Fetch connection status
async function fetchStatus() {
    try {
        const response = await fetch('/api/status');
        if (!response.ok) {
            throw new Error('Failed to fetch status');
        }
        
        const status = await response.json();
        
        if (status.connected && !status.is_hotspot_active) {
            connectionStatus.classList.remove('hidden');
            connectedSsid.textContent = status.current_connection.ssid;
            ipAddress.textContent = status.current_connection.ip_address;
        } else {
            connectionStatus.classList.add('hidden');
        }
    } catch (error) {
        console.error('Error fetching status:', error);
        connectionStatus.classList.add('hidden');
    }
}

// Connect to network
async function connectToNetwork(ssid, password) {
    showConnecting();
    
    try {
        const response = await fetch('/api/connect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ssid: ssid,
                password: password || null
            })
        });
        
        // Check if response is not OK
        if (!response.ok) {
            if (response.status === 422) {
                // Validation error
                const errorData = await response.json();
                console.error('Validation error:', errorData);
                let errorMessage = 'Validation error: ';
                
                // Extract error details from the validation error response
                if (errorData.detail && Array.isArray(errorData.detail)) {
                    errorMessage += errorData.detail.map(err => `${err.loc.join('.')} - ${err.msg}`).join(', ');
                } else {
                    errorMessage += JSON.stringify(errorData);
                }
                
                showStatus(errorMessage, true);
                showConnectForm();
                return;
            }
            
            // Other errors
            throw new Error(`Server error: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            showStatus(`Successfully connected to ${ssid}`);
            
            // Check if we have a redirect URL
            if (result.data && result.data.redirect_url) {
                // Show message about redirection
                connectingMessage.innerHTML = `
                    <div class="flex">
                        <div class="loading"></div> Connection successful!
                    </div>
                    <p>You are now connected to ${ssid}.</p>
                    <p>Redirecting to dashboard in 3 seconds...</p>
                `;
                
                // Wait and then redirect
                setTimeout(() => {
                    // Use the IP address if available
                    if (result.data.ip_address && result.data.ip_address !== "Unknown") {
                        // Check if we're using mDNS
                        if (window.location.hostname === "distiller.local") {
                            window.location.href = `${window.location.protocol}//${window.location.host}${result.data.redirect_url}`;
                        } else {
                            // Try using the IP directly - this helps if we change networks
                            window.location.href = `${window.location.protocol}//${result.data.ip_address}:${window.location.port}${result.data.redirect_url}`;
                        }
                    } else {
                        // Just use relative URL if no IP is available
                        window.location.href = result.data.redirect_url;
                    }
                }, 3000);
            } else {
                // No redirect - just update status and show form
                setTimeout(async () => {
                    await fetchStatus();
                    showConnectForm();
                }, 3000);
            }
        } else {
            // Format a more detailed error message
            let errorMessage = `Failed to connect: ${result.message}`;
            
            // Add additional details if available
            if (result.data && result.data.error_details) {
                console.error('Connection error details:', result.data);
                
                // Extract specific error messages for common failure cases
                if (result.data.error_details.includes('password')) {
                    errorMessage = 'Invalid password for this network. Please check and try again.';
                } else if (result.data.error_details.includes('not found')) {
                    errorMessage = `Network "${ssid}" not found. Please check the network name.`;
                } else if (result.data.error_details.includes('timeout')) {
                    errorMessage = 'Connection timed out. Please try again.';
                }
            }
            
            showStatus(errorMessage, true);
            showConnectForm();
        }
    } catch (error) {
        console.error('Error connecting:', error);
        showStatus(`Connection error: ${error.message}`, true);
        showConnectForm();
    }
}

// Event Listeners
connectForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const ssid = ssidInput.value;
    const password = passwordInput.value;
    
    if (!ssid) {
        showStatus('Network name is required', true);
        return;
    }
    
    await connectToNetwork(ssid, password);
});

// Initialize
async function initialize() {
    await fetchStatus();
}

// Start app
initialize();

// Poll for status updates every 5 seconds
setInterval(fetchStatus, 5000); 