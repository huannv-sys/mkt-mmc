// Khởi tạo biến để lưu các chart
let trafficChart = null;
let resourceChart = null;
let clientChart = null;

// Hàm khởi tạo chart traffic
function initTrafficChart(containerId) {
    const ctx = document.getElementById(containerId).getContext('2d');
    trafficChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Tải xuống (Mbps)',
                    borderColor: '#2196f3',
                    backgroundColor: 'rgba(33, 150, 243, 0.1)',
                    data: [],
                    fill: true
                },
                {
                    label: 'Tải lên (Mbps)',
                    borderColor: '#4caf50',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    data: [],
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value + ' Mbps';
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    mode: 'index',
                    intersect: false
                },
                legend: {
                    position: 'top'
                }
            }
        }
    });
}

// Hàm cập nhật chart traffic
function updateTrafficChart(data) {
    if (!trafficChart) return;
    
    // Thêm thời gian mới
    trafficChart.data.labels.push(new Date().toLocaleTimeString());
    
    // Giới hạn số điểm hiển thị
    const maxDataPoints = 20;
    if (trafficChart.data.labels.length > maxDataPoints) {
        trafficChart.data.labels.shift();
        trafficChart.data.datasets[0].data.shift();
        trafficChart.data.datasets[1].data.shift();
    }
    
    // Thêm dữ liệu mới
    trafficChart.data.datasets[0].data.push(data.download);
    trafficChart.data.datasets[1].data.push(data.upload);
    
    // Cập nhật chart
    trafficChart.update();
}

// Hàm khởi tạo chart tài nguyên
function initResourceChart(containerId) {
    const ctx = document.getElementById(containerId).getContext('2d');
    resourceChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['CPU', 'RAM', 'Ổ cứng'],
            datasets: [{
                data: [0, 0, 0],
                backgroundColor: [
                    'rgba(255, 99, 132, 0.8)',
                    'rgba(54, 162, 235, 0.8)',
                    'rgba(255, 206, 86, 0.8)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.label + ': ' + context.raw + '%';
                        }
                    }
                }
            }
        }
    });
}

// Hàm cập nhật chart tài nguyên
function updateResourceChart(data) {
    if (!resourceChart) return;
    
    resourceChart.data.datasets[0].data = [
        data.cpu,
        data.ram,
        data.disk
    ];
    
    resourceChart.update();
}

// Hàm khởi tạo chart client
function initClientChart(containerId) {
    const ctx = document.getElementById(containerId).getContext('2d');
    clientChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Clients',
                    backgroundColor: 'rgba(75, 192, 192, 0.8)',
                    data: []
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

// Hàm cập nhật chart client
function updateClientChart(data) {
    if (!clientChart) return;
    
    clientChart.data.labels = data.labels;
    clientChart.data.datasets[0].data = data.values;
    
    clientChart.update();
}

// Khởi tạo tất cả charts khi trang được load
document.addEventListener('DOMContentLoaded', function() {
    // Khởi tạo các charts
    if (document.getElementById('trafficChart')) {
        initTrafficChart('trafficChart');
    }
    if (document.getElementById('resourceChart')) {
        initResourceChart('resourceChart');
    }
    if (document.getElementById('clientChart')) {
        initClientChart('clientChart');
    }
    
    // Kết nối WebSocket để nhận dữ liệu realtime
    const ws = new WebSocket('ws://' + window.location.host + '/ws');
    
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        
        // Cập nhật các charts dựa trên loại dữ liệu
        switch (data.type) {
            case 'traffic':
                updateTrafficChart(data);
                break;
            case 'resource':
                updateResourceChart(data);
                break;
            case 'client':
                updateClientChart(data);
                break;
        }
    };
    
    ws.onerror = function(error) {
        console.error('WebSocket error:', error);
    };
    
    ws.onclose = function() {
        console.log('WebSocket connection closed');
        // Thử kết nối lại sau 5 giây
        setTimeout(function() {
            location.reload();
        }, 5000);
    };
});