/**
 * JavaScript cho trang cài đặt chung
 */

// Khởi tạo khi trang đã tải xong
$(document).ready(function() {
    // Tải cài đặt hiện tại
    loadSettings();
    
    // Xử lý sự kiện nút lưu cài đặt
    $('#saveSettingsBtn').on('click', function() {
        saveSettings();
    });
    
    // Xử lý sự kiện nút khôi phục mặc định
    $('#resetSettingsBtn').on('click', function() {
        resetSettings();
    });
    
    // Hiệu ứng chuyển đổi dark mode
    $('#darkMode').on('change', function() {
        if ($(this).is(':checked')) {
            $('body').addClass('dark-mode');
        } else {
            $('body').removeClass('dark-mode');
        }
    });
});

/**
 * Tải cài đặt từ server
 */
function loadSettings() {
    // Hiển thị loading spinner
    showLoading(true);
    
    // Gọi API để lấy cài đặt hiện tại
    $.ajax({
        url: '/api/settings/general',
        type: 'GET',
        dataType: 'json',
        success: function(response) {
            if (response.success) {
                populateSettingsForm(response.data);
                showToast('success', 'Đã tải cài đặt thành công');
            } else {
                showToast('error', 'Không thể tải cài đặt: ' + response.error);
            }
        },
        error: function(xhr, status, error) {
            console.error('Lỗi khi tải cài đặt:', error);
            showToast('error', 'Lỗi khi tải cài đặt: ' + error);
        },
        complete: function() {
            showLoading(false);
        }
    });
}

/**
 * Điền dữ liệu vào form cài đặt
 * @param {Object} data - Dữ liệu cài đặt
 */
function populateSettingsForm(data) {
    // Điền form cài đặt hiển thị
    $('#refreshInterval').val(data.display.refreshInterval || 5);
    $('#pageSize').val(data.display.pageSize || 25);
    $('#chartDataPoints').val(data.display.chartDataPoints || 30);
    $('#darkMode').prop('checked', data.display.darkMode || false);
    
    // Điền form cài đặt hệ thống
    $('#logLevel').val(data.system.logLevel || 'INFO');
    $('#logRetention').val(data.system.logRetention || 30);
    $('#language').val(data.system.language || 'vi');
    $('#autoUpdate').prop('checked', data.system.autoUpdate !== false);
    
    // Điền form cài đặt cảnh báo
    $('#cpuThreshold').val(data.alerts.cpuThreshold || 80);
    $('#memoryThreshold').val(data.alerts.memoryThreshold || 80);
    $('#diskThreshold').val(data.alerts.diskThreshold || 90);
    $('#interfaceThreshold').val(data.alerts.interfaceThreshold || 80);
    $('#enableClientAlerts').prop('checked', data.alerts.enableClientAlerts !== false);
    $('#enableFirewallAlerts').prop('checked', data.alerts.enableFirewallAlerts !== false);
    
    // Cập nhật UI dark mode nếu được bật
    if (data.display.darkMode) {
        $('body').addClass('dark-mode');
    } else {
        $('body').removeClass('dark-mode');
    }
}

/**
 * Lưu cài đặt
 */
function saveSettings() {
    // Thu thập dữ liệu từ form
    var settings = {
        display: {
            refreshInterval: parseInt($('#refreshInterval').val()),
            pageSize: parseInt($('#pageSize').val()),
            chartDataPoints: parseInt($('#chartDataPoints').val()),
            darkMode: $('#darkMode').is(':checked')
        },
        system: {
            logLevel: $('#logLevel').val(),
            logRetention: parseInt($('#logRetention').val()),
            language: $('#language').val(),
            autoUpdate: $('#autoUpdate').is(':checked')
        },
        alerts: {
            cpuThreshold: parseInt($('#cpuThreshold').val()),
            memoryThreshold: parseInt($('#memoryThreshold').val()),
            diskThreshold: parseInt($('#diskThreshold').val()),
            interfaceThreshold: parseInt($('#interfaceThreshold').val()),
            enableClientAlerts: $('#enableClientAlerts').is(':checked'),
            enableFirewallAlerts: $('#enableFirewallAlerts').is(':checked')
        }
    };
    
    // Hiển thị loading spinner
    showLoading(true);
    
    // Gọi API để lưu cài đặt
    $.ajax({
        url: '/api/settings/general',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(settings),
        success: function(response) {
            if (response.success) {
                showToast('success', 'Đã lưu cài đặt thành công');
            } else {
                showToast('error', 'Không thể lưu cài đặt: ' + response.error);
            }
        },
        error: function(xhr, status, error) {
            console.error('Lỗi khi lưu cài đặt:', error);
            showToast('error', 'Lỗi khi lưu cài đặt: ' + error);
        },
        complete: function() {
            showLoading(false);
        }
    });
}

/**
 * Khôi phục cài đặt mặc định
 */
function resetSettings() {
    // Hiển thị hộp thoại xác nhận
    if (confirm('Bạn có chắc chắn muốn khôi phục cài đặt về mặc định không?')) {
        // Hiển thị loading spinner
        showLoading(true);
        
        // Gọi API để khôi phục mặc định
        $.ajax({
            url: '/api/settings/reset',
            type: 'POST',
            success: function(response) {
                if (response.success) {
                    // Tải lại cài đặt
                    loadSettings();
                    showToast('success', 'Đã khôi phục cài đặt mặc định');
                } else {
                    showToast('error', 'Không thể khôi phục cài đặt: ' + response.error);
                }
            },
            error: function(xhr, status, error) {
                console.error('Lỗi khi khôi phục cài đặt:', error);
                showToast('error', 'Lỗi khi khôi phục cài đặt: ' + error);
            },
            complete: function() {
                showLoading(false);
            }
        });
    }
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