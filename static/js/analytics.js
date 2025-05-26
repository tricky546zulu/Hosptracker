// Analytics Dashboard JavaScript
let analyticsCharts = {};
let currentPeriod = 7;

document.addEventListener('DOMContentLoaded', function() {
    console.log('Starting analytics dashboard...');
    initializeAnalytics();
    
    // Period selector event listeners
    document.querySelectorAll('input[name="period"]').forEach(radio => {
        radio.addEventListener('change', function() {
            currentPeriod = parseInt(this.value);
            loadAnalyticsData();
        });
    });
});

async function initializeAnalytics() {
    try {
        await loadAnalyticsData();
    } catch (error) {
        console.error('Error initializing analytics:', error);
        showError('Failed to load analytics data');
    }
}

async function loadAnalyticsData() {
    try {
        console.log(`Loading analytics data for ${currentPeriod} days...`);
        
        const response = await fetch(`/api/analytics/${currentPeriod}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            updateSummaryStats(data.summary);
            updateHospitalCharts(data.hospital_data);
            updateComparisonCharts(data.comparison);
        } else {
            showError('Failed to load analytics data');
        }
    } catch (error) {
        console.error('Error loading analytics:', error);
        showError('Error loading analytics data');
    }
}

function updateSummaryStats(summary) {
    document.getElementById('totalDataPoints').textContent = summary.total_data_points || '0';
    document.getElementById('avgPatients').textContent = Math.round(summary.avg_patients_per_day || 0);
    document.getElementById('peakPatients').textContent = summary.peak_patient_count || '0';
    document.getElementById('busiestHospital').textContent = summary.busiest_hospital || '-';
}

function updateHospitalCharts(hospitalData) {
    const hospitals = ['RUH', 'SPH', 'SCH'];
    
    hospitals.forEach(hospital => {
        const data = hospitalData[hospital];
        if (data) {
            updateDailyChart(hospital, data.daily_trends);
            updateHourlyChart(hospital, data.hourly_patterns);
            updateWeeklyChart(hospital, data.weekly_patterns);
        }
    });
}

function updateDailyChart(hospital, dailyData) {
    const ctx = document.getElementById(`${hospital.toLowerCase()}DailyChart`).getContext('2d');
    
    // Destroy existing chart if it exists
    if (analyticsCharts[`${hospital}Daily`]) {
        analyticsCharts[`${hospital}Daily`].destroy();
    }
    
    const labels = dailyData.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-CA', { month: 'short', day: 'numeric' });
    });
    
    analyticsCharts[`${hospital}Daily`] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Average Patients',
                data: dailyData.map(d => d.avg_patients),
                borderColor: '#17a2b8',
                backgroundColor: 'rgba(23, 162, 184, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#fff' }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#6c757d' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                },
                y: {
                    ticks: { color: '#6c757d' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    beginAtZero: true
                }
            }
        }
    });
}

function updateHourlyChart(hospital, hourlyData) {
    const ctx = document.getElementById(`${hospital.toLowerCase()}HourlyChart`).getContext('2d');
    
    if (analyticsCharts[`${hospital}Hourly`]) {
        analyticsCharts[`${hospital}Hourly`].destroy();
    }
    
    const labels = hourlyData.map(d => `${d.hour}:00`);
    
    analyticsCharts[`${hospital}Hourly`] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Average Patients',
                data: hourlyData.map(d => d.avg_patients),
                backgroundColor: 'rgba(23, 162, 184, 0.7)',
                borderColor: '#17a2b8',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#fff' }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#6c757d' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                },
                y: {
                    ticks: { color: '#6c757d' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    beginAtZero: true
                }
            }
        }
    });
}

function updateWeeklyChart(hospital, weeklyData) {
    const ctx = document.getElementById(`${hospital.toLowerCase()}WeeklyChart`).getContext('2d');
    
    if (analyticsCharts[`${hospital}Weekly`]) {
        analyticsCharts[`${hospital}Weekly`].destroy();
    }
    
    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const labels = weeklyData.map(d => dayNames[d.day_of_week]);
    
    analyticsCharts[`${hospital}Weekly`] = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Average Patients',
                data: weeklyData.map(d => d.avg_patients),
                borderColor: '#17a2b8',
                backgroundColor: 'rgba(23, 162, 184, 0.2)',
                pointBackgroundColor: '#17a2b8',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: '#17a2b8'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#fff' }
                }
            },
            scales: {
                r: {
                    angleLines: { color: 'rgba(255, 255, 255, 0.1)' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    pointLabels: { color: '#6c757d' },
                    ticks: { 
                        color: '#6c757d',
                        backdropColor: 'transparent'
                    },
                    beginAtZero: true
                }
            }
        }
    });
}

function updateComparisonCharts(comparisonData) {
    updateAverageComparisonChart(comparisonData.averages);
    updatePeakComparisonChart(comparisonData.peaks);
}

function updateAverageComparisonChart(averageData) {
    const ctx = document.getElementById('comparisonChart').getContext('2d');
    
    if (analyticsCharts.comparison) {
        analyticsCharts.comparison.destroy();
    }
    
    const hospitals = Object.keys(averageData);
    const values = Object.values(averageData).map(v => Math.round(v * 10) / 10);
    
    analyticsCharts.comparison = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: hospitals.map(h => getFullHospitalName(h)),
            datasets: [{
                data: values,
                backgroundColor: [
                    'rgba(23, 162, 184, 0.8)',
                    'rgba(40, 167, 69, 0.8)',
                    'rgba(255, 193, 7, 0.8)'
                ],
                borderColor: [
                    '#17a2b8',
                    '#28a745',
                    '#ffc107'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#fff' }
                }
            }
        }
    });
}

function updatePeakComparisonChart(peakData) {
    const ctx = document.getElementById('peakComparisonChart').getContext('2d');
    
    if (analyticsCharts.peakComparison) {
        analyticsCharts.peakComparison.destroy();
    }
    
    const hospitals = Object.keys(peakData);
    const averages = hospitals.map(h => Math.round(peakData[h].average * 10) / 10);
    const peaks = hospitals.map(h => peakData[h].peak);
    
    analyticsCharts.peakComparison = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hospitals.map(h => getFullHospitalName(h)),
            datasets: [
                {
                    label: 'Average',
                    data: averages,
                    backgroundColor: 'rgba(23, 162, 184, 0.7)',
                    borderColor: '#17a2b8',
                    borderWidth: 1
                },
                {
                    label: 'Peak',
                    data: peaks,
                    backgroundColor: 'rgba(220, 53, 69, 0.7)',
                    borderColor: '#dc3545',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#fff' }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#6c757d' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                },
                y: {
                    ticks: { color: '#6c757d' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    beginAtZero: true
                }
            }
        }
    });
}

function getFullHospitalName(code) {
    const names = {
        'RUH': 'Royal University Hospital',
        'SPH': 'Saskatoon City Hospital', 
        'SCH': 'St. Paul\'s Hospital'
    };
    return names[code] || code;
}

function showError(message) {
    console.error(message);
    // You could add a toast notification here
}