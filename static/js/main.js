/**
 * MikroTik MSC - JavaScript chính
 * 
 * File này chứa các utility function được sử dụng trong toàn bộ ứng dụng
 */

/**
 * Định dạng bytes thành đơn vị dễ đọc (KB, MB, GB)
 * @param {number} bytes - Số bytes cần định dạng
 * @param {number} decimals - Số chữ số thập phân
 * @returns {string} Giá trị đã định dạng
 */
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals)) + ' ' + sizes[i];
}

/**
 * Định dạng thời gian uptime
 * @param {string} uptime - Thời gian uptime theo định dạng MikroTik
 * @returns {string} Thời gian đã định dạng
 */
function formatUptime(uptime) {
    if (!uptime) return 'N/A';
    
    // MikroTik format: "1w2d3h4m5s"
    let result = uptime;
    
    result = result.replace(/w/g, ' tuần ');
    result = result.replace(/d/g, ' ngày ');
    result = result.replace(/h/g, ' giờ ');
    result = result.replace(/m(?!s)/g, ' phút ');
    result = result.replace(/s/g, ' giây');
    
    return result;
}

/**
 * Định dạng ngày giờ
 * @param {string|Date} date - Ngày cần định dạng
 * @returns {string} Ngày đã định dạng
 */
function formatDateTime(date) {
    if (!date) return 'N/A';
    
    const d = new Date(date);
    if (isNaN(d.getTime())) return date; // Nếu không parse được thì trả về giá trị gốc
    
    return d.toLocaleString('vi-VN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

/**
 * Hiển thị thông báo toast
 * @param {string} type - Kiểu thông báo (success, error, warning, info)
 * @param {string} message - Nội dung thông báo
 * @param {number} duration - Thời gian hiển thị (ms)
 */
function showToast(type, message, duration = 5000) {
    // Kiểm tra xem đã có toast container chưa
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        toastContainer.style.zIndex = '1100';
        document.body.appendChild(toastContainer);
    }
    
    // Tạo toast
    const toastId = 'toast-' + Date.now();
    const toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    
    // Hiển thị toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: duration
    });
    
    toast.show();
    
    // Xóa toast khỏi DOM sau khi ẩn
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

/**
 * Hiển thị hộp thoại xác nhận
 * @param {string} title - Tiêu đề
 * @param {string} message - Nội dung
 * @param {Function} onConfirm - Callback khi xác nhận
 * @param {Function} onCancel - Callback khi hủy
 * @param {string} confirmText - Nội dung nút xác nhận
 * @param {string} cancelText - Nội dung nút hủy
 * @param {string} confirmClass - Class cho nút xác nhận
 */
function showConfirmDialog(title, message, onConfirm, onCancel = null, confirmText = 'Xác nhận', cancelText = 'Hủy', confirmClass = 'btn-danger') {
    // Kiểm tra xem đã có modal container chưa
    const modalId = 'confirmModal';
    let modalElement = document.getElementById(modalId);
    
    if (modalElement) {
        // Xóa modal cũ
        modalElement.remove();
    }
    
    // Tạo modal mới
    const modalHTML = `
        <div class="modal fade" id="${modalId}" tabindex="-1" aria-labelledby="${modalId}Label" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="${modalId}Label">${title}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        ${message}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">${cancelText}</button>
                        <button type="button" class="btn ${confirmClass}" id="${modalId}ConfirmBtn">${confirmText}</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Lấy modal element
    modalElement = document.getElementById(modalId);
    const modal = new bootstrap.Modal(modalElement);
    
    // Xử lý sự kiện click nút xác nhận
    const confirmBtn = document.getElementById(`${modalId}ConfirmBtn`);
    confirmBtn.addEventListener('click', function() {
        if (typeof onConfirm === 'function') {
            onConfirm();
        }
        modal.hide();
    });
    
    // Xử lý sự kiện khi modal đóng
    if (typeof onCancel === 'function') {
        modalElement.addEventListener('hidden.bs.modal', function(event) {
            // Kiểm tra xem đóng bằng nút Cancel hay không
            if (event.target.querySelector(`#${modalId}ConfirmBtn`).getAttribute('clicked') !== 'true') {
                onCancel();
            }
        });
        
        confirmBtn.addEventListener('click', function() {
            this.setAttribute('clicked', 'true');
        });
    }
    
    // Hiển thị modal
    modal.show();
    
    // Xóa modal khỏi DOM sau khi ẩn
    modalElement.addEventListener('hidden.bs.modal', function() {
        setTimeout(() => {
            modalElement.remove();
        }, 200);
    });
}

/**
 * Khởi tạo DataTable
 * @param {string} selector - CSS Selector cho table
 * @param {object} options - Tùy chọn cho DataTable
 * @returns {object} DataTable instance
 */
function initDataTable(selector, options = {}) {
    // Mặc định options
    const defaultOptions = {
        language: {
            lengthMenu: 'Hiển thị _MENU_ bản ghi',
            zeroRecords: 'Không tìm thấy dữ liệu',
            info: 'Hiển thị _START_ đến _END_ của _TOTAL_ bản ghi',
            infoEmpty: 'Hiển thị 0 đến 0 của 0 bản ghi',
            infoFiltered: '(lọc từ _MAX_ bản ghi)',
            search: 'Tìm kiếm:',
            paginate: {
                first: 'Đầu',
                last: 'Cuối',
                next: 'Sau',
                previous: 'Trước'
            }
        },
        responsive: true,
        autoWidth: false
    };
    
    // Merge options
    const mergedOptions = {...defaultOptions, ...options};
    
    // Khởi tạo DataTable
    return new DataTable(selector, mergedOptions);
}

// Khởi tạo popovers và tooltips khi tài liệu sẵn sàng
document.addEventListener('DOMContentLoaded', function() {
    // Khởi tạo popovers
    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
    [...popoverTriggerList].map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl));
    
    // Khởi tạo tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
});