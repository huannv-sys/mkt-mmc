// Biến toàn cục
let clientsTable;
let selectedDevice = "";
let clientTrafficChart;
let currentClientId = null;
let clientsData = [];

// Format bytes to KB, MB, GB
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

// Khởi tạo DataTable
function initializeClientsTable() {
    clientsTable = $('#clients-table').DataTable({
        responsive: true,
        dom: 'Bfrtip',
        pageLength: 25,
        language: {
            search: "Tìm kiếm:",
            lengthMenu: "Hiển thị _MENU_ clients",
            info: "Hiển thị _START_ đến _END_ của _TOTAL_ clients",
            infoEmpty: "Hiển thị 0 đến 0 của 0 clients",
            infoFiltered: "(lọc từ _MAX_ clients)",
            zeroRecords: "Không tìm thấy client phù hợp",
            paginate: {
                first: "Đầu",
                last: "Cuối",
                next: "Tiếp",
                previous: "Trước"
            }
        },
        columns: [
            { data: 'hostname' },
            { data: 'ip_address' },
            { data: 'mac_address' },
            { data: 'interface' },
            { data: 'connection_type' },
            { 
                data: null,
                render: function(data, type, row) {
                    return `
                        <div class="traffic-rate">
                            <i class="bi bi-arrow-up"></i> ${formatBytes((row.tx_rate || 0), 1)}/s
                            <i class="bi bi-arrow-down"></i> ${formatBytes((row.rx_rate || 0), 1)}/s
                        </div>`;
                }
            },
            { 
                data: 'status',
                render: function(data, type, row) {
                    let statusClass = 'status-disabled';
                    if (data === 'active') {
                        statusClass = 'status-active';
                    } else if (data === 'warning') {
                        statusClass = 'status-warning';
                    } else if (data === 'blocked') {
                        statusClass = 'status-error';
                    }
                    return `<span class="status-label ${statusClass}">${data}</span>`;
                }
            },
            {
                data: null,
                render: function(data, type, row) {
                    let actionButtons = `
                        <button class="btn btn-sm btn-info view-client-btn" data-client-id="${row.id}" title="View Details">
                            <i class="bi bi-info-circle"></i>
                        </button>`;
                    
                    if (row.status === 'blocked') {
                        actionButtons += `
                            <button class="btn btn-sm btn-success ms-1 unblock-client-btn" data-client-id="${row.id}" 
                                data-ip="${row.ip_address}" data-mac="${row.mac_address}" title="Unblock Client">
                                <i class="bi bi-shield-check"></i>
                            </button>`;
                    } else {
                        actionButtons += `
                            <button class="btn btn-sm btn-danger ms-1 block-client-btn" data-client-id="${row.id}" 
                                data-ip="${row.ip_address}" data-mac="${row.mac_address}" title="Block Client">
                                <i class="bi bi-shield-fill-x"></i>
                            </button>`;
                    }
                    
                    return actionButtons;
                }
            }
        ]
    });
}

// Khởi tạo biểu đồ traffic của client
function initializeClientTrafficChart() {
    const ctx = document.getElementById('clientTrafficChart').getContext('2d');
    clientTrafficChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Nhận (RX)',
                    data: [],
                    borderColor: 'rgba(25, 135, 84, 1)',
                    backgroundColor: 'rgba(25, 135, 84, 0.1)',
                    borderWidth: 2,
                    pointRadius: 1,
                    tension: 0.3,
                    fill: true
                },
                {
                    label: 'Gửi (TX)',
                    data: [],
                    borderColor: 'rgba(220, 53, 69, 1)',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    borderWidth: 2,
                    pointRadius: 1,
                    tension: 0.3,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += formatBytes(context.parsed.y) + '/s';
                            }
                            return label;
                        }
                    }
                }
            },
            interaction: {
                intersect: false,
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: false
                    },
                    ticks: {
                        maxTicksLimit: 10
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Lưu lượng (Bytes/s)'
                    },
                    ticks: {
                        callback: function(value) {
                            return formatBytes(value);
                        }
                    }
                }
            }
        }
    });
}

// Lấy danh sách clients từ API
function fetchClientsData(type = 'all') {
    let url = '/api/clients';
    
    // Xác định loại client để lấy
    if (type === 'wireless') {
        url = '/api/clients/wireless';
        $('#client-table-title').text('Wireless Clients');
    } else if (type === 'dhcp') {
        url = '/api/clients/dhcp-leases';
        $('#client-table-title').text('DHCP Leases');
    } else if (type === 'blocked') {
        url = '/api/clients/blocked';
        $('#client-table-title').text('Blocked Clients');
    } else {
        url = '/api/clients';
        $('#client-table-title').text('All Clients');
    }
    
    // Thêm device_id nếu có
    if (selectedDevice) {
        url += `?device_id=${selectedDevice}`;
    }
    
    // Lấy dữ liệu từ API
    fetch(url)
        .then(response => response.json())
        .then(data => {
            // Lưu dữ liệu vào biến toàn cục
            clientsData = data;
            
            // Cập nhật bảng
            updateClientsTable(data);
            
            // Cập nhật số lượng
            updateClientsCounts();
        })
        .catch(error => {
            console.error('Error fetching clients data:', error);
        });
}

// Cập nhật bảng clients
function updateClientsTable(data) {
    // Xóa dữ liệu cũ
    clientsTable.clear();
    
    // Thêm dữ liệu mới
    clientsTable.rows.add(data);
    
    // Vẽ lại bảng
    clientsTable.draw();
    
    // Gắn sự kiện cho các nút
    attachButtonEvents();
}

// Cập nhật số lượng clients
function updateClientsCounts() {
    // Lấy thông tin số lượng từ API
    fetch('/api/monitoring/clients/counts' + (selectedDevice ? `?device_id=${selectedDevice}` : ''))
        .then(response => response.json())
        .then(data => {
            document.getElementById('total-clients-count').innerText = data.total || 0;
            document.getElementById('wireless-clients-count').innerText = data.wireless || 0;
            document.getElementById('dhcp-leases-count').innerText = data.dhcp || 0;
            document.getElementById('blocked-clients-count').innerText = data.blocked || 0;
        })
        .catch(error => {
            console.error('Error fetching client counts:', error);
        });
}

// Gắn sự kiện cho các nút trong bảng
function attachButtonEvents() {
    // Xem chi tiết client
    document.querySelectorAll('.view-client-btn').forEach(button => {
        button.addEventListener('click', function() {
            const clientId = this.getAttribute('data-client-id');
            openClientDetails(clientId);
        });
    });
    
    // Block client
    document.querySelectorAll('.block-client-btn').forEach(button => {
        button.addEventListener('click', function() {
            const clientId = this.getAttribute('data-client-id');
            const ip = this.getAttribute('data-ip');
            const mac = this.getAttribute('data-mac');
            
            // Điền thông tin vào form block
            document.getElementById('block-ip').value = ip || '';
            document.getElementById('block-mac').value = mac || '';
            document.getElementById('block-comment').value = '';
            
            // Hiển thị modal block
            const blockModal = new bootstrap.Modal(document.getElementById('blockClientModal'));
            blockModal.show();
        });
    });
    
    // Unblock client
    document.querySelectorAll('.unblock-client-btn').forEach(button => {
        button.addEventListener('click', function() {
            const clientId = this.getAttribute('data-client-id');
            const ip = this.getAttribute('data-ip');
            const mac = this.getAttribute('data-mac');
            
            if (confirm('Bạn có chắc chắn muốn bỏ chặn client này không?')) {
                unblockClient(ip, mac);
            }
        });
    });
}

// Mở chi tiết client
function openClientDetails(clientId) {
    currentClientId = clientId;
    
    // Tìm client trong dữ liệu đã lấy
    const client = clientsData.find(c => c.id === clientId);
    if (!client) return;
    
    // Điền thông tin vào modal
    document.getElementById('detail-hostname').innerText = client.hostname || 'N/A';
    document.getElementById('detail-ip').innerText = client.ip_address || 'N/A';
    document.getElementById('detail-mac').innerText = client.mac_address || 'N/A';
    document.getElementById('detail-interface').innerText = client.interface || 'N/A';
    document.getElementById('detail-connection-type').innerText = client.connection_type || 'N/A';
    document.getElementById('detail-status').innerText = client.status || 'N/A';
    document.getElementById('detail-last-activity').innerText = client.last_activity || 'N/A';
    document.getElementById('detail-comment').innerText = client.comment || 'N/A';
    
    document.getElementById('detail-tx-rate').innerText = formatBytes(client.tx_rate || 0) + '/s';
    document.getElementById('detail-rx-rate').innerText = formatBytes(client.rx_rate || 0) + '/s';
    document.getElementById('detail-tx-bytes').innerText = formatBytes(client.tx_bytes || 0);
    document.getElementById('detail-rx-bytes').innerText = formatBytes(client.rx_bytes || 0);
    document.getElementById('detail-signal-strength').innerText = client.signal_strength ? `${client.signal_strength} dBm` : 'N/A';
    document.getElementById('detail-uptime').innerText = client.uptime || 'N/A';
    
    // Cập nhật trạng thái các nút
    if (client.status === 'blocked') {
        document.getElementById('detail-block-btn').style.display = 'none';
        document.getElementById('detail-unblock-btn').style.display = 'block';
    } else {
        document.getElementById('detail-block-btn').style.display = 'block';
        document.getElementById('detail-unblock-btn').style.display = 'none';
    }
    
    // Lấy dữ liệu traffic history
    fetchClientTraffic(clientId);
    
    // Hiển thị modal
    const clientModal = new bootstrap.Modal(document.getElementById('clientDetailModal'));
    clientModal.show();
}

// Lấy dữ liệu traffic history của client
function fetchClientTraffic(clientId) {
    fetch(`/api/clients/${clientId}/traffic?period=hour`)
        .then(response => response.json())
        .then(data => {
            updateClientTrafficChart(data);
        })
        .catch(error => {
            console.error('Error fetching client traffic:', error);
        });
}

// Cập nhật biểu đồ traffic của client
function updateClientTrafficChart(data) {
    if (!clientTrafficChart) return;
    
    // Cập nhật dữ liệu cho biểu đồ
    clientTrafficChart.data.labels = data.labels || [];
    clientTrafficChart.data.datasets[0].data = data.rx || [];
    clientTrafficChart.data.datasets[1].data = data.tx || [];
    
    // Cập nhật biểu đồ
    clientTrafficChart.update();
}

// Chặn client
function blockClient(ip, mac, comment) {
    const formData = new FormData();
    if (ip) formData.append('ip', ip);
    if (mac) formData.append('mac', mac);
    if (comment) formData.append('comment', comment);
    
    fetch('/api/clients/block', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Client đã được chặn thành công!');
            
            // Đóng modal
            const blockModal = bootstrap.Modal.getInstance(document.getElementById('blockClientModal'));
            blockModal.hide();
            
            // Làm mới dữ liệu
            fetchClientsData();
        } else {
            alert('Lỗi khi chặn client: ' + (data.message || 'Unknown error'));
        }
    })
    .catch(error => {
        alert('Lỗi khi chặn client: ' + error);
    });
}

// Bỏ chặn client
function unblockClient(ip, mac) {
    const formData = new FormData();
    if (ip) formData.append('ip', ip);
    if (mac) formData.append('mac', mac);
    
    fetch('/api/clients/unblock', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Client đã được bỏ chặn thành công!');
            
            // Làm mới dữ liệu
            fetchClientsData();
            
            // Đóng modal chi tiết nếu đang mở
            if (currentClientId) {
                const clientModal = bootstrap.Modal.getInstance(document.getElementById('clientDetailModal'));
                if (clientModal) {
                    clientModal.hide();
                }
            }
        } else {
            alert('Lỗi khi bỏ chặn client: ' + (data.message || 'Unknown error'));
        }
    })
    .catch(error => {
        alert('Lỗi khi bỏ chặn client: ' + error);
    });
}

// Lấy danh sách thiết bị
function fetchDevices() {
    fetch('/api/devices')
        .then(response => response.json())
        .then(data => {
            const deviceList = document.getElementById('deviceList');
            deviceList.innerHTML = '';
            
            data.forEach(device => {
                const li = document.createElement('li');
                li.innerHTML = `<a class="dropdown-item" href="#" data-device-id="${device.id}">${device.hostname || device.ip_address}</a>`;
                deviceList.appendChild(li);
            });
            
            // Gắn sự kiện click cho các thiết bị
            document.querySelectorAll('#deviceList a').forEach(item => {
                item.addEventListener('click', function(e) {
                    e.preventDefault();
                    selectedDevice = this.getAttribute('data-device-id');
                    document.getElementById('deviceDropdown').innerText = this.innerText;
                    
                    // Làm mới dữ liệu
                    fetchClientsData();
                });
            });
        })
        .catch(error => {
            console.error('Error fetching devices:', error);
        });
}

// Xử lý sự kiện khi tài liệu đã tải xong
document.addEventListener('DOMContentLoaded', function() {
    // Khởi tạo bảng clients
    initializeClientsTable();
    
    // Khởi tạo biểu đồ traffic
    initializeClientTrafficChart();
    
    // Lấy danh sách thiết bị
    fetchDevices();
    
    // Lấy dữ liệu ban đầu
    fetchClientsData();
    
    // Xử lý sự kiện click nút refresh
    document.getElementById('refreshBtn').addEventListener('click', function() {
        fetchClientsData();
    });
    
    // Xử lý sự kiện click các nút filter
    document.getElementById('all-clients-btn').addEventListener('click', function() {
        fetchClientsData('all');
    });
    
    document.getElementById('wireless-clients-btn').addEventListener('click', function() {
        fetchClientsData('wireless');
    });
    
    document.getElementById('dhcp-leases-btn').addEventListener('click', function() {
        fetchClientsData('dhcp');
    });
    
    document.getElementById('blocked-clients-btn').addEventListener('click', function() {
        fetchClientsData('blocked');
    });
    
    // Xử lý sự kiện click nút block trong modal chi tiết
    document.getElementById('detail-block-btn').addEventListener('click', function() {
        const client = clientsData.find(c => c.id === currentClientId);
        if (client) {
            // Điền thông tin vào form block
            document.getElementById('block-ip').value = client.ip_address || '';
            document.getElementById('block-mac').value = client.mac_address || '';
            document.getElementById('block-comment').value = '';
            
            // Đóng modal chi tiết
            const clientModal = bootstrap.Modal.getInstance(document.getElementById('clientDetailModal'));
            clientModal.hide();
            
            // Hiển thị modal block
            const blockModal = new bootstrap.Modal(document.getElementById('blockClientModal'));
            blockModal.show();
        }
    });
    
    // Xử lý sự kiện click nút unblock trong modal chi tiết
    document.getElementById('detail-unblock-btn').addEventListener('click', function() {
        const client = clientsData.find(c => c.id === currentClientId);
        if (client) {
            if (confirm('Bạn có chắc chắn muốn bỏ chặn client này không?')) {
                unblockClient(client.ip_address, client.mac_address);
            }
        }
    });
    
    // Xử lý sự kiện click nút confirm block trong modal block
    document.getElementById('confirm-block-btn').addEventListener('click', function() {
        const ip = document.getElementById('block-ip').value;
        const mac = document.getElementById('block-mac').value;
        const comment = document.getElementById('block-comment').value;
        
        if (!ip && !mac) {
            alert('Vui lòng nhập ít nhất một trong hai: địa chỉ IP hoặc MAC');
            return;
        }
        
        blockClient(ip, mac, comment);
    });
    
    // Xử lý sự kiện export
    document.getElementById('export-csv').addEventListener('click', function(e) {
        e.preventDefault();
        clientsTable.button('.buttons-csv').trigger();
    });
    
    document.getElementById('export-pdf').addEventListener('click', function(e) {
        e.preventDefault();
        clientsTable.button('.buttons-pdf').trigger();
    });
    
    document.getElementById('export-excel').addEventListener('click', function(e) {
        e.preventDefault();
        clientsTable.button('.buttons-excel').trigger();
    });
});