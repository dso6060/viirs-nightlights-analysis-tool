# 🌍 VIIRS Nightlights Analysis Tool

An interactive web application for analyzing nighttime lights data from NASA/NOAA VIIRS satellite imagery. Track economic activity, urban development, and infrastructure changes through satellite data visualization.

![VIIRS Data](https://img.shields.io/badge/Data-NOAA%20EOG-blue)
![Version](https://img.shields.io/badge/Version-1.0.0-green)
![License](https://img.shields.io/badge/License-Non--commercial%20OSS-black)

## 🎯 Features

- **🔍 City Search**: Intelligent geocoding with OSM Nominatim API
- **📊 Interactive Visualization**: Leaflet.js maps + D3.js timeline graphs
- **📈 Bias Correction**: Implements Elvidge et al. (2021) methodology
- **🎬 Animation**: Timeline playback of nightlights changes
- **📥 Data Export**: Excel, CSV, and JSON export functionality
- **🌓 Dark Theme**: Optimized for nightlights data visualization
- **📱 Responsive**: Works on desktop and mobile devices

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** (for backend)
- **Modern web browser** (Chrome, Firefox, Safari, Edge)
- **4GB RAM minimum** (recommended: 8GB)
- **Internet connection** (for NOAA data downloads)

### Installation

1. **Clone or download this repository**

```bash
cd /Users/user/Documents/repo/satDataTest
```

2. **Create a virtualenv (recommended)**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. **Install Python dependencies**

```bash
cd backend
pip install -r requirements.txt
```

4. **Configure environment variables (recommended)**

Copy `.env.example` to `backend/.env` and adjust paths if needed:

```bash
cp ../.env.example .env
```

By default the app runs in **NOAA mode** (`VIIRS_SOURCE=noaa`) and does not require any Google accounts.

If you want to run in **Google Earth Engine mode** (`VIIRS_SOURCE=gee`), follow `docs/GEE_SETUP.md`.

5. **Start the backend server**

```bash
python main.py
```

The API will start on `http://localhost:8000`

> Note: This repository is **real-data only**. Any mock/synthetic data generation used during early testing has been removed.

6. **Generate the city hotlist (for autocomplete + clusters)**

The UI uses a ~800-place hotlist for instant autocomplete and predefined clusters. Generate it once:

```bash
python3 scripts/build_hotlist.py
```

This creates `backend/data/hotlist.json` locally (it is intentionally not committed to the repo).

7. **Open the frontend**

Open `frontend/index.html` in your web browser, or use a simple HTTP server:

```bash
cd frontend
python -m http.server 8080
```

Then navigate to `http://localhost:8080`

## 📖 Usage Guide

### Basic Workflow

1. **Search for a city** - Enter city name (e.g., "Mumbai") or coordinates (e.g., "19.07, 72.87")
2. **Select date range** - Choose start/end months and years (2012-2025)
3. **Click "Analyze"** - Wait for data to be fetched from NOAA
4. **Explore visualizations**:
   - **Map**: Geographic view with radiance intensity circles
   - **Graph**: Timeline showing radiance trends
   - **Animation**: Play timeline to see changes over time
5. **Export data** - Download processed data as Excel, CSV, or JSON

### City Search Examples

```
Mumbai
Berlin, Germany
52.52, 13.40
New York
```

### Date Range

- **Minimum**: 2012-01 (VIIRS data start)
- **Maximum**: Current month - 2 months (processing lag)
- **Granularity**: Monthly composites

### Understanding the Data

#### Radiance Values

- **Units**: nW/cm²/sr (nanowatts per square centimeter per steradian)
- **Typical Urban Values**: 0.5 - 10 nW/cm²/sr
- **Interpretation**: Higher values = more nighttime lighting = more economic activity

#### Percentage Change

- **Calculation**: `((current - baseline) / baseline) × 100`
- **Baseline**: First year in selected range (same month)
- **Color Coding**:
  - 🟢 Green (+40%+): Large increase vs baseline
  - 🟡 Yellow (-40% to +40%): Stable (typical seasonality)
  - 🔴 Red (-40%-): Large decrease (e.g. conflict / outage)

#### Missing / null months (data quality)

Some months have **very low cloud-free coverage** (e.g., monsoon-heavy periods). To avoid misleading “dips to zero”, this backend treats months with `cloud_free_coverage < MIN_CF_CVG` as **missing**:

- `radiance = null`
- `radiance_corrected = null`

You can tune the threshold using `MIN_CF_CVG` (see `.env.example`).

#### Map legend & disclosures (matches the hosted app)

- **Analysis radius is approximate**: the dashed ring is a fixed-distance circle around the geocoded center, not an official city/district/port boundary.
- **Not a statutory map**: shapes are for orientation only and do not follow legal administrative borders.
- **How the monthly point is computed**: VIIRS pixels in a square bounding box (±radius) are averaged with equal weight, then bias-corrected (Elvidge et al., 2021).
- **How “% change” is defined**: for each month-of-year, the current value is compared to the same month in the first year of your selected range (the “baseline”), which helps reduce seasonality effects.
- **Exports include raw and processed**: exports include both `Radiance_Raw` and `Radiance_BiasCorrected`.
- **Exports include quality flags**: exports include `Data_Quality` and `Null_Reason` so you can see when/why a month is missing.

## 🔧 API Documentation

### Base URL

```
http://localhost:8000
```

### Endpoints

#### 1. Get Latest Available Data

```http
GET /viirs/latest-available
```

**Response:**
```json
{
  "year": 2025,
  "month": 9,
  "date_string": "2025-09"
}
```

#### 2. Fetch City Data

```http
POST /viirs/city
Content-Type: application/json

{
  "city": "Mumbai",
  "country": "India",
  "start_month": 1,
  "start_year": 2019,
  "end_month": 12,
  "end_year": 2024
}
```

**Response:**
```json
{
  "status": "success",
  "city_info": {
    "city": "Mumbai",
    "country": "India",
    "lat": 19.0760,
    "lon": 72.8777,
    "radius_km": 10
  },
  "data": [
    {
      "date": "2019-01",
      "city": "Mumbai",
      "country": "India",
      "latitude": 19.0760,
      "longitude": 72.8777,
      "radiance": 5.234,
      "radiance_corrected": 5.678,
      "cloud_free_coverage": 87.5
    }
  ],
  "metadata": {
    "baseline_year": 2019,
    "data_points": 72,
    "data_source": "NOAA Earth Observation Group"
  }
}
```

#### 3. Search Cities (Autocomplete)

```http
GET /search?q=Mumb&limit=10
```

#### 4. Fetch Coordinates Data

```http
POST /viirs/coordinates
Content-Type: application/json

{
  "latitude": 19.07,
  "longitude": 72.87,
  "radius_km": 10,
  "start_month": 1,
  "start_year": 2019,
  "end_month": 12,
  "end_year": 2024
}
```

## 🧪 Methodology

### Data Source

**NOAA Earth Observation Group (EOG)**  
https://eogdata.mines.edu/nighttime_light/monthly/v10

- **Satellite**: Suomi NPP VIIRS DNB
- **Resolution**: ~750m
- **Temporal**: Monthly composites (2012-present)
- **Coverage**: Global (-65° to 75°N)

### Bias Correction

Implements **Elvidge et al. (2021)** methodology:

```
corrected_radiance = radiance × (1 + α × (1 - cloud_free_coverage/100))
```

Where:
- `α ≈ 0.2` (empirically determined)
- `cloud_free_coverage` = percentage of cloud-free observations

**Reference:**  
Elvidge, C. D., Zhizhin, M., Ghosh, T., Hsu, F. C., & Taneja, J. (2021). "But clouds got in my way: Bias and bias correction of VIIRS nighttime lights data." *Remote Sensing of Environment*, 258, 112165. https://doi.org/10.1016/j.rse.2021.112165

### Spatial Aggregation Method

#### ⚠️ City Boundary Representation

**This tool uses a simplified circular/square approximation for city boundaries:**

**How it works:**
1. Each city is assigned a **fixed circular radius** (e.g., Mumbai: 20 km, Tiruppur: 8 km)
2. Data is extracted from a **square bounding box** (±radius in lat/lon)
3. All pixels within the box are averaged with **equal weight**

**Example:** For a 10 km radius city:
- **Square area**: 20×20 km = 400 km²
- **Pixel count**: ~729 pixels (at 750m resolution)
- **Averaging**: Simple mean of all pixel radiance values

#### ✅ What This Method Is Good For:

- **Temporal trend analysis** - Track changes in the same city over time
- **City-to-city comparisons** - Compare multiple cities consistently
- **Economic activity monitoring** - Detect growth, decline, or stability patterns
- **Regional analysis** - Understand broad urban development trends
- **Policy impact assessment** - Before/after analysis of infrastructure projects

#### ❌ What This Method Is NOT Good For:

- **Precise urban boundaries** - Does not follow actual city limits or administrative boundaries
- **Irregular city shapes** - Treats all cities as circles/squares regardless of actual shape
  - Linear cities (coastal, along rivers) will include water/rural areas
  - Cities with industrial corridors or satellite towns may be under/over-represented
- **Fine spatial detail** - Corner pixels (27% extra area) dilute the urban core signal
- **Absolute radiance accuracy** - Different cities averaged over varying pixel counts
- **Dense urban cores** - Suburban/rural areas at edges weighted equally to downtown
- **Distance-based analysis** - No weighting by distance from city center

#### 🎯 Accuracy Considerations:

| Component | Impact | Magnitude |
|-----------|--------|-----------|
| **Square vs Circle** | Extra area in corners | +27% area |
| **High latitude distortion** | Longitude degree approximation | ±50% at 60° latitude |
| **VIIRS pixel resolution** | Spatial aggregation limit | ~750m at nadir |
| **Variable pixel counts** | Small vs large cities | 300-6,400 pixels |
| **No distance weighting** | Edge pixels = center pixels | No gradient |

#### 💡 Recommendations for Users:

**For best results:**
- Use for **time-series analysis** within the same city
- Compare cities of **similar sizes** for more meaningful comparisons
- Interpret absolute radiance values with caution
- Consider that coastal/linear cities may have diluted values
- Use percentage change metrics rather than absolute values when comparing different cities

**Alternative approaches for precise analysis:**
- Download actual city boundary shapefiles from OpenStreetMap
- Use GIS software (QGIS, ArcGIS) with VIIRS GeoTIFF files
- Implement distance-weighted averaging or circular masks
- Consider population-weighted metrics for accuracy

### Percentage Change Calculation

```python
baseline = first_year_data[same_month]
percentage_change = ((current - baseline) / baseline) × 100
```

## 🖥️ VPS Deployment

### Baseline VPS sizing (example)

- **RAM**: 4–8GB
- **CPU**: 2 cores
- **Storage**: 50GB+ (more if you persist caches or store large datasets)
- **Network**: stable outbound bandwidth (NOAA downloads can be large)

### Deployment Steps (example)

#### 1. Install Dependencies

```bash
sudo apt update
sudo apt install python3-pip nginx

cd /path/to/satDataTest/backend
pip3 install -r requirements.txt
```

#### 2. Create Systemd Service

```bash
sudo nano /etc/systemd/system/viirs-backend.service
```

```ini
[Unit]
Description=VIIRS Nightlights Backend
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/satDataTest/backend
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable viirs-backend
sudo systemctl start viirs-backend
```

#### 3. Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/viirs
```

```nginx
server {
    listen 80;
    server_name <your-domain>;

    # Frontend
    location / {
        root /path/to/satDataTest/frontend;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/viirs /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 4. Monthly Data Update Cron Job

```bash
crontab -e
```

Add:
```
0 2 5 * * /usr/bin/python3 /path/to/satDataTest/backend/update_preprocessed_cities.py >> /var/log/viirs_update.log 2>&1
```

## 📊 Pre-Processed Cities Database

The tool includes a pre-processed database of 140 major cities for instant results:

- **45 Indian cities** (metros, SEZ, defense hubs, border cities)
- **25 American cities** (major metros)
- **30 European capitals**
- **20 Pakistani cities** (cross-border analysis)
- **20 Conflict zone cities** (Ukraine, Russia, Middle East)

**Storage**: ~70 MB (SQLite)  
**Response time**: <100ms (vs 30-60s for new cities)

## 🐛 Troubleshooting

### Backend Issues

**Error: "Module not found"**
```bash
pip install -r backend/requirements.txt
```

### Earth Engine (GEE) mode issues

If you set `VIIRS_SOURCE=gee` and see initialization/auth errors, follow the setup checklist in `docs/GEE_SETUP.md`.

**Error: "Address already in use"**
```bash
# Change port in main.py
uvicorn main:app --port 8000
```

**Error: "NOAA server timeout"**
- Check internet connection
- NOAA servers may be temporarily down
- Try again in a few minutes

### Frontend Issues

**Map not loading**
- Check browser console for errors
- Ensure backend is running (`http://localhost:8000`)
- Try different map style (OSM, Dark, Satellite)

**Export not working**
- Check browser allows downloads
- Ensure SheetJS library loaded (check console)

## 📚 Resources

- [NOAA EOG VIIRS Data](https://eogdata.mines.edu/nighttime_light/monthly/)
- [Elvidge et al. (2021) Paper](https://doi.org/10.1016/j.rse.2021.112165)
- [OpenStreetMap Nominatim](https://nominatim.org/)
- [Leaflet.js Documentation](https://leafletjs.com/)
- [D3.js Documentation](https://d3js.org/)

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

This project is **open source for non-commercial use** (personal, educational, and non-profit research). **Commercial use is not permitted** without separate written permission. See [LICENSE](LICENSE) and the [methodology page](frontend/methodology.html#license) for details.

**Repository:** https://github.com/dso6060/viirs-nightlights-analysis-tool

## 🙏 Acknowledgments

- **Data**: NOAA Earth Observation Group
- **Methodology**: Elvidge et al. (2021)
- **Geocoding**: OpenStreetMap / Nominatim
- **Inspiration**: ukRus VIIRS project

## 📧 Contact

For issues or questions:
- Open a GitHub issue
- Check troubleshooting section
- Review API documentation

---

**Built with 🛰️ satellite data and ❤️ for data visualization**







