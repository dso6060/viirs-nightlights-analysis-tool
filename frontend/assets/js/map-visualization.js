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
        this.baseLayerGroup = null;
        this.isMultiCity = false;
        this.calibrating = false;
        this.currentCityData = [];
        this._viewportListenersBound = false;
        this._suppressViewportEvent = false;
        this.onVisibleCitiesChanged = null;
        this._lastValidByCity = {};
    }

    setCalibrating(isCalibrating) {
        this.calibrating = Boolean(isCalibrating);
        // Refresh labels if we already have a timeline position
        if (this.dates && this.dates.length > 0) {
            this.updateDate(this.dates[this.currentDateIndex || 0], this.currentDateIndex || 0);
        }
    }

  /**
   * Map label suffix for % change. Uses "…" until a real value is available.
   */
    cityDisplayName(obj) {
        if (!obj) return '';
        if (obj.display_name) {
            return String(obj.display_name).split(',')[0].trim();
        }
        return obj.city || '';
    }

    formatPercentageLabelSuffix(point) {
        if (point.data_missing) {
            return ' · —';
        }
        if (this.calibrating) {
            return ' …';
        }
        if (point.is_baseline_year) {
            return ' …';
        }
        if (point.percentage_change == null || point.percentage_change_ready === false) {
            return ' …';
        }
        const v = point.percentage_change;
        const sign = v > 0 ? '+' : '';
        return ` ${sign}${v.toFixed(1)}%`;
    }

    formatPercentagePopupText(point) {
        if (point.data_missing) {
            return '<span style="color:#888;">No observation (low cloud-free coverage)</span>';
        }
        if (this.calibrating) {
            return '<span style="color:#888;">Calibrating…</span>';
        }
        if (point.is_baseline_year) {
            return '<span style="color:#888;">Baseline year (no % change yet)</span>';
        }
        if (point.percentage_change == null || point.percentage_change_ready === false) {
            return '<span style="color:#888;">Calibrating…</span>';
        }
        const v = point.percentage_change;
        const sign = v > 0 ? '+' : '';
        const color = this.getPercentageChangeColor(v);
        return `<span style="color: ${color}; font-weight: bold;">${sign}${v.toFixed(1)}%</span>`;
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
        this.fitMapToSelection();
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

        // If the map hasn't been created yet (first run single-city),
        // create it now before attempting to render markers/layers.
        if (!this.map) {
            this.createMap();
            this.setupMapControls();
        }
        
        // Update visualizations for first date
        this.updateDate(this.dates[0], 0);
        this.fitMapToSelection();
    }

    destroyMap() {
        if (this.map) {
            this.map.remove();
            this.map = null;
        }
        this.markers = {};
        this.baseLayerGroup = null;
        this._viewportListenersBound = false;
        this.currentCityData = [];
    }

    getCityInfoList() {
        if (Array.isArray(this.cityInfo)) {
            return this.cityInfo;
        }
        if (this.cityInfo) {
            return [this.cityInfo];
        }
        return [];
    }

    getSelectionLatLngs() {
        const latlngs = [];
        const seen = new Set();

        const add = (lat, lon) => {
            if (lat == null || lon == null) {
                return;
            }
            const key = `${Number(lat).toFixed(4)}_${Number(lon).toFixed(4)}`;
            if (seen.has(key)) {
                return;
            }
            seen.add(key);
            latlngs.push([lat, lon]);
        };

        this.getCityInfoList().forEach((city) => add(city.lat, city.lon));

        (this.data || []).forEach((point) => {
            add(point.latitude ?? point.lat, point.longitude ?? point.lon);
        });

        return latlngs;
    }

    getBoundsForSelection() {
        const latlngs = this.getSelectionLatLngs();
        if (latlngs.length === 0) {
            return null;
        }
        if (latlngs.length === 1) {
            const city = this.getCityInfoList()[0];
            const radiusM = ((city?.radius_km) || 10) * 1000;
            return L.latLng(latlngs[0]).toBounds(Math.max(radiusM * 2, 20000));
        }
        return L.latLngBounds(latlngs);
    }

    fitMapToSelection() {
        if (!this.map) {
            return;
        }

        const bounds = this.getBoundsForSelection();
        if (!bounds) {
            return;
        }

        this._suppressViewportEvent = true;

        if (this.getSelectionLatLngs().length === 1) {
            this.map.fitBounds(bounds, { padding: [48, 48], maxZoom: 12 });
        } else {
            this.map.fitBounds(bounds, { padding: [56, 56], maxZoom: 14 });
        }

        window.setTimeout(() => {
            this._suppressViewportEvent = false;
            this.refreshVisibleMarkers();
        }, 280);
    }

    setupMapViewportListeners() {
        if (!this.map || this._viewportListenersBound) {
            return;
        }

        const onViewportChange = () => {
            if (this._suppressViewportEvent) {
                return;
            }
            this.refreshVisibleMarkers();
        };

        this.map.on('moveend', onViewportChange);
        this.map.on('zoomend', onViewportChange);
        this._viewportListenersBound = true;
    }

    getVisibleCityPoints() {
        if (!this.map || !this.currentCityData?.length) {
            return [];
        }

        const bounds = this.map.getBounds();
        return this.currentCityData.filter((point) =>
            bounds.contains([point.latitude, point.longitude])
        );
    }

    getVisibleCityNames() {
        return this.getVisibleCityPoints().map((point) => point.city);
    }

    notifyVisibleCitiesChanged() {
        if (typeof this.onVisibleCitiesChanged === 'function') {
            this.onVisibleCitiesChanged(this.getVisibleCityNames());
        }
    }
    
    createMap() {
        // Check if map already exists
        if (this.map) {
            console.log("Map container is already initialized.");
            return;
        }
        
        const latlngs = this.getSelectionLatLngs();
        const center = latlngs.length
            ? [
                latlngs.reduce((sum, ll) => sum + ll[0], 0) / latlngs.length,
                latlngs.reduce((sum, ll) => sum + ll[1], 0) / latlngs.length,
            ]
            : [20, 0];
        
        this.map = L.map(this.containerId).setView(center, latlngs.length > 1 ? 5 : 10);
        
        // Add default tile layer (dark mode)
        this.addTileLayer('dark');
        this.setupMapViewportListeners();
        this.renderBaseLayers();
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
    
    renderBaseLayers(visiblePoints = null) {
        if (!this.map) {
            return;
        }

        if (this.baseLayerGroup) {
            this.map.removeLayer(this.baseLayerGroup);
        }

        this.baseLayerGroup = L.layerGroup().addTo(this.map);

        const points = Array.isArray(visiblePoints) ? visiblePoints : this.getVisibleCityPoints();
        let cities;

        if (points.length > 0) {
            const visibleKeys = new Set(points.map((p) => `${p.city}_${p.country}`));
            cities = this.getCityInfoList().filter((city) =>
                visibleKeys.has(`${city.city}_${city.country}`)
            );
        } else if (this.currentCityData?.length) {
            cities = [];
        } else {
            cities = this.getCityInfoList();
        }

        cities.forEach((city) => {
            const radiusKm = city.radius_km || 10;

            L.circle([city.lat, city.lon], {
                radius: radiusKm * 1000,
                color: '#1e88e5',
                fillColor: '#1e88e5',
                fillOpacity: 0.1,
                weight: 2,
                dashArray: '5, 10',
            }).addTo(this.baseLayerGroup);

            const marker = L.circleMarker([city.lat, city.lon], {
                radius: 8,
                color: '#ffffff',
                fillColor: '#1e88e5',
                fillOpacity: 1,
                weight: 2,
            });

            marker.bindPopup(`
                <strong>${this.cityDisplayName(city)}</strong><br>
                ${city.country}<br>
                Lat: ${city.lat.toFixed(4)}, Lon: ${city.lon.toFixed(4)}
            `);

            marker.addTo(this.baseLayerGroup);
        });
    }

    refreshVisibleMarkers() {
        if (!this.map) {
            return;
        }

        Object.values(this.markers).forEach((marker) => {
            this.map.removeLayer(marker);
        });
        this.markers = {};

        const visiblePoints = this.getVisibleCityPoints();
        this.renderBaseLayers(visiblePoints);

        visiblePoints.forEach((cityPoint) => {
            const markerKey = `${cityPoint.city}_${cityPoint.country}`;
            const marker = this.createRadianceMarker(cityPoint);
            this.markers[markerKey] = marker;
            marker.addTo(this.map);
        });

        this.notifyVisibleCitiesChanged();
    }
    
    setupMapControls() {
        // Map style selector
        const styleSelect = document.getElementById('map-style');
        styleSelect.addEventListener('change', (e) => {
            this.addTileLayer(e.target.value);
        });
    }
    
    updateDate(date, dateIndex) {
        this.currentDateIndex = dateIndex;
        // Defensive: ensure Leaflet map exists before touching layers/markers.
        if (!this.map) {
            this.createMap();
            this.setupMapControls();
            if (!this.map) {
                return;
            }
        }

        const dateData = this.dataByDate[date] || [];

        if (dateData.length === 0) {
            this.currentCityData = this.buildMissingMonthFromCityInfo(date);
        } else {
            this.currentCityData = this.aggregateDataByCity(dateData);
        }

        this.currentCityData.forEach((point) => {
            const key = `${point.city}_${point.country}`;
            if (!point.data_missing && point.radiance_corrected != null) {
                this._lastValidByCity[key] = point.radiance_corrected;
            }
        });

        this.refreshVisibleMarkers();
    }

    buildMissingMonthFromCityInfo(date) {
        return this.getCityInfoList().map((city) => {
            const key = `${city.city}_${city.country}`;
            return {
                city: city.city,
                country: city.country,
                latitude: city.lat,
                longitude: city.lon,
                date,
                data_missing: true,
                radiance_corrected: null,
                last_radiance_corrected: this._lastValidByCity[key] ?? null,
                percentage_change: null,
                percentage_change_ready: false,
                is_baseline_year: false,
            };
        });
    }
    
    aggregateDataByCity(data) {
        const cityGroups = {};
        
        data.forEach((point) => {
            const cityKey = `${point.city}_${point.country}`;
            if (!cityGroups[cityKey]) {
                cityGroups[cityKey] = {
                    city: point.city,
                    country: point.country,
                    lat: point.latitude,
                    lon: point.longitude,
                    radiance: [],
                    radiance_corrected: [],
                    percentage_change: [],
                    is_baseline_year: false,
                    date: point.date,
                    has_valid: false,
                };
            }

            if (point.latitude != null) {
                cityGroups[cityKey].lat = point.latitude;
            }
            if (point.longitude != null) {
                cityGroups[cityKey].lon = point.longitude;
            }

            if (point.radiance_corrected != null) {
                cityGroups[cityKey].has_valid = true;
                cityGroups[cityKey].radiance.push(point.radiance);
                cityGroups[cityKey].radiance_corrected.push(point.radiance_corrected);
            }

            if (point.is_baseline_year) {
                cityGroups[cityKey].is_baseline_year = true;
            }
            if (typeof point.percentage_change === 'number' && point.percentage_change_ready !== false) {
                cityGroups[cityKey].percentage_change.push(point.percentage_change);
            }
        });
        
        const cityPoints = [];
        Object.values(cityGroups).forEach((city) => {
            const key = `${city.city}_${city.country}`;
            const hasPct = city.percentage_change.length > 0;
            const avgPct = hasPct
                ? (city.percentage_change.reduce((a, b) => a + b, 0) / city.percentage_change.length)
                : null;

            const dataMissing = !city.has_valid;

            cityPoints.push({
                city: city.city,
                country: city.country,
                latitude: city.lat,
                longitude: city.lon,
                date: city.date,
                data_missing: dataMissing,
                radiance: dataMissing
                    ? null
                    : city.radiance.reduce((a, b) => a + b, 0) / city.radiance.length,
                radiance_corrected: dataMissing
                    ? null
                    : city.radiance_corrected.reduce((a, b) => a + b, 0) / city.radiance_corrected.length,
                last_radiance_corrected: dataMissing ? (this._lastValidByCity[key] ?? null) : null,
                percentage_change: avgPct,
                percentage_change_ready: hasPct && !city.is_baseline_year,
                is_baseline_year: city.is_baseline_year,
            });
        });
        
        return cityPoints;
    }
    
    createRadianceMarker(point) {
        const minSize = 8;
        const maxSize = 40;
        const refRadiance =
            point.data_missing
                ? point.last_radiance_corrected
                : point.radiance_corrected;
        const normalizedSize =
            refRadiance != null
                ? Math.min(maxSize, minSize + refRadiance * 2) / 2
                : 7;

        let marker;
        let color = '#9e9e9e';
        let labelText = `${this.cityDisplayName(point)}${this.formatPercentageLabelSuffix(point)}`;
        let labelClass = 'city-label-text';

        if (point.data_missing) {
            marker = L.circleMarker([point.latitude, point.longitude], {
                radius: normalizedSize,
                color: '#bdbdbd',
                fillColor: '#757575',
                fillOpacity: 0.2,
                weight: 2,
                dashArray: '4, 3',
                className: 'static-radiance-circle missing-month',
            });
            labelClass = 'city-label-text city-label-missing';
        } else {
            color = this.getRadianceColor(point.radiance_corrected);
            marker = L.circleMarker([point.latitude, point.longitude], {
                radius: normalizedSize,
                color: '#ffffff',
                fillColor: color,
                fillOpacity: 0.8,
                weight: 2,
                className: 'static-radiance-circle',
            });
        }

        const { latDelta, lonDelta, anchorX, anchorY } = this.getLabelOffset(point.city, point.country);
        const labelLat = point.latitude + latDelta;
        const labelLon = point.longitude + lonDelta;
        
        const cityLabel = L.marker([labelLat, labelLon], {
            icon: L.divIcon({
                className: 'city-label',
                html: `<div class="${labelClass}">${labelText}</div>`,
                iconSize: [140, 20],
                iconAnchor: [anchorX, anchorY],
            }),
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
        markerGroup.bindPopup(`
            <div style="color: #333; min-width: 200px;">
                <div style="text-align: center; margin-bottom: 10px;">
                    <div style="font-size: 18px; font-weight: bold; color: ${color};">
                        ${this.cityDisplayName(point)}
                    </div>
                    <div style="font-size: 12px; color: #666;">
                        ${point.country}
                    </div>
                </div>
                <div style="border-top: 1px solid #eee; padding-top: 8px;">
                    <strong>Date:</strong> ${point.date || 'Current'}<br>
                    <strong>Radiance:</strong> ${
                        point.data_missing
                            ? '<span style="color:#888;">No observation (low cloud coverage)</span>'
                            : `${point.radiance_corrected.toFixed(3)} nW/cm²/sr`
                    }<br>
                    <strong>Coordinates:</strong> ${point.latitude.toFixed(4)}, ${point.longitude.toFixed(4)}<br>
                    <strong>Change:</strong> ${this.formatPercentagePopupText(point)}
                </div>
                <div style="margin-top: 8px; font-size: 11px; color: #888; text-align: center;">
                    Click to focus on graph
                </div>
            </div>
        `);
        
        return markerGroup;
    }

    getLabelOffset(city, country) {
        // Deterministic placement around the marker to reduce label overlap.
        // Uses a simple hash to pick one of several offset "slots".
        const key = `${city || ''}_${country || ''}`;
        let h = 0;
        for (let i = 0; i < key.length; i++) {
            h = (h * 31 + key.charCodeAt(i)) >>> 0;
        }
        const slot = h % 8;

        // Offsets in degrees; tuned for India-scale view at zoom ~6–10.
        // (Lon degrees vary by latitude; good enough for UI labels.)
        const offsets = [
            { latDelta: 0.00, lonDelta: 0.030, anchorX: 0, anchorY: 10 },   // E
            { latDelta: 0.012, lonDelta: 0.026, anchorX: 0, anchorY: 10 },  // ENE
            { latDelta: -0.012, lonDelta: 0.026, anchorX: 0, anchorY: 10 }, // ESE
            { latDelta: 0.018, lonDelta: 0.016, anchorX: 0, anchorY: 10 },  // NE
            { latDelta: -0.018, lonDelta: 0.016, anchorX: 0, anchorY: 10 }, // SE
            { latDelta: 0.018, lonDelta: -0.016, anchorX: 140, anchorY: 10 }, // NW (anchor right)
            { latDelta: -0.018, lonDelta: -0.016, anchorX: 140, anchorY: 10 }, // SW
            { latDelta: 0.00, lonDelta: -0.030, anchorX: 140, anchorY: 10 },   // W
        ];

        return offsets[slot];
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

