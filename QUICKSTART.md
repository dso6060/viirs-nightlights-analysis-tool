# 🚀 Quick Start Guide

Get the VIIRS Nightlights Analysis Tool running in 5 minutes!

## Step 1: Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed fastapi-0.104.1 uvicorn-0.24.0 rasterio-1.3.9 ...
```

## Step 2: Start the Backend Server

```bash
python main.py
```

**Expected output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

✅ **Backend is now running!** Leave this terminal open.

> Note: This repository is **real-data only**. Any mock/synthetic data generation used during early testing has been removed.

## Step 3: Open the Frontend

### Option A: Double-click (Easiest)

1. Navigate to `frontend/` folder
2. Double-click `index.html`
3. Your browser will open automatically

### Option B: Local Server (Recommended)

Open a **new terminal** and run:

```bash
cd frontend
python -m http.server 8080
```

Then open: http://localhost:8080

## Step 4: Try Your First Analysis

1. **Search**: Type "Mumbai" in the search box
2. **Date Range**: 
   - Start: January 2019
   - End: December 2024
3. **Click**: "Analyze" button
4. **Wait**: ~30-60 seconds for first-time data fetch
5. **Explore**: Map, graph, and animation!

## 🎯 Example Queries to Try

| City | Country | Interesting Pattern |
|------|---------|-------------------|
| Kyiv | Ukraine | Dramatic drop in 2022 (conflict) |
| Delhi | India | Steady growth 2012-2023 |
| New York | USA | Stable with seasonal variation |
| Gaza | Palestine | Conflict impact visible |
| Shanghai | China | Rapid urbanization |

## 🔥 Pro Tips

1. **Use coordinates** for precise locations:
   ```
   19.0760, 72.8777  (Mumbai)
   52.5200, 13.4050  (Berlin)
   ```

2. **Start with short date ranges** for faster results:
   - 1-2 years loads in ~10 seconds
   - 5+ years takes 30-60 seconds

3. **Try animation** to see temporal changes:
   - Click "Play" button
   - Adjust speed with +/- buttons

4. **Export data** for further analysis:
   - Excel: Full dataset with statistics
   - CSV: Simple format
   - JSON: Raw API response

## ⚠️ Common Issues

### "Connection refused" error

**Problem**: Backend not running  
**Solution**: Start backend with `python main.py`

### "City not found"

**Problem**: Typo or ambiguous name  
**Solution**: Add country, e.g., "Paris, France"

### "Data not available for date"

**Problem**: NOAA data lag (1-2 months)  
**Solution**: Try earlier end date

### Slow response (>60s)

**Problem**: Large date range or first-time city  
**Solution**: 
- Start with 1-2 years
- Data will be cached for next time

## 📊 Understanding the Visualization

### Map View

- **Circle Size**: Larger = higher radiance (more lights)
- **Circle Color**: Yellow (low) → Orange → Red (high)
- **Blue Circle**: Analysis area boundary

### Graph View

- **Blue Line**: Radiance over time
- **Orange Dashed Line**: Current date indicator
- **Toggle**: "Show % Change" checkbox for percentage view

### Animation

- **Play Speed**: 0.5x to 4x
- **Slider**: Manual timeline control
- **Auto-loop**: Starts over at end

## 🎓 Next Steps

1. Read full [README.md](README.md) for detailed documentation
2. Explore API endpoints at http://localhost:8000/docs
3. Try multi-city comparison (coming soon)
4. Deploy to VPS (see README deployment section)

## 🐛 Still Having Issues?

1. Check Python version: `python --version` (need 3.9+)
2. Check port 8000 available: `lsof -i :8000`
3. Check internet connection (needs NOAA access)
4. See full troubleshooting in [README.md](README.md)

---

**Happy analyzing! 🛰️✨**












