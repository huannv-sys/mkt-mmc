/**
 * MikroTik MSC - Quản lý Backup Manager
 * 
 * File này chứa các chức năng liên quan đến quản lý backup/restore
 */

document.addEventListener('DOMContentLoaded', function() {
    // Các elements
    const backupListContainer = document.getElementById('backupListContainer');
    const createBackupModal = new bootstrap.Modal(document.getElementById('createBackupModal'));
    const uploadBackupModal = new bootstrap.Modal(document.getElementById('uploadBackupModal'));
    const restoreConfirmModal = new bootstrap.Modal(document.getElementById('restoreConfirmModal'));
    const viewExportModal = new bootstrap.Modal(document.getElementById('viewExportModal'));
    
    const backupType = document.getElementById('backupType');
    const backupTypeInfo = document.getElementById('backupTypeInfo');
    const sensitiveInfoContainer = document.getElementById('sensitiveInfoContainer');
    const scheduleTimeContainer = document.getElementById('scheduleTimeContainer');
    const scheduleIntervalContainer = document.getElementById('scheduleIntervalContainer');
    const scheduleDate = document.getElementById('scheduleDate');
    const scheduleTimeInput = document.getElementById('scheduleTimeInput');
    const createBackupBtn = document.getElementById('createBackupBtn');
    const createBackupSpinner = document.getElementById('createBackupSpinner');
    const createBackupIcon = document.getElementById('createBackupIcon');
    
    const uploadBackupBtn = document.getElementById('uploadBackupBtn');
    const uploadBackupSpinner = document.getElementById('uploadBackupSpinner');
    const uploadBackupIcon = document.getElementById('uploadBackupIcon');
    
    const refreshBackupListBtn = document.getElementById('refreshBackupList');
    const restoreFileName = document.getElementById('restoreFileName');
    const restoreBackupInfo = document.getElementById('restoreBackupInfo');
    const restoreExportInfo = document.getElementById('restoreExportInfo');
    const confirmRestoreBtn = document.getElementById('confirmRestoreBtn');
    const restoreSpinner = document.getElementById('restoreSpinner');
    const restoreIcon = document.getElementById('restoreIcon');
    
    const viewExportFileName = document.getElementById('viewExportFileName');
    const exportContent = document.getElementById('exportContent');
    const copyExportContentBtn = document.getElementById('copyExportContentBtn');
    
    // Thêm event listeners
    backupType.addEventListener('change', toggleBackupTypeInfo);
    createBackupBtn.addEventListener('click', createBackup);
    uploadBackupBtn.addEventListener('click', uploadBackup);
    refreshBackupListBtn.addEventListener('click', loadBackups);
    confirmRestoreBtn.addEventListener('click', restoreBackup);
    copyExportContentBtn.addEventListener('click', copyExportContent);
    
    // Xử lý ẩn/hiện lịch backup
    document.querySelector('input[name="schedule_type"][value="now"]').addEventListener('change', toggleScheduleOptions);
    document.querySelector('input[name="schedule_type"][value="scheduled"]').addEventListener('change', toggleScheduleOptions);
    
    // Xử lý ẩn/hiện tùy chọn lặp lại
    document.getElementById('scheduleRecurring').addEventListener('change', function() {
        document.getElementById('scheduleIntervalContainer').classList.toggle('d-none', !this.checked);
    });
    
    // Thiết lập giá trị mặc định cho ngày và giờ
    const now = new Date();
    const formattedDate = now.toISOString().split('T')[0];
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const formattedTime = `${hours}:${minutes}`;
    
    scheduleDate.value = formattedDate;
    scheduleTimeInput.value = formattedTime;
    
    // Biến lưu trữ thông tin file hiện tại đang xử lý
    let currentBackupFile = null;
    
    // Khởi tạo
    loadBackups();
    
    /**
     * Cập nhật thông tin về loại backup
     */
    function toggleBackupTypeInfo() {
        if (backupType.value === 'backup') {
            backupTypeInfo.textContent = 'Sao lưu hoàn chỉnh hệ thống. Khi khôi phục, thiết bị sẽ khởi động lại.';
            sensitiveInfoContainer.classList.add('d-none');
        } else {
            backupTypeInfo.textContent = 'Xuất cấu hình dạng văn bản, có thể chỉnh sửa. Hỗ trợ tùy chọn ẩn thông tin nhạy cảm.';
            sensitiveInfoContainer.classList.remove('d-none');
        }
    }
    
    /**
     * Tải danh sách các file backup
     */
    async function loadBackups() {
        try {
            showLoading(backupListContainer, true);
            
            const response = await fetch('/api/backup/list');
            const data = await response.json();
            
            if (data.success) {
                renderBackupList(data.data);
            } else {
                showToast('error', data.error || 'Không thể tải danh sách backup');
                backupListContainer.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-circle"></i> Lỗi: ${data.error || 'Không thể tải danh sách backup'}
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading backups:', error);
            showToast('error', 'Lỗi kết nối khi tải danh sách backup');
            backupListContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle"></i> Lỗi kết nối khi tải danh sách backup
                </div>
            `;
        } finally {
            showLoading(backupListContainer, false);
        }
    }
    
    /**
     * Hiển thị danh sách backup
     * @param {Array} backups - Danh sách các file backup
     */
    function renderBackupList(backups) {
        if (!backups || backups.length === 0) {
            backupListContainer.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle"></i> Chưa có file backup nào. Hãy tạo mới hoặc tải lên.
                </div>
            `;
            return;
        }
        
        // Tạo bảng
        let html = `
            <div class="table-responsive">
                <table class="table table-hover align-middle">
                    <thead class="table-light">
                        <tr>
                            <th>Tên file</th>
                            <th>Loại</th>
                            <th>Kích thước</th>
                            <th>Ngày tạo</th>
                            <th>Hành động</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        // Thêm các dòng
        backups.forEach(backup => {
            html += `
                <tr>
                    <td>
                        <div class="d-flex align-items-center">
                            <i class="fas ${backup.type === 'backup' ? 'fa-save' : 'fa-file-code'} text-${backup.type === 'backup' ? 'primary' : 'success'} me-2"></i>
                            <span>${backup.name}</span>
                        </div>
                    </td>
                    <td>
                        <span class="badge bg-${backup.type === 'backup' ? 'primary' : 'success'}">${backup.type === 'backup' ? 'Backup' : 'Export'}</span>
                    </td>
                    <td>${formatFileSize(backup.size)}</td>
                    <td>${backup.created}</td>
                    <td>
                        <div class="btn-group">
                            <button class="btn btn-sm btn-outline-secondary download-backup" data-filename="${backup.name}">
                                <i class="fas fa-download"></i>
                            </button>
                            ${backup.type === 'export' ? 
                                `<button class="btn btn-sm btn-outline-secondary view-export" data-filename="${backup.name}">
                                    <i class="fas fa-eye"></i>
                                </button>` : 
                                ''}
                            <button class="btn btn-sm btn-outline-warning restore-backup" data-filename="${backup.name}" data-type="${backup.type}">
                                <i class="fas fa-sync-alt"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger delete-backup" data-filename="${backup.name}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        // Cập nhật container
        backupListContainer.innerHTML = html;
        
        // Thêm event listeners cho các nút
        document.querySelectorAll('.download-backup').forEach(btn => {
            btn.addEventListener('click', function() {
                downloadBackup(this.dataset.filename);
            });
        });
        
        document.querySelectorAll('.view-export').forEach(btn => {
            btn.addEventListener('click', function() {
                viewExport(this.dataset.filename);
            });
        });
        
        document.querySelectorAll('.restore-backup').forEach(btn => {
            btn.addEventListener('click', function() {
                showRestoreConfirm(this.dataset.filename, this.dataset.type);
            });
        });
        
        document.querySelectorAll('.delete-backup').forEach(btn => {
            btn.addEventListener('click', function() {
                deleteBackup(this.dataset.filename);
            });
        });
    }
    
    /**
     * Ẩn/hiện các tùy chọn lịch backup
     */
    function toggleScheduleOptions() {
        const isScheduled = document.querySelector('input[name="schedule_type"][value="scheduled"]').checked;
        scheduleTimeContainer.classList.toggle('d-none', !isScheduled);
    }
    
    /**
     * Tạo backup mới
     */
    async function createBackup() {
        try {
            // Xác định loại lịch
            const scheduleType = document.querySelector('input[name="schedule_type"]:checked').value;
            
            // Tạo form data
            const data = {
                type: backupType.value,
                name: document.getElementById('backupName').value.trim(),
                include_sensitive: document.getElementById('includeSensitive').checked,
                device_id: document.getElementById('deviceSelect').value,
                schedule_type: scheduleType
            };
            
            // Nếu là backup theo lịch, bổ sung thông tin lịch
            if (scheduleType === 'scheduled') {
                data.schedule_date = scheduleDate.value;
                data.schedule_time = scheduleTimeInput.value;
                data.schedule_recurring = document.getElementById('scheduleRecurring').checked;
                
                if (data.schedule_recurring) {
                    data.schedule_interval = document.getElementById('scheduleInterval').value;
                }
            }
            
            // Hiển thị spinner
            toggleButtonLoading(createBackupBtn, createBackupSpinner, createBackupIcon, true);
            
            // Gửi request
            const response = await fetch('/api/backup/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            // Xử lý kết quả
            if (result.success) {
                showToast('success', result.message || 'Đã tạo backup thành công');
                createBackupModal.hide();
                
                // Reset form
                document.getElementById('createBackupForm').reset();
                
                // Làm mới danh sách
                loadBackups();
            } else {
                showToast('error', result.error || 'Không thể tạo backup');
            }
        } catch (error) {
            console.error('Error creating backup:', error);
            showToast('error', 'Lỗi kết nối khi tạo backup');
        } finally {
            // Ẩn spinner
            toggleButtonLoading(createBackupBtn, createBackupSpinner, createBackupIcon, false);
        }
    }
    
    /**
     * Tải lên file backup
     */
    async function uploadBackup() {
        try {
            const fileInput = document.getElementById('backupFile');
            
            if (!fileInput.files || fileInput.files.length === 0) {
                showToast('error', 'Vui lòng chọn file để tải lên');
                return;
            }
            
            // Hiển thị spinner
            toggleButtonLoading(uploadBackupBtn, uploadBackupSpinner, uploadBackupIcon, true);
            
            // Tạo FormData
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            
            // Gửi request
            const response = await fetch('/api/backup/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            // Xử lý kết quả
            if (result.success) {
                showToast('success', result.message || 'Đã tải lên file thành công');
                uploadBackupModal.hide();
                
                // Reset form
                document.getElementById('uploadBackupForm').reset();
                
                // Làm mới danh sách
                loadBackups();
            } else {
                showToast('error', result.error || 'Không thể tải lên file');
            }
        } catch (error) {
            console.error('Error uploading backup:', error);
            showToast('error', 'Lỗi kết nối khi tải lên file');
        } finally {
            // Ẩn spinner
            toggleButtonLoading(uploadBackupBtn, uploadBackupSpinner, uploadBackupIcon, false);
        }
    }
    
    /**
     * Tải xuống file backup
     * @param {string} filename - Tên file cần tải xuống
     */
    function downloadBackup(filename) {
        try {
            // Tạo URL tải xuống
            const downloadUrl = `/api/backup/download/${filename}`;
            
            // Tạo thẻ a ẩn và kích hoạt click
            const downloadLink = document.createElement('a');
            downloadLink.href = downloadUrl;
            downloadLink.download = filename;
            document.body.appendChild(downloadLink);
            downloadLink.click();
            document.body.removeChild(downloadLink);
            
            showToast('info', `Đang tải xuống file ${filename}`);
        } catch (error) {
            console.error('Error downloading backup:', error);
            showToast('error', 'Không thể tải xuống file');
        }
    }
    
    /**
     * Xem nội dung file export
     * @param {string} filename - Tên file export cần xem
     */
    async function viewExport(filename) {
        try {
            // Hiển thị tên file
            viewExportFileName.textContent = filename;
            
            // Lấy nội dung file
            const response = await fetch(`/api/backup/download/${filename}`);
            const content = await response.text();
            
            // Hiển thị nội dung
            exportContent.textContent = content;
            
            // Hiển thị modal
            viewExportModal.show();
        } catch (error) {
            console.error('Error viewing export:', error);
            showToast('error', 'Không thể xem nội dung file export');
        }
    }
    
    /**
     * Sao chép nội dung export vào clipboard
     */
    function copyExportContent() {
        try {
            const content = exportContent.textContent;
            navigator.clipboard.writeText(content);
            showToast('success', 'Đã sao chép nội dung vào clipboard');
        } catch (error) {
            console.error('Error copying export content:', error);
            showToast('error', 'Không thể sao chép nội dung');
        }
    }
    
    /**
     * Hiển thị modal xác nhận khôi phục
     * @param {string} filename - Tên file backup cần khôi phục
     * @param {string} type - Loại file (backup hoặc export)
     */
    function showRestoreConfirm(filename, type) {
        // Lưu thông tin file hiện tại
        currentBackupFile = { filename, type };
        
        // Hiển thị tên file
        restoreFileName.textContent = filename;
        
        // Hiển thị thông tin tương ứng với loại file
        if (type === 'backup') {
            restoreBackupInfo.classList.remove('d-none');
            restoreExportInfo.classList.add('d-none');
        } else {
            restoreBackupInfo.classList.add('d-none');
            restoreExportInfo.classList.remove('d-none');
        }
        
        // Hiển thị modal
        restoreConfirmModal.show();
    }
    
    /**
     * Khôi phục từ file backup
     */
    async function restoreBackup() {
        try {
            if (!currentBackupFile) {
                showToast('error', 'Không có file nào được chọn');
                return;
            }
            
            // Hiển thị spinner
            toggleButtonLoading(confirmRestoreBtn, restoreSpinner, restoreIcon, true);
            
            // Gửi request
            const response = await fetch('/api/backup/restore', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    filename: currentBackupFile.filename
                })
            });
            
            const result = await response.json();
            
            // Xử lý kết quả
            if (result.success) {
                showToast('success', result.message || 'Đã khôi phục thành công');
                restoreConfirmModal.hide();
                
                // Reset thông tin file hiện tại
                currentBackupFile = null;
            } else {
                showToast('error', result.error || 'Không thể khôi phục');
            }
        } catch (error) {
            console.error('Error restoring backup:', error);
            showToast('error', 'Lỗi kết nối khi khôi phục');
        } finally {
            // Ẩn spinner
            toggleButtonLoading(confirmRestoreBtn, restoreSpinner, restoreIcon, false);
        }
    }
    
    /**
     * Xóa file backup
     * @param {string} filename - Tên file backup cần xóa
     */
    async function deleteBackup(filename) {
        // Xác nhận xóa
        if (!confirm(`Bạn có chắc chắn muốn xóa file ${filename}?`)) {
            return;
        }
        
        try {
            // Gửi request
            const response = await fetch(`/api/backup/delete/${filename}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            // Xử lý kết quả
            if (result.success) {
                showToast('success', result.message || `Đã xóa file ${filename}`);
                
                // Làm mới danh sách
                loadBackups();
            } else {
                showToast('error', result.error || 'Không thể xóa file');
            }
        } catch (error) {
            console.error('Error deleting backup:', error);
            showToast('error', 'Lỗi kết nối khi xóa file');
        }
    }
    
    /**
     * Hiển thị/ẩn loading spinner
     * @param {HTMLElement} container - Container chứa spinner
     * @param {boolean} show - true để hiển thị, false để ẩn
     */
    function showLoading(container, show) {
        if (show) {
            container.innerHTML = `
                <div class="d-flex justify-content-center py-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            `;
        }
    }
    
    /**
     * Hiển thị/ẩn loading trên nút
     * @param {HTMLElement} button - Nút cần xử lý
     * @param {HTMLElement} spinner - Element spinner
     * @param {HTMLElement} icon - Element icon
     * @param {boolean} loading - true để hiển thị loading, false để ẩn
     */
    function toggleButtonLoading(button, spinner, icon, loading) {
        if (loading) {
            button.disabled = true;
            spinner.classList.remove('d-none');
            icon.classList.add('d-none');
        } else {
            button.disabled = false;
            spinner.classList.add('d-none');
            icon.classList.remove('d-none');
        }
    }
    
    /**
     * Hiển thị thông báo toast
     * @param {string} type - Kiểu thông báo (success, error, warning, info)
     * @param {string} message - Nội dung thông báo
     */
    function showToast(type, message) {
        // Sử dụng showToast từ file main.js
        if (typeof window.showToast === 'function') {
            window.showToast(type, message);
        } else {
            // Fallback nếu không tìm thấy hàm showToast toàn cục
            const toastEl = document.getElementById('notificationToast');
            const toastBody = toastEl.querySelector('.toast-body');
            
            // Set toast color based on type
            toastEl.className = 'toast align-items-center';
            if (type === 'success') {
                toastEl.classList.add('text-bg-success');
            } else if (type === 'error') {
                toastEl.classList.add('text-bg-danger');
            } else if (type === 'warning') {
                toastEl.classList.add('text-bg-warning');
            } else {
                toastEl.classList.add('text-bg-info');
            }
            
            toastBody.textContent = message;
            
            const toast = new bootstrap.Toast(toastEl);
            toast.show();
        }
    }
    
    /**
     * Định dạng kích thước file
     * @param {number} bytes - Kích thước tính bằng bytes
     * @returns {string} Kích thước đã định dạng
     */
    function formatFileSize(bytes) {
        // Sử dụng formatBytes từ file main.js nếu có
        if (typeof window.formatBytes === 'function') {
            return window.formatBytes(bytes);
        } else {
            // Fallback nếu không tìm thấy hàm formatBytes toàn cục
            if (bytes === 0) return '0 Bytes';
            
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
    }
});