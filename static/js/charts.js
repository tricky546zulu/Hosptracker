// Hospital Capacity Dashboard Charts and Data Management

let capacityChart = null;
let trendsChart = null;
let hospitalData = {};
let currentTrendHospital = 'RUH';

// Initialize the dashboard
function initializeDashboard() {
    console.log('Initializing hospital capacity dashboard...');
    
    // Load initial data
    loadHospitalData();
    updateScrapingStatus();
    
    // Initialize charts
    initializeCapacityChart();
    initializeTrendsChart();
    
    // Load initial trends for RUH
    loadHistoricalData('RUH');
}

// Load current hospital data
async function loadHospitalData() {
    try {
        showLoading(true);
        
        const response = await fetch('/api/hospital-data');
        const result = await response.json();
        
        if (result.status === 'success') {
            hospitalData = result.data;
            updateHospitalCards();
            updateCapacityChart();
            updateLastUpdatedTime(result.last_updated);
            hideAlerts();
        } else {
            showError('Failed to load hospital data: ' + (result.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error loading hospital data:', error);
        showError('Network error while loading hospital data');
    } finally {
        showLoading(false);
    }
}

// Update hospital data cards
function updateHospitalCards() {
    const hospitals = ['RUH', 'SPH', 'SCH'];
    
    hospitals.forEach(hospital => {
        const data = hospitalData[hospital];
        
        if (data && data.status === 'success') {
            updateHospitalCard(hospital, data);
        } else {
            updateHospitalCard(hospital, null);
        }
    });
}

// Update individual hospital card
function updateHospitalCard(hospital, data) {
    const prefix = hospital.toLowerCase();
    
    if (data) {
        // Update Emergency Department metrics
        document.getElementById(`${prefix}-admitted`).textContent = data.admitted_pts_in_ed || '-';
        document.getElementById(`${prefix}-active`).textContent = data.active_patients || '-';
        document.getElementById(`${prefix}-consults`).textContent = data.consults || '-';
        document.getElementById(`${prefix}-total-patients`).textContent = data.total_patients || '-';
        
        // Update capacity percentage
        const percentage = data.capacity_percentage || 0;
        document.getElementById(`${prefix}-percentage`).textContent = `${percentage.toFixed(1)}%`;
        
        // Update progress bar
        const progressBar = document.getElementById(`${prefix}-progress`);
        progressBar.style.width = `${percentage}%`;
        progressBar.className = `progress-bar ${getCapacityClass(percentage)}`;
        
        // Update badge color
        const badge = document.getElementById(`${prefix}-percentage`);
        badge.className = `badge fs-6 ${getCapacityBadgeClass(percentage)}`;
        
        // Add update animation
        const card = progressBar.closest('.card');
        card.classList.add('data-update');
        setTimeout(() => card.classList.remove('data-update'), 500);
        
    } else {
        // Show no data state
        document.getElementById(`${prefix}-admitted`).textContent = '-';
        document.getElementById(`${prefix}-active`).textContent = '-';
        document.getElementById(`${prefix}-consults`).textContent = '-';
        document.getElementById(`${prefix}-total-patients`).textContent = '-';
        document.getElementById(`${prefix}-percentage`).textContent = '--%';
        
        const progressBar = document.getElementById(`${prefix}-progress`);
        progressBar.style.width = '0%';
        progressBar.className = 'progress-bar bg-secondary';
        
        const badge = document.getElementById(`${prefix}-percentage`);
        badge.className = 'badge bg-secondary fs-6';
    }
}

// Get capacity level CSS class
function getCapacityClass(percentage) {
    if (percentage >= 90) return 'capacity-high';
    if (percentage >= 75) return 'capacity-medium';
    return 'capacity-low';
}

// Get capacity badge CSS class
function getCapacityBadgeClass(percentage) {
    if (percentage >= 90) return 'bg-danger';
    if (percentage >= 75) return 'bg-warning';
    return 'bg-success';
}

// Initialize capacity comparison chart
function initializeCapacityChart() {
    const ctx = document.getElementById('capacityChart').getContext('2d');
    
    capacityChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Royal University Hospital', "St. Paul's Hospital", 'Saskatoon City Hospital'],
            datasets: [{
                label: 'ED Capacity %',
                data: [0, 0, 0],
                backgroundColor: [
                    'rgba(75, 192, 192, 0.8)',
                    'rgba(54, 162, 235, 0.8)',
                    'rgba(255, 206, 86, 0.8)'
                ],
                borderColor: [
                    'rgba(75, 192, 192, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const hospital = context.label;
                            const hospitalCode = getHospitalCode(hospital);
                            const data = hospitalData[hospitalCode];
                            
                            if (data) {
                                return [
                                    `Capacity: ${context.parsed.y.toFixed(1)}%`,
                                    `Occupied: ${data.occupied_beds || 0}/${data.total_beds || 0} beds`,
                                    `Admitted in ED: ${data.admitted_pts_in_ed || 0}`
                                ];
                            }
                            return `Capacity: ${context.parsed.y.toFixed(1)}%`;
                        }
                    }
                }
            }
        }
    });
}

// Initialize trends chart
function initializeTrendsChart() {
    const ctx = document.getElementById('trendsChart').getContext('2d');
    
    trendsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Capacity %',
                data: [],
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'hour',
                        displayFormats: {
                            hour: 'HH:mm'
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Capacity: ${context.parsed.y.toFixed(1)}%`;
                        }
                    }
                }
            }
        }
    });
}

// Update capacity chart with current data
function updateCapacityChart() {
    if (!capacityChart) return;
    
    const hospitals = ['RUH', 'SPH', 'SCH'];
    const capacityData = hospitals.map(hospital => {
        const data = hospitalData[hospital];
        return data ? (data.capacity_percentage || 0) : 0;
    });
    
    capacityChart.data.datasets[0].data = capacityData;
    
    // Update bar colors based on capacity levels
    capacityChart.data.datasets[0].backgroundColor = capacityData.map(percentage => {
        if (percentage >= 90) return 'rgba(220, 53, 69, 0.8)';
        if (percentage >= 75) return 'rgba(255, 193, 7, 0.8)';
        return 'rgba(25, 135, 84, 0.8)';
    });
    
    capacityChart.data.datasets[0].borderColor = capacityData.map(percentage => {
        if (percentage >= 90) return 'rgba(220, 53, 69, 1)';
        if (percentage >= 75) return 'rgba(255, 193, 7, 1)';
        return 'rgba(25, 135, 84, 1)';
    });
    
    capacityChart.update();
}

// Load historical data for trends chart
async function loadHistoricalData(hospitalCode) {
    try {
        currentTrendHospital = hospitalCode;
        
        const response = await fetch(`/api/hospital-history/${hospitalCode}`);
        const result = await response.json();
        
        if (result.status === 'success') {
            updateTrendsChart(result.data);
        } else {
            console.error('Failed to load historical data:', result.message);
            updateTrendsChart([]);
        }
    } catch (error) {
        console.error('Error loading historical data:', error);
        updateTrendsChart([]);
    }
}

// Update trends chart with historical data
function updateTrendsChart(data) {
    if (!trendsChart) return;
    
    const labels = data.map(item => new Date(item.timestamp));
    const capacityData = data.map(item => item.capacity_percentage || 0);
    
    trendsChart.data.labels = labels;
    trendsChart.data.datasets[0].data = capacityData;
    
    // Update chart title to show selected hospital
    const hospitalName = getFullHospitalName(currentTrendHospital);
    trendsChart.options.plugins.title = {
        display: true,
        text: `${hospitalName} - 24 Hour Trends`
    };
    
    trendsChart.update();
}

// Update scraping status
async function updateScrapingStatus() {
    try {
        const response = await fetch('/api/scraping-status');
        const result = await response.json();
        
        if (result.status === 'success') {
            const lastScrape = result.last_scrape;
            const statusElement = document.getElementById('scraping-status');
            
            if (lastScrape.timestamp) {
                const scrapeTime = new Date(lastScrape.timestamp);
                const now = new Date();
                const diffMinutes = Math.floor((now - scrapeTime) / (1000 * 60));
                
                let statusText = '';
                let statusClass = '';
                
                if (lastScrape.status === 'success') {
                    statusText = `Last updated ${diffMinutes} min ago`;
                    statusClass = 'text-success-custom';
                } else {
                    statusText = `Error ${diffMinutes} min ago`;
                    statusClass = 'text-danger-custom';
                }
                
                statusElement.textContent = `Status: ${statusText}`;
                statusElement.className = statusClass;
            } else {
                statusElement.textContent = 'Status: Never run';
                statusElement.className = 'text-muted';
            }
        }
    } catch (error) {
        console.error('Error updating scraping status:', error);
        document.getElementById('scraping-status').textContent = 'Status: Unknown';
    }
}

// Update last updated time
function updateLastUpdatedTime(timestamp) {
    if (!timestamp) return;
    
    const updateTime = new Date(timestamp);
    const now = new Date();
    const diffMinutes = Math.floor((now - updateTime) / (1000 * 60));
    
    let timeText = '';
    if (diffMinutes < 1) {
        timeText = 'Just now';
    } else if (diffMinutes === 1) {
        timeText = '1 minute ago';
    } else {
        timeText = `${diffMinutes} minutes ago`;
    }
    
    document.getElementById('update-time').textContent = timeText;
}

// Show/hide loading state
function showLoading(show) {
    const cards = document.querySelectorAll('.card-body h3, .card-body .badge');
    cards.forEach(card => {
        if (show) {
            card.classList.add('loading-placeholder');
        } else {
            card.classList.remove('loading-placeholder');
        }
    });
}

// Show error alert
function showError(message) {
    const errorAlert = document.getElementById('error-alert');
    const errorMessage = document.getElementById('error-message');
    
    errorMessage.textContent = message;
    errorAlert.classList.remove('d-none');
    
    // Re-initialize feather icons for the alert
    feather.replace();
    
    // Auto-hide after 10 seconds
    setTimeout(() => {
        errorAlert.classList.add('d-none');
    }, 10000);
}

// Show no data alert
function showNoDataAlert() {
    const noDataAlert = document.getElementById('no-data-alert');
    noDataAlert.classList.remove('d-none');
    
    // Re-initialize feather icons
    feather.replace();
}

// Hide all alerts
function hideAlerts() {
    document.getElementById('error-alert').classList.add('d-none');
    document.getElementById('no-data-alert').classList.add('d-none');
}

// Helper functions
function getHospitalCode(hospitalName) {
    const codeMap = {
        'Royal University Hospital': 'RUH',
        "St. Paul's Hospital": 'SPH',
        'Saskatoon City Hospital': 'SCH'
    };
    return codeMap[hospitalName] || hospitalName;
}

function getFullHospitalName(code) {
    const nameMap = {
        'RUH': 'Royal University Hospital',
        'SPH': "St. Paul's Hospital",
        'SCH': 'Saskatoon City Hospital'
    };
    return nameMap[code] || code;
}
