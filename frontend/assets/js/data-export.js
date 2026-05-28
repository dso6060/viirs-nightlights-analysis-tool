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
    
    exportToExcel(data, cityInfo, metadata, filename) {
        // Create workbook
        const wb = XLSX.utils.book_new();
        
        // Sheet 1: Processed Data
        const processedData = data.map(d => ({
            'Date': d.date,
            'City': d.city,
            'Country': d.country,
            'Latitude': d.latitude,
            'Longitude': d.longitude,
            'Radiance (nW/cm²/sr)': d.radiance.toFixed(4),
            'Radiance Corrected (nW/cm²/sr)': d.radiance_corrected.toFixed(4),
            'Percentage Change (%)': d.percentage_change.toFixed(2),
            'Cloud Free Coverage (%)': d.cloud_free_coverage ? d.cloud_free_coverage.toFixed(2) : 'N/A'
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
            ['Data Source', 'NOAA Earth Observation Group'],
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
        
        // Save file
        XLSX.writeFile(wb, `${filename}.xlsx`);
        
        console.log('Excel export completed');
    }
    
    exportToCSV(data, filename) {
        // Convert data to CSV format
        const headers = [
            'Date',
            'City',
            'Country',
            'Latitude',
            'Longitude',
            'Radiance',
            'Radiance_Corrected',
            'Percentage_Change',
            'Cloud_Free_Coverage'
        ];
        
        const csvRows = [headers.join(',')];
        
        data.forEach(d => {
            const row = [
                d.date,
                `"${d.city}"`,
                `"${d.country}"`,
                d.latitude,
                d.longitude,
                d.radiance.toFixed(4),
                d.radiance_corrected.toFixed(4),
                d.percentage_change.toFixed(2),
                d.cloud_free_coverage ? d.cloud_free_coverage.toFixed(2) : 'N/A'
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
            
            const radiances = yearData.map(d => d.radiance_corrected);
            const percentages = yearData.map(d => d.percentage_change);
            
            summaryStats.push({
                'Year': year,
                'Count': yearData.length,
                'Avg Radiance': this.mean(radiances).toFixed(3),
                'Min Radiance': Math.min(...radiances).toFixed(3),
                'Max Radiance': Math.max(...radiances).toFixed(3),
                'Std Dev Radiance': this.standardDeviation(radiances).toFixed(3),
                'Avg % Change': this.mean(percentages).toFixed(2),
                'Min % Change': Math.min(...percentages).toFixed(2),
                'Max % Change': Math.max(...percentages).toFixed(2),
                'Std Dev % Change': this.standardDeviation(percentages).toFixed(2)
            });
        });
        
        return summaryStats;
    }
    
    mean(arr) {
        return arr.reduce((a, b) => a + b, 0) / arr.length;
    }
    
    standardDeviation(arr) {
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

