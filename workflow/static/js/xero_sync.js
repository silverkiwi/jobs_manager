'use strict';

// Constants for entity names and their order
const ENTITIES = ['accounts', 'contacts', 'invoices', 'bills', 'journals', 'credit-notes'];
const TOTAL_ENTITIES = ENTITIES.length;

// UI Elements
const closeButton = document.getElementById('close-button');
const currentEntity = document.getElementById('current-entity');
const entityProgress = document.getElementById('entity-progress');
const entityPercent = document.getElementById('entity-percent');
const syncLog = document.getElementById('sync-log');

function formatLastSync(lastSync) {
    if (!lastSync || lastSync === '2000-01-01T00:00:00Z') {
        return '-';
    }
    return new Date(lastSync).toLocaleString();
}

class XeroSyncProgress {
    constructor() {
        this.eventSource = new EventSource('/api/xero/sync-stream/');
        this.eventSource.onmessage = this.handleMessage.bind(this);
        this.eventSource.onerror = this.handleError.bind(this);
        this.retryCount = 0;
        this.maxRetries = 3;
        
        // Request initial sync info
        fetch('/api/xero/sync-info/')
            .then(response => response.json())
            .then(data => {
                // Update last sync times
                if (data.last_syncs) {
                    Object.entries(data.last_syncs).forEach(([entity, lastSync]) => {
                        updateEntityRow(entity, { 
                            lastSync,
                            status: 'Pending'  // Ensure status stays as Pending
                        });
                    });
                }
                
                // Update sync range info
                if (data.sync_range) {
                    document.getElementById('sync-range').textContent = data.sync_range;
                }
            })
            .catch(error => console.error('Error fetching sync info:', error));
    }

    handleMessage(event) {
        try {
            const message = JSON.parse(event.data);
            addLogMessage(message);
            
            // Update sync range info if provided
            if (message.entity === 'sync' && message.message.includes('looking back')) {
                document.getElementById('sync-range').textContent = message.message;
            }
            
            if (message.entity && message.entity !== 'sync') {
                const currentStatus = entityStats[message.entity]?.status;
                if (currentStatus === 'Pending') {
                    handleEntityChange(message.entity);
                }
                
                if (message.progress !== null) {
                    updateEntityProgress(message.entity, message.progress);
                }
                
                if (message.progress === 1) {
                    handleEntityCompletion(message.entity, true, message.lastSync);
                }

                // Update lastSync time and records whenever provided
                const updates = {};
                if (message.lastSync) {
                    updates.lastSync = message.lastSync;
                }
                
                // Extract records updated from message
                const recordsMatch = message.message.match(/Processed (\d+)/);
                if (recordsMatch) {
                    updates.recordsUpdated = parseInt(recordsMatch[1], 10);
                }
                
                if (Object.keys(updates).length > 0) {
                    updateEntityRow(message.entity, updates);
                }
            }
            
            // Update overall progress
            updateOverallProgress();
            
            if (message.message === 'Sync stream ended') {
                this.disconnect();
                syncComplete(true);
                updateOverallProgress(); // Update one final time
            }
            
            if (message.severity === 'error') {
                if (message.entity && message.entity !== 'sync') {
                    handleEntityCompletion(message.entity, false, message.lastSync);
                }
                syncComplete(false);
            }

            // Reset retry count on successful message
            this.retryCount = 0;
        } catch (e) {
            console.error('Error processing message:', e);
            addLogMessage({
                datetime: new Date().toISOString(),
                severity: 'error',
                message: `Error processing message: ${e}`,
            });
        }
    }

    handleError(error) {
        this.eventSource?.close();
        
        if (this.retryCount < this.maxRetries) {
            this.retryCount++;
            addLogMessage({
                datetime: new Date().toISOString(),
                severity: 'warning',
                message: `Connection lost. Retrying in ${this.retryCount} seconds...`,
            });
            setTimeout(() => this.connect(), 1000 * this.retryCount);
        } else {
            addLogMessage({
                datetime: new Date().toISOString(),
                severity: 'error',
                message: 'Max retries reached. Please refresh the page to try again.',
            });
        }
    }

    connect() {
        this.eventSource = new EventSource('/api/xero/sync-stream/');
        this.eventSource.onmessage = this.handleMessage.bind(this);
        this.eventSource.onerror = this.handleError.bind(this);
    }

    disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    }
}

// State tracking
let completedEntities = 0;
let entityStats = {};

// Initialize stats for each entity
ENTITIES.forEach(entity => {
    entityStats[entity] = {
        status: 'Pending',
        lastSync: '-',
        recordsUpdated: 0
    };
});

// Disable close button initially
closeButton.disabled = true;
closeButton.classList.add('opacity-50', 'cursor-not-allowed');

function updateEntityProgress(entity, progress) {
    entityProgress.style.width = `${progress * 100}%`;
    entityPercent.textContent = `${Math.round(progress * 100)}%`;
}

function updateEntityRow(entity, updates = {}) {
    const row = document.getElementById(`row-${entity}`);
    if (!row) return;

    // Update our stats object
    entityStats[entity] = { ...entityStats[entity], ...updates };
    const stats = entityStats[entity];

    // Update the row cells
    if (updates.lastSync) {
        const lastSyncDate = new Date(updates.lastSync);
        row.querySelector('.last-sync').textContent = formatLastSync(updates.lastSync);
    }
    if (updates.status) {
        const statusCell = row.querySelector('.status');
        statusCell.textContent = updates.status;
        
        // Update status classes
        statusCell.className = 'status'; // Reset classes
        switch (updates.status) {
            case 'In Progress':
                statusCell.classList.add('status-in-progress');
                break;
            case 'Completed':
                statusCell.classList.add('status-completed');
                break;
            case 'Error':
                statusCell.classList.add('status-error');
                break;
            default:
                statusCell.classList.add('status-pending');
        }
    }
    if (updates.recordsUpdated !== undefined) {
        row.querySelector('.records').textContent = updates.recordsUpdated;
    }
}

function addLogMessage(message) {
    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry';
    
    // Format timestamp
    const timestamp = new Date(message.datetime).toLocaleTimeString();
    
    // Style based on severity
    switch (message.severity) {
        case 'error':
            logEntry.classList.add('error');
            break;
        case 'warning':
            logEntry.classList.add('warning');
            break;
        case 'success':
            logEntry.classList.add('success');
            break;
    }
    
    // Extract record count if present in message
    const recordMatch = message.message.match(/Updated (\d+) records?/i);
    if (recordMatch && message.entity) {
        updateEntityRow(message.entity, { recordsUpdated: parseInt(recordMatch[1], 10) });
    }
    
    logEntry.textContent = `[${timestamp}] ${message.message}`;
    syncLog.appendChild(logEntry);
    syncLog.scrollTop = syncLog.scrollHeight;
}

function handleEntityChange(entity) {
    // Update current entity display
    currentEntity.textContent = entity.charAt(0).toUpperCase() + entity.slice(1);
    
    // Reset entity progress
    entityProgress.style.width = '0%';
    entityPercent.textContent = '0%';
    
    // Update status
    updateEntityRow(entity, {
        status: 'In Progress',
        lastSync: new Date().toISOString()
    });
}

function handleEntityCompletion(entity, success = true, lastSync = null) {
    completedEntities++;
    updateEntityRow(entity, {
        status: success ? 'Completed' : 'Error',
        lastSync: lastSync || new Date().toISOString()
    });
}

function syncComplete(success = true) {
    closeButton.disabled = false;
    closeButton.classList.remove('opacity-50', 'cursor-not-allowed');
    
    if (success) {
        closeButton.classList.remove('btn-secondary');
        closeButton.classList.add('btn-success');
    }
}

// Add function to calculate and update overall progress
function updateOverallProgress() {
    const entities = Object.keys(entityStats);
    let completedCount = 0;
    
    entities.forEach(entity => {
        if (entityStats[entity].status === 'Completed') {
            completedCount++;
        }
    });
    
    const progress = (completedCount / entities.length) * 100;
    const overallProgressBar = document.getElementById('overall-progress');
    const overallPercent = document.getElementById('overall-percent');
    
    if (overallProgressBar && overallPercent) {
        overallProgressBar.style.width = `${progress}%`;
        overallPercent.textContent = `${Math.round(progress)}%`;
    }
}

// Start the sync progress when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.xeroSyncProgress = new XeroSyncProgress();

    // Clean up when the page is unloaded
    window.addEventListener('unload', () => {
        if (window.xeroSyncProgress) {
            window.xeroSyncProgress.disconnect();
        }
    });
}); 