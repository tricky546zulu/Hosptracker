// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadHospitalData();
    loadScrapingStatus();
    loadWeatherData();

    // Auto-refresh every 10 minutes
    setInterval(() => {
        loadHospitalData();
        loadScrapingStatus();
        loadWeatherData();
    }, 10 * 60 * 1000);
});

function loadHospitalData() {
    fetch('/api/hospital-data')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateHospitalCards(data.data);
            }
        })
        .catch(error => {
            console.error('Error loading hospital data:', error);
        });
}

function updateHospitalCards(hospitals) {
    hospitals.forEach(hospital => {
        const code = hospital.hospital_code.toLowerCase();
        const patientsElement = document.getElementById(`${code}-total-patients`);
        const timeElement = document.getElementById(`${code}-time`);

        if (patientsElement) {
            const totalPatients = hospital.total_patients || '-';
            const admittedInED = hospital.admitted_patients_in_ed;

            // Display total patients with admitted breakdown if available
            if (admittedInED !== null && admittedInED !== undefined) {
                patientsElement.innerHTML = `
                    <div class="fs-1 fw-bold text-primary">${totalPatients}</div>
                    <div class="mt-2">
                        <span class="badge rounded-pill border border-info text-info bg-transparent px-3 py-2 fs-6">
                            <i class="fas fa-bed me-1"></i>${admittedInED} Admitted in ED
                        </span>
                    </div>
                `;
            } else {
                patientsElement.innerHTML = `<div class="fs-1 fw-bold text-primary">${totalPatients}</div>`;
            }
        }

        if (timeElement) {
            const time = new Date(hospital.timestamp);
            const saskTime = new Date(time.getTime() - (6 * 60 * 60 * 1000)); // UTC-6
            timeElement.textContent = `Updated: ${saskTime.toLocaleTimeString('en-CA', {hour12: false})}`;
        }
    });
}



function loadScrapingStatus() {
    fetch('/api/scraping-status')
        .then(response => response.json())
        .then(data => {
            console.log('Status data received:', data);
            if (data.success) {
                updateStatusDisplay(data);
            } else {
                console.error('Status request failed:', data);
            }
        })
        .catch(error => {
            console.error('Error loading status:', error);
            // Show error status
            updateStatusDisplay({
                status: 'error',
                message: 'Unable to connect to server',
                timestamp: null
            });
        });
}

function updateStatusDisplay(status) {
    const statusContent = document.getElementById('status-content');
    const timestamp = status.timestamp ? new Date(status.timestamp) : null;
    const saskTime = timestamp ? new Date(timestamp.getTime() - (6 * 60 * 60 * 1000)) : null;

    let statusClass = 'text-success';
    let statusIcon = 'check-circle';

    if (status.status === 'error') {
        statusClass = 'text-danger';
        statusIcon = 'alert-circle';
    } else if (status.status === 'no_data') {
        statusClass = 'text-warning';
        statusIcon = 'clock';
    }

    statusContent.innerHTML = `
        <div class="d-flex align-items-center">
            <i data-feather="${statusIcon}" class="${statusClass} me-2"></i>
            <div>
                <strong>Last Update:</strong> ${saskTime ? saskTime.toLocaleString('en-CA') : 'Never'}
                <br>
                <small class="text-muted">${status.message}</small>
            </div>
        </div>
    `;
    feather.replace();
}

function refreshData() {
    const btn = document.getElementById('refresh-btn');
    btn.disabled = true;
    btn.innerHTML = '<i data-feather="loader" class="me-1"></i>Refreshing...';

    loadHospitalData();
    loadScrapingStatus();
    loadWeatherData();

    setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = '<i data-feather="refresh-cw" class="me-1"></i>Refresh';
        feather.replace();
    }, 2000);
}

function loadWeatherData() {
    fetch('/api/weather')
        .then(response => response.json())
        .then(data => {
            console.log('Weather data received:', data);
            if (data.success) {
                updateWeatherDisplay(data.data);
            } else {
                console.error('Weather request failed:', data);
                updateWeatherDisplay(null, data.error || 'Unable to load weather data');
            }
        })
        .catch(error => {
            console.error('Error loading weather:', error);
            updateWeatherDisplay(null, 'Weather service unavailable');
        });
}

function updateWeatherDisplay(weather, error) {
    const weatherContent = document.getElementById('weather-content');

    if (!weatherContent) {
        console.error('Weather content element not found');
        return;
    }

    if (error || !weather) {
        weatherContent.innerHTML = `
            <div class="text-center text-muted">
                <i data-feather="cloud-off" class="mb-2"></i>
                <p class="mb-0">${error || 'Weather data unavailable'}</p>
            </div>
        `;
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
        return;
    }

    const iconUrl = `https://openweathermap.org/img/wn/${weather.icon}@2x.png`;

    weatherContent.innerHTML = `
        <div class="text-center">
            <div class="d-flex align-items-center justify-content-center mb-2">
                <img src="${iconUrl}" alt="${weather.description}" style="width: 48px; height: 48px;">
                <div class="ms-2">
                    <h3 class="mb-0">${weather.temperature}°C</h3>
                    <small class="text-muted">Feels like ${weather.feels_like}°C</small>
                </div>
            </div>
            <p class="text-capitalize mb-2">${weather.description}</p>
            <small class="text-muted">${weather.city}</small>

            <hr class="my-3">

            <div class="row g-2 text-center">
                <div class="col-6">
                    <div class="d-flex align-items-center justify-content-center">
                        <i data-feather="percent" class="me-1" style="width: 14px; height: 14px;"></i>
                        <small>${weather.humidity}%</small>
                    </div>
                </div>
                <div class="col-6">
                    <div class="d-flex align-items-center justify-content-center">
                        <i data-feather="wind" class="me-1" style="width: 14px; height: 14px;"></i>
                        <small>${weather.wind_speed} km/h</small>
                    </div>
                </div>
                <div class="col-6">
                    <div class="d-flex align-items-center justify-content-center">
                        <i data-feather="eye" class="me-1" style="width: 14px; height: 14px;"></i>
                        <small>${weather.visibility} km</small>
                    </div>
                </div>
                <div class="col-6">
                    <div class="d-flex align-items-center justify-content-center">
                        <i data-feather="thermometer" class="me-1" style="width: 14px; height: 14px;"></i>
                        <small>${weather.pressure} hPa</small>
                    </div>
                </div>
            </div>
        </div>
    `;

    if (typeof feather !== 'undefined') {
        feather.replace();
    }
}
