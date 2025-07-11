// Hospital Capacity Dashboard Charts and Data Management

let capacityChart = null;
let hospitalData = {};
let miniCharts = {};
let previousData = {};

// Initialize the dashboard
function initializeDashboard() {
    console.log('Starting dashboard...');

    try {
        // Load current data first
        loadHospitalData();
        updateScrapingStatus();

        // Initialize capacity chart
        setTimeout(() => {
            initializeCapacityChart();
        }, 100);

        // Initialize individual hospital charts
        setTimeout(() => {
            initializeMiniCharts();
        }, 200);

    } catch (error) {
        console.error('Error starting dashboard:', error);
    }
}

// Manual refresh function
function refreshData() {
    const refreshBtn = document.getElementById('refresh-btn');
    const icon = refreshBtn.querySelector('i');

    // Show loading state
    refreshBtn.disabled = true;
    icon.style.animation = 'spin 1s linear infinite';

    loadHospitalData().finally(() => {
        // Reset button state
        refreshBtn.disabled = false;
        icon.style.animation = '';
    });
}

// Load current hospital data
async function loadHospitalData() {
    fetch('/api/hospital-data')
        .then(response => response.json())
        .then(data => {
            console.log('Hospital data received:', data);
            if (data.success) {
                hospitalData = data.data;

                // Debug: Log each hospital's data
                hospitalData.forEach(hospital => {
                    console.log(`${hospital.hospital_code}: ${hospital.admitted_patients_in_ed} admitted, ${hospital.total_patients} total (${hospital.timestamp})`);
                });

                updateHospitalCards();
                updateCapacityChart();
                updateMiniCharts();
            } else {
                console.error('Failed to load hospital data:', data.error);
            }
        })
        .catch(error => {
            console.error('Error loading hospital data:', error);
        });
}

// Update hospital data cards
function updateHospitalCards() {
    const hospitals = ['RUH', 'SPH', 'SCH', 'JPCH'];

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
        const currentPatients = data.total_patients || 0;
        const previousPatients = previousData[hospital] || currentPatients;

        // Update Total patients count
        document.getElementById(`${prefix}-total-patients`).textContent = currentPatients;

        // Update percentage change
        const change = currentPatients - previousPatients;
        const changeElement = document.getElementById(`${prefix}-change`);
        if (change > 0) {
            changeElement.textContent = `+${change}`;
            changeElement.className = 'badge bg-danger';
        } else if (change < 0) {
            changeElement.textContent = `${change}`;
            changeElement.className = 'badge bg-success';
        } else {
            changeElement.textContent = 'No change';
            changeElement.className = 'badge bg-light text-dark';
        }

        // Update time since last update
        const timeSince = getTimeSinceUpdate(data.timestamp);
        document.getElementById(`${prefix}-time-since`).textContent = `Updated ${timeSince}`;

        // Store current data as previous for next comparison
        previousData[hospital] = currentPatients;

        // Add update animation
        const card = document.getElementById(`${prefix}-total-patients`).closest('.card');
        card.classList.add('data-update');
        setTimeout(() => card.classList.remove('data-update'), 500);

    } else {
        // Show no data state
        document.getElementById(`${prefix}-total-patients`).textContent = '-';
        document.getElementById(`${prefix}-change`).textContent = '-';
        document.getElementById(`${prefix}-time-since`).textContent = 'No recent data';
    }
}

// Get capacity level for Emergency Department
function getCapacityLevel(patientCount) {
    if (patientCount >= 70) {
        return { text: 'Very Busy', class: 'bg-danger' };
    } else if (patientCount >= 50) {
        return { text: 'Busy', class: 'bg-warning' };
    } else if (patientCount >= 30) {
        return { text: 'Moderate', class: 'bg-info' };
    } else {
        return { text: 'Quiet', class: 'bg-success' };
    }
}

// Get time since last update in plain language
function getTimeSinceUpdate(timestamp) {
    if (!timestamp) return 'unknown time ago';

    const now = new Date();
    const updateTime = new Date(timestamp);
    const diffMinutes = Math.floor((now - updateTime) / (1000 * 60));

    if (diffMinutes < 1) return 'just now';
    if (diffMinutes === 1) return '1 minute ago';
    if (diffMinutes < 60) return `${diffMinutes} minutes ago`;

    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours === 1) return '1 hour ago';
    if (diffHours < 24) return `${diffHours} hours ago`;

    return 'over a day ago';
}

// Get capacity level CSS class (legacy function)
function getCapacityClass(percentage) {
    if (percentage >= 90) return 'capacity-high';
    if (percentage >= 75) return 'capacity-medium';
    return 'capacity-low';
}

// Get capacity badge CSS class (legacy function)
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
            labels: ['Royal University Hospital', "St. Paul's Hospital", 'Saskatoon City Hospital', "Jim Pattison Children's Hospital"],
            datasets: [{
                label: 'Total Patients',
                data: [0, 0, 0, 0],
                backgroundColor: [
                    'rgba(75, 192, 192, 0.8)',
                    'rgba(255, 99, 132, 0.8)',
                    'rgba(54, 162, 235, 0.8)',
                    'rgba(255, 206, 86, 0.8)'
                ],
                borderColor: [
                    'rgba(75, 192, 192, 1)',
                    'rgba(255, 99, 132, 1)',
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
                x: {
                    title: {
                        display: true,
                        text: 'Hospitals'
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 80,
                    title: {
                        display: true,
                        text: 'Number of Patients'
                    },
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

// Initialize individual hospital line charts
function initializeMiniCharts() {
    console.log('Initializing hospital line charts...');

    const hospitals = [
        { code: 'ruh', name: 'RUH', color: 'rgba(75, 192, 192, 1)' },
        { code: 'sph', name: 'SPH', color: 'rgba(255, 99, 132, 1)' },
        { code: 'sch', name: 'SCH', color: 'rgba(54, 162, 235, 1)' },
        { code: 'jpch', name: 'JPCH', color: 'rgba(255, 206, 86, 1)' }
    ];

    hospitals.forEach(hospital => {
        const canvas = document.getElementById(`${hospital.code}-mini-chart`);
        if (canvas && canvas.getContext) {
            const ctx = canvas.getContext('2d');

            miniCharts[hospital.code] = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        borderColor: hospital.color,
                        backgroundColor: hospital.color.replace('1)', '0.1)'),
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 2,
                        pointHoverRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                title: function(context) {
                                    // Show Saskatchewan time for this data point
                                    const label = context[0].label;
                                    return `${label} SK Time`;
                                },
                                label: function(context) {
                                    return `${context.parsed.y} patients`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: { 
                            display: false
                        },
                        y: { 
                            display: true,
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Patients'
                            }
                        }
                    },
                    elements: {
                        point: { radius: 0 }
                    }
                }
            });

            // Load data for this hospital
            loadHospitalChart(hospital.code.toUpperCase());
        }
    });
}

// Update capacity chart with current data
function updateCapacityChart() {
    if (!capacityChart) return;

    const hospitals = ['RUH', 'SPH', 'SCH', 'JPCH'];
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

// Load data for individual hospital chart
async function loadHospitalChart(hospitalCode) {
    try {
        const response = await fetch(`/api/hospital-history/${hospitalCode}`);
        const result = await response.json();

        if (result.status === 'success' && result.data && result.data.length > 0) {
            const chart = miniCharts[hospitalCode.toLowerCase()];
            if (chart) {
                // Filter out duplicate timestamps and smooth the data
                const filteredData = [];
                const seenTimestamps = new Set();

                // Sort data by timestamp to ensure chronological order (oldest first)
                result.data.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

                // Process data to get unique entries by minute
                result.data.forEach(item => {
                    const timeKey = new Date(item.timestamp).toISOString().slice(0, 16); // Group by minute
                    if (!seenTimestamps.has(timeKey)) {
                        seenTimestamps.add(timeKey);
                        filteredData.push(item);
                    }
                });

                // Get last 15 unique data points for cleaner display (most recent 15)
                const recentData = filteredData.slice(-15);

                // Create consistent time labels in Saskatchewan time (UTC-6) 
                const labels = recentData.map(item => {
                    const utcDate = new Date(item.timestamp);
                    // Direct UTC-6 conversion for Saskatchewan time
                    const saskHour = (utcDate.getUTCHours() - 6 + 24) % 24;
                    const saskMinute = utcDate.getUTCMinutes();

                    return `${saskHour.toString().padStart(2, '0')}:${saskMinute.toString().padStart(2, '0')}`;
                });

                const data = recentData.map(item => item.total_patients || 0);

                chart.data.labels = labels;
                chart.data.datasets[0].data = data;
                chart.update();

                console.log(`Updated ${hospitalCode} chart with ${data.length} filtered points`);
            }
        }
    } catch (error) {
        console.error(`Error loading ${hospitalCode} chart:`, error);
    }
}



// Remove old function - no longer needed

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
                const nowUTC = new Date();
                const diffMinutes = Math.floor((nowUTC.getTime() - scrapeTime.getTime()) / (1000 * 60));

                // Saskatchewan is UTC-6 (no daylight saving) - only for display
                const saskTime = new Date(scrapeTime.getTime() - (6 * 60 * 60 * 1000));
                const timeString = saskTime.toLocaleString('en-CA', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: false
                });

                let statusText = '';
                let statusClass = '';

                if (lastScrape.status === 'success') {
                    statusText = `Last updated ${timeString}`;
                    statusClass = 'text-success-custom';
                } else {
                    statusText = `Error at ${timeString}`;
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