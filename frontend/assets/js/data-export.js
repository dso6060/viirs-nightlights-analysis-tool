/**
 * Data Export Module
 * 
 * Handles export to Excel, CSV, and JSON formats using SheetJS.
 */

export class DataExport {
    constructor() {
        // Check if XLSX library is loaded
        if (typeof XLSX === 'undefined') {
            console.error('SheetJS (XLSX) library not loaded');
        }
    }

    _fmtNumber(value, digits) {
        if (value === null || value === undefined || Number.isNaN(value)) return '';
        if (typeof value !== 'number') return String(value);
        return value.toFixed(digits);
    }

    _nullReason(d) {
        if (d && d.data_quality === 'low' && (d.radiance_corrected == null || d.radiance == null)) {
            return 'Low cloud-free observations (below threshold)';
        }
        return d && d.radiance_corrected == null ? 'Missing/filtered' : '';
    }

    _processingNotes(metadata) {
        const baselineYear = metadata && metadata.baseline_year != null ? metadata.baseline_year : '';
        const minCf = metadata && metadata.min_cf_cvg != null ? metadata.min_cf_cvg : 'server default';

        return [
            ['Processing & disclosure (full)'],
            [''],
            ['Raw radiance', 'Monthly mean VIIRS DNB radiance value for the analysis buffer (nW/cm²/sr).'],
            ['Bias-corrected radiance', 'Elvidge et al. (2021) correction applied to raw radiance using cloud-free observations.'],
            ['Low-quality months → NULL', `If cloud_free_coverage is below MIN_CF_CVG (${minCf}), radiance fields are set to NULL to avoid misleading zeros.`],
            ['% change (map labels)', `For each city and each month-of-year, percent_change = ((bias_corrected - baseline_month) / baseline_month) * 100. Baseline is the first available year in the selected range (often ${baselineYear}).`],
        ];
    }
    
    exportToExcel(data, cityInfo, metadata, filename) {
        // Create workbook
        const wb = XLSX.utils.book_new();
        
        // Sheet 1: Data (raw + processed)
        const processedData = data.map(d => ({
            'Date': d.date,
            'City': d.city,
            'Country': d.country,
            'Latitude': d.latitude,
            'Longitude': d.longitude,
            'Radiance Raw (nW/cm²/sr)': this._fmtNumber(d.radiance, 4),
            'Radiance Bias-Corrected (nW/cm²/sr)': this._fmtNumber(d.radiance_corrected, 4),
            'Percentage Change (%)': this._fmtNumber(d.percentage_change, 2),
            'Cloud Free Coverage': this._fmtNumber(d.cloud_free_coverage, 2),
            'Data Quality': d.data_quality || '',
            'Null Reason': this._nullReason(d)
        }));
        
        const ws1 = XLSX.utils.json_to_sheet(processedData);
        XLSX.utils.book_append_sheet(wb, ws1, 'Data');
        
        // Sheet 2: Metadata
        const metadataSheet = [
            ['VIIRS Nightlights Analysis Tool'],
            [''],
            ['City Information'],
        ];
        
        // Handle both single city and multi-city
        if (Array.isArray(cityInfo)) {
            metadataSheet.push(['Number of Cities', cityInfo.length]);
            cityInfo.forEach((city, index) => {
                metadataSheet.push([`City ${index + 1}`, city.city]);
                metadataSheet.push([`Country ${index + 1}`, city.country]);
                metadataSheet.push([`Latitude ${index + 1}`, city.lat]);
                metadataSheet.push([`Longitude ${index + 1}`, city.lon]);
                metadataSheet.push([`Radius ${index + 1} (km)`, city.radius_km]);
            });
        } else {
            metadataSheet.push(['City', cityInfo.city]);
            metadataSheet.push(['Country', cityInfo.country]);
            metadataSheet.push(['Latitude', cityInfo.lat]);
            metadataSheet.push(['Longitude', cityInfo.lon]);
            metadataSheet.push(['Radius (km)', cityInfo.radius_km]);
        }
        
        metadataSheet.push(
            [''],
            ['Data Information'],
            ['Data Source', (metadata && metadata.data_source) ? metadata.data_source : 'Google Earth Engine (NOAA VIIRS)'],
            ['Bias Correction', 'Elvidge et al. (2021)'],
            ['Baseline Year', metadata.baseline_year],
            ['Total Data Points', metadata.data_points],
            ['Date Range', `${data[0].date} to ${data[data.length - 1].date}`],
            [''],
            ['Export Information'],
            ['Export Date', new Date().toISOString()],
            ['Tool Version', '1.0.0']
        );
        
        const ws2 = XLSX.utils.aoa_to_sheet(metadataSheet);
        XLSX.utils.book_append_sheet(wb, ws2, 'Metadata');
        
        // Sheet 3: Summary Statistics
        const summaryStats = this.calculateSummaryStats(data);
        const ws3 = XLSX.utils.json_to_sheet(summaryStats);
        XLSX.utils.book_append_sheet(wb, ws3, 'Summary');

        // Sheet 4: Processing notes (disclosure)
        const ws4 = XLSX.utils.aoa_to_sheet(this._processingNotes(metadata));
        XLSX.utils.book_append_sheet(wb, ws4, 'Processing Notes');
        
        // Save file
        XLSX.writeFile(wb, `${filename}.xlsx`);
        
        console.log('Excel export completed');
    }
    
    exportToCSV(data, filename) {
        // Convert data to CSV format (includes raw + processed + disclosure notes)
        const headers = [
            'Date',
            'City',
            'Country',
            'Latitude',
            'Longitude',
            'Radiance_Raw',
            'Radiance_BiasCorrected',
            'Percentage_Change',
            'Cloud_Free_Coverage',
            'Data_Quality',
            'Null_Reason'
        ];
        
        const csvRows = [];
        // Notes first (comment lines)
        csvRows.push('# VIIRS Nightlights Analysis Tool — Export');
        csvRows.push('# Columns include raw radiance, bias-corrected radiance, % change, and quality flags.');
        csvRows.push('# Low-quality months may be NULL (not 0) to avoid misleading zeros.');
        csvRows.push('# % change is computed per-city per-month-of-year against the baseline year month.');
        csvRows.push('');
        csvRows.push(headers.join(','));
        
        data.forEach(d => {
            const row = [
                d.date,
                `"${d.city}"`,
                `"${d.country}"`,
                d.latitude,
                d.longitude,
                this._fmtNumber(d.radiance, 4),
                this._fmtNumber(d.radiance_corrected, 4),
                this._fmtNumber(d.percentage_change, 2),
                this._fmtNumber(d.cloud_free_coverage, 2),
                d.data_quality || '',
                `"${this._nullReason(d)}"`
            ];
            csvRows.push(row.join(','));
        });
        
        const csvContent = csvRows.join('\n');
        
        // Download
        this.downloadFile(csvContent, `${filename}.csv`, 'text/csv');
        
        console.log('CSV export completed');
    }
    
    exportToJSON(fullData, filename) {
        const jsonContent = JSON.stringify(fullData, null, 2);
        this.downloadFile(jsonContent, `${filename}.json`, 'application/json');
        
        console.log('JSON export completed');
    }
    
    calculateSummaryStats(data) {
        // Group by year
        const dataByYear = {};
        
        data.forEach(d => {
            const year = d.date.split('-')[0];
            if (!dataByYear[year]) {
                dataByYear[year] = [];
            }
            dataByYear[year].push(d);
        });
        
        // Calculate stats for each year
        const summaryStats = [];
        
        Object.keys(dataByYear).sort().forEach(year => {
            const yearData = dataByYear[year];
            const radiances = yearData.map(d => d.radiance_corrected).filter(v => v != null && !Number.isNaN(v));
            const percentages = yearData.map(d => d.percentage_change).filter(v => v != null && !Number.isNaN(v));
            if (radiances.length === 0 || percentages.length === 0) {
                summaryStats.push({
                    'Year': year,
                    'Count': yearData.length,
                    'Avg Radiance': '',
                    'Min Radiance': '',
                    'Max Radiance': '',
                    'Std Dev Radiance': '',
                    'Avg % Change': '',
                    'Min % Change': '',
                    'Max % Change': '',
                    'Std Dev % Change': ''
                });
                return;
            }
            
            summaryStats.push({
                'Year': year,
                'Count': yearData.length,
                'Avg Radiance': this._fmtNumber(this.mean(radiances), 3),
                'Min Radiance': this._fmtNumber(Math.min(...radiances), 3),
                'Max Radiance': this._fmtNumber(Math.max(...radiances), 3),
                'Std Dev Radiance': this._fmtNumber(this.standardDeviation(radiances), 3),
                'Avg % Change': this._fmtNumber(this.mean(percentages), 2),
                'Min % Change': this._fmtNumber(Math.min(...percentages), 2),
                'Max % Change': this._fmtNumber(Math.max(...percentages), 2),
                'Std Dev % Change': this._fmtNumber(this.standardDeviation(percentages), 2)
            });
        });
        
        return summaryStats;
    }
    
    mean(arr) {
        if (!arr.length) return NaN;
        return arr.reduce((a, b) => a + b, 0) / arr.length;
    }
    
    standardDeviation(arr) {
        if (!arr.length) return NaN;
        const avg = this.mean(arr);
        const squareDiffs = arr.map(value => Math.pow(value - avg, 2));
        const avgSquareDiff = this.mean(squareDiffs);
        return Math.sqrt(avgSquareDiff);
    }
    
    downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        URL.revokeObjectURL(url);
    }
}

