/**
 * Admin Data Upload - Client-side Application
 * 
 * This module handles the admin upload functionality including:
 * - TNVED code file uploads
 * - URL mapping file uploads
 * - Progress tracking and updates
 * - Error handling and display
 * - Upload summary display
 */

class AdminUploadApp {
    constructor() {
        this.activeUploads = new Set();
        this.progressIntervals = new Map();
        
        // Initialize the application
        this.init();
    }
    
    /**
     * Initialize the application
     */
    init() {
        this.setupEventListeners();
        this.setupFileInputHandlers();
    }
    
    /**
     * Setup event listeners for UI interactions
     */
    setupEventListeners() {
        // TNVED upload form
        const tnvedForm = document.getElementById('tnved-upload-form');
        tnvedForm.addEventListener('submit', (e) => this.handleUpload(e, 'tnved'));
        
        // URL upload form
        const urlForm = document.getElementById('url-upload-form');
        urlForm.addEventListener('submit', (e) => this.handleUpload(e, 'urls'));
        
        // File input changes
        const tnvedFileInput = document.getElementById('tnved-file-input');
        tnvedFileInput.addEventListener('change', (e) => this.handleFileSelect(e, 'tnved'));
        
        const urlFileInput = document.getElementById('url-file-input');
        urlFileInput.addEventListener('change', (e) => this.handleFileSelect(e, 'url'));
    }
    
    /**
     * Setup drag and drop handlers for file inputs
     */
    setupFileInputHandlers() {
        // TNVED file input drag and drop
        const tnvedWrapper = document.getElementById('tnved-file-wrapper');
        this.setupDragAndDrop(tnvedWrapper, 'tnved-file-input', 'tnved');
        
        // URL file input drag and drop
        const urlWrapper = document.getElementById('url-file-wrapper');
        this.setupDragAndDrop(urlWrapper, 'url-file-input', 'url');
    }
    
    /**
     * Setup drag and drop for a file input wrapper
     */
    setupDragAndDrop(wrapper, inputId, uploadType) {
        wrapper.addEventListener('dragover', (e) => {
            e.preventDefault();
            wrapper.classList.add('drag-over');
        });
        
        wrapper.addEventListener('dragleave', (e) => {
            e.preventDefault();
            wrapper.classList.remove('drag-over');
        });
        
        wrapper.addEventListener('drop', (e) => {
            e.preventDefault();
            wrapper.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const fileInput = document.getElementById(inputId);
                fileInput.files = files;
                this.handleFileSelect({ target: fileInput }, uploadType);
            }
        });
    }
    
    /**
     * Handle file selection
     */
    handleFileSelect(event, uploadType) {
        const file = event.target.files[0];
        if (file) {
            this.updateFileInputDisplay(file, uploadType);
            this.validateFileClient(file, uploadType);
        }
    }
    
    /**
     * Update file input display when file is selected
     */
    updateFileInputDisplay(file, uploadType) {
        const wrapper = document.getElementById(`${uploadType}-file-wrapper`);
        const label = wrapper.querySelector('.file-input-label span');
        
        wrapper.classList.add('has-file');
        label.textContent = `Selected: ${file.name} (${this.formatFileSize(file.size)})`;
    }
    
    /**
     * Client-side file validation
     */
    validateFileClient(file, uploadType) {
        const errors = [];
        
        // Check file size (100MB limit)
        const maxSize = 100 * 1024 * 1024; // 100MB in bytes
        if (file.size > maxSize) {
            errors.push(`File size (${this.formatFileSize(file.size)}) exceeds 100MB limit`);
        }
        
        // Check file extension
        const allowedExtensions = ['.xlsx', '.xls', '.parquet'];
        const fileName = file.name.toLowerCase();
        const hasValidExtension = allowedExtensions.some(ext => fileName.endsWith(ext));
        
        if (!hasValidExtension) {
            errors.push(`Unsupported file format. Allowed: ${allowedExtensions.join(', ')}`);
        }
        
        if (errors.length > 0) {
            this.showError(errors.join('. '), uploadType);
        } else {
            this.hideError(uploadType);
        }
    }
    
    /**
     * Handle form submission for uploads
     */
    async handleUpload(event, uploadType) {
        event.preventDefault();
        
        // Prevent multiple simultaneous uploads of the same type
        if (this.activeUploads.has(uploadType)) {
            this.showError('Upload already in progress for this type', uploadType);
            return;
        }
        
        const form = event.target;
        const formData = new FormData(form);
        const file = formData.get('file');
        const sourceName = formData.get('source_name');
        
        // Validate inputs
        if (!file || file.size === 0) {
            this.showError('Please select a file to upload', uploadType);
            return;
        }
        
        if (!sourceName || !sourceName.trim()) {
            this.showError('Please provide a source name', uploadType);
            return;
        }
        
        // Validate source name format
        if (!/^[a-zA-Z0-9_-]+$/.test(sourceName.trim())) {
            this.showError('Source name can only contain letters, numbers, hyphens, and underscores', uploadType);
            return;
        }
        
        try {
            this.activeUploads.add(uploadType);
            this.setUploadButtonState(uploadType, true); // disabled
            this.hideError(uploadType);
            this.hideSummary(uploadType);
            
            // Start upload
            await this.uploadFile(formData, uploadType);
            
        } catch (error) {
            console.error(`${uploadType} upload error:`, error);
            this.showError(error.message || 'Upload failed', uploadType);
        } finally {
            this.activeUploads.delete(uploadType);
            this.setUploadButtonState(uploadType, false); // enabled
        }
    }
    
    /**
     * Upload file to server
     */
    async uploadFile(formData, uploadType) {
        this.showLoading();
        
        try {
            const response = await fetch(`/admin/upload/${uploadType}`, {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}: Upload failed`);
            }
            
            const result = await response.json();
            console.log(`${uploadType} upload initiated:`, result);
            
            // Show progress and start polling
            this.showProgress(uploadType);
            this.startProgressPolling(result.upload_id || 'unknown', uploadType);
            
        } catch (error) {
            console.error(`Upload request failed:`, error);
            throw error;
        } finally {
            this.hideLoading();
        }
    }
    
    /**
     * Start polling for progress updates
     */
    startProgressPolling(uploadId, uploadType) {
        // Clear any existing interval
        if (this.progressIntervals.has(uploadType)) {
            clearInterval(this.progressIntervals.get(uploadType));
        }
        
        const pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/admin/upload/progress/${uploadId}`, {
                    credentials: 'include'
                });
                
                if (response.ok) {
                    const progress = await response.json();
                    this.updateProgressBar(uploadType, progress);
                    
                    // Check if completed
                    if (progress.status === 'completed') {
                        clearInterval(pollInterval);
                        this.progressIntervals.delete(uploadType);
                        this.handleUploadComplete(uploadId, uploadType, progress);
                    } else if (progress.status === 'failed') {
                        clearInterval(pollInterval);
                        this.progressIntervals.delete(uploadType);
                        this.handleUploadError(uploadType, progress.error_message || 'Upload failed');
                    }
                } else if (response.status === 404) {
                    // Upload not found, might be completed already
                    clearInterval(pollInterval);
                    this.progressIntervals.delete(uploadType);
                    this.handleUploadComplete(uploadId, uploadType, null);
                }
            } catch (error) {
                console.error('Progress polling error:', error);
                // Continue polling, don't stop on network errors
            }
        }, 1000); // Poll every second
        
        this.progressIntervals.set(uploadType, pollInterval);
        
        // Set a timeout to stop polling after 30 minutes
        setTimeout(() => {
            if (this.progressIntervals.has(uploadType)) {
                clearInterval(this.progressIntervals.get(uploadType));
                this.progressIntervals.delete(uploadType);
                this.handleUploadError(uploadType, 'Upload timeout - please check server logs');
            }
        }, 30 * 60 * 1000); // 30 minutes
    }
    
    /**
     * Update progress bar and statistics
     */
    updateProgressBar(uploadType, progress) {
        const progressPercent = Math.round((progress.processed || 0) / Math.max(progress.total || 1, 1) * 100);
        
        // Update progress bar
        const progressFill = document.getElementById(`${uploadType}-progress-fill`);
        const progressText = document.getElementById(`${uploadType}-progress-text`);
        
        if (progressFill) {
            progressFill.style.width = `${progressPercent}%`;
        }
        
        if (progressText) {
            progressText.textContent = `${progressPercent}% complete`;
        }
        
        // Update statistics
        this.updateProgressStats(uploadType, progress);
    }
    
    /**
     * Update progress statistics
     */
    updateProgressStats(uploadType, progress) {
        const stats = {
            processed: progress.processed || 0,
            total: progress.total || 0,
            errors: progress.failed_records || progress.error_count || 0,
            speed: Math.round(progress.records_per_sec || 0)
        };
        
        // Update common stats
        this.updateStatElement(`${uploadType}-processed`, stats.processed);
        this.updateStatElement(`${uploadType}-total`, stats.total);
        this.updateStatElement(`${uploadType}-speed`, stats.speed);
        
        if (uploadType === 'tnved') {
            this.updateStatElement('tnved-errors', stats.errors);
        } else if (uploadType === 'url') {
            // URL uploads have additional stats
            this.updateStatElement('url-valid', progress.successful_records || 0);
            this.updateStatElement('url-invalid', stats.errors);
        }
    }
    
    /**
     * Update a single stat element
     */
    updateStatElement(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value.toLocaleString();
        }
    }
    
    /**
     * Handle upload completion
     */
    async handleUploadComplete(uploadId, uploadType, progressData) {
        console.log(`${uploadType} upload completed:`, progressData);
        
        this.hideProgress(uploadType);
        
        // Try to get detailed summary from server
        let summaryData = progressData;
        if (uploadId && uploadId !== 'unknown') {
            try {
                const response = await fetch(`/admin/upload/summary/${uploadId}`, {
                    credentials: 'include'
                });
                if (response.ok) {
                    summaryData = await response.json();
                }
            } catch (error) {
                console.warn('Could not fetch detailed summary:', error);
            }
        }
        
        this.showSummary(uploadType, summaryData);
        
        // Reset form for next upload
        this.resetForm(uploadType);
    }
    
    /**
     * Handle upload error
     */
    handleUploadError(uploadType, errorMessage) {
        console.error(`${uploadType} upload failed:`, errorMessage);
        
        this.hideProgress(uploadType);
        this.showError(errorMessage, uploadType);
        
        // Reset form
        this.resetForm(uploadType);
    }
    
    /**
     * Show upload summary
     */
    showSummary(uploadType, summaryData) {
        const summaryContainer = document.getElementById(`${uploadType}-summary`);
        const summaryStats = document.getElementById(`${uploadType}-summary-stats`);
        
        if (!summaryContainer || !summaryStats) return;
        
        // Build summary HTML
        let summaryHTML = '';
        
        if (summaryData) {
            const stats = [
                { label: 'Total Records', value: summaryData.total_records || 0 },
                { label: 'Successful', value: summaryData.successful_records || 0 },
                { label: 'Failed', value: summaryData.failed_records || 0 },
                { label: 'Processing Time', value: this.formatDuration(summaryData.processing_time_seconds || 0) },
                { label: 'Speed', value: `${Math.round(summaryData.records_per_second || 0)} rec/sec` },
                { label: 'Database Total', value: summaryData.database_total_records || 'N/A' }
            ];
            
            // Add upload-type specific stats
            if (uploadType === 'url') {
                stats.splice(3, 0, 
                    { label: 'Invalid URLs', value: summaryData.invalid_urls || 0 },
                    { label: 'Invalid Codes', value: summaryData.invalid_codes || 0 }
                );
            }
            
            summaryHTML = stats.map(stat => `
                <div class="summary-stat">
                    <span class="value">${stat.value}</span>
                    <div class="label">${stat.label}</div>
                </div>
            `).join('');
        } else {
            summaryHTML = `
                <div class="summary-stat">
                    <span class="value">✓</span>
                    <div class="label">Upload Completed</div>
                </div>
            `;
        }
        
        summaryStats.innerHTML = summaryHTML;
        summaryContainer.style.display = 'block';
    }
    
    /**
     * Show error message
     */
    showError(message, uploadType) {
        const errorContainer = document.getElementById(`${uploadType}-errors-container`);
        const errorMessage = document.getElementById(`${uploadType}-error-message`);
        
        if (errorContainer && errorMessage) {
            errorMessage.textContent = message;
            errorContainer.style.display = 'block';
        }
    }
    
    /**
     * Hide error message
     */
    hideError(uploadType) {
        const errorContainer = document.getElementById(`${uploadType}-errors-container`);
        if (errorContainer) {
            errorContainer.style.display = 'none';
        }
    }
    
    /**
     * Show progress section
     */
    showProgress(uploadType) {
        const progressContainer = document.getElementById(`${uploadType}-progress`);
        if (progressContainer) {
            progressContainer.style.display = 'block';
        }
    }
    
    /**
     * Hide progress section
     */
    hideProgress(uploadType) {
        const progressContainer = document.getElementById(`${uploadType}-progress`);
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }
    }
    
    /**
     * Show summary section
     */
    showSummary(uploadType, summaryData) {
        // Implementation already exists above
        this.showSummary(uploadType, summaryData);
    }
    
    /**
     * Hide summary section
     */
    hideSummary(uploadType) {
        const summaryContainer = document.getElementById(`${uploadType}-summary`);
        if (summaryContainer) {
            summaryContainer.style.display = 'none';
        }
    }
    
    /**
     * Set upload button state (enabled/disabled)
     */
    setUploadButtonState(uploadType, disabled) {
        const button = document.getElementById(`${uploadType}-upload-btn`);
        if (button) {
            button.disabled = disabled;
            if (disabled) {
                button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';
            } else {
                const text = uploadType === 'tnved' ? 'Upload TNVED Data' : 'Upload URL Mappings';
                button.innerHTML = `<i class="fas fa-upload"></i> ${text}`;
            }
        }
    }
    
    /**
     * Reset form after upload
     */
    resetForm(uploadType) {
        const form = document.getElementById(`${uploadType}-upload-form`);
        const wrapper = document.getElementById(`${uploadType}-file-wrapper`);
        const label = wrapper.querySelector('.file-input-label span');
        
        if (form) {
            form.reset();
        }
        
        if (wrapper) {
            wrapper.classList.remove('has-file');
        }
        
        if (label) {
            const text = uploadType === 'tnved' ? 'Select TNVED file or drag here' : 'Select URL mapping file or drag here';
            label.innerHTML = text + '<br><small style="margin-top: 5px; color: #999;">Supported: .xlsx, .xls, .parquet (max 100MB)</small>';
        }
    }
    
    /**
     * Show loading overlay
     */
    showLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'flex';
        }
    }
    
    /**
     * Hide loading overlay
     */
    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }
    
    /**
     * Format file size for display
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    /**
     * Format duration in seconds to human readable format
     */
    formatDuration(seconds) {
        if (seconds < 60) {
            return `${Math.round(seconds)}s`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = Math.round(seconds % 60);
            return `${minutes}m ${remainingSeconds}s`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new AdminUploadApp();
});