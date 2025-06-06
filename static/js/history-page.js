let historicalChart = null;
let originalChartDatasets = []; // Store all datasets before filtering

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    initializeHistoricalChart();

    const dateRangeSelect = document.getElementById('dateRangeSelect');
    if (dateRangeSelect) {
        dateRangeSelect.addEventListener('change', loadHistoricalData);
    }

    loadHistoricalData(); // Initial load

    // Setup checkbox listeners
    ['toggleRUH', 'toggleSPH', 'toggleSCH', 'toggleJPCH'].forEach(id => {
        const checkbox = document.getElementById(id);
        if (checkbox) {
            checkbox.addEventListener('change', updateChartVisibility);
        }
    });

    // Auto-refresh every 10 minutes (respecting selected date range)
    setInterval(() => {
        loadHistoricalData();
    }, 10 * 60 * 1000);
});

function initializeHistoricalChart() {
    const ctx = document.getElementById('historicalChart').getContext('2d');
    historicalChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: []
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Emergency Department Patients'
                    }
                },
                x: {
                    type: 'time', // Set x-axis type to 'time'
                    time: {
                        tooltipFormat: 'MMM dd, yyyy HH:mm', // Format for tooltips
                        displayFormats: {
                            hour: 'HH:mm',        // Display hour and minute
                            day: 'MMM dd',        // Display month and day
                            week: 'MMM dd',       // Display month and day for week start
                            month: 'MMM yyyy'     // Display month and year
                        }
                    },
                    title: {
                        display: true,
                        text: 'Time Period'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            }
        }
    });
}

function showChartLoadingOverlay(show) {
    const overlay = document.getElementById('chart-loading-overlay');
    if (overlay) {
        overlay.style.display = show ? 'flex' : 'none';
    }
}

function loadHistoricalData() {
    showChartLoadingOverlay(true); // Show loading overlay

    const hospitals = ['RUH', 'SPH', 'SCH', 'JPCH'];
    const colors = {
        'RUH': '#FF6384',
        'SPH': '#36A2EB',
        'SCH': '#FFCE56',
        'JPCH': '#4BC0C0'
    };

    const dateRangeSelect = document.getElementById('dateRangeSelect');
    const daysValue = dateRangeSelect ? dateRangeSelect.value : '7';
    const rangeText = dateRangeSelect ? dateRangeSelect.options[dateRangeSelect.selectedIndex].text : 'Last 7 days';

    // Update page subtitle and chart title
    const pageSubtitle = document.querySelector('h1.display-6 + p.text-muted');
    if (pageSubtitle) {
        pageSubtitle.textContent = `${rangeText} view of Emergency Department patient counts`;
    }
    const chartCardHeader = document.querySelector('#historicalChart').closest('.card').querySelector('.card-header h5');
    if (chartCardHeader) {
        chartCardHeader.textContent = `${rangeText} Patient Count Trends`;
    }
    const chartCanvas = document.getElementById('historicalChart');
    if (chartCanvas) {
        chartCanvas.setAttribute('aria-label', `Chart showing ${rangeText} patient count trends for Saskatoon hospitals`);
    }
    // Update summary statistics title
    const summaryCardHeader = document.querySelector('#summary-table').closest('.card').querySelector('.card-header h5');
    if (summaryCardHeader) {
        summaryCardHeader.textContent = `${rangeText} Summary Statistics`;
    }
    // Update summary table headers
    const summaryTable = document.getElementById('summary-table');
    if (summaryTable) {
        const thAverage = summaryTable.querySelector('thead th:nth-child(4)'); // 7-Day Average
        const thPeak = summaryTable.querySelector('thead th:nth-child(5)'); // Peak This Week
        const thLowest = summaryTable.querySelector('thead th:nth-child(6)'); // Lowest This Week
        if (thAverage) thAverage.textContent = `${rangeText} Average`;
        if (thPeak) thPeak.textContent = `Peak (${rangeText})`;
        if (thLowest) thLowest.textContent = `Lowest (${rangeText})`;
    }


    Promise.all(hospitals.map(code =>
        fetch(`/api/hospital-history/${code}?days=${daysValue}`).then(r => r.json())
    )).then(results => {
        originalChartDatasets = []; // Clear previous datasets
        const allData = {};
        const allLabels = new Set();

        results.forEach((result, index) => {
            const hospital = hospitals[index];
            if (result.success && result.data.length > 0) {
                let sortedData = result.data.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
                sortedData = filterDataAnomalies(sortedData, hospital);
                allData[hospital] = sortedData;

                const dataPoints = sortedData.map(item => {
                    const utcTime = new Date(item.timestamp);
                    // Convert to Saskatchewan time (UTC-6) for label generation if needed, but store Date objects
                    const saskTime = new Date(utcTime.getTime() - (6 * 60 * 60 * 1000));
                    allLabels.add(saskTime); // Add the Date object itself for the time scale
                    return item.total_patients;
                });

                originalChartDatasets.push({
                    label: hospital,
                    data: dataPoints,
                    borderColor: colors[hospital],
                    backgroundColor: colors[hospital] + '20',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.1
                });

                updateHospitalTable(hospital.toLowerCase(), sortedData);
            }
        });

        // Sort Date objects correctly
        const sortedLabels = Array.from(allLabels).sort((a, b) => a - b);
        historicalChart.data.labels = sortedLabels;

        updateChartVisibility(); // This will filter and update the chart
        updateSummaryStats(allData);
        showChartLoadingOverlay(false); // Hide loading overlay
    }).catch(error => {
        console.error('Error loading historical data:', error);
        // Potentially clear chart or show error message on chart
        if (historicalChart) {
            historicalChart.data.labels = [];
            historicalChart.data.datasets = [];
            historicalChart.update();
        }
        showChartLoadingOverlay(false); // Hide loading overlay even on error
    });
}

function updateChartVisibility() {
    if (!historicalChart || !originalChartDatasets) {
        return;
    }

    const selectedHospitals = [];
    ['toggleRUH', 'toggleSPH', 'toggleSCH', 'toggleJPCH'].forEach(id => {
        const checkbox = document.getElementById(id);
        if (checkbox && checkbox.checked) {
            selectedHospitals.push(checkbox.value);
        }
    });

    const filteredDatasets = originalChartDatasets.filter(dataset =>
        selectedHospitals.includes(dataset.label)
    );

    historicalChart.data.datasets = filteredDatasets;
    historicalChart.update();
}

function updateHospitalTable(hospitalCode, data) {
    const container = document.getElementById(`${hospitalCode}-history`);

    if (data.length === 0) {
        container.innerHTML = '<p class="text-muted">No historical data available</p>';
        return;
    }

    let tableHTML = `
        <table class="table table-sm">
            <thead>
                <tr>
                    <th>Date/Time</th>
                    <th>Total Patients</th>
                    <th>Admitted</th>
                    <th>Change</th>
                </tr>
            </thead>
            <tbody>
    `;

    data.slice(-10).reverse().forEach((item, index, arr) => {
        const timestamp = new Date(item.timestamp);
        const saskTime = new Date(timestamp.getTime() - (6 * 60 * 60 * 1000));
        const admittedInED = item.admitted_patients_in_ed || 0;

        let change = '';
        let changeClass = '';
        if (index < arr.length - 1) {
            const prevCount = arr[index + 1].total_patients;
            const diff = item.total_patients - prevCount;
            if (diff > 0) {
                change = `+${diff}`;
                changeClass = 'text-danger';
            } else if (diff < 0) {
                change = `${diff}`;
                changeClass = 'text-success';
            } else {
                change = '0';
                changeClass = 'text-muted';
            }
        }

        tableHTML += `
            <tr>
                <td><small>${saskTime.toLocaleDateString('en-CA')} ${saskTime.toLocaleTimeString('en-CA', {hour: '2-digit', minute: '2-digit', hour12: false})}</small></td>
                <td><strong>${item.total_patients}</strong></td>
                <td><strong>${admittedInED}</strong></td>
                <td><small class="${changeClass}">${change}</small></td>
            </tr>
        `;
    });

    tableHTML += '</tbody></table>';
    container.innerHTML = tableHTML;
}

function filterDataAnomalies(data, hospital) {
    if (data.length === 0) return data;

    // Remove duplicates based on timestamp (keep most recent for each minute)
    const uniqueData = [];
    const seenMinutes = new Map();

    data.forEach(item => {
        const minuteKey = new Date(item.timestamp).toISOString().slice(0, 16);
        if (!seenMinutes.has(minuteKey) || new Date(item.timestamp) > new Date(seenMinutes.get(minuteKey).timestamp)) {
            seenMinutes.set(minuteKey, item);
        }
    });

    // Convert back to array and sort
    const deduplicatedData = Array.from(seenMinutes.values()).sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

    // Define reasonable ranges for each hospital
    const hospitalRanges = {
        'RUH': { min: 15, max: 120 },
        'SPH': { min: 5, max: 80 },
        'SCH': { min: 0, max: 60 },
        'JPCH': { min: 0, max: 40 }
    };

    const range = hospitalRanges[hospital] || { min: 0, max: 200 };

    // Filter out values outside reasonable ranges
    const validData = deduplicatedData.filter(item => {
        const patients = item.total_patients || 0;
        return patients >= range.min && patients <= range.max;
    });

    // Remove sudden drops/spikes (more than 50% change within 15 minutes)
    const smoothedData = [];

    for (let i = 0; i < validData.length; i++) {
        const current = validData[i];

        if (i === 0) {
            smoothedData.push(current);
            continue;
        }

        const previous = smoothedData[smoothedData.length - 1];
        const currentTime = new Date(current.timestamp);
        const previousTime = new Date(previous.timestamp);
        const timeDiff = (currentTime - previousTime) / (1000 * 60); // minutes

        // If readings are within 15 minutes, check for sudden changes
        if (timeDiff <= 15 && previous.total_patients > 0) {
            const changePercent = Math.abs((current.total_patients - previous.total_patients) / previous.total_patients);

            // Skip readings with more than 50% change (likely data errors)
            if (changePercent > 0.5) {
                console.log(`Filtering anomaly for ${hospital}: ${previous.total_patients} -> ${current.total_patients} (${(changePercent * 100).toFixed(1)}% change)`);
                continue;
            }
        }

        smoothedData.push(current);
    }

    console.log(`${hospital}: ${data.length} -> ${deduplicatedData.length} -> ${validData.length} -> ${smoothedData.length} data points after filtering`);
    return smoothedData;
}

function updateSummaryStats(allData) {
    const container = document.getElementById('summary-stats');

    if (!container) {
        console.error('Summary stats container not found');
        return;
    }

    let statsHTML = '';
    const hospitalNames = {
        'RUH': 'Royal University Hospital',
        'SPH': 'St. Paul\'s Hospital',
        'SCH': 'Saskatoon City Hospital',
        'JPCH': 'Jim Pattison Children\'s Hospital'
    };

    if (Object.keys(allData).length === 0) {
        statsHTML = '<tr><td colspan="7" class="text-center text-muted">No data available for summary statistics</td></tr>';
    } else {
        Object.keys(allData).forEach(hospital => {
            const data = allData[hospital];
            if (data.length === 0) return;

            const counts = data.map(item => item.total_patients || 0);
            const current = counts[counts.length - 1] || 0;
            const currentAdmitted = data[data.length - 1]?.admitted_patients_in_ed || 0;
            const max = Math.max(...counts) || 0;
            const min = Math.min(...counts) || 0;
            const avg = counts.length > 0 ? Math.round(counts.reduce((a, b) => a + b, 0) / counts.length) : 0;

            // Calculate trend (compare first 25% vs last 25% of data)
            const quarterSize = Math.floor(counts.length / 4);
            const firstQuarter = quarterSize > 0 ? counts.slice(0, quarterSize) : [counts[0]];
            const lastQuarter = quarterSize > 0 ? counts.slice(-quarterSize) : [counts[counts.length - 1]];

            const firstAvg = firstQuarter.reduce((a, b) => a + b, 0) / firstQuarter.length;
            const lastAvg = lastQuarter.reduce((a, b) => a + b, 0) / lastQuarter.length;
            const trendPercent = ((lastAvg - firstAvg) / firstAvg * 100).toFixed(1);

            let trendIcon = '';
            let trendClass = '';
            if (trendPercent > 5) {
                trendIcon = '↗️';
                trendClass = 'text-danger';
            } else if (trendPercent < -5) {
                trendIcon = '↘️';
                trendClass = 'text-success';
            } else {
                trendIcon = '→';
                trendClass = 'text-muted';
            }

            statsHTML += `
                <tr>
                    <td>
                        <strong>${hospital}</strong><br>
                        <small class="text-muted">${hospitalNames[hospital] || hospital}</small>
                    </td>
                    <td class="text-center">
                        <span class="badge bg-primary fs-6">${current}</span>
                    </td>
                    <td class="text-center">
                        <span class="badge rounded-pill border border-info text-info bg-transparent px-3 py-1">
                            <i class="fas fa-bed me-1"></i>${currentAdmitted}
                        </span>
                    </td>
                    <td class="text-center">
                        <span class="fs-6">${avg}</span>
                    </td>
                    <td class="text-center">
                        <span class="text-danger fw-bold">${max}</span>
                    </td>
                    <td class="text-center">
                        <span class="text-success fw-bold">${min}</span>
                    </td>
                    <td class="text-center">
                        <span class="${trendClass}">${trendIcon} ${Math.abs(trendPercent)}%</span>
                    </td>
                </tr>
            `;
        });
    }

    container.innerHTML = statsHTML;
}
