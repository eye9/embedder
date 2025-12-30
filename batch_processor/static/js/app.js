/**
 * Batch Excel Processor - Client-side Application
 * 
 * This module handles the client-side functionality including:
 * - User authentication
 * - File upload with progress tracking
 * - WebSocket connection for real-time updates
 * - Dynamic UI updates for processing status
 */

class BatchProcessorApp {
    constructor() {
        this.currentTaskId = null;
        this.websocket = null;
        this.authCredentials = null;
        this.uploadedFile = null;
        
        // Initialize the application
        this.init();
    }
    
    /**
     * Initialize the application
     */
    init() {
        this.setupEventListeners();
        this.showAuthSection();
    }
    
    /**
     * Setup event listeners for UI interactions
     */
    setupEventListeners() {
        // Authentication form
        const authForm = document.getElementById('auth-form');
        authForm.addEventListener('submit', (e) => this.handleAuth(e));
        
        // File upload form
        const uploadForm = document.getElementById('upload-form');
        uploadForm.addEventListener('submit', (e) => this.handleFileUpload(e));
        
        // File input change
        const fileInput = document.getElementById('file-input');
        fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Drag and drop for file input
        const fileInputWrapper = document.querySelector('.file-input-wrapper');
        fileInputWrapper.addEventListener('dragover', (e) => this.handleDragOver(e));
        fileInputWrapper.addEventListener('drop', (e) => this.handleFileDrop(e));
        
        // Download button
        const downloadBtn = document.getElementById('download-btn');
        downloadBtn.addEventListener('click', () => this.handleDownload());
        
        // New file button
        const newFileBtn = document.getElementById('new-file-btn');
        newFileBtn.addEventListener('click', () => this.resetToUpload());
        
        // Retry button
        const retryBtn = document.getElementById('retry-btn');
        retryBtn.addEventListener('click', () => this.resetToUpload());
    }
    
    /**
     * Handle user authentication
     */
    async handleAuth(event) {
        event.preventDefault();
        
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        // Store credentials for API calls
        this.authCredentials = btoa(`${username}:${password}`);
        
        try {
            this.showLoading();
            
            // Test authentication by calling a protected endpoint
            const response = await this.makeAuthenticatedRequest('/health');
            
            if (response.ok) {
                this.hideAuthError();
                this.showAppSection();
            } else {
                throw new Error('Invalid credentials');
            }
        } catch (error) {
            this.showAuthError('Неверные учетные данные. Попробуйте снова.');
            this.authCredentials = null;
        } finally {
            this.hideLoading();
        }
    }
    
    /**
     * Handle file selection
     */
    handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            this.uploadedFile = file;
            this.updateFileInputDisplay(file);
            this.validateFile(file);
        }
    }
    
    /**
     * Handle drag over event
     */
    handleDragOver(event) {
        event.preventDefault();
        event.currentTarget.classList.add('drag-over');
    }
    
    /**
     * Handle file drop
     */
    handleFileDrop(event) {
        event.preventDefault();
        event.currentTarget.classList.remove('drag-over');
        
        const files = event.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            document.getElementById('file-input').files = files;
            this.uploadedFile = file;
            this.updateFileInputDisplay(file);
            this.validateFile(file);
        }
    }
    
    /**
     * Update file input display
     */
    updateFileInputDisplay(file) {
        const wrapper = document.querySelector('.file-input-wrapper');
        const label = wrapper.querySelector('.file-input-label span');
        
        wrapper.classList.add('has-file');
        label.textContent = `Выбран файл: ${file.name} (${this.formatFileSize(file.size)})`;
    }
    
    /**
     * Validate selected file
     */
    async validateFile(file) {
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await this.makeAuthenticatedRequest('/upload/validate', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.is_valid) {
                    this.showValidationInfo(result);
                } else {
                    this.showUploadError(result.error_message);
                }
            } else {
                throw new Error('Validation failed');
            }
        } catch (error) {
            this.showUploadError('Ошибка при проверке файла: ' + error.message);
        }
    }
    
    /**
     * Handle file upload and processing
     */
    async handleFileUpload(event) {
        event.preventDefault();
        
        if (!this.uploadedFile) {
            this.showUploadError('Пожалуйста, выберите файл для загрузки');
            return;
        }
        
        try {
            this.showLoading();
            
            const formData = new FormData();
            formData.append('file', this.uploadedFile);
            formData.append('process_mode', document.getElementById('process-mode').value);
            formData.append('algorithm', document.getElementById('algorithm').value);
            
            const response = await this.makeAuthenticatedRequest('/upload', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                this.currentTaskId = result.task_id;
                this.showProgressSection();
                this.connectWebSocket(result.task_id);
                this.startProgressPolling(result.task_id);
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Upload failed');
            }
        } catch (error) {
            this.showUploadError('Ошибка при загрузке файла: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    /**
     * Connect to WebSocket for real-time updates
     */
    connectWebSocket(taskId) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${taskId}`;
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket connected');
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.updateProgress(data);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };
            
            this.websocket.onclose = (event) => {
                console.log('WebSocket disconnected:', event.code, event.reason);
                // Don't try to reconnect automatically to avoid spam
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                // WebSocket failed, rely on polling only
                this.websocket = null;
            };
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.websocket = null;
        }
    }
    
    /**
     * Start polling for progress updates (fallback for WebSocket)
     */
    startProgressPolling(taskId) {
        const pollInterval = setInterval(async () => {
            try {
                const response = await this.makeAuthenticatedRequest(`/task/${taskId}/status`);
                if (response.ok) {
                    const status = await response.json();
                    
                    if (status.status === 'completed') {
                        clearInterval(pollInterval);
                        this.handleProcessingComplete(taskId);
                    } else if (status.status === 'failed') {
                        clearInterval(pollInterval);
                        this.handleProcessingError(status.error_message);
                    } else {
                        this.updateProgressFromStatus(status);
                    }
                }
            } catch (error) {
                console.error('Error polling progress:', error);
            }
        }, 2000); // Poll every 2 seconds
        
        // Store interval ID for cleanup
        this.progressInterval = pollInterval;
    }
    
    /**
     * Update progress display
     */
    updateProgress(data) {
        const progressPercent = Math.round(data.progress * 100);
        
        // Update progress bar
        const progressFill = document.getElementById('progress-fill');
        progressFill.style.width = `${progressPercent}%`;
        
        // Update statistics
        document.getElementById('processed-rows').textContent = data.processed_rows || 0;
        document.getElementById('total-rows').textContent = data.total_rows || 0;
        document.getElementById('error-count').textContent = data.error_count || 0;
        document.getElementById('progress-percent').textContent = `${progressPercent}%`;
        
        // Update time remaining
        const timeRemaining = document.getElementById('time-remaining');
        if (data.estimated_time_remaining) {
            timeRemaining.textContent = this.formatTimeRemaining(data.estimated_time_remaining);
        } else {
            timeRemaining.textContent = 'Расчет...';
        }
        
        // Update current operation
        const currentOperation = document.getElementById('current-operation');
        if (data.current_operation) {
            currentOperation.textContent = data.current_operation;
        }
    }
    
    /**
     * Update progress from status polling
     */
    updateProgressFromStatus(status) {
        this.updateProgress({
            progress: status.progress,
            processed_rows: status.processed_rows,
            total_rows: status.total_rows,
            error_count: status.error_count,
            estimated_time_remaining: status.estimated_time_remaining
        });
    }
    
    /**
     * Handle processing completion
     */
    async handleProcessingComplete(taskId) {
        try {
            // Close WebSocket
            if (this.websocket) {
                this.websocket.close();
                this.websocket = null;
            }
            
            // Clear polling interval
            if (this.progressInterval) {
                clearInterval(this.progressInterval);
            }
            
            // Get processing summary
            const response = await this.makeAuthenticatedRequest(`/task/${taskId}/summary`);
            if (response.ok) {
                const summary = await response.json();
                this.showResults(summary);
            } else {
                this.showResults(null);
            }
        } catch (error) {
            console.error('Error handling completion:', error);
            this.showResults(null);
        }
    }
    
    /**
     * Handle processing error
     */
    handleProcessingError(errorMessage) {
        // Close WebSocket
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        // Clear polling interval
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }
        
        this.showError(errorMessage || 'Произошла ошибка при обработке файла');
    }
    
    /**
     * Handle file download
     */
    async handleDownload() {
        if (!this.currentTaskId) {
            return;
        }
        
        try {
            const response = await this.makeAuthenticatedRequest(`/task/${this.currentTaskId}/download/file`);
            
            if (response.ok) {
                // Create download link
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `processed_${this.uploadedFile.name}`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            } else {
                throw new Error('Download failed');
            }
        } catch (error) {
            alert('Ошибка при скачивании файла: ' + error.message);
        }
    }
    
    /**
     * Make authenticated API request
     */
    async makeAuthenticatedRequest(url, options = {}) {
        const headers = {
            ...options.headers
        };
        
        if (this.authCredentials) {
            headers['Authorization'] = `Basic ${this.authCredentials}`;
        }
        
        return fetch(url, {
            ...options,
            headers
        });
    }
    
    /**
     * Show authentication section
     */
    showAuthSection() {
        document.getElementById('auth-section').style.display = 'flex';
        document.getElementById('app-section').style.display = 'none';
    }
    
    /**
     * Show main application section
     */
    showAppSection() {
        document.getElementById('auth-section').style.display = 'none';
        document.getElementById('app-section').style.display = 'block';
        this.resetToUpload();
    }
    
    /**
     * Show validation information
     */
    showValidationInfo(result) {
        const validationSection = document.getElementById('validation-section');
        const validationInfo = document.getElementById('validation-info');
        
        validationInfo.innerHTML = `
            <div class="validation-stat">
                <span class="stat-value">${result.total_rows}</span>
                <div class="stat-label">Всего строк</div>
            </div>
            <div class="validation-stat">
                <span class="stat-value">${result.rows_with_descriptions}</span>
                <div class="stat-label">Строк с описаниями</div>
            </div>
            <div class="validation-stat">
                <span class="stat-value">${result.rows_with_existing_codes}</span>
                <div class="stat-label">Строк с кодами HTS</div>
            </div>
        `;
        
        validationSection.style.display = 'block';
        validationSection.classList.add('fade-in');
    }
    
    /**
     * Show progress section
     */
    showProgressSection() {
        this.hideAllSections();
        document.getElementById('progress-section').style.display = 'block';
        document.getElementById('progress-section').classList.add('slide-up');
    }
    
    /**
     * Show results section
     */
    showResults(summary) {
        this.hideAllSections();
        
        const resultsSection = document.getElementById('results-section');
        const summaryDiv = document.getElementById('processing-summary');
        
        if (summary) {
            summaryDiv.innerHTML = `
                <div class="summary-grid">
                    <div class="summary-item">
                        <span class="summary-value">${summary.processed_rows}</span>
                        <div class="summary-label">Обработано строк</div>
                    </div>
                    <div class="summary-item">
                        <span class="summary-value">${summary.successful_assignments}</span>
                        <div class="summary-label">Успешных назначений</div>
                    </div>
                    <div class="summary-item">
                        <span class="summary-value">${summary.failed_assignments}</span>
                        <div class="summary-label">Неудачных назначений</div>
                    </div>
                    <div class="summary-item">
                        <span class="summary-value">${Math.round(summary.processing_time_seconds)}с</span>
                        <div class="summary-label">Время обработки</div>
                    </div>
                </div>
            `;
        } else {
            summaryDiv.innerHTML = '<p>Обработка завершена. Сводка недоступна.</p>';
        }
        
        resultsSection.style.display = 'block';
        resultsSection.classList.add('slide-up');
    }
    
    /**
     * Show error section
     */
    showError(errorMessage) {
        this.hideAllSections();
        
        const errorSection = document.getElementById('error-section');
        const errorDetails = document.getElementById('error-details');
        
        errorDetails.textContent = errorMessage;
        errorSection.style.display = 'block';
        errorSection.classList.add('slide-up');
    }
    
    /**
     * Reset to upload state
     */
    resetToUpload() {
        this.hideAllSections();
        this.currentTaskId = null;
        this.uploadedFile = null;
        
        // Reset form
        document.getElementById('upload-form').reset();
        document.querySelector('.file-input-wrapper').classList.remove('has-file');
        document.querySelector('.file-input-label span').textContent = 'Выберите Excel файл или перетащите сюда';
        
        // Show upload section
        document.getElementById('upload-section').style.display = 'block';
        
        // Clear errors
        this.hideUploadError();
    }
    
    /**
     * Hide all main sections
     */
    hideAllSections() {
        const sections = [
            'upload-section',
            'validation-section', 
            'progress-section',
            'results-section',
            'error-section'
        ];
        
        sections.forEach(sectionId => {
            const section = document.getElementById(sectionId);
            section.style.display = 'none';
            section.classList.remove('fade-in', 'slide-up');
        });
    }
    
    /**
     * Show loading overlay
     */
    showLoading() {
        document.getElementById('loading-overlay').style.display = 'flex';
    }
    
    /**
     * Hide loading overlay
     */
    hideLoading() {
        document.getElementById('loading-overlay').style.display = 'none';
    }
    
    /**
     * Show authentication error
     */
    showAuthError(message) {
        const errorDiv = document.getElementById('auth-error');
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }
    
    /**
     * Hide authentication error
     */
    hideAuthError() {
        document.getElementById('auth-error').style.display = 'none';
    }
    
    /**
     * Show upload error
     */
    showUploadError(message) {
        const errorDiv = document.getElementById('upload-error');
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }
    
    /**
     * Hide upload error
     */
    hideUploadError() {
        document.getElementById('upload-error').style.display = 'none';
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
     * Format time remaining for display
     */
    formatTimeRemaining(seconds) {
        if (seconds < 60) {
            return `${Math.round(seconds)}с`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = Math.round(seconds % 60);
            return `${minutes}м ${remainingSeconds}с`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}ч ${minutes}м`;
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new BatchProcessorApp();
});