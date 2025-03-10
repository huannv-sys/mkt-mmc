// Định nghĩa một số biến chung
let selectedDevice = "";
let selectedInterface = "all";
let refreshInterval = 5000; // 5 giây
let chartData = {
    labels: [],
    rx: [],
    tx: []
};
let refreshTimer;
let socket;
let trafficChart;

// Khởi tạo biểu đồ traffic
function initializeTrafficChart() {
    const ctx = document.getElementById('networkTrafficChart').getContext('2d');
    trafficChart = new Chart(ctx, {
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

// Format bytes thành đơn vị KB, MB, GB
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

// Cập nhật thông tin thiết bị
function updateDeviceInfo(data) {
    // Cập nhật CPU và Memory
    const cpuLoad = data.system.cpu_load || 0;
    const memoryUsage = data.system.memory_usage || 0;
    
    document.getElementById('cpu-load').innerText = `${cpuLoad}%`;
    document.getElementById('cpu-progress').style.width = `${cpuLoad}%`;
    document.getElementById('cpu-progress').setAttribute('aria-valuenow', cpuLoad);
    
    document.getElementById('memory-usage').innerText = `${memoryUsage}%`;
    document.getElementById('memory-progress').style.width = `${memoryUsage}%`;
    document.getElementById('memory-progress').setAttribute('aria-valuenow', memoryUsage);
    
    // Cập nhật uptime và version
    document.getElementById('uptime').innerText = data.system.uptime || '00:00:00';
    document.getElementById('system-version').innerText = data.system.version || 'RouterOS v0.0.0';
    
    // Cập nhật số lượng clients
    document.getElementById('active-clients').innerText = data.clients.active || 0;
    document.getElementById('total-clients').innerText = `Total: ${data.clients.total || 0}`;
}

// Cập nhật bảng interfaces
function updateInterfacesTable(interfaces) {
    const tableBody = document.getElementById('interfaces-table').getElementsByTagName('tbody')[0];
    tableBody.innerHTML = '';
    
    // Cập nhật dropdown interface
    const interfaceList = document.getElementById('interface-list');
    // Giữ lại option "All Interfaces"
    interfaceList.innerHTML = '<li><a class="dropdown-item" href="#" data-interface="all">All Interfaces</a></li>';
    
    interfaces.forEach(iface => {
        // Thêm vào bảng
        const row = tableBody.insertRow();
        
        // Tên interface
        const nameCell = row.insertCell(0);
        nameCell.innerHTML = `<strong>${iface.name}</strong>`;
        
        // Loại interface
        const typeCell = row.insertCell(1);
        typeCell.innerText = iface.type || 'N/A';
        
        // TX/RX tốc độ
        const trafficCell = row.insertCell(2);
        trafficCell.innerHTML = `
            <span class="traffic-rate">
                <i class="bi bi-arrow-up"></i> ${formatBytes(iface.tx_rate || 0)}/s
                <i class="bi bi-arrow-down"></i> ${formatBytes(iface.rx_rate || 0)}/s
            </span>
        `;
        
        // Trạng thái
        const statusCell = row.insertCell(3);
        let statusClass = 'status-disabled';
        if (iface.status === 'active') {
            statusClass = 'status-active';
        } else if (iface.status === 'warning') {
            statusClass = 'status-warning';
        } else if (iface.status === 'error') {
            statusClass = 'status-error';
        }
        statusCell.innerHTML = `<span class="status-label ${statusClass}">${iface.status || 'unknown'}</span>`;
        
        // Thêm vào dropdown
        const li = document.createElement('li');
        li.innerHTML = `<a class="dropdown-item" href="#" data-interface="${iface.name}">${iface.name}</a>`;
        interfaceList.appendChild(li);
    });
    
    // Gắn sự kiện click cho các interface trong dropdown
    document.querySelectorAll('#interface-list a').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            selectedInterface = this.getAttribute('data-interface');
            document.getElementById('selected-interface').innerText = selectedInterface === 'all' ? 'All Interfaces' : selectedInterface;
            
            // Reset biểu đồ khi chọn interface mới
            resetChartData();
            updateTrafficChart(chartData);
        });
    });
}

// Cập nhật bảng DHCP leases
function updateDHCPTable(leases) {
    const tableBody = document.getElementById('dhcp-table').getElementsByTagName('tbody')[0];
    tableBody.innerHTML = '';
    
    leases.forEach(lease => {
        const row = tableBody.insertRow();
        
        // Hostname
        const hostnameCell = row.insertCell(0);
        hostnameCell.innerText = lease.hostname || 'N/A';
        
        // IP Address
        const ipCell = row.insertCell(1);
        ipCell.innerText = lease.address || 'N/A';
        
        // MAC Address
        const macCell = row.insertCell(2);
        macCell.innerText = lease.mac_address || 'N/A';
        
        // Expires in
        const expiresCell = row.insertCell(3);
        expiresCell.innerText = lease.expires || 'N/A';
    });
}

// Cập nhật bảng System Logs
function updateLogsTable(logs) {
    const tableBody = document.getElementById('logs-table').getElementsByTagName('tbody')[0];
    tableBody.innerHTML = '';
    
    logs.forEach(log => {
        const row = tableBody.insertRow();
        
        // Time
        const timeCell = row.insertCell(0);
        timeCell.innerText = log.time || 'N/A';
        
        // Topic
        const topicCell = row.insertCell(1);
        topicCell.innerText = log.topic || 'N/A';
        
        // Message
        const messageCell = row.insertCell(2);
        messageCell.innerText = log.message || 'N/A';
    });
}

// Cập nhật biểu đồ lưu lượng mạng
function updateTrafficChart(data) {
    if (!trafficChart) return;
    
    // Cập nhật dữ liệu cho biểu đồ
    trafficChart.data.labels = data.labels;
    trafficChart.data.datasets[0].data = data.rx;
    trafficChart.data.datasets[1].data = data.tx;
    
    // Cập nhật biểu đồ
    trafficChart.update();
}

// Reset dữ liệu biểu đồ
function resetChartData() {
    chartData = {
        labels: [],
        rx: [],
        tx: []
    };
}

// Thêm điểm dữ liệu mới vào biểu đồ
function addDataPoint(label, rx, tx) {
    // Giới hạn số điểm dữ liệu (để biểu đồ không quá dài)
    const maxDataPoints = 20;
    
    if (chartData.labels.length >= maxDataPoints) {
        chartData.labels.shift();
        chartData.rx.shift();
        chartData.tx.shift();
    }
    
    chartData.labels.push(label);
    chartData.rx.push(rx);
    chartData.tx.push(tx);
    
    updateTrafficChart(chartData);
}

// Kết nối WebSocket
function connectWebSocket() {
    // Ngắt kết nối cũ nếu có
    if (socket) {
        socket.close();
    }
    
    // Tạo kết nối mới
    socket = new WebSocket(`ws://${window.location.host}/ws/monitoring`);
    
    socket.onopen = function(e) {
        console.log("WebSocket connected");
    };
    
    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        processRealTimeData(data);
    };
    
    socket.onclose = function(event) {
        console.log("WebSocket disconnected, reconnecting in 3 seconds...");
        setTimeout(connectWebSocket, 3000);
    };
    
    socket.onerror = function(error) {
        console.error("WebSocket error:", error);
        socket.close();
    };
}

// Xử lý dữ liệu thời gian thực
function processRealTimeData(data) {
    // Cập nhật thông tin thiết bị
    updateDeviceInfo(data);
    
    // Cập nhật bảng interfaces
    if (data.interfaces) {
        updateInterfacesTable(data.interfaces);
    }
    
    // Cập nhật bảng DHCP leases
    if (data.dhcp_leases) {
        updateDHCPTable(data.dhcp_leases);
    }
    
    // Cập nhật bảng logs
    if (data.logs) {
        updateLogsTable(data.logs);
    }
    
    // Cập nhật biểu đồ traffic
    if (data.traffic) {
        let rxData = 0;
        let txData = 0;
        
        if (selectedInterface === 'all') {
            // Tính tổng lưu lượng của tất cả interfaces
            data.interfaces.forEach(iface => {
                rxData += iface.rx_rate || 0;
                txData += iface.tx_rate || 0;
            });
        } else {
            // Lấy lưu lượng của interface đã chọn
            const selectedIface = data.interfaces.find(iface => iface.name === selectedInterface);
            if (selectedIface) {
                rxData = selectedIface.rx_rate || 0;
                txData = selectedIface.tx_rate || 0;
            }
        }
        
        // Thêm điểm dữ liệu mới
        const now = new Date();
        const timeLabel = now.getHours().toString().padStart(2, '0') + ':' +
                         now.getMinutes().toString().padStart(2, '0') + ':' +
                         now.getSeconds().toString().padStart(2, '0');
        
        addDataPoint(timeLabel, rxData, txData);
    }
}

// Thiết lập polling cho dữ liệu
function startPolling() {
    // Xóa timer cũ nếu có
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
    
    // Cập nhật dữ liệu ban đầu
    fetchDashboardData();
    
    // Thiết lập timer mới
    refreshTimer = setInterval(fetchDashboardData, refreshInterval);
}

// Lấy dữ liệu dashboard từ API
function fetchDashboardData() {
    fetch(`/api/monitoring/dashboard${selectedDevice ? '?device_id=' + selectedDevice : ''}`)
        .then(response => response.json())
        .then(data => {
            processRealTimeData(data);
        })
        .catch(error => {
            console.error('Error fetching dashboard data:', error);
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
                    
                    // Reset biểu đồ và cập nhật dữ liệu
                    resetChartData();
                    fetchDashboardData();
                });
            });
        })
        .catch(error => {
            console.error('Error fetching devices:', error);
        });
}

// Xử lý sự kiện khi tài liệu đã tải xong
document.addEventListener('DOMContentLoaded', function() {
    // Khởi tạo biểu đồ
    initializeTrafficChart();
    
    // Lấy danh sách thiết bị
    fetchDevices();
    
    // Bắt đầu polling dữ liệu
    startPolling();
    
    // Kết nối WebSocket nếu được hỗ trợ
    if ('WebSocket' in window) {
        connectWebSocket();
    } else {
        console.log('WebSocket not supported in this browser, falling back to polling');
    }
    
    // Xử lý sự kiện click nút refresh
    document.getElementById('refreshBtn').addEventListener('click', function() {
        fetchDashboardData();
    });
    
    // Xử lý sự kiện click các nút khoảng thời gian
    document.getElementById('live-monitoring').addEventListener('click', function() {
        refreshInterval = 2000; // 2 giây
        startPolling();
    });
    
    document.getElementById('interval-1m').addEventListener('click', function() {
        refreshInterval = 60000; // 1 phút
        startPolling();
    });
    
    document.getElementById('interval-5m').addEventListener('click', function() {
        refreshInterval = 300000; // 5 phút
        startPolling();
    });
    
    document.getElementById('interval-15m').addEventListener('click', function() {
        refreshInterval = 900000; // 15 phút
        startPolling();
    });
});