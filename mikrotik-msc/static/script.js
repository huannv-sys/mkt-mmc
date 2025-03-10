document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts and visualizations
    const fileTypesChart = document.getElementById('fileTypesChart');
    
    // Extract file types data from the template
    const fileTypesData = JSON.parse(document.getElementById('fileTypesData').textContent);
    
    new Chart(fileTypesChart, {
        type: 'pie',
        data: {
            labels: Object.keys(fileTypesData),
            datasets: [{
                data: Object.values(fileTypesData),
                backgroundColor: [
                    '#3498db',
                    '#e74c3c',
                    '#2ecc71',
                    '#f1c40f',
                    '#9b59b6',
                    '#34495e',
                    '#1abc9c',
                    '#e67e22'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                },
                title: {
                    display: true,
                    text: 'File Type Distribution'
                }
            }
        }
    });

    // Add interactivity to sections
    const sections = document.querySelectorAll('.analysis-section');
    sections.forEach(section => {
        const header = section.querySelector('h2');
        const content = section.querySelector('div');
        
        header.addEventListener('click', () => {
            content.style.display = content.style.display === 'none' ? 'block' : 'none';
        });
    });

    // Add severity highlighting
    const severityCells = document.querySelectorAll('[class^="severity-"]');
    severityCells.forEach(cell => {
        const severity = cell.textContent.trim();
        cell.innerHTML += ` <span class="severity-indicator">${
            severity === 'HIGH' ? '⚠️' : 
            severity === 'MEDIUM' ? '⚡' : '📌'
        }</span>`;
    });
});
