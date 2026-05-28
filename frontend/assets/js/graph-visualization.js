/**
 * Graph Visualization with D3.js
 * 
 * Timeline graph showing radiance trends over time.
 */

export class GraphVisualization {
    constructor(containerId) {
        this.containerId = containerId;
        this.svg = null;
        this.data = null;
        
        // Dimensions
        this.margin = { top: 20, right: 30, bottom: 50, left: 60 };
    }
    
    initialize(data, dates, cityName) {
        this.data = data;
        this.dates = dates;
        this.cityName = cityName;
        
        // Clear container
        const container = document.getElementById(this.containerId);
        container.innerHTML = '';
        
        // Create SVG
        this.createGraph();
    }
    
    createGraph() {
        const container = document.getElementById(this.containerId);
        const width = container.clientWidth;
        const height = container.clientHeight;
        
        this.width = width - this.margin.left - this.margin.right;
        this.height = height - this.margin.top - this.margin.bottom;
        
        // Create SVG
        this.svg = d3.select(`#${this.containerId}`)
            .append('svg')
            .attr('width', width)
            .attr('height', height)
            .append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);
        
        // Parse dates
        const parseDate = d3.timeParse("%Y-%m");
        this.data.forEach(d => {
            d.parsedDate = parseDate(d.date);
        });
        
        // Create scales
        this.xScale = d3.scaleTime()
            .domain(d3.extent(this.data, d => d.parsedDate))
            .range([0, this.width]);
        
        this.yScale = d3.scaleLinear()
            .domain([0, d3.max(this.data, d => d.radiance_corrected) * 1.1])
            .range([this.height, 0]);
        
        // Add axes
        this.xAxis = d3.axisBottom(this.xScale);
        this.yAxis = d3.axisLeft(this.yScale);
        
        this.svg.append('g')
            .attr('class', 'x-axis axis')
            .attr('transform', `translate(0,${this.height})`)
            .call(this.xAxis);
        
        this.svg.append('g')
            .attr('class', 'y-axis axis')
            .call(this.yAxis);
        
        // Add axis labels
        this.yAxisLabel = this.svg.append('text')
            .attr('class', 'y-axis-label')
            .attr('transform', 'rotate(-90)')
            .attr('y', -45)
            .attr('x', -this.height / 2)
            .attr('text-anchor', 'middle')
            .style('fill', '#b0b0b0')
            .style('font-size', '12px')
            .text('Radiance (nW/cm²/sr)');
        
        this.svg.append('text')
            .attr('class', 'x-axis-label')
            .attr('y', this.height + 40)
            .attr('x', this.width / 2)
            .attr('text-anchor', 'middle')
            .style('fill', '#b0b0b0')
            .style('font-size', '12px')
            .text('Date');
        
        // Add grid lines
        this.svg.append('g')
            .attr('class', 'grid')
            .attr('opacity', 0.1)
            .call(d3.axisLeft(this.yScale)
                .tickSize(-this.width)
                .tickFormat('')
            );
        
        // Draw lines for each city
        this.line = d3.line()
            .x(d => this.xScale(d.parsedDate))
            .y(d => this.yScale(d.radiance_corrected));
        
        // Group data by city
        const cityGroups = d3.group(this.data, d => d.city);
        const colors = ['#1e88e5', '#e85d00', '#43a047', '#d32f2f', '#7b1fa2'];
        
        // Draw a line for each city
        this.linePaths = [];
        this.cityLabels = [];
        cityGroups.forEach((cityData, cityName) => {
            const colorIndex = Array.from(cityGroups.keys()).indexOf(cityName);
            const color = colors[colorIndex % colors.length];
            
            const linePath = this.svg.append('path')
                .datum(cityData)
                .attr('class', 'line')
                .attr('fill', 'none')
                .attr('stroke', color)
                .attr('stroke-width', 2.5)
                .attr('d', this.line);
            
            this.linePaths.push({ path: linePath, city: cityName, color: color });
            
            // Add city label at the end of the line (like ukRus)
            const lastPoint = cityData[cityData.length - 1];
            const label = this.svg.append('text')
                .attr('class', 'city-label')
                .attr('x', this.xScale(lastPoint.parsedDate) + 8)
                .attr('y', this.yScale(lastPoint.radiance_corrected))
                .attr('text-anchor', 'start')
                .attr('dominant-baseline', 'middle')
                .style('fill', color)
                .style('font-size', '12px')
                .style('font-weight', 'bold')
                .style('pointer-events', 'none')
                .text(cityName);
            
            this.cityLabels.push({ label: label, city: cityName, color: color });
        });
        
        // Add dots colored by city
        this.dots = this.svg.selectAll('.dot')
            .data(this.data)
            .enter()
            .append('circle')
            .attr('class', 'dot')
            .attr('cx', d => this.xScale(d.parsedDate))
            .attr('cy', d => this.yScale(d.radiance_corrected))
            .attr('r', 4)
            .attr('fill', d => {
                const cityIndex = Array.from(cityGroups.keys()).indexOf(d.city);
                return colors[cityIndex % colors.length];
            })
            .attr('stroke', '#fff')
            .attr('stroke-width', 1.5)
            .on('mouseover', (event, d) => this.showTooltip(event, d))
            .on('mouseout', () => this.hideTooltip());
        
        // Add vertical line indicator (for current date)
        this.currentDateLine = this.svg.append('line')
            .attr('class', 'current-date-line')
            .attr('y1', 0)
            .attr('y2', this.height)
            .attr('stroke', '#ff6f00')
            .attr('stroke-width', 2)
            .attr('stroke-dasharray', '5,5')
            .style('display', 'none');
    }
    
    updateTimeline(currentDate) {
        // Parse current date
        const parseDate = d3.timeParse("%Y-%m");
        const parsedCurrentDate = parseDate(currentDate);
        
        // Update vertical line position
        if (this.currentDateLine) {
            this.currentDateLine
                .attr('x1', this.xScale(parsedCurrentDate))
                .attr('x2', this.xScale(parsedCurrentDate))
                .style('display', 'block');
        }
    }
    
    
    showTooltip(event, d) {
        // Remove existing tooltip
        d3.selectAll('.tooltip-d3').remove();
        
        // Create tooltip
        const tooltip = d3.select('body')
            .append('div')
            .attr('class', 'tooltip-d3')
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 10) + 'px');
        
        tooltip.html(`
            <strong>${d.city}</strong><br>
            <strong>Date:</strong> ${d.date}<br>
            <strong>Radiance:</strong> ${d.radiance_corrected.toFixed(3)} nW/cm²/sr
        `);
    }
    
    hideTooltip() {
        d3.selectAll('.tooltip-d3').remove();
    }
    
    focusOnCity(cityName) {
        // Highlight the selected city line and dim others
        if (this.linePaths) {
            this.linePaths.forEach(linePath => {
                if (linePath.city === cityName) {
                    linePath.path
                        .attr('stroke-width', 4)
                        .attr('opacity', 1);
                } else {
                    linePath.path
                        .attr('stroke-width', 1.5)
                        .attr('opacity', 0.3);
                }
            });
        }
        
        // Highlight city label
        if (this.cityLabels) {
            this.cityLabels.forEach(cityLabel => {
                if (cityLabel.city === cityName) {
                    cityLabel.label
                        .style('font-size', '14px')
                        .style('opacity', 1);
                } else {
                    cityLabel.label
                        .style('font-size', '10px')
                        .style('opacity', 0.3);
                }
            });
        }
        
        // Update dots opacity
        if (this.dots) {
            this.dots.style('opacity', d => d.city === cityName ? 1 : 0.3);
        }
    }
    
    showAllCities() {
        // Reset all lines to normal appearance
        if (this.linePaths) {
            this.linePaths.forEach(linePath => {
                linePath.path
                    .attr('stroke-width', 2.5)
                    .attr('opacity', 1);
            });
        }
        
        // Reset city labels
        if (this.cityLabels) {
            this.cityLabels.forEach(cityLabel => {
                cityLabel.label
                    .style('font-size', '12px')
                    .style('opacity', 1);
            });
        }
        
        // Reset dots
        if (this.dots) {
            this.dots.style('opacity', 1);
        }
    }
}

