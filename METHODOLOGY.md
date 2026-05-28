# 📖 VIIRS Nightlights Analysis Tool - Complete Methodology & Data Flow

**Version:** 1.0.0  
**Last Updated:** November 7, 2025  
**Purpose:** Academic research, urban development analysis, economic activity monitoring

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Complete Data Flow](#complete-data-flow)
3. [Data Sources & Credits](#data-sources--credits)
4. [Step 1: City Geocoding](#step-1-city-geocoding-osm-nominatim)
5. [Step 2: Data Fetching](#step-2-viirs-data-fetching-noaa-eog)
6. [Step 3: Spatial Aggregation](#step-3-spatial-aggregation--city-boundary-representation)
7. [Step 4: Bias Correction](#step-4-bias-correction-elvidge-et-al-2021)
8. [Step 5: Visualization](#step-5-data-visualization)
9. [Accuracy & Limitations](#accuracy--limitations)
10. [Appropriate Use Cases](#appropriate-use-cases)
11. [Inappropriate Use Cases](#inappropriate-use-cases)
12. [Technical Stack](#technical-stack)
13. [License & Attribution](#license--attribution)

---

## 🌍 Overview

The **VIIRS Nightlights Analysis Tool** processes satellite nighttime light data to track economic activity, urban development, and infrastructure changes over time (2012-2025). This document provides a complete end-to-end explanation of how the system works, from user input to final visualization.

### Key Features

- **Real-time data fetching** from NOAA Earth Observation Group
- **Automated geocoding** via OpenStreetMap Nominatim
- **Scientific bias correction** using Elvidge et al. (2021) methodology
- **Interactive visualization** with Leaflet.js and D3.js
- **Multi-city comparison** capabilities
- **Data export** in Excel, CSV, and JSON formats

---

## 🔄 Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER INPUT                                  │
│  "Mumbai" or "19.07, 72.87" + Date Range (2019-2024)          │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: GEOCODING (OpenStreetMap Nominatim)                   │
│  • Convert city name → lat/lon coordinates                      │
│  • Determine appropriate analysis radius                        │
│  • Validate coordinates (-65° to 75°N, -180° to 180°E)         │
│                                                                  │
│  Output: {lat: 19.0760, lon: 72.8777, radius_km: 20}          │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: TILE IDENTIFICATION (NOAA EOG VIIRS)                  │
│  • Determine which global tile contains coordinates             │
│  • Global coverage: 6 tiles (75N180W, 75N060W, etc.)           │
│  • Each tile: ~60° latitude × 120° longitude                   │
│                                                                  │
│  Output: tile_name = "75N060W"                                 │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: AUTHENTICATION & DOWNLOAD (NOAA EOG)                  │
│  • OAuth 2.0 authentication with NOAA EOG                       │
│  • Download monthly composite GeoTIFF (.tgz archives)          │
│  • Extract avg_rade9h.tif (radiance band)                      │
│  • URL pattern: eogdata.mines.edu/nighttime_light/monthly/v10/ │
│                                                                  │
│  Output: GeoTIFF file (~50-200 MB per month)                   │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: SPATIAL EXTRACTION (Rasterio + PyProj)                │
│  • Open GeoTIFF with rasterio                                   │
│  • Transform WGS84 coordinates → GeoTIFF projection            │
│  • Extract square bounding box (±radius_deg around center)     │
│  • Read pixel values (~750m resolution)                         │
│                                                                  │
│  Output: 2D array of radiance values (e.g., 27×27 pixels)     │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 5: AGGREGATION & AVERAGING                               │
│  • Filter invalid values (NaN, negative, >1e10)                │
│  • Calculate mean radiance: avg = nanmean(pixel_array)         │
│  • Estimate cloud coverage: (valid_pixels / total_pixels) × 100│
│                                                                  │
│  Output: {radiance: 15.34, cf_cvg: 78.5}                      │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 6: BIAS CORRECTION (Elvidge et al. 2021)                 │
│  • Apply formula: corrected = raw × (1 + 0.2 × (1 - cf_cvg/100))│
│  • Accounts for cloud obscuration in monthly composites         │
│  • α = 0.2 (empirically determined)                            │
│                                                                  │
│  Output: {radiance_corrected: 16.12}                           │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 7: PERCENTAGE CHANGE CALCULATION                         │
│  • Baseline = first year data (same month)                     │
│  • Change = ((current - baseline) / baseline) × 100            │
│                                                                  │
│  Output: {percentage_change: +12.5}                            │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 8: VISUALIZATION (Leaflet.js + D3.js)                    │
│  • Map: Leaflet.js with CircleMarkers (size = radiance)        │
│  • Graph: D3.js line chart showing temporal trends             │
│  • Animation: Timeline playback of changes                      │
│  • Export: Excel/CSV/JSON download                             │
│                                                                  │
│  Output: Interactive web visualization                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🌐 Data Sources & Credits

### Primary Data Source

#### NOAA Earth Observation Group (EOG)

**Official Website:** [https://eogdata.mines.edu/nighttime_light/monthly/v10](https://eogdata.mines.edu/nighttime_light/monthly/v10)

**Data Specifications:**
- **Satellite:** Suomi NPP VIIRS Day/Night Band (DNB)
- **Sensor Resolution:** ~750 meters at nadir
- **Temporal Resolution:** Monthly composites
- **Coverage:** Global (-65° to 75° latitude)
- **Time Range:** January 2012 - Present
- **Update Frequency:** Monthly (with 1-2 month lag)
- **Data Format:** GeoTIFF (.tif files in .tgz archives)
- **Units:** Radiance (nW/cm²/sr)

**File Structure:**
```
SVDNB_npp_YYYYMMDD_TILE_vcmslcfg_v10_c*.avg_rade9h.tif
Example: SVDNB_npp_20240115_75N060W_vcmslcfg_v10_c202401171200.avg_rade9h.tif
```

**Citation:**
> Earth Observation Group, Payne Institute for Public Policy, Colorado School of Mines. (2012-2025). VIIRS Nighttime Day/Night Band Composites Version 1. https://eogdata.mines.edu

**License:** Public domain data provided by NOAA

### Geocoding Service

#### OpenStreetMap Nominatim API

**Official Website:** [https://nominatim.openstreetmap.org](https://nominatim.openstreetmap.org)

**Service Specifications:**
- **Data Source:** OpenStreetMap (OSM) database
- **Coverage:** Global place name database
- **Coordinate System:** WGS84 (EPSG:4326)
- **Precision:** ~11 meters (4 decimal places)
- **Rate Limit:** 1 request per second (honored by this tool)

**Usage in This Tool:**
- Convert city names to coordinates (e.g., "Mumbai" → 19.0760, 72.8777)
- Reverse geocoding (coordinates → place names)
- City boundary radius estimation based on place type

**Citation:**
> OpenStreetMap contributors. (2024). OpenStreetMap. https://www.openstreetmap.org

**License:** Open Data Commons Open Database License (ODbL)

### Scientific Methodology

#### Elvidge et al. (2021) - Bias Correction

**Full Citation:**
> Elvidge, C. D., Zhizhin, M., Ghosh, T., Hsu, F. C., & Taneja, J. (2021). "But clouds got in my way: Bias and bias correction of VIIRS nighttime lights data." *Remote Sensing of Environment*, 258, 112165.  
> DOI: [https://doi.org/10.1016/j.rse.2021.112165](https://doi.org/10.1016/j.rse.2021.112165)

**Key Contribution:**
Developed empirically-validated correction factor (α ≈ 0.2) to compensate for cloud obscuration bias in monthly VIIRS composites.

**Formula:**
```
corrected_radiance = raw_radiance × (1 + α × (1 - cloud_free_coverage/100))
```

Where:
- `α = 0.2` (empirically determined coefficient)
- `cloud_free_coverage` = percentage of cloud-free observations (0-100%)

---

## 🔍 STEP 1: City Geocoding (OSM Nominatim)

### How It Works

When you enter a city name (e.g., "Mumbai" or "Berlin, Germany"), the system:

1. **Sends request to Nominatim API:**
   ```
   GET https://nominatim.openstreetmap.org/search?
       q=Mumbai&format=json&limit=1&addressdetails=1
   ```

2. **Receives structured response:**
   ```json
   {
     "lat": "19.0760",
     "lon": "72.8777",
     "display_name": "Mumbai, Maharashtra, India",
     "type": "city",
     "address": {
       "city": "Mumbai",
       "state": "Maharashtra",
       "country": "India"
     }
   }
   ```

3. **Determines analysis radius based on city type:**
   - **City:** 15 km
   - **Town:** 10 km
   - **Village:** 5 km
   - **Municipality:** 12 km
   - **Administrative:** 20 km

4. **Validates coordinates:**
   - Latitude: -90° to +90°
   - Longitude: -180° to +180°
   - VIIRS coverage: -65° to +75° latitude

### Code Implementation

**File:** `backend/osm_service.py`

```python
class OSMService:
    def geocode_city(self, city: str, country: Optional[str] = None):
        # Rate limiting (1 req/sec)
        self._rate_limit()
        
        # Build query
        query = f"{city}, {country}" if country else city
        
        # Request with proper headers
        response = requests.get(
            f"{self.BASE_URL}/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "VIIRSNightlightsApp/1.0"}
        )
        
        # Parse and return
        return {
            "lat": float(result["lat"]),
            "lon": float(result["lon"]),
            "radius_km": self._estimate_radius(result["type"])
        }
```

### Coordinate Systems

**Input:** Any coordinate system (city names, WGS84 coordinates)  
**Internal:** WGS84 (EPSG:4326) - latitude/longitude in decimal degrees  
**Output:** WGS84 coordinates ready for VIIRS tile lookup

---

## 🛰️ STEP 2: VIIRS Data Fetching (NOAA EOG)

### Authentication

The system uses **OAuth 2.0** authentication with NOAA EOG's Keycloak server:

**File:** `backend/noaa_auth.py`

```python
class NOAAAuthenticator:
    def authenticate(self):
        # 1. Request protected resource (triggers OAuth redirect)
        # 2. Parse Keycloak login form
        # 3. Submit credentials with hidden form fields
        # 4. Follow OAuth callback redirects
        # 5. Capture authenticated session cookies
```

### Tile Selection

NOAA provides 6 global tiles covering the entire Earth:

| Tile Name | Latitude Range | Longitude Range | Coverage |
|-----------|----------------|-----------------|----------|
| 75N180W | 0° to 75°N | -180° to -60° | North America (West) |
| 75N060W | 0° to 75°N | -60° to 60° | Americas, Europe, Africa |
| 75N060E | 0° to 75°N | 60° to 180° | Asia, Australia |
| 00N180W | -65° to 0° | -180° to -60° | South America (West) |
| 00N060W | -65° to 0° | -60° to 60° | South America, Africa |
| 00N060E | -65° to 0° | 60° to 180° | Southern Asia, Australia |

**Code Implementation:**

```python
def get_tile_for_location(self, lat: float, lon: float) -> str:
    for tile_name, bounds in self.TILES.items():
        lat_min, lat_max = bounds['lat_range']
        lon_min, lon_max = bounds['lon_range']
        
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return tile_name
```

### Download Process

**File:** *(bulk loader removed for open-source cleanup)*

```python
async def _download_tile_with_retry(self, year_month: str, tile_name: str):
    # 1. Construct URL
    url = f"https://eogdata.mines.edu/nighttime_light/monthly/v10/{year}/{year_month}/vcmslcfg/"
    
    # 2. Find .tgz file by parsing HTML directory listing
    href = self._find_tgz_file(url, tile_name)
    
    # 3. Download with authenticated session
    async with aiohttp.ClientSession(cookies=auth_cookies) as session:
        data = await session.get(file_url).read()
    
    # 4. Extract .tif from .tgz archive
    tif_data = self._extract_tif_from_tgz(data, tile_name)
    
    return tif_data
```

### File Formats

**Downloaded:** `.tgz` archive (~50-200 MB compressed)  
**Extracted:** `.tif` GeoTIFF file (~100-400 MB uncompressed)  
**Bands:** `avg_rade9h` (average radiance) - this tool uses this  
**Note:** `cf_cvg` (cloud-free coverage) band available but not currently used

---

## 📐 STEP 3: Spatial Aggregation & City Boundary Representation

### ⚠️ IMPORTANT: Methodology Limitation

**This is the most critical section for understanding data accuracy and appropriate use cases.**

### How City Boundaries Are Defined

Unlike GIS software that can use actual administrative boundaries, this tool uses a **simplified approach**:

1. **Fixed Circular Radius:** Each city is assigned a predefined radius
   - Mumbai: 20 km
   - Delhi: 25 km
   - Tiruppur: 8 km
   - Custom cities: Estimated from OSM place type

2. **Square Bounding Box Extraction:** Despite the "radius" being circular, data is extracted from a **square box**
   ```
   Square boundaries:
   - West:  longitude - (radius_km / 111.0)
   - East:  longitude + (radius_km / 111.0)
   - South: latitude - (radius_km / 111.0)
   - North: latitude + (radius_km / 111.0)
   ```

3. **Equal-Weight Averaging:** All pixels within the square are averaged with equal weight

### Visual Representation

```
What the UI shows (circular radius):
       ╭─────────╮
     ╱░░░░░░░░░░░╲
   ╱░░░░░░░░░░░░░░░╲
  │░░░░░░░░░░░░░░░░░│
  │░░░░░░ ★ ░░░░░░░░│   ★ = City center
  │░░░░░░░░░░░░░░░░░│   ░ = "Included" area
   ╲░░░░░░░░░░░░░░░╱
     ╲░░░░░░░░░░░╱
       ╰─────────╯

What actually gets extracted (square box):
┌─────────────────────────┐
│░░░░░░░░░░░░░░░░░░░░░░░░░│
│░░░░░░░░░░░░░░░░░░░░░░░░░│
│░░░░░░░░░░░░░░░░░░░░░░░░░│
│░░░░░░░░░░░ ★ ░░░░░░░░░░░│   ★ = City center
│░░░░░░░░░░░░░░░░░░░░░░░░░│   ░ = Actually extracted
│░░░░░░░░░░░░░░░░░░░░░░░░░│   ▓ = Corner "extra" area
│░░░░░░░░░░░░░░░░░░░░░░░░░│
└─────────────────────────┘

Difference: Corners include ~27% extra area!
```

### Code Implementation

**File:** *(bulk loader removed for open-source cleanup)*

```python
# Get city location and radius
lat = city['lat']
lon = city['lon']
radius_km = city.get('radius_km', 10.0)

# Convert radius to degrees (APPROXIMATE!)
radius_deg = radius_km / 111.0  # 1 degree ≈ 111 km

# Define SQUARE bounding box
window = from_bounds(
    lon - radius_deg,  # West
    lat - radius_deg,  # South
    lon + radius_deg,  # East
    lat + radius_deg,  # North
    transform=src.transform
)

# Read ALL pixels in square
data = src.read(1, window=window)  # Returns 2D array

# Filter invalid values
data = np.where(data < 0, np.nan, data)
data = np.where(data > 1e10, np.nan, data)

# Simple unweighted average
avg_radiance = float(np.nanmean(data))
```

### Pixel Counts by City Size

| Radius | Square Size | Pixel Count (~750m) | Area Difference |
|--------|-------------|---------------------|-----------------|
| 5 km | 10×10 km | ~178 pixels | +27% vs circle |
| 10 km | 20×20 km | ~711 pixels | +27% vs circle |
| 15 km | 30×30 km | ~1,600 pixels | +27% vs circle |
| 20 km | 40×40 km | ~2,844 pixels | +27% vs circle |
| 25 km | 50×50 km | ~4,444 pixels | +27% vs circle |

### Implications

1. **Corner Pixels:** The four corners of the square are **outside** the intended circular radius
2. **Extra Area:** ~27% more pixels included than a true circle
3. **Dilution Effect:** Urban core signal diluted by suburban/rural areas in corners
4. **Coastal Cities:** Linear cities along coasts will include water areas
5. **Irregular Shapes:** Cities with industrial corridors not well-represented

---

## 🔬 STEP 4: Bias Correction (Elvidge et al. 2021)

### Why Bias Correction Is Needed

VIIRS monthly composites are created by averaging **only cloud-free observations**. If a location was cloudy for 20 out of 30 nights, the composite only uses 10 nights of data, which can introduce systematic bias (clouds correlate with weather patterns, seasons, etc.).

### The Correction Formula

```
corrected_radiance = raw_radiance × (1 + α × (1 - cf_cvg/100))
```

**Where:**
- `raw_radiance` = Average pixel value from GeoTIFF
- `α = 0.2` = Empirically determined correction coefficient (Elvidge et al. 2021)
- `cf_cvg` = Cloud-free coverage percentage (0-100%)

### Examples

| Raw Radiance | Cloud-Free Coverage | Correction Factor | Corrected Radiance |
|--------------|---------------------|-------------------|--------------------|
| 10.0 | 80% | 1.04 | 10.4 |
| 10.0 | 60% | 1.08 | 10.8 |
| 10.0 | 40% | 1.12 | 11.2 |
| 10.0 | 20% | 1.16 | 11.6 |

**Interpretation:** Lower cloud-free coverage → higher correction (more uncertain data).

### Code Implementation

**File:** `backend/bias_correction.py`

```python
class BiasCorrection:
    ALPHA = 0.2  # Elvidge et al. (2021)
    FALLBACK_FACTOR = 1.15  # When cf_cvg unavailable
    
    @staticmethod
    def apply_correction(radiance, cloud_free_coverage=None):
        if cloud_free_coverage is None:
            # No cloud data available
            return radiance * BiasCorrection.FALLBACK_FACTOR
        
        # Validate cloud coverage (0-100%)
        cloud_free_coverage = max(0, min(100, cloud_free_coverage))
        
        # Apply Elvidge et al. (2021) correction
        correction_factor = 1 + BiasCorrection.ALPHA * (1 - cloud_free_coverage / 100)
        corrected = radiance * correction_factor
        
        return corrected
```

### Limitations

1. **Cloud Coverage Estimation:** Currently estimated as `(valid_pixels / total_pixels)` rather than using the actual `cf_cvg` band from NOAA
2. **Uniform Application:** Applied uniformly across the region (doesn't account for spatial variation)
3. **Seasonal Bias:** Not adjusted for seasonal lighting variations (except for latitudes > 40°)

---

## 📊 STEP 5: Data Visualization

### Frontend Stack

**Technologies:**
- **Leaflet.js** - Interactive map rendering
- **D3.js** - Time-series graph visualization  
- **Vanilla JavaScript** - Application logic
- **CSS Grid** - Responsive layout

### Map Visualization

**File:** `frontend/assets/js/map-visualization.js`

**Features:**
- Circle markers sized by radiance intensity
- Color gradient: Yellow (low) → Orange → Red (high)
- Analysis radius shown as dashed circle
- Click to focus on specific city
- Multiple basemap options (OSM, Dark, Satellite)

```javascript
// Create radiance marker
const marker = L.circleMarker([lat, lon], {
    radius: normalizedSize / 2,        // Size based on radiance
    color: '#ffffff',
    fillColor: getRadianceColor(radiance),  // Yellow → Red
    fillOpacity: 0.8,
    weight: 2
});
```

### Graph Visualization

**File:** `frontend/assets/js/graph-visualization.js`

**Features:**
- D3.js line chart with temporal axis
- Hover tooltips showing exact values
- Multi-city comparison (different colors per city)
- Percentage change indicators
- Responsive scaling

### Animation

**Features:**
- Timeline playback of radiance changes
- Adjustable speed (0.5x - 4x)
- Slider scrubbing through time
- Synchronized map and graph updates

---

## ⚠️ Accuracy & Limitations

### Spatial Accuracy

| Component | Accuracy | Issue |
|-----------|----------|-------|
| **OSM Geocoding** | ±11 meters | High precision for city centers |
| **VIIRS Resolution** | ~750 meters | Sensor limitation |
| **Square vs Circle** | +27% area | Corner pixels outside intended radius |
| **Coordinate Transform** | Sub-meter | Professional pyproj library |
| **Radius Approximation** | ±50% at 60° lat | Simple km→degree conversion |
| **Pixel Count Variation** | 300-6,400 pixels | Small vs large cities |

### Temporal Accuracy

| Component | Accuracy | Issue |
|-----------|----------|-------|
| **Monthly Composites** | ±15 days | Mid-month reference date |
| **Cloud Bias Correction** | ±15-20% | Empirical α coefficient |
| **Processing Lag** | 1-2 months | NOAA data availability |

### Known Issues

1. **Coastal Cities:** Water areas included in square extraction
2. **Linear Cities:** Elongated cities (along rivers, coasts) poorly represented
3. **Industrial Corridors:** Satellite industrial zones may be outside radius
4. **High Latitude:** Longitude degree approximation breaks down (±50% error at 60°)
5. **No Distance Weighting:** Suburban edge pixels weighted equally to urban core
6. **Administrative Boundaries:** Does not follow official city limits

---

## ✅ Appropriate Use Cases

**This tool is GOOD for:**

1. **Temporal Trend Analysis**
   - Track single city over time
   - Identify growth, decline, or stability patterns
   - Detect seasonal variations
   - Before/after policy analysis

2. **Comparative Analysis**
   - Compare multiple cities consistently
   - Regional development patterns
   - Cross-country urban growth
   - Economic activity comparisons

3. **Large-Scale Studies**
   - National or global urban trends
   - Electrification progress
   - Conflict zone monitoring
   - Disaster impact assessment

4. **Educational Purposes**
   - Demonstrate remote sensing principles
   - Teach urban geography
   - Visualize economic data

5. **Initial Screening**
   - Identify cities for detailed study
   - Rapid assessment of urban changes
   - Hypothesis generation

### Example Research Questions

✅ "How has nighttime lighting in Indian cities changed from 2012-2024?"  
✅ "Which cities showed the largest growth during COVID-19 recovery?"  
✅ "Do textile hub cities (Tiruppur, Surat) show different patterns than tech hubs (Bengaluru)?"  
✅ "What is the seasonal variation in lighting for high-latitude cities?"  

---

## ❌ Inappropriate Use Cases

**This tool is NOT GOOD for:**

1. **Precise Boundary Mapping**
   - Defining official city limits
   - Property boundary analysis
   - Urban planning requiring exact boundaries

2. **Fine Spatial Detail**
   - Neighborhood-level analysis
   - Individual building analysis
   - Street-level infrastructure mapping

3. **Absolute Radiance Comparisons**
   - "Mumbai is 1.5x brighter than Delhi" (depends on radius choice!)
   - Cross-city radiance rankings
   - Radiance per capita calculations

4. **Irregular City Shapes**
   - Coastal cities (will include ocean)
   - Linear cities along rivers
   - Cities with multiple urban cores

5. **Dense Urban Cores**
   - Downtown lighting analysis
   - Central business district metrics
   - Distance decay analysis from center

6. **Publication-Grade Research** (without additional validation)
   - Requires GIS software verification
   - Should use actual city boundary shapefiles
   - Need distance-weighted or population-weighted metrics

### Example Questions NOT Suitable

❌ "What is the exact radiance of Mumbai's downtown?"  
❌ "How much brighter per square kilometer is Delhi vs Mumbai?"  
❌ "Map the precise boundary of urban vs suburban areas."  
❌ "Analyze lighting along Mumbai's coastline."  

---

## 🛠️ Technical Stack

### Backend

**Language:** Python 3.9+  
**Framework:** FastAPI (async ASGI)  
**Database:** SQLite (for caching and preprocessed cities)

**Key Libraries:**
```python
fastapi==0.104.1           # Web framework
rasterio==1.3.9            # GeoTIFF processing
numpy==1.26.2              # Array operations
pyproj==3.6.1              # Coordinate transformations
requests==2.31.0           # HTTP client (sync)
aiohttp==3.9.1             # HTTP client (async)
beautifulsoup4==4.12.2     # HTML parsing (OAuth forms)
```

**Attribution:**
- **FastAPI** by Sebastián Ramírez - [https://fastapi.tiangolo.com](https://fastapi.tiangolo.com) - MIT License
- **Rasterio** by Mapbox - [https://rasterio.readthedocs.io](https://rasterio.readthedocs.io) - BSD License
- **PyProj** - [https://pyproj4.github.io/pyproj](https://pyproj4.github.io/pyproj) - MIT License

### Frontend

**Core:**
- **Leaflet.js** 1.9.4 - [https://leafletjs.com](https://leafletjs.com) - BSD 2-Clause License
- **D3.js** v7 - [https://d3js.org](https://d3js.org) - ISC License
- **SheetJS** (xlsx) - [https://sheetjs.com](https://sheetjs.com) - Apache 2.0 License

**Basemap Providers:**
- **OpenStreetMap** - [https://www.openstreetmap.org](https://www.openstreetmap.org) - ODbL License
- **CARTO** (Dark tiles) - [https://carto.com/basemaps](https://carto.com/basemaps) - CC BY 3.0
- **Esri** (Satellite tiles) - [https://www.esri.com](https://www.esri.com) - Attribution required

### Infrastructure

**Deployment Options:**
- **Docker** - Containerized deployment
- **Nginx** - Reverse proxy and static file serving
- **Uvicorn** - ASGI server for FastAPI

---

## 📄 License & Attribution

### This Tool

**License:** MIT License

```
Copyright (c) 2025 VIIRS Nightlights Analysis Tool

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### Data Attribution Requirements

**When using this tool or its data, please cite:**

1. **VIIRS Data:**
   > Earth Observation Group, Payne Institute for Public Policy, Colorado School of Mines. VIIRS Nighttime Day/Night Band Composites Version 1. https://eogdata.mines.edu

2. **Bias Correction Methodology:**
   > Elvidge, C. D., Zhizhin, M., Ghosh, T., Hsu, F. C., & Taneja, J. (2021). "But clouds got in my way: Bias and bias correction of VIIRS nighttime lights data." *Remote Sensing of Environment*, 258, 112165. https://doi.org/10.1016/j.rse.2021.112165

3. **Geocoding Data:**
   > OpenStreetMap contributors. (2024). OpenStreetMap. https://www.openstreetmap.org

4. **This Tool (Optional):**
   > VIIRS Nightlights Analysis Tool (2025). Version 1.0.0. [Your URL/GitHub]

### Disclaimer

This tool is provided for educational and research purposes. The spatial aggregation methodology uses simplified city boundary approximations (see [Step 3](#step-3-spatial-aggregation--city-boundary-representation)). For publication-grade research, verify results using GIS software with actual administrative boundaries.

**No warranty is provided regarding:**
- Accuracy of spatial aggregations
- Completeness of temporal data
- Suitability for specific use cases
- Real-time data availability

**Users are responsible for:**
- Validating results for their specific use case
- Understanding methodology limitations
- Proper citation of data sources
- Compliance with data source terms of use

---

## 📧 Contact & Support

**For Issues or Questions:**
- Review this methodology documentation
- Check the main README.md for troubleshooting
- Consult individual data source documentation

**Data Source Support:**
- **NOAA EOG:** [https://eogdata.mines.edu/contact/](https://eogdata.mines.edu/contact/)
- **OpenStreetMap:** [https://www.openstreetmap.org/help](https://www.openstreetmap.org/help)

---

## 🔄 Version History

**Version 1.0.0** (November 7, 2025)
- Initial comprehensive methodology documentation
- Complete end-to-end workflow explanation
- Detailed spatial aggregation limitations
- Full attribution and licensing information

---

**Last Updated:** November 7, 2025  
**Document Version:** 1.0.0  
**Tool Version:** 1.0.0

---

*Built with 🛰️ satellite data and ❤️ for data visualization*






