/**
 * Map Visualization with Leaflet.js
 * 
 * Handles interactive map display with VIIRS data visualization.
 */

export class MapVisualization {
    constructor(containerId) {
        this.containerId = containerId;
        this.map = null;
        this.markers = {};
        this.currentLayer = null;
        this.isMultiCity = false;
    }
    
    initialize(cityInfo, data, dates) {
        this.cityInfo = cityInfo;
        this.data = data;
        this.dates = dates;
        this.isMultiCity = Array.isArray(cityInfo);
        
        // Group data by date for quick lookup
        this.dataByDate = {};
        data.forEach(point => {
            if (!this.dataByDate[point.date]) {
                this.dataByDate[point.date] = [];
            }
            this.dataByDate[point.date].push(point);
        });
        
        // Initialize map
        this.createMap();
        this.setupMapControls();
    }
    
    updateData(cityInfo, data, dates) {
        // Update data without reinitializing the map
        this.cityInfo = cityInfo;
        this.data = data;
        this.dates = dates;
        this.isMultiCity = Array.isArray(cityInfo);
        
        // Group data by date for quick lookup
        this.dataByDate = {};
        data.forEach(point => {
            if (!this.dataByDate[point.date]) {
                this.dataByDate[point.date] = [];
            }
            this.dataByDate[point.date].push(point);
        });
        
        // Update visualizations for first date
        this.updateDate(this.dates[0], 0);
    }
    
    createMap() {
        // Check if map already exists
        if (this.map) {
            console.log("Map container is already initialized.");
            return;
        }
        
        // Create map centered on first city or center of all cities
        let centerLat, centerLon, zoom;
        
        if (Array.isArray(this.cityInfo)) {
            // Multi-city: center on average of all cities
            centerLat = this.cityInfo.reduce((sum, city) => sum + city.lat, 0) / this.cityInfo.length;
            centerLon = this.cityInfo.reduce((sum, city) => sum + city.lon, 0) / this.cityInfo.length;
            zoom = 6; // Wider view for multiple cities
        } else {
            // Single city
            centerLat = this.cityInfo.lat;
            centerLon = this.cityInfo.lon;
            zoom = 10;
        }
        
        this.map = L.map(this.containerId).setView([centerLat, centerLon], zoom);
        
        // Add default tile layer (dark mode)
        this.addTileLayer('dark');
        
        // Add circle for analysis radius
        this.addRadiusCircle();
    }
    
    addTileLayer(style) {
        // Remove current layer if exists
        if (this.currentLayer) {
            this.map.removeLayer(this.currentLayer);
        }
        
        let tileUrl, options;
        
        switch (style) {
            case 'osm':
                tileUrl = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
                options = {
                    attribution: '© OpenStreetMap contributors'
                };
                break;
            
            case 'dark':
                tileUrl = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
                options = {
                    attribution: '© OpenStreetMap contributors © CARTO'
                };
                break;
            
            case 'satellite':
                tileUrl = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
                options = {
                    attribution: 'Esri, DigitalGlobe, GeoEye'
                };
                break;
            
            default:
                tileUrl = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
                options = {
                    attribution: '© OpenStreetMap contributors © CARTO'
                };
        }
        
        this.currentLayer = L.tileLayer(tileUrl, options);
        this.currentLayer.addTo(this.map);
    }
    
    addRadiusCircle() {
        // Add semi-transparent circles showing analysis radius for each city
        if (Array.isArray(this.cityInfo)) {
            // Multi-city: add circles for each city
            this.cityInfo.forEach(city => {
                const circle = L.circle(
                    [city.lat, city.lon],
                    {
                        radius: city.radius_km * 1000, // convert to meters
                        color: '#1e88e5',
                        fillColor: '#1e88e5',
                        fillOpacity: 0.1,
                        weight: 2,
                        dashArray: '5, 10'
                    }
                );
                circle.addTo(this.map);
            });
        } else {
            // Single city
            const circle = L.circle(
                [this.cityInfo.lat, this.cityInfo.lon],
                {
                    radius: this.cityInfo.radius_km * 1000, // convert to meters
                    color: '#1e88e5',
                    fillColor: '#1e88e5',
                    fillOpacity: 0.1,
                    weight: 2,
                    dashArray: '5, 10'
                }
            );
            circle.addTo(this.map);
        }
        
        // Add city markers for each city
        if (Array.isArray(this.cityInfo)) {
            // Multi-city: add markers for each city
            this.cityInfo.forEach(city => {
                const marker = L.circleMarker(
                    [city.lat, city.lon],
                    {
                        radius: 8,
                        color: '#ffffff',
                        fillColor: '#1e88e5',
                        fillOpacity: 1,
                        weight: 2
                    }
                );
                
                marker.bindPopup(`
                    <strong>${city.city}</strong><br>
                    ${city.country}<br>
                    Lat: ${city.lat.toFixed(4)}, Lon: ${city.lon.toFixed(4)}
                `);
                
                marker.addTo(this.map);
            });
        } else {
            // Single city
            const marker = L.circleMarker(
                [this.cityInfo.lat, this.cityInfo.lon],
                {
                    radius: 8,
                    color: '#ffffff',
                    fillColor: '#1e88e5',
                    fillOpacity: 1,
                    weight: 2
                }
            );
            
            marker.bindPopup(`
                <strong>${this.cityInfo.city}</strong><br>
                ${this.cityInfo.country}<br>
                Lat: ${this.cityInfo.lat.toFixed(4)}, Lon: ${this.cityInfo.lon.toFixed(4)}
            `);
            
            marker.addTo(this.map);
        }
    }
    
    setupMapControls() {
        // Map style selector
        const styleSelect = document.getElementById('map-style');
        styleSelect.addEventListener('change', (e) => {
            this.addTileLayer(e.target.value);
        });
    }
    
    updateDate(date, dateIndex) {
        // Remove existing markers
        Object.values(this.markers).forEach(marker => {
            this.map.removeLayer(marker);
        });
        this.markers = {};
        
        // Get data for this date
        const dateData = this.dataByDate[date];
        
        if (!dateData || dateData.length === 0) {
            return;
        }
        
        // Aggregate by city (like ukRus project)
        const cityData = this.aggregateDataByCity(dateData);
        
        // Render all cities simultaneously
        cityData.forEach(cityPoint => {
            const marker = this.createRadianceMarker(cityPoint);
            this.markers[cityPoint.city] = marker;
            marker.addTo(this.map);
        });
    }
    
    aggregateDataByCity(data) {
        // Group data by city and calculate average radiance (like ukRus)
        const cityGroups = {};
        
        data.forEach(point => {
            const cityKey = `${point.city}_${point.country}`;
            if (!cityGroups[cityKey]) {
                cityGroups[cityKey] = {
                    city: point.city,
                    country: point.country,
                    lat: point.latitude,
                    lon: point.longitude,
                    radiance: [],
                    radiance_corrected: []
                };
            }
            cityGroups[cityKey].radiance.push(point.radiance);
            cityGroups[cityKey].radiance_corrected.push(point.radiance_corrected);
        });
        
        // Calculate averages for each city
        const cityPoints = [];
        Object.values(cityGroups).forEach(city => {
            cityPoints.push({
                city: city.city,
                country: city.country,
                latitude: city.lat,
                longitude: city.lon,
                radiance: city.radiance.reduce((a, b) => a + b, 0) / city.radiance.length,
                radiance_corrected: city.radiance_corrected.reduce((a, b) => a + b, 0) / city.radiance_corrected.length
            });
        });
        
        return cityPoints;
    }
    
    createRadianceMarker(point) {
        // Calculate marker size based on radiance (static position, only radius changes)
        const radiance = point.radiance_corrected;
        const minSize = 8;   // Minimum circle size
        const maxSize = 40;  // Maximum circle size
        const normalizedSize = Math.min(maxSize, minSize + (radiance * 2));
        
        // Calculate color based on radiance (ukRus color scale: yellow -> orange -> red)
        const color = this.getRadianceColor(radiance);
        
        // Create single static circle (no movement, no CoG animations)
        const marker = L.circleMarker(
            [point.latitude, point.longitude],
            {
                radius: normalizedSize / 2,
                color: '#ffffff',
                fillColor: color,
                fillOpacity: 0.8,
                weight: 2,
                className: 'static-radiance-circle'
            }
        );
        
        // Add city label with percentage change (positioned to the right of circle)
        const percentageChange = point.percentage_change || 0;
        const percentageSign = percentageChange >= 0 ? '+' : '';
        const labelText = `${point.city} ${percentageSign}${percentageChange.toFixed(1)}%`;
        
        // Position label to the right of the circle with some offset
        const labelLat = point.latitude;
        const labelLon = point.longitude + 0.02; // Move to the right
        
        const cityLabel = L.marker([labelLat, labelLon], {
            icon: L.divIcon({
                className: 'city-label',
                html: `<div class="city-label-text">${labelText}</div>`,
                iconSize: [140, 20],
                iconAnchor: [0, 10]
            })
        });
        
        // Create layer group for circle + label (both stay in fixed positions)
        const markerGroup = L.layerGroup();
        markerGroup.addLayer(marker);
        markerGroup.addLayer(cityLabel);
        
        // Add click handler for map-to-graph interaction
        markerGroup.on('click', (e) => {
            this.onCityClick(point.city);
        });
        
        // Create enhanced popup content
        const percentageChangeColor = this.getPercentageChangeColor(percentageChange);
        
        markerGroup.bindPopup(`
            <div style="color: #333; min-width: 200px;">
                <div style="text-align: center; margin-bottom: 10px;">
                    <div style="font-size: 18px; font-weight: bold; color: ${color};">
                        ${point.city}
                    </div>
                    <div style="font-size: 12px; color: #666;">
                        ${point.country}
                    </div>
                </div>
                <div style="border-top: 1px solid #eee; padding-top: 8px;">
                    <strong>Date:</strong> ${point.date || 'Current'}<br>
                    <strong>Radiance:</strong> ${radiance.toFixed(3)} nW/cm²/sr<br>
                    <strong>Coordinates:</strong> ${point.latitude.toFixed(4)}, ${point.longitude.toFixed(4)}<br>
                    <strong>Change:</strong> <span style="color: ${percentageChangeColor}; font-weight: bold;">${percentageSign}${percentageChange.toFixed(1)}%</span>
                </div>
                <div style="margin-top: 8px; font-size: 11px; color: #888; text-align: center;">
                    Click to focus on graph
                </div>
            </div>
        `);
        
        return markerGroup;
    }
    
    onCityClick(cityName) {
        // Emit event to parent app for graph interaction
        if (this.onCitySelected) {
            this.onCitySelected(cityName);
        }
    }
    
    getRadianceColor(radiance) {
        // ukRus color scale: yellow (low) → orange → red (high)
        // Based on VIIRS radiance values
        
        if (radiance < 0.5) {
            return '#ffff00'; // yellow
        } else if (radiance < 2) {
            return '#ffcc00'; // yellow-orange
        } else if (radiance < 4) {
            return '#ff9900'; // orange
        } else if (radiance < 8) {
            return '#ff6600'; // red-orange
        } else {
            return '#ff0000'; // red
        }
    }
    
    getPercentageChangeColor(percentage) {
        if (percentage > 5) {
            return '#4caf50'; // green (increase)
        } else if (percentage < -5) {
            return '#f44336'; // red (decrease)
        } else {
            return '#ff9800'; // orange (stable)
        }
    }
}

