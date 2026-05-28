/**
 * VIIRS Nightlights Analysis Tool - Main Application
 * 
 * Handles API communication, data processing, and UI orchestration.
 */

import { MapVisualization } from './map-visualization.js';
import { GraphVisualization } from './graph-visualization.js';
import { DataExport } from './data-export.js';

class VIIRSApp {
    constructor() {
        // Use /api/ path for Docker/Nginx, or localhost:8000 for local dev
        this.API_BASE_URL = window.location.hostname === 'localhost' ? 
            'http://localhost:8000' : '/api';
        this.data = null;
        this.cityInfo = null;
        this.currentDateIndex = 0;
        this.isPlaying = false;
        this.playSpeed = 1.0;
        this.playInterval = null;
        this.selectedCities = []; // Array to store selected cities
        this.selectedCity = null; // Currently selected city from autocomplete
        this.searchTimeout = null; // For debouncing search
        
        // Visualization instances
        this.mapViz = null;
        this.graphViz = null;
        this.dataExport = null;
        
        this.init();
    }
    
    async init() {
        console.log('Initializing VIIRS App...');
        
        // Populate year dropdowns
        this.populateYearDropdowns();
        
        // Fetch latest available data
        await this.fetchLatestAvailable();
        
        // Set up event listeners
        this.setupEventListeners();
        
        console.log('App initialized successfully');
    }
    
    populateYearDropdowns() {
        const startYearSelect = document.getElementById('start-year');
        const endYearSelect = document.getElementById('end-year');
        
        const currentYear = new Date().getFullYear();
        
        // Populate 2012 to current year
        for (let year = 2012; year <= currentYear; year++) {
            const optionStart = document.createElement('option');
            optionStart.value = year;
            optionStart.textContent = year;
            if (year === 2019) optionStart.selected = true;
            startYearSelect.appendChild(optionStart);
            
            const optionEnd = document.createElement('option');
            optionEnd.value = year;
            optionEnd.textContent = year;
            if (year === currentYear) optionEnd.selected = true;
            endYearSelect.appendChild(optionEnd);
        }
    }
    
    async fetchLatestAvailable() {
        try {
            const response = await fetch(`${this.API_BASE_URL}/viirs/latest-available`);
            const data = await response.json();
            
            const badge = document.getElementById('latest-data-badge');
            badge.textContent = `Latest data available: ${data.date_string}`;
            
            // Store latest month for validation
            this.latestYear = data.year;
            this.latestMonth = data.month;
        } catch (error) {
            console.error('Error fetching latest available:', error);
            const badge = document.getElementById('latest-data-badge');
            badge.textContent = 'Unable to check latest data';
        }
    }
    
    setupEventListeners() {
        // Analyze button
        document.getElementById('analyze-btn').addEventListener('click', () => {
            this.handleAnalyze();
        });
        
        // City search autocomplete
        const searchInput = document.getElementById('city-search');
        searchInput.addEventListener('input', (e) => {
            this.handleSearchInput(e.target.value);
        });
        
        // Add city button
        document.getElementById('add-city-btn').addEventListener('click', () => {
            this.addSelectedCity();
        });
        
        // Quick city buttons
        document.querySelectorAll('.quick-city-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const cityName = e.target.dataset.city;
                if (cityName && !this.selectedCities.includes(cityName)) {
                    this.selectedCities.push(cityName);
                    this.renderSelectedCities();
                }
            });
        });
        
        // Play/pause button
        document.getElementById('play-pause-btn').addEventListener('click', () => {
            this.togglePlay();
        });
        
        // Timeline slider
        document.getElementById('timeline-slider').addEventListener('input', (e) => {
            this.handleSliderChange(e.target.value);
        });
        
        // Speed controls
        document.getElementById('speed-increase').addEventListener('click', () => {
            this.changeSpeed(0.5);
        });
        
        document.getElementById('speed-decrease').addEventListener('click', () => {
            this.changeSpeed(-0.5);
        });
        
        // Export buttons
        document.getElementById('export-excel').addEventListener('click', () => {
            this.exportData('excel');
        });
        
        document.getElementById('export-csv').addEventListener('click', () => {
            this.exportData('csv');
        });
        
        document.getElementById('export-json').addEventListener('click', () => {
            this.exportData('json');
        });
        
        // Error dismiss
        document.getElementById('dismiss-error').addEventListener('click', () => {
            document.getElementById('error-display').style.display = 'none';
        });
        
    }
    
    async handleSearchInput(query) {
        // Clear previous timeout
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
        
        if (query.length < 2) {
            this.hideAutocomplete();
            return;
        }
        
        // Debounce search - wait 300ms after user stops typing
        this.searchTimeout = setTimeout(async () => {
            try {
                // First try predefined cities for faster results
                const predefinedResults = this.searchPredefinedCities(query);
                if (predefinedResults.length > 0) {
                    this.showAutocomplete(predefinedResults);
                    return;
                }
                
                // Fallback to API search for other cities
                const response = await fetch(
                    `${this.API_BASE_URL}/search?q=${encodeURIComponent(query)}&limit=5`
                );
                const data = await response.json();
                
                if (data.results && data.results.length > 0) {
                    // Filter for better results (prioritize cities over other places)
                    const filteredResults = data.results.filter(result => 
                        result.raw && result.raw.class === 'place' && 
                        ['city', 'town', 'village'].includes(result.raw.type)
                    );
                    
                    if (filteredResults.length > 0) {
                        this.showAutocomplete(filteredResults);
                    } else {
                        this.hideAutocomplete();
                    }
                } else {
                    this.hideAutocomplete();
                }
            } catch (error) {
                console.error('Search error:', error);
                this.hideAutocomplete();
            }
        }, 300);
    }
    
    searchPredefinedCities(query) {
        const predefinedCities = [
            { city: 'Mumbai', country: 'India', lat: 19.0760, lon: 72.8777, display_name: 'Mumbai, India' },
            { city: 'Delhi', country: 'India', lat: 28.7041, lon: 77.1025, display_name: 'Delhi, India' },
            { city: 'Bengaluru', country: 'India', lat: 12.9716, lon: 77.5946, display_name: 'Bengaluru, India' },
            { city: 'Chennai', country: 'India', lat: 13.0827, lon: 80.2707, display_name: 'Chennai, India' },
            { city: 'Tiruppur', country: 'India', lat: 11.1085, lon: 77.3411, display_name: 'Tiruppur, India' },
            { city: 'Kolkata', country: 'India', lat: 22.5726, lon: 88.3639, display_name: 'Kolkata, India' },
            { city: 'Hyderabad', country: 'India', lat: 17.3850, lon: 78.4867, display_name: 'Hyderabad, India' },
            { city: 'Pune', country: 'India', lat: 18.5204, lon: 73.8567, display_name: 'Pune, India' },
            { city: 'Ahmedabad', country: 'India', lat: 23.0225, lon: 72.5714, display_name: 'Ahmedabad, India' },
            { city: 'Jaipur', country: 'India', lat: 26.9124, lon: 75.7873, display_name: 'Jaipur, India' }
        ];
        
        const queryLower = query.toLowerCase();
        return predefinedCities.filter(city => 
            city.city.toLowerCase().includes(queryLower) ||
            city.display_name.toLowerCase().includes(queryLower)
        ).slice(0, 5);
    }
    
    showAutocomplete(results) {
        const dropdown = document.getElementById('autocomplete-dropdown');
        dropdown.innerHTML = '';
        dropdown.classList.add('active');
        
        results.forEach(result => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            item.textContent = result.display_name || `${result.city}, ${result.country}`;
            
            item.addEventListener('click', () => {
                document.getElementById('city-search').value = result.city;
                this.selectedCity = result;
                this.hideAutocomplete();
            });
            
            dropdown.appendChild(item);
        });
    }
    
    hideAutocomplete() {
        const dropdown = document.getElementById('autocomplete-dropdown');
        dropdown.classList.remove('active');
    }
    
    addSelectedCity() {
        const searchInput = document.getElementById('city-search');
        const cityName = searchInput.value.trim();
        
        if (!cityName) {
            this.showError('Please enter a city name or coordinates');
            return;
        }
        
        if (this.selectedCities.length >= 5) {
            this.showError('Maximum 5 cities can be selected for comparison');
            return;
        }
        
        // Check if city is already selected
        if (this.selectedCities.includes(cityName)) {
            this.showError('City already selected');
            return;
        }
        
        this.selectedCities.push(cityName);
        this.renderSelectedCities();
        searchInput.value = ''; // Clear input
        this.hideAutocomplete();
    }
    
    removeSelectedCity(cityName) {
        this.selectedCities = this.selectedCities.filter(city => city !== cityName);
        this.renderSelectedCities();
    }
    
    renderSelectedCities() {
        const container = document.getElementById('selected-cities-container');
        container.innerHTML = '';
        
        if (this.selectedCities.length === 0) {
            container.innerHTML = '<p class="no-cities-message">No cities selected. Add up to 5 cities.</p>';
            return;
        }
        
        this.selectedCities.forEach(city => {
            const div = document.createElement('div');
            div.classList.add('selected-city-tag');
            div.innerHTML = `
                <span>${city}</span>
                <button class="remove-city-button" data-city="${city}">×</button>
            `;
            container.appendChild(div);
        });
        
        // Add event listeners for remove buttons
        container.querySelectorAll('.remove-city-button').forEach(button => {
            button.addEventListener('click', (e) => {
                this.removeSelectedCity(e.target.dataset.city);
            });
        });
    }
    
    async handleAnalyze() {
        if (this.selectedCities.length === 0) {
            this.showError('Please add at least one city to analyze');
            return;
        }
        
        // Get date range
        const startMonth = parseInt(document.getElementById('start-month').value);
        const startYear = parseInt(document.getElementById('start-year').value);
        const endMonth = parseInt(document.getElementById('end-month').value);
        const endYear = parseInt(document.getElementById('end-year').value);
        
        // Validate date range
        const startDate = new Date(startYear, startMonth - 1);
        const endDate = new Date(endYear, endMonth - 1);
        
        if (startDate >= endDate) {
            this.showError('Start date must be before end date');
            return;
        }
        
        // Show loading
        this.showLoading('Fetching VIIRS data from NOAA...');
        
        try {
            let response;
            
            if (this.selectedCities.length === 1) {
                // Single city request
                response = await fetch(`${this.API_BASE_URL}/viirs/city`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        city: this.selectedCities[0],
                        start_month: startMonth,
                        start_year: startYear,
                        end_month: endMonth,
                        end_year: endYear
                    })
                });
            } else {
                // Multi-city request
                response = await fetch(`${this.API_BASE_URL}/viirs/cities`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        cities: this.selectedCities,
                        start_month: startMonth,
                        start_year: startYear,
                        end_month: endMonth,
                        end_year: endYear
                    })
                });
            }
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to fetch data');
            }
            
            const result = await response.json();
            
            this.hideLoading();
            
            if (result.status === 'success') {
                this.processData(result);
                this.showVisualizations();
            } else {
                this.showError('Failed to fetch data');
            }
        } catch (error) {
            this.hideLoading();
            this.showError(error.message);
        }
    }
    
    processData(result) {
        this.data = result.data;
        // Handle both single city (city_info) and multi-city (cities) responses
        this.cityInfo = result.city_info || result.cities;
        this.metadata = result.metadata;
        
        // Sort data by date
        this.data.sort((a, b) => a.date.localeCompare(b.date));
        
        // Calculate percentage changes (baseline = first year)
        this.calculatePercentageChanges();
        
        // Extract unique dates
        this.dates = [...new Set(this.data.map(d => d.date))].sort();
        this.currentDateIndex = 0;
        
        // Update slider
        const slider = document.getElementById('timeline-slider');
        slider.max = this.dates.length - 1;
        slider.value = 0;
        
        console.log('Data processed:', {
            points: this.data.length,
            dates: this.dates.length,
            cities: Array.isArray(this.cityInfo) ? this.cityInfo.length : 1,
            cityInfo: this.cityInfo
        });
    }
    
    calculatePercentageChanges() {
        // Group data by city first, then calculate city-specific baselines
        const cityGroups = {};
        
        // Group data by city
        this.data.forEach(point => {
            const cityKey = `${point.city}_${point.country}`;
            if (!cityGroups[cityKey]) {
                cityGroups[cityKey] = [];
            }
            cityGroups[cityKey].push(point);
        });
        
        // Calculate percentage changes for each city
        Object.values(cityGroups).forEach(cityData => {
            // Sort by date to get chronological order
            cityData.sort((a, b) => a.date.localeCompare(b.date));
            
            // Get first year as baseline
            const firstYear = cityData[0].date.split('-')[0];
            const baselineByMonth = {};
            
            // Store baseline values (first year, same month)
            cityData.forEach(point => {
                const [year, month] = point.date.split('-');
                if (year === firstYear) {
                    baselineByMonth[month] = point.radiance_corrected;
                }
            });
            
            // Calculate percentage changes for this city
            cityData.forEach(point => {
                const [year, month] = point.date.split('-');
                const baseline = baselineByMonth[month];
                
                if (baseline && baseline > 0) {
                    point.percentage_change = ((point.radiance_corrected - baseline) / baseline) * 100;
                } else {
                    point.percentage_change = 0;
                }
            });
        });
        
        console.log('Percentage changes calculated:', this.data.slice(0, 5).map(d => ({
            city: d.city,
            date: d.date,
            radiance_corrected: d.radiance_corrected,
            percentage_change: d.percentage_change
        })));
        
        // Debug: Check if we have any non-zero percentage changes
        const nonZeroChanges = this.data.filter(d => d.percentage_change !== 0);
        console.log('Non-zero percentage changes:', nonZeroChanges.length);
        if (nonZeroChanges.length > 0) {
            console.log('Sample non-zero changes:', nonZeroChanges.slice(0, 3));
        }
    }
    
    showVisualizations() {
        // Show main content
        document.getElementById('main-content').style.display = 'block';
        
        // Initialize map (reinitialize if data structure changed)
        if (!this.mapViz) {
            this.mapViz = new MapVisualization('map-container');
        }
        
        // Set up map-to-graph interaction
        this.mapViz.onCitySelected = (cityName) => {
            this.focusOnCityInGraph(cityName);
        };
        
        // Check if we need to reinitialize the map (single city vs multi-city)
        const isMultiCity = Array.isArray(this.cityInfo);
        const wasMultiCity = this.mapViz.isMultiCity;
        
        if (isMultiCity !== wasMultiCity) {
            // Data structure changed, reinitialize map
            this.mapViz.initialize(this.cityInfo, this.data, this.dates);
        } else {
            // Same structure, just update data
            this.mapViz.updateData(this.cityInfo, this.data, this.dates);
        }
        
        // Initialize graph
        if (!this.graphViz) {
            this.graphViz = new GraphVisualization('graph-container');
        }
        // Handle both single city and multi-city for graph
        const cityName = Array.isArray(this.cityInfo) ? 
            `${this.cityInfo.length} Cities` : 
            this.cityInfo.city;
        this.graphViz.initialize(this.data, this.dates, cityName);
        
        // Initialize data export
        if (!this.dataExport) {
            this.dataExport = new DataExport();
        }
        
        // Update visualizations for first date
        this.updateVisualizations();
    }
    
    focusOnCityInGraph(cityName) {
        // Focus on the selected city in the graph
        if (this.graphViz) {
            this.graphViz.focusOnCity(cityName);
        }
        
        // Show a brief message
        this.showMessage(`Focused on ${cityName}`, 'info');
        
        // Auto-reset after 3 seconds
        setTimeout(() => {
            if (this.graphViz) {
                this.graphViz.showAllCities();
            }
        }, 3000);
    }
    
    updateVisualizations() {
        const currentDate = this.dates[this.currentDateIndex];
        
        // Update date display
        document.getElementById('current-date-display').textContent = currentDate;
        
        // Update map
        if (this.mapViz) {
            this.mapViz.updateDate(currentDate, this.currentDateIndex);
        }
        
        // Update graph
        if (this.graphViz) {
            this.graphViz.updateTimeline(currentDate);
        }
    }
    
    togglePlay() {
        this.isPlaying = !this.isPlaying;
        
        const btn = document.getElementById('play-pause-btn');
        const icon = document.getElementById('play-icon');
        
        if (this.isPlaying) {
            icon.textContent = '⏸️';
            btn.innerHTML = `<span id="play-icon">⏸️</span> Pause`;
            this.startAnimation();
        } else {
            icon.textContent = '▶️';
            btn.innerHTML = `<span id="play-icon">▶️</span> Play`;
            this.stopAnimation();
        }
    }
    
    startAnimation() {
        const baseInterval = 1000; // 1 second per frame at 1x speed
        const interval = baseInterval / this.playSpeed;
        
        this.playInterval = setInterval(() => {
            this.currentDateIndex++;
            
            if (this.currentDateIndex >= this.dates.length) {
                this.currentDateIndex = 0;
            }
            
            // Update slider
            document.getElementById('timeline-slider').value = this.currentDateIndex;
            
            this.updateVisualizations();
        }, interval);
    }
    
    stopAnimation() {
        if (this.playInterval) {
            clearInterval(this.playInterval);
            this.playInterval = null;
        }
    }
    
    handleSliderChange(value) {
        this.currentDateIndex = parseInt(value);
        this.updateVisualizations();
    }
    
    changeSpeed(delta) {
        this.playSpeed = Math.max(0.5, Math.min(4.0, this.playSpeed + delta));
        document.getElementById('speed-display').textContent = `${this.playSpeed}x`;
        
        // Restart animation if playing
        if (this.isPlaying) {
            this.stopAnimation();
            this.startAnimation();
        }
    }
    
    exportData(format) {
        if (!this.data || !this.dataExport) {
            this.showError('No data to export');
            return;
        }
        
        const cityName = Array.isArray(this.cityInfo) ? 
            `${this.cityInfo.length}cities` : 
            this.cityInfo.city;
        const filename = `viirs_${cityName}_${this.data[0].date}_${this.data[this.data.length - 1].date}`;
        
        try {
            switch (format) {
                case 'excel':
                    this.dataExport.exportToExcel(this.data, this.cityInfo, this.metadata, filename);
                    break;
                case 'csv':
                    this.dataExport.exportToCSV(this.data, filename);
                    break;
                case 'json':
                    this.dataExport.exportToJSON({
                        city_info: this.cityInfo,
                        data: this.data,
                        metadata: this.metadata
                    }, filename);
                    break;
            }
        } catch (error) {
            this.showError(`Export failed: ${error.message}`);
        }
    }
    
    showLoading(message) {
        document.getElementById('loading-message').textContent = message;
        document.getElementById('loading-indicator').style.display = 'block';
        document.getElementById('analyze-btn').disabled = true;
    }
    
    hideLoading() {
        document.getElementById('loading-indicator').style.display = 'none';
        document.getElementById('analyze-btn').disabled = false;
    }
    
    showError(message) {
        document.getElementById('error-message').textContent = message;
        document.getElementById('error-display').style.display = 'flex';
    }
    
    showMessage(message, type = 'info') {
        // Create a temporary message element
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${type}`;
        messageDiv.textContent = message;
        messageDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'info' ? '#e85d00' : '#d32f2f'};
            color: white;
            padding: 12px 20px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 500;
            z-index: 1000;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(messageDiv);
        
        // Auto-hide after 2 seconds
        setTimeout(() => {
            messageDiv.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                if (messageDiv.parentNode) {
                    messageDiv.parentNode.removeChild(messageDiv);
                }
            }, 300);
        }, 2000);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.viirsApp = new VIIRSApp();
});

