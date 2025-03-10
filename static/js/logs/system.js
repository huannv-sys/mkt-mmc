/**
 * JavaScript cho trang logs hệ thống
 */

// Khởi tạo khi trang đã tải xong
$(document).ready(function() {
    // Tải dữ liệu logs
    loadLogs();
    
    // Xử lý sự kiện submit form lọc
    $('#logsFilterForm').on('submit', function(e) {
        e.preventDefault();
        loadLogs();
    });
    
    // Xử lý sự kiện nút làm mới
    $('#refreshLogsBtn').on('click', function() {
        loadLogs();
    });
    
    // Xử lý sự kiện nút xuất logs
    $('#exportLogsBtn').on('click', function() {
        $('#exportLogsModal').modal('show');
    });
    
    // Xử lý sự kiện nút xóa logs
    $('#clearLogsBtn').on('click', function() {
        $('#clearLogsModal').modal('show');
    });
    
    // Xử lý sự kiện xác nhận xuất logs
    $('#confirmExportLogsBtn').on('click', function() {
        exportLogs();
    });
    
    // Xử lý sự kiện xác nhận xóa logs
    $('#confirmClearLogsBtn').on('click', function() {
        clearLogs();
    });
    
    // Xử lý sự kiện phân trang
    $(document).on('click', '.pagination .page-link', function(e) {
        e.preventDefault();
        
        // Chỉ xử lý nếu không phải là nút đã disabled
        if (!$(this).parent().hasClass('disabled')) {
            const page = $(this).data('page');
            if (page) {
                loadLogs(page);
            }
        }
    });
    
    // Tự động cập nhật
    setInterval(function() {
        // Kiểm tra xem có đang mở tab logs không
        if ($('.nav-link.active').attr('href') === '/logs/system') {
            loadLogs(currentPage);
        }
    }, 60000); // 1 phút
});

// Biến lưu trữ trang hiện tại
let currentPage = 1;

/**
 * Tải dữ liệu logs
 * @param {number} page - Số trang
 */
function loadLogs(page = 1) {
    // Cập nhật trang hiện tại
    currentPage = page;
    
    // Thu thập dữ liệu filter
    const filterData = {
        level: $('#logLevel').val(),
        topic: $('#logTopic').val(),
        fromDate: $('#fromDate').val(),
        toDate: $('#toDate').val(),
        searchText: $('#searchText').val(),
        limit: $('#logLimit').val(),
        page: page
    };
    
    // Hiển thị loading spinner
    showLoading(true);
    
    // Gọi API để lấy dữ liệu logs
    $.ajax({
        url: '/api/logs/system',
        type: 'GET',
        data: filterData,
        dataType: 'json',
        success: function(response) {
            if (response.success) {
                updateLogsTable(response.data.logs);
                updatePagination(response.data.pagination);
            } else {
                showToast('error', 'Không thể tải logs: ' + response.error);
            }
        },
        error: function(xhr, status, error) {
            console.error('Lỗi khi tải logs:', error);
            showToast('error', 'Lỗi khi tải logs: ' + error);
        },
        complete: function() {
            showLoading(false);
        }
    });
}

/**
 * Cập nhật bảng logs
 * @param {Array} logs - Danh sách logs
 */
function updateLogsTable(logs) {
    const tableBody = $('#systemLogsTable tbody');
    tableBody.empty();
    
    if (!logs || logs.length === 0) {
        tableBody.append('<tr><td colspan="5" class="text-center">Không có logs nào</td></tr>');
        return;
    }
    
    logs.forEach(function(log) {
        // Xác định màu badge dựa trên level
        let badgeClass = 'bg-info';
        switch (log.level.toLowerCase()) {
            case 'error':
                badgeClass = 'bg-danger';
                break;
            case 'warning':
                badgeClass = 'bg-warning';
                break;
            case 'info':
                badgeClass = 'bg-success';
                break;
            case 'critical':
                badgeClass = 'bg-dark';
                break;
        }
        
        const row = `
            <tr>
                <td>${formatDate(log.timestamp)}</td>
                <td><span class="badge ${badgeClass}">${log.level}</span></td>
                <td>${log.topic}</td>
                <td>${log.device}</td>
                <td>${log.message}</td>
            </tr>
        `;
        tableBody.append(row);
    });
}

/**
 * Cập nhật phân trang
 * @param {Object} pagination - Thông tin phân trang
 */
function updatePagination(pagination) {
    const paginationElement = $('.pagination');
    paginationElement.empty();
    
    // Nút Trước
    const prevDisabled = pagination.currentPage === 1 ? 'disabled' : '';
    paginationElement.append(`
        <li class="page-item ${prevDisabled}">
            <a class="page-link" href="#" data-page="${pagination.currentPage - 1}" tabindex="-1" aria-disabled="${prevDisabled ? 'true' : 'false'}">Trước</a>
        </li>
    `);
    
    // Tạo các nút trang
    const startPage = Math.max(1, pagination.currentPage - 2);
    const endPage = Math.min(pagination.totalPages, pagination.currentPage + 2);
    
    for (let i = startPage; i <= endPage; i++) {
        const active = i === pagination.currentPage ? 'active' : '';
        paginationElement.append(`
            <li class="page-item ${active}">
                <a class="page-link" href="#" data-page="${i}">${i}</a>
            </li>
        `);
    }
    
    // Nút Sau
    const nextDisabled = pagination.currentPage === pagination.totalPages ? 'disabled' : '';
    paginationElement.append(`
        <li class="page-item ${nextDisabled}">
            <a class="page-link" href="#" data-page="${pagination.currentPage + 1}" aria-disabled="${nextDisabled ? 'true' : 'false'}">Sau</a>
        </li>
    `);
}

/**
 * Xuất logs
 */
function exportLogs() {
    // Thu thập dữ liệu từ form
    const format = $('#exportFormat').val();
    const days = $('#exportDays').val();
    const filtered = $('#exportFiltered').is(':checked');
    
    // Thu thập dữ liệu filter nếu cần
    const filterData = filtered ? {
        level: $('#logLevel').val(),
        topic: $('#logTopic').val(),
        fromDate: $('#fromDate').val(),
        toDate: $('#toDate').val(),
        searchText: $('#searchText').val()
    } : {};
    
    // Tạo URL với tham số
    let url = `/api/logs/export?format=${format}&days=${days}`;
    if (filtered) {
        for (const [key, value] of Object.entries(filterData)) {
            if (value) {
                url += `&${key}=${encodeURIComponent(value)}`;
            }
        }
    }
    
    // Đóng modal
    $('#exportLogsModal').modal('hide');
    
    // Tải xuống file
    window.location.href = url;
}

/**
 * Xóa logs
 */
function clearLogs() {
    // Thu thập dữ liệu từ form
    const days = $('#clearLogsDays').val();
    const type = $('#clearLogsType').val();
    
    // Hiển thị loading spinner
    showLoading(true);
    
    // Gọi API để xóa logs
    $.ajax({
        url: '/api/logs/clear',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            days: days,
            type: type
        }),
        success: function(response) {
            if (response.success) {
                showToast('success', 'Đã xóa logs thành công');
                $('#clearLogsModal').modal('hide');
                loadLogs();
            } else {
                showToast('error', 'Không thể xóa logs: ' + response.error);
            }
        },
        error: function(xhr, status, error) {
            console.error('Lỗi khi xóa logs:', error);
            showToast('error', 'Lỗi khi xóa logs: ' + error);
        },
        complete: function() {
            showLoading(false);
        }
    });
}

/**
 * Định dạng ngày
 * @param {string} dateString - Chuỗi ngày
 * @returns {string} Ngày đã định dạng
 */
function formatDate(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    return `${date.getDate().toString().padStart(2, '0')}/${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getFullYear()} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;
}

/**
 * Hiển thị loading spinner
 * @param {boolean} show - true để hiển thị, false để ẩn
 */
function showLoading(show) {
    if (show) {
        // Nếu chưa có spinner, tạo mới
        if ($('#loadingSpinner').length === 0) {
            $('body').append('<div id="loadingSpinner" class="loading-spinner"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Đang tải...</span></div></div>');
        }
        $('#loadingSpinner').show();
    } else {
        $('#loadingSpinner').hide();
    }
}

/**
 * Hiển thị thông báo toast
 * @param {string} type - Kiểu thông báo (success, error, warning, info)
 * @param {string} message - Nội dung thông báo
 */
function showToast(type, message) {
    // Màu sắc theo loại
    var bgClass = 'bg-primary';
    switch (type) {
        case 'success':
            bgClass = 'bg-success';
            break;
        case 'error':
            bgClass = 'bg-danger';
            break;
        case 'warning':
            bgClass = 'bg-warning';
            break;
        case 'info':
            bgClass = 'bg-info';
            break;
    }
    
    // Tạo ID duy nhất cho toast
    var toastId = 'toast-' + Date.now();
    
    // HTML cho toast
    var toastHtml = `
        <div id="${toastId}" class="toast align-items-center ${bgClass} text-white border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    // Thêm toast vào container hoặc tạo mới nếu chưa có
    if ($('#toastContainer').length === 0) {
        $('body').append('<div id="toastContainer" class="toast-container position-fixed bottom-0 end-0 p-3"></div>');
    }
    
    // Thêm toast vào container và hiển thị
    $('#toastContainer').append(toastHtml);
    var toast = new bootstrap.Toast(document.getElementById(toastId), {
        delay: 5000
    });
    toast.show();
}