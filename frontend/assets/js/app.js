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
        this.API_BASE_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') ?
            'http://localhost:8000' : '/api';
        this.data = null;
        this.cityInfo = null;
        this.currentDateIndex = 0;
        this.isPlaying = false;
        this.playSpeed = 1.0;
        this.playInterval = null;
        this.selectedCities = []; // [{ city, country, label }]
        this.selectedCity = null; // Currently highlighted autocomplete place
        this.searchTimeout = null; // For debouncing search
        this.hotlistPlaces = []; // ~800 preloaded places for instant suggest
        this.placeClusters = []; // e.g. Ports of China / India
        this.activeCluster = null; // { id, label } when a cluster is loaded
        this.maxIndividualCities = 5;
        this.maxPlacesPerRequest = 12;
        this.autocompleteResults = [];
        this.autocompleteHighlight = -1;
        
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
        await this.loadHotlistDictionary();
        await this.loadPlaceClusters();
        
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
        searchInput.addEventListener('keydown', (e) => {
            this.handleSearchKeydown(e);
        });
        
        // Add city button
        document.getElementById('add-city-btn').addEventListener('click', () => {
            this.addSelectedCity();
        });
        
        // Quick city buttons
        document.querySelectorAll('.quick-city-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const cityName = e.target.dataset.city;
                const country = e.target.dataset.country || null;
                this.addPlaceToSelection({ city: cityName, country, label: country ? `${cityName}, ${country}` : cityName });
            });
        });

        document.querySelectorAll('.quick-cluster-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const clusterId = e.target.dataset.cluster;
                if (clusterId) {
                    this.addClusterToSelection(clusterId);
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
    
    async loadHotlistDictionary() {
        try {
            const response = await fetch(`${this.API_BASE_URL}/hotlist`);
            if (!response.ok) {
                console.warn('Hotlist dictionary unavailable:', response.status);
                return;
            }
            const data = await response.json();
            this.hotlistPlaces = (data.places || []).map((p) => ({
                city: p.city,
                country: p.country,
                admin1: p.admin1,
                display_name: p.display_name || `${p.city}, ${p.country}`,
                lat: p.lat,
                lon: p.lon,
                source: 'hotlist',
            }));
            console.log(`Loaded hotlist dictionary: ${this.hotlistPlaces.length} places`);
        } catch (error) {
            console.warn('Failed to load hotlist dictionary:', error);
        }
    }

    async loadPlaceClusters() {
        try {
            const response = await fetch(`${this.API_BASE_URL}/clusters`);
            if (!response.ok) {
                console.warn('Place clusters unavailable:', response.status);
                this.showPresetSectionsError(
                    `Preset clusters unavailable (HTTP ${response.status}). Start backend: cd backend && python3 main.py`
                );
                return;
            }
            const data = await response.json();
            this.placeClusters = data.clusters || [];
            if (data.max_individual_places) {
                this.maxIndividualCities = data.max_individual_places;
            }
            if (data.max_places_per_request) {
                this.maxPlacesPerRequest = data.max_places_per_request;
            }
            console.log(`Loaded ${this.placeClusters.length} place clusters`);
            this.renderPresetSections();
        } catch (error) {
            console.warn('Failed to load place clusters:', error);
            this.showPresetSectionsError(
                'Could not load preset clusters. Is the API running on http://localhost:8000 ? (Use http://localhost:8090 if CORS blocks 127.0.0.1.)'
            );
        }
    }

    showPresetSectionsError(message) {
        const root = document.getElementById('preset-sections');
        if (!root) return;
        root.innerHTML = `<p class="preset-sections-error">${this.escapeHtml(message)}</p>`;
    }

    clustersBySection(sectionId) {
        return this.placeClusters.filter((c) => c.section === sectionId);
    }

    generalPresetClusters() {
        return this.placeClusters.filter((c) => !c.section);
    }

    renderPresetSections() {
        const root = document.getElementById('preset-sections');
        if (!root) return;
        root.innerHTML = '';

        const sections = [
            {
                id: 'user-request',
                title: '1. User-request — Gulf / Hormuz ports',
                subtitle: 'Hand-curated terminal coordinates & radii (see panel below when selected).',
            },
            {
                id: 'gdelt-missile',
                title: '2. GDELT missile / artillery impacts',
                subtitle: 'Automated from GDELT — not human-curated.',
            },
            {
                id: 'gdelt-drone',
                title: '3. GDELT air / drone impacts',
                subtitle: 'Automated from GDELT — not human-curated.',
            },
        ];

        for (const sec of sections) {
            const clusters = this.clustersBySection(sec.id);
            if (!clusters.length) continue;

            const block = document.createElement('div');
            block.className = 'preset-section-block';
            block.dataset.section = sec.id;

            const h = document.createElement('div');
            h.className = 'preset-section-header';
            h.innerHTML = `<strong>${sec.title}</strong><span class="preset-section-sub">${sec.subtitle}</span>`;
            block.appendChild(h);

            const row = document.createElement('div');
            row.className = 'quick-add-cities quick-add-clusters preset-cluster-row';

            for (const cluster of clusters) {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'quick-cluster-btn';
                btn.dataset.cluster = cluster.id;
                const count = cluster.place_count || (cluster.places || []).length;
                btn.textContent = cluster.label;
                btn.title = cluster.description || cluster.label;
                if (count === 0) {
                    btn.disabled = true;
                    btn.title = 'No sites loaded — run scripts/build_conflict_strike_sites.py with GDELT_CLOUD_API_KEY';
                }
                row.appendChild(btn);

                const pills = (cluster.countries_covered || []).filter(Boolean);
                if (pills.length) {
                    const pillWrap = document.createElement('span');
                    pillWrap.className = 'country-pills';
                    pillWrap.textContent = pills.join(' · ');
                    row.appendChild(pillWrap);
                }
            }
            block.appendChild(row);
            root.appendChild(block);
        }

        root.querySelectorAll('.quick-cluster-btn').forEach((btn) => {
            btn.addEventListener('click', (e) => {
                const clusterId = e.target.dataset.cluster;
                if (clusterId) this.addClusterToSelection(clusterId);
            });
        });
    }

    applyClusterDefaultDates(cluster) {
        const startYear = document.getElementById('start-year');
        const startMonth = document.getElementById('start-month');
        const endYear = document.getElementById('end-year');
        const endMonth = document.getElementById('end-month');

        const isGdelt = cluster.section === 'gdelt-missile' || cluster.section === 'gdelt-drone';
        if (isGdelt && cluster.study_sites?.length) {
            let earliest = null;
            for (const site of cluster.study_sites) {
                if (!site.event_date) continue;
                const d = new Date(`${site.event_date}T00:00:00`);
                if (!Number.isNaN(d.getTime()) && (!earliest || d < earliest)) {
                    earliest = d;
                }
            }
            if (earliest) {
                const start = new Date(earliest);
                start.setMonth(start.getMonth() - 6);
                const y = String(start.getFullYear());
                const m = String(start.getMonth() + 1).padStart(2, '0');
                if (startYear?.querySelector(`option[value="${y}"]`)) startYear.value = y;
                if (startMonth) startMonth.value = m;
            }
            if (this.latestYear && endYear && endMonth) {
                const ey = String(this.latestYear);
                const em = String(this.latestMonth).padStart(2, '0');
                if (endYear.querySelector(`option[value="${ey}"]`)) endYear.value = ey;
                endMonth.value = em;
            }
            return;
        }

        if (!cluster?.default_start) return;
        const [y, m] = String(cluster.default_start).split('-');
        if (y && startYear?.querySelector(`option[value="${y}"]`)) {
            startYear.value = y;
        }
        if (m && startMonth) {
            startMonth.value = m.padStart(2, '0');
        }
        if (this.latestYear && endYear && endMonth) {
            const ey = String(this.latestYear);
            const em = String(this.latestMonth).padStart(2, '0');
            if (endYear.querySelector(`option[value="${ey}"]`)) endYear.value = ey;
            endMonth.value = em;
        }
    }

    updateClusterInfoPanels(cluster) {
        const panel = document.getElementById('cluster-radius-panel');
        const banner = document.getElementById('gdelt-disclosure-banner');
        if (!cluster) {
            if (panel) panel.hidden = true;
            if (banner) banner.hidden = true;
            return;
        }

        const isGdelt = cluster.section === 'gdelt-missile' || cluster.section === 'gdelt-drone';
        if (banner) {
            if (isGdelt) {
                banner.hidden = false;
                banner.textContent =
                    'Strike locations are automatically pulled from GDELT news events — not human-curated or battlefield-verified. Do not cite as confirmed impact coordinates.';
            } else {
                banner.hidden = true;
                banner.textContent = '';
            }
        }

        if (panel) {
            panel.hidden = false;
            const title = document.getElementById('cluster-radius-title');
            const methodology = document.getElementById('cluster-radius-methodology');
            const wrap = document.getElementById('cluster-radius-table-wrap');
            if (title) title.textContent = `How radius (km) was set — ${cluster.label}`;
            if (methodology) {
                methodology.textContent =
                    cluster.radius_methodology ||
                    'Each place uses a fixed radius_km around a center point. VIIRS monthly pixels (~750 m) are averaged in a square box ±radius km (map shows a circle for orientation).';
            }
            if (wrap) {
                const sites = cluster.study_sites || [];
                if (!sites.length) {
                    wrap.innerHTML = '<p class="cluster-radius-empty">No per-site radius detail available for this cluster.</p>';
                } else {
                    const rows = sites
                        .map(
                            (s) => `<tr>
              <td>${this.escapeHtml(s.label || '')}</td>
              <td>${this.escapeHtml(s.country || '')}</td>
              <td><strong>${s.radius_km != null ? s.radius_km : '—'}</strong></td>
              <td class="radius-rationale-cell">${this.escapeHtml(s.radius_rationale || '—')}</td>
            </tr>`
                        )
                        .join('');
                    wrap.innerHTML = `<table class="cluster-radius-table">
            <thead><tr><th>Place</th><th>Country</th><th>Radius (km)</th><th>How it was set</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>`;
                }
            }
        }
    }

    escapeHtml(text) {
        const d = document.createElement('div');
        d.textContent = text;
        return d.innerHTML;
    }

    searchClusters(query, limit = 3) {
        const q = query.trim().toLowerCase();
        if (q.length < 2 || !this.placeClusters.length) {
            return [];
        }

        const scored = [];
        for (const cluster of this.placeClusters) {
            const label = (cluster.label || '').toLowerCase();
            const desc = (cluster.description || '').toLowerCase();
            const aliases = (cluster.aliases || []).map((a) => a.toLowerCase());

            let score = 0;
            if (label.startsWith(q) || label.includes(q)) {
                score = 25;
            } else if (aliases.some((a) => a.includes(q) || q.includes(a))) {
                score = 20;
            } else if (desc.includes(q)) {
                score = 6;
            } else {
                continue;
            }

            scored.push({ cluster, score });
        }

        scored.sort((a, b) => b.score - a.score);
        return scored.slice(0, limit).map((s) => ({
            type: 'cluster',
            cluster_id: s.cluster.id,
            label: s.cluster.label,
            description: s.cluster.description,
            place_count: s.cluster.place_count,
            display_name: `${s.cluster.label} (${s.cluster.place_count} places)`,
            source: 'cluster',
        }));
    }

    getClusterById(clusterId) {
        return this.placeClusters.find((c) => c.id === clusterId);
    }

    countIndividualPlaces() {
        return this.selectedCities.filter((p) => !p.clusterId).length;
    }

    searchHotlist(query, limit = 8) {
        const q = query.trim().toLowerCase();
        if (q.length < 2 || !this.hotlistPlaces.length) {
            return [];
        }

        const scored = [];
        for (const place of this.hotlistPlaces) {
            const name = (place.city || '').toLowerCase();
            const country = (place.country || '').toLowerCase();
            const display = (place.display_name || '').toLowerCase();

            let score = 0;
            if (name.startsWith(q)) {
                score = 20;
            } else if (name.split(/\s+/)[0].startsWith(q)) {
                score = 15;
            } else if (name.includes(q)) {
                score = 8;
            } else if (display.includes(q)) {
                score = 4;
            } else {
                continue;
            }

            scored.push({ place, score });
        }

        scored.sort((a, b) => {
            if (b.score !== a.score) return b.score - a.score;
            return a.place.display_name.localeCompare(b.place.display_name);
        });

        return scored.slice(0, limit).map((s) => s.place);
    }

    async handleSearchInput(query) {
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }

        if (query.length < 2) {
            this.hideAutocomplete();
            return;
        }

        const clusterHits = this.searchClusters(query, 2);
        const localHits = this.searchHotlist(query, 8);
        const combined = [...clusterHits, ...localHits];
        if (combined.length > 0) {
            this.showAutocomplete(combined);
            return;
        }

        this.searchTimeout = setTimeout(async () => {
            try {
                if (!this.hotlistPlaces.length) {
                    const suggestRes = await fetch(
                        `${this.API_BASE_URL}/suggest?q=${encodeURIComponent(query)}&limit=8`
                    );
                    if (suggestRes.ok) {
                        const suggestData = await suggestRes.json();
                        if (suggestData.results?.length) {
                            this.showAutocomplete(suggestData.results);
                            return;
                        }
                    }
                }

                const response = await fetch(
                    `${this.API_BASE_URL}/search?q=${encodeURIComponent(query)}&limit=8`
                );
                const data = await response.json();

                if (data.results && data.results.length > 0) {
                    this.showAutocomplete(data.results);
                } else {
                    this.hideAutocomplete();
                }
            } catch (error) {
                console.error('Search error:', error);
                this.hideAutocomplete();
            }
        }, 250);
    }

    handleSearchKeydown(e) {
        const dropdown = document.getElementById('autocomplete-dropdown');
        if (!dropdown.classList.contains('active') || !this.autocompleteResults.length) {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.addSelectedCity();
            }
            return;
        }

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            this.autocompleteHighlight = Math.min(
                this.autocompleteHighlight + 1,
                this.autocompleteResults.length - 1
            );
            this.renderAutocompleteHighlight();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this.autocompleteHighlight = Math.max(this.autocompleteHighlight - 1, 0);
            this.renderAutocompleteHighlight();
        } else if (e.key === 'Enter') {
            e.preventDefault();
            const pick = this.autocompleteResults[this.autocompleteHighlight] || this.autocompleteResults[0];
            if (pick) {
                if (pick.type === 'cluster') {
                    this.addClusterToSelection(pick.cluster_id);
                    document.getElementById('city-search').value = '';
                    this.hideAutocomplete();
                } else {
                    this.selectAutocompleteResult(pick);
                    this.addSelectedCity();
                }
            }
        } else if (e.key === 'Escape') {
            this.hideAutocomplete();
        }
    }

    selectAutocompleteResult(result) {
        if (result.type === 'cluster') {
            this.selectedCity = result;
            document.getElementById('city-search').value = result.label;
            document.getElementById('city-search').dataset.country = '';
            return;
        }
        this.selectedCity = result;
        document.getElementById('city-search').value = result.city;
        document.getElementById('city-search').dataset.country = result.country || '';
    }

    renderAutocompleteHighlight() {
        const dropdown = document.getElementById('autocomplete-dropdown');
        const items = dropdown.querySelectorAll('.autocomplete-item');
        items.forEach((el, idx) => {
            el.classList.toggle('active', idx === this.autocompleteHighlight);
        });
        if (items[this.autocompleteHighlight]) {
            this.selectedCity = this.autocompleteResults[this.autocompleteHighlight];
        }
    }

    showAutocomplete(results) {
        this.autocompleteResults = results;
        this.autocompleteHighlight = 0;

        const dropdown = document.getElementById('autocomplete-dropdown');
        dropdown.innerHTML = '';
        dropdown.classList.add('active');

        results.forEach((result, index) => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item' + (index === 0 ? ' active' : '');
            const isCluster = result.type === 'cluster';
            const label = result.display_name || `${result.city}, ${result.country}`;
            const tag = isCluster ? ' — cluster' : (result.source === 'hotlist' ? ' (cached)' : '');
            item.classList.toggle('autocomplete-item-cluster', isCluster);
            item.textContent = `${label}${tag}`;

            item.addEventListener('click', () => {
                if (isCluster) {
                    this.addClusterToSelection(result.cluster_id);
                    document.getElementById('city-search').value = '';
                    this.hideAutocomplete();
                } else {
                    this.selectAutocompleteResult(result);
                    this.hideAutocomplete();
                }
            });

            item.addEventListener('mouseenter', () => {
                this.autocompleteHighlight = index;
                this.renderAutocompleteHighlight();
            });

            dropdown.appendChild(item);
        });

        if (results.length > 0) {
            this.selectedCity = results[0];
        }
    }

    hideAutocomplete() {
        const dropdown = document.getElementById('autocomplete-dropdown');
        dropdown.classList.remove('active');
        this.autocompleteResults = [];
        this.autocompleteHighlight = -1;
    }

    placeKey(place) {
        return `${place.city}__${place.country || ''}`.toLowerCase();
    }

    isPlaceSelected(place) {
        const key = this.placeKey(place);
        return this.selectedCities.some((p) => this.placeKey(p) === key);
    }

    addClusterToSelection(clusterId) {
        const cluster = this.getClusterById(clusterId);
        if (!cluster) {
            this.showError('Unknown place cluster');
            return;
        }

        const placeList = cluster.places || [];
        if (placeList.length === 0) {
            this.showError(
                'This cluster has no sites yet. For GDELT clusters, run scripts/build_conflict_strike_sites.py with GDELT_CLOUD_API_KEY.'
            );
            return;
        }

        if (this.activeCluster && this.activeCluster.id !== clusterId) {
            this.showError('Remove the current cluster before adding another');
            return;
        }

        if (this.countIndividualPlaces() > 0) {
            this.showError('Clear individual cities first, or remove them before adding a cluster');
            return;
        }

        const members = (cluster.places || []).map((p) => ({
            city: p.city,
            country: p.country || null,
            label: p.display_name || `${p.city}, ${p.country}`,
            clusterId: cluster.id,
        }));

        if (members.length > this.maxPlacesPerRequest) {
            this.showError(`This cluster has too many places (max ${this.maxPlacesPerRequest})`);
            return;
        }

        this.selectedCities = members;
        this.activeCluster = {
            id: cluster.id,
            label: cluster.label,
            section: cluster.section,
            human_curated: cluster.human_curated,
        };
        this.applyClusterDefaultDates(cluster);
        this.updateClusterInfoPanels(cluster);
        this.renderSelectedCities();
        this.hideError();
    }

    addPlaceToSelection(place) {
        if (!place || !place.city) {
            return;
        }

        if (this.activeCluster) {
            this.showError('Remove the cluster first to add individual cities');
            return;
        }

        if (this.countIndividualPlaces() >= this.maxIndividualCities) {
            this.showError(`Maximum ${this.maxIndividualCities} cities can be selected (use a cluster for more)`);
            return;
        }

        if (this.isPlaceSelected(place)) {
            this.showError('City already selected');
            return;
        }

        const normalized = {
            city: place.city,
            country: place.country || null,
            label: place.label || place.display_name || `${place.city}${place.country ? `, ${place.country}` : ''}`,
            clusterId: null,
        };

        this.selectedCities.push(normalized);
        this.renderSelectedCities();
        this.hideError();
    }

    addSelectedCity() {
        const searchInput = document.getElementById('city-search');
        const cityName = searchInput.value.trim();

        if (!cityName) {
            this.showError('Please enter a city name or coordinates');
            return;
        }

        if (this.selectedCity?.type === 'cluster') {
            this.addClusterToSelection(this.selectedCity.cluster_id);
            searchInput.value = '';
            this.selectedCity = null;
            this.hideAutocomplete();
            return;
        }

        if (this.selectedCity && this.selectedCity.city) {
            this.addPlaceToSelection({
                city: this.selectedCity.city,
                country: this.selectedCity.country,
                label: this.selectedCity.display_name || `${this.selectedCity.city}, ${this.selectedCity.country}`,
            });
        } else {
            const clusterHit = this.searchClusters(cityName, 1)[0];
            if (clusterHit) {
                this.addClusterToSelection(clusterHit.cluster_id);
            } else {
                const hotHit = this.searchHotlist(cityName, 1)[0];
                if (hotHit) {
                    this.addPlaceToSelection(hotHit);
                } else {
                    this.addPlaceToSelection({ city: cityName, country: searchInput.dataset.country || null, label: cityName });
                }
            }
        }

        searchInput.value = '';
        searchInput.dataset.country = '';
        this.selectedCity = null;
        this.hideAutocomplete();
    }

    removeSelectedCity(placeKey) {
        const removed = this.selectedCities.find((p) => this.placeKey(p) === placeKey);
        this.selectedCities = this.selectedCities.filter((p) => this.placeKey(p) !== placeKey);
        if (removed?.clusterId && !this.selectedCities.some((p) => p.clusterId === removed.clusterId)) {
            this.activeCluster = null;
            this.updateClusterInfoPanels(null);
        }
        this.renderSelectedCities();
    }

    removeActiveCluster() {
        this.selectedCities = [];
        this.activeCluster = null;
        this.updateClusterInfoPanels(null);
        this.renderSelectedCities();
    }

    renderSelectedCities() {
        const container = document.getElementById('selected-cities-container');
        container.innerHTML = '';

        if (this.selectedCities.length === 0) {
            container.innerHTML = '<p class="no-cities-message">No cities selected. Add up to 5 cities, or pick a cluster.</p>';
            return;
        }

        if (this.activeCluster) {
            const div = document.createElement('div');
            div.classList.add('selected-city-tag', 'selected-cluster-tag');
            div.innerHTML = `
                <span><strong>${this.activeCluster.label}</strong> — ${this.selectedCities.length} places</span>
                <button class="remove-city-button" data-cluster="1" title="Remove cluster">×</button>
            `;
            container.appendChild(div);
            div.querySelector('[data-cluster]').addEventListener('click', () => this.removeActiveCluster());
            return;
        }

        this.selectedCities.forEach((place) => {
            const key = this.placeKey(place);
            const div = document.createElement('div');
            div.classList.add('selected-city-tag');
            div.innerHTML = `
                <span>${place.label}</span>
                <button class="remove-city-button" data-key="${key}">×</button>
            `;
            container.appendChild(div);
        });

        container.querySelectorAll('.remove-city-button[data-key]').forEach((button) => {
            button.addEventListener('click', (e) => {
                this.removeSelectedCity(e.target.dataset.key);
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
        this.hideError();
        this.showLoading('Fetching VIIRS data...');
        if (this.mapViz) {
            this.mapViz.setCalibrating(true);
        }
        
        try {
            let response;
            
            const datePayload = {
                start_month: startMonth,
                start_year: startYear,
                end_month: endMonth,
                end_year: endYear,
            };

            if (this.selectedCities.length === 1) {
                const place = this.selectedCities[0];
                response = await fetch(`${this.API_BASE_URL}/viirs/city`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        city: place.city,
                        country: place.country || null,
                        ...datePayload,
                    }),
                });
            } else {
                response = await fetch(`${this.API_BASE_URL}/viirs/places`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        places: this.selectedCities.map((p) => ({
                            city: p.city,
                            country: p.country || null,
                        })),
                        ...datePayload,
                    }),
                });
            }
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to fetch data');
            }
            
            const result = await response.json();
            
            this.hideLoading();
            
            if (result.status === 'success') {
                if (!result.data || result.data.length === 0) {
                    const errDetail = result.errors?.length
                        ? result.errors.map((e) => `${e.city}: ${e.error}`).join('; ')
                        : null;
                    this.showError(
                        errDetail ||
                            'No VIIRS data returned for this date range. Local dev: copy backend/.env.example → backend/.env, set VIIRS_SOURCE=gee plus GEE_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS (see docs/GEE_SETUP.md), then restart the API.'
                    );
                    if (this.mapViz) {
                        this.mapViz.setCalibrating(false);
                    }
                    return;
                }
                this.hideError();
                this.processData(result);
                this.showVisualizations();
            } else {
                this.showError('Failed to fetch data');
            }
        } catch (error) {
            this.hideLoading();
            if (this.mapViz) {
                this.mapViz.setCalibrating(false);
            }
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
            // Skip low-quality/missing months
            if (point.radiance_corrected == null) return;
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

                // Baseline year months compare to themselves → always ~0% and misleading on the map
                if (year === firstYear) {
                    point.percentage_change = null;
                    point.percentage_change_ready = false;
                    point.is_baseline_year = true;
                    return;
                }
                
                if (baseline && baseline > 0) {
                    point.percentage_change = ((point.radiance_corrected - baseline) / baseline) * 100;
                    point.percentage_change_ready = true;
                    point.is_baseline_year = false;
                } else {
                    // Not ready / no baseline for this month — avoid showing misleading 0.0%
                    point.percentage_change = null;
                    point.percentage_change_ready = false;
                    point.is_baseline_year = false;
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
        this.mapViz.setCalibrating(false);
        
        // Set up map-to-graph interaction
        this.mapViz.onCitySelected = (cityName) => {
            this.focusOnCityInGraph(cityName);
        };

        this.mapViz.onVisibleCitiesChanged = (visibleCities) => {
            if (this.graphViz) {
                this.graphViz.updateVisibleCities(visibleCities);
                const currentDate = this.dates[this.currentDateIndex];
                if (currentDate) {
                    this.graphViz.updateTimeline(currentDate, this.getMonthDataStatus(currentDate));
                }
            }
        };
        
        // Check if we need to reinitialize the map (single city vs multi-city)
        const isMultiCity = Array.isArray(this.cityInfo);
        const wasMultiCity = this.mapViz.isMultiCity;
        
        if (isMultiCity !== wasMultiCity) {
            this.mapViz.destroyMap();
            this.mapViz.initialize(this.cityInfo, this.data, this.dates);
        } else {
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
        if (this.mapViz) {
            this.graphViz.updateVisibleCities(this.mapViz.getVisibleCityNames());
        }
        
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
    
    getMonthDataStatus(date) {
        const monthPoints = (this.data || []).filter((d) => d.date === date);
        const withData = monthPoints.filter((d) => d.radiance_corrected != null);
        const missingAtCurrent = monthPoints
            .filter((d) => d.radiance_corrected == null)
            .map((d) => d.city);

        return {
            total: monthPoints.length,
            validCount: withData.length,
            missingAtCurrent,
            allMissing: monthPoints.length > 0 && withData.length === 0,
        };
    }

    updateVisualizations() {
        const currentDate = this.dates[this.currentDateIndex];
        const monthStatus = this.getMonthDataStatus(currentDate);
        
        // Update date display
        document.getElementById('current-date-display').textContent = currentDate;
        
        // Update map
        if (this.mapViz) {
            this.mapViz.updateDate(currentDate, this.currentDateIndex);
        }
        
        // Update graph
        if (this.graphViz) {
            this.graphViz.updateTimeline(currentDate, monthStatus);
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
    
    hideError() {
        document.getElementById('error-display').style.display = 'none';
    }

    showError(message) {
        const msg =
            (typeof message === 'string') ? message :
            (message && message.message && typeof message.message === 'string') ? message.message :
            JSON.stringify(message);
        document.getElementById('error-message').textContent = msg;
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

