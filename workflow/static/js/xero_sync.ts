interface SyncMessage {
    datetime: string;
    entity: string;
    severity: 'info' | 'warning' | 'error';
    message: string;
    progress: number | null;
}

class XeroSyncProgress {
    private eventSource: EventSource | null = null;
    private retryCount = 0;
    private maxRetries = 3;
    private entityProgress: { [key: string]: number } = {
        accounts: 0,
        contacts: 0,
        invoices: 0,
        bills: 0,
        journals: 0
    };

    constructor() {
        this.connect();
    }

    private connect() {
        this.eventSource = new EventSource('/api/xero/sync-stream/');
        this.eventSource.onmessage = this.handleMessage.bind(this);
        this.eventSource.onerror = this.handleError.bind(this);
    }

    private handleMessage(event: MessageEvent) {
        try {
            const data: SyncMessage = JSON.parse(event.data);
            this.addLogMessage(data);
            
            if (data.progress !== null) {
                this.updateProgress(data.entity, data.progress);
            }

            // Reset retry count on successful message
            this.retryCount = 0;
        } catch (e) {
            console.error('Error processing message:', e);
            this.addLogMessage({
                datetime: new Date().toISOString(),
                entity: 'system',
                severity: 'error',
                message: `Error processing message: ${e}`,
                progress: null
            });
        }
    }

    private handleError(event: Event) {
        this.eventSource?.close();
        
        if (this.retryCount < this.maxRetries) {
            this.retryCount++;
            this.addLogMessage({
                datetime: new Date().toISOString(),
                entity: 'system',
                severity: 'warning',
                message: `Connection lost. Retrying in ${this.retryCount} seconds...`,
                progress: null
            });
            setTimeout(() => this.connect(), 1000 * this.retryCount);
        } else {
            this.addLogMessage({
                datetime: new Date().toISOString(),
                entity: 'system',
                severity: 'error',
                message: 'Max retries reached. Please refresh the page to try again.',
                progress: null
            });
        }
    }

    private updateProgress(entity: string, progress: number) {
        // Update entity progress
        if (entity in this.entityProgress) {
            this.entityProgress[entity] = progress;
            
            const progressBar = document.getElementById(`${entity}-progress`);
            const percentText = document.getElementById(`${entity}-percent`);
            
            if (progressBar && percentText) {
                const percent = Math.round(progress * 100);
                progressBar.style.width = `${percent}%`;
                percentText.textContent = `${percent}%`;
            }
        }

        // Update overall progress
        const overallProgress = Object.values(this.entityProgress).reduce((a, b) => a + b, 0) / Object.keys(this.entityProgress).length;
        const overallProgressBar = document.getElementById('overall-progress');
        if (overallProgressBar) {
            overallProgressBar.style.width = `${Math.round(overallProgress * 100)}%`;
        }
    }

    private addLogMessage(data: SyncMessage) {
        const logContainer = document.getElementById('sync-log');
        if (!logContainer) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `mb-1 ${this.getSeverityClass(data.severity)}`;
        
        const time = new Date(data.datetime).toLocaleTimeString();
        messageDiv.textContent = `[${time}] [${data.entity}] ${data.message}`;
        
        logContainer.appendChild(messageDiv);
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    private getSeverityClass(severity: string): string {
        switch (severity) {
            case 'error':
                return 'text-red-600';
            case 'warning':
                return 'text-yellow-600';
            default:
                return 'text-gray-600';
        }
    }

    public disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    }
}

// Start the sync progress when the page loads
document.addEventListener('DOMContentLoaded', () => {
    const syncProgress = new XeroSyncProgress();

    // Clean up when the page is unloaded
    window.addEventListener('unload', () => {
        syncProgress.disconnect();
    });
}); 