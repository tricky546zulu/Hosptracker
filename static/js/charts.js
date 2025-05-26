// Hospital Capacity Dashboard Charts and Data Management

let capacityChart = null;
let trendsChart = null;
let hospitalData = {};
let miniCharts = {};
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
    initializeMiniCharts();
    
    // Load all hospital historical data for combined view
    loadAllHospitalTrends();
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
        // Update Total patients count
        document.getElementById(`${prefix}-total-patients`).textContent = data.total_patients || '-';
        
        // Add update animation
        const card = document.getElementById(`${prefix}-total-patients`).closest('.card');
        card.classList.add('data-update');
        setTimeout(() => card.classList.remove('data-update'), 500);
        
    } else {
        // Show no data state
        document.getElementById(`${prefix}-total-patients`).textContent = '-';
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
    const chartElement = document.getElementById('capacityChart');
    if (!chartElement) {
        console.warn('Capacity chart element not found');
        return;
    }
    
    const ctx = chartElement.getContext('2d');
    
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
                    max: 80,
                    ticks: {
                        callback: function(value) {
                            return value + ' patients';
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
                                return `Total Patients: ${data.total_patients || 0}`;
                            }
                            return `Total Patients: ${context.parsed.y}`;
                        }
                    }
                }
            }
        }
    });
}

// Initialize trends chart
function initializeTrendsChart() {
    const chartElement = document.getElementById('trendsChart');
    if (!chartElement) {
        console.warn('Trends chart element not found');
        return;
    }
    
    const ctx = chartElement.getContext('2d');
    
    trendsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: []
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
                            hour: 'MMM DD, HH:mm'
                        },
                        tooltipFormat: 'MMM DD, YYYY HH:mm'
                    },
                    title: {
                        display: true,
                        text: 'Saskatchewan Time'
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 80,
                    ticks: {
                        callback: function(value) {
                            return value + ' patients';
                        }
                    },
                    title: {
                        display: true,
                        text: 'Total Patients'
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            const date = new Date(context[0].parsed.x);
                            return date.toLocaleString('en-CA', {
                                timeZone: 'America/Regina',
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                            });
                        },
                        label: function(context) {
                            return `${context.dataset.label}: ${context.parsed.y} patients`;
                        }
                    }
                }
            }
        }
    });
}

// Initialize simple CSS-based mini charts
function initializeMiniCharts() {
    console.log('Initializing mini charts with CSS...');
    // Mini charts will be created with CSS/HTML - no complex Chart.js needed
}

// Update capacity chart with current data
function updateCapacityChart() {
    if (!capacityChart) return;
    
    const hospitals = ['RUH', 'SPH', 'SCH'];
    const totalPatientsData = hospitals.map(hospital => {
        const data = hospitalData[hospital];
        return data ? (data.total_patients || 0) : 0;
    });
    
    capacityChart.data.datasets[0].data = totalPatientsData;
    
    // Update bar colors based on patient counts
    capacityChart.data.datasets[0].backgroundColor = totalPatientsData.map(count => {
        if (count >= 40) return 'rgba(220, 53, 69, 0.8)';
        if (count >= 20) return 'rgba(255, 193, 7, 0.8)';
        return 'rgba(25, 135, 84, 0.8)';
    });
    
    capacityChart.data.datasets[0].borderColor = totalPatientsData.map(count => {
        if (count >= 40) return 'rgba(220, 53, 69, 1)';
        if (count >= 20) return 'rgba(255, 193, 7, 1)';
        return 'rgba(25, 135, 84, 1)';
    });
    
    capacityChart.update();
}

// Load historical data for all hospitals combined
async function loadAllHospitalTrends() {
    try {
        const hospitals = ['RUH', 'SPH', 'SCH'];
        const allData = {};
        
        // Fetch data for all hospitals
        for (const hospital of hospitals) {
            const response = await fetch(`/api/hospital-history/${hospital}`);
            const result = await response.json();
            
            if (result.status === 'success') {
                allData[hospital] = result.data;
                // Update mini chart for this hospital
                updateMiniChart(hospital.toLowerCase(), result.data);
            }
        }
        
        // Update combined trends chart
        updateCombinedTrendsChart(allData);
        
    } catch (error) {
        console.error('Error loading hospital trends:', error);
    }
}

// Update mini chart for individual hospital using SVG
function updateMiniChart(hospitalCode, data) {
    if (!data || data.length === 0) return;
    
    const lineElement = document.getElementById(`${hospitalCode}-line`);
    const loadingElement = document.querySelector(`#${hospitalCode}-mini-chart .mini-chart-loading`);
    
    if (!lineElement) return;
    
    // Hide loading text
    if (loadingElement) loadingElement.style.display = 'none';
    
    // Get patient data
    const patientData = data.map(item => item.total_patients || 0);
    const maxPatients = Math.max(...patientData, 60); // At least 60 for scale
    
    // Create SVG points for the line
    const width = 100; // SVG viewBox width
    const height = 100; // SVG viewBox height
    const points = patientData.map((value, index) => {
        const x = (index / Math.max(patientData.length - 1, 1)) * width;
        const y = height - (value / maxPatients) * height;
        return `${x},${y}`;
    }).join(' ');
    
    // Update the polyline points
    lineElement.setAttribute('points', points);
    lineElement.parentElement.setAttribute('viewBox', `0 0 ${width} ${height}`);
}

// Update trends chart with combined hospital data
function updateCombinedTrendsChart(allData) {
    if (!trendsChart) return;
    
    // Clear existing datasets
    trendsChart.data.datasets = [];
    
    const hospitals = [
        { code: 'RUH', name: 'Royal University Hospital', color: 'rgba(75, 192, 192, 1)' },
        { code: 'SPH', name: "St. Paul's Hospital", color: 'rgba(255, 99, 132, 1)' },
        { code: 'SCH', name: 'Saskatoon City Hospital', color: 'rgba(54, 162, 235, 1)' }
    ];
    
    let allTimestamps = new Set();
    
    // Add datasets for each hospital
    hospitals.forEach(hospital => {
        const data = allData[hospital.code] || [];
        if (data.length > 0) {
            // Convert to Saskatchewan time
            const labels = data.map(item => {
                const date = new Date(item.timestamp);
                // Saskatchewan is UTC-6 (CST)
                return new Date(date.getTime() - (6 * 60 * 60 * 1000));
            });
            const patientData = data.map(item => item.total_patients || 0);
            
            // Add timestamps to the set
            labels.forEach(label => allTimestamps.add(label.getTime()));
            
            trendsChart.data.datasets.push({
                label: hospital.name,
                data: labels.map((label, index) => ({
                    x: label,
                    y: patientData[index]
                })),
                borderColor: hospital.color,
                backgroundColor: hospital.color.replace('1)', '0.1)'),
                borderWidth: 2,
                fill: false,
                tension: 0.4
            });
        }
    });
    
    // Sort timestamps and use for x-axis
    const sortedTimestamps = Array.from(allTimestamps).sort();
    trendsChart.data.labels = sortedTimestamps.map(ts => new Date(ts));
    
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
