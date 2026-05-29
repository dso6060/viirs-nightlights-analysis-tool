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
        this.cityColors = {};
        this._visibleCities = null;
        this.margin = { top: 20, right: 30, bottom: 50, left: 60 };
    }

    initialize(data, dates, cityName) {
        this.data = data;
        this.dates = dates;
        this.cityName = cityName;

        const container = document.getElementById(this.containerId);
        container.innerHTML = '';

        this.createGraph();
    }

    createGraph() {
        const container = document.getElementById(this.containerId);
        const width = container.clientWidth;
        const height = container.clientHeight;

        this.width = width - this.margin.left - this.margin.right;
        this.height = height - this.margin.top - this.margin.bottom;

        this.svg = d3
            .select(`#${this.containerId}`)
            .append('svg')
            .attr('width', width)
            .attr('height', height)
            .append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);

        const parseDate = d3.timeParse('%Y-%m');
        this.data.forEach((d) => {
            d.parsedDate = parseDate(d.date);
        });

        const validData = this.data.filter((d) => d.radiance_corrected != null && d.parsedDate);
        const datedData = this.data.filter((d) => d.parsedDate);

        this.xScale = d3
            .scaleTime()
            .domain(d3.extent(datedData, (d) => d.parsedDate))
            .range([0, this.width]);

        const yMax = d3.max(validData, (d) => d.radiance_corrected);
        this.yScale = d3
            .scaleLinear()
            .domain([0, (yMax || 1) * 1.1])
            .range([this.height, 0]);

        this.xAxis = d3.axisBottom(this.xScale);
        this.yAxis = d3.axisLeft(this.yScale);

        this.svg.append('g').attr('class', 'x-axis axis').attr('transform', `translate(0,${this.height})`).call(this.xAxis);

        this.svg.append('g').attr('class', 'y-axis axis').call(this.yAxis);

        this.svg
            .append('text')
            .attr('class', 'y-axis-label')
            .attr('transform', 'rotate(-90)')
            .attr('y', -45)
            .attr('x', -this.height / 2)
            .attr('text-anchor', 'middle')
            .style('fill', '#b0b0b0')
            .style('font-size', '12px')
            .text('Radiance (nW/cm²/sr)');

        this.svg
            .append('text')
            .attr('class', 'x-axis-label')
            .attr('y', this.height + 40)
            .attr('x', this.width / 2)
            .attr('text-anchor', 'middle')
            .style('fill', '#b0b0b0')
            .style('font-size', '12px')
            .text('Date');

        this.svg
            .append('g')
            .attr('class', 'grid')
            .attr('opacity', 0.1)
            .call(d3.axisLeft(this.yScale).tickSize(-this.width).tickFormat(''));

        this.line = d3
            .line()
            .defined((d) => d.radiance_corrected != null && d.parsedDate != null)
            .x((d) => this.xScale(d.parsedDate))
            .y((d) => this.yScale(d.radiance_corrected));

        const cityGroups = d3.group(validData, (d) => d.city);
        const colors = ['#1e88e5', '#e85d00', '#43a047', '#d32f2f', '#7b1fa2'];

        this.linePaths = [];
        this.cityLabels = [];
        this.cityColors = {};

        cityGroups.forEach((cityData, cityNameKey) => {
            const colorIndex = Array.from(cityGroups.keys()).indexOf(cityNameKey);
            const color = colors[colorIndex % colors.length];
            this.cityColors[cityNameKey] = color;

            const linePath = this.svg
                .append('path')
                .datum(cityData)
                .attr('class', 'line')
                .attr('fill', 'none')
                .attr('stroke', color)
                .attr('stroke-width', 2.5)
                .attr('d', this.line);

            this.linePaths.push({ path: linePath, city: cityNameKey, color });

            const lastPoint = cityData[cityData.length - 1];
            const label = this.svg
                .append('text')
                .attr('class', 'city-label')
                .attr('x', this.xScale(lastPoint.parsedDate) + 8)
                .attr('y', this.yScale(lastPoint.radiance_corrected))
                .attr('text-anchor', 'start')
                .attr('dominant-baseline', 'middle')
                .style('fill', color)
                .style('font-size', '12px')
                .style('font-weight', 'bold')
                .style('pointer-events', 'none')
                .text(cityNameKey);

            this.cityLabels.push({ label, city: cityNameKey, color });
        });

        this.dots = this.svg
            .selectAll('.dot')
            .data(validData)
            .enter()
            .append('circle')
            .attr('class', 'dot')
            .attr('cx', (d) => this.xScale(d.parsedDate))
            .attr('cy', (d) => this.yScale(d.radiance_corrected))
            .attr('r', 4)
            .attr('fill', (d) => this.cityColors[d.city] || '#1e88e5')
            .attr('stroke', '#fff')
            .attr('stroke-width', 1.5)
            .on('mouseover', (event, d) => this.showTooltip(event, d))
            .on('mouseout', () => this.hideTooltip());

        this.currentDateLine = this.svg
            .append('line')
            .attr('class', 'current-date-line')
            .attr('y1', 0)
            .attr('y2', this.height)
            .attr('stroke', '#ff6f00')
            .attr('stroke-width', 2)
            .attr('stroke-dasharray', '5,5')
            .style('display', 'none');

        this.currentMonthLayer = this.svg.append('g').attr('class', 'current-month-layer');
    }

    getLastValidPoint(cityName, beforeDate) {
        const parseDate = d3.timeParse('%Y-%m');
        const target = parseDate(beforeDate);
        const cityRows = this.data
            .filter((d) => d.city === cityName && d.radiance_corrected != null && d.parsedDate)
            .filter((d) => d.parsedDate <= target)
            .sort((a, b) => a.parsedDate - b.parsedDate);
        return cityRows.length ? cityRows[cityRows.length - 1] : null;
    }

    updateTimeline(currentDate, monthStatus = {}) {
        const parseDate = d3.timeParse('%Y-%m');
        const parsedCurrentDate = parseDate(currentDate);

        if (this.currentDateLine && parsedCurrentDate) {
            const x = this.xScale(parsedCurrentDate);
            this.currentDateLine.attr('x1', x).attr('x2', x).style('display', 'block');
        }

        if (this.dots) {
            this.dots
                .attr('r', (d) => (d.date === currentDate ? 5 : 4))
                .attr('opacity', (d) => {
                    if (!this._isCityVisible(d.city)) {
                        return 0;
                    }
                    if (d.date === currentDate) {
                        return 1;
                    }
                    return 0.45;
                });
        }

        if (this.linePaths) {
            this.linePaths.forEach((linePath) => {
                linePath.path.attr('opacity', 0.9);
            });
        }

        this.renderCurrentMonthGlyphs(currentDate, monthStatus);
        this.updatePlaybackHint(currentDate, monthStatus);
    }

    renderCurrentMonthGlyphs(currentDate, monthStatus) {
        if (!this.currentMonthLayer) {
            return;
        }

        this.currentMonthLayer.selectAll('*').remove();

        const parseDate = d3.timeParse('%Y-%m');
        const parsedCurrentDate = parseDate(currentDate);
        if (!parsedCurrentDate) {
            return;
        }

        const x = this.xScale(parsedCurrentDate);
        const missingCities = monthStatus.missingAtCurrent || [];

        missingCities.forEach((cityName) => {
            const last = this.getLastValidPoint(cityName, currentDate);
            if (!last) {
                return;
            }

            const color = this.cityColors[cityName] || '#9e9e9e';
            const y = this.yScale(last.radiance_corrected);

            this.currentMonthLayer
                .append('circle')
                .attr('class', 'null-month-glyph')
                .attr('data-city', cityName)
                .attr('cx', x)
                .attr('cy', y)
                .attr('r', 6)
                .attr('fill', 'none')
                .attr('stroke', color)
                .attr('stroke-width', 2)
                .attr('stroke-dasharray', '3,2')
                .attr('opacity', 0.85)
                .attr('title', `${cityName}: no observation in ${currentDate} (low cloud coverage)`);
        });
    }

    updatePlaybackHint(currentDate, monthStatus) {
        const el = document.getElementById('playback-data-hint');
        if (!el) {
            return;
        }

        const missing = monthStatus.missingAtCurrent || [];
        const validCount = monthStatus.validCount ?? 0;

        if (missing.length === 0) {
            el.hidden = true;
            el.textContent = '';
            return;
        }

        el.hidden = false;
        if (monthStatus.allMissing) {
            el.textContent = `${currentDate}: no cloud-free VIIRS observation this month — timeline continues; map shows placeholders (not zero).`;
        } else if (missing.length === 1) {
            el.textContent = `${currentDate}: ${missing[0]} — no observation (low clouds). Other cities: ${validCount} with data.`;
        } else if (missing.length <= 3) {
            el.textContent = `${currentDate}: no data for ${missing.join(', ')} (low clouds).`;
        } else {
            el.textContent = `${currentDate}: ${missing.length} places have no observation this month (low cloud coverage).`;
        }
    }

    _isCityVisible(cityName) {
        if (!this._visibleCities) {
            return true;
        }
        return this._visibleCities.includes(cityName);
    }

    updateVisibleCities(visibleCities) {
        if (!this.linePaths) {
            return;
        }

        this._visibleCities = visibleCities;
        const visibleSet = Array.isArray(visibleCities) ? new Set(visibleCities) : null;

        const isVisible = (cityName) => {
            if (!visibleSet) {
                return true;
            }
            return visibleSet.has(cityName);
        };

        this.linePaths.forEach((linePath) => {
            const show = isVisible(linePath.city);
            linePath.path.style('display', show ? null : 'none').attr('opacity', show ? 0.9 : 0);
        });

        if (this.cityLabels) {
            this.cityLabels.forEach((cityLabel) => {
                const show = isVisible(cityLabel.city);
                cityLabel.label.style('display', show ? null : 'none').style('opacity', show ? 1 : 0);
            });
        }

        if (this.dots) {
            this.dots
                .style('display', (d) => (isVisible(d.city) ? null : 'none'))
                .style('opacity', (d) => (isVisible(d.city) ? null : 0));
        }

        if (this.currentMonthLayer) {
            this.currentMonthLayer.selectAll('.null-month-glyph').style('display', function () {
                const city = d3.select(this).attr('data-city');
                return isVisible(city) ? null : 'none';
            });
        }
    }

    showTooltip(event, d) {
        d3.selectAll('.tooltip-d3').remove();

        const tooltip = d3
            .select('body')
            .append('div')
            .attr('class', 'tooltip-d3')
            .style('left', `${event.pageX + 10}px`)
            .style('top', `${event.pageY - 10}px`);

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
        if (this.linePaths) {
            this.linePaths.forEach((linePath) => {
                if (linePath.city === cityName) {
                    linePath.path.attr('stroke-width', 4).attr('opacity', 1);
                } else {
                    linePath.path.attr('stroke-width', 1.5).attr('opacity', 0.3);
                }
            });
        }

        if (this.cityLabels) {
            this.cityLabels.forEach((cityLabel) => {
                if (cityLabel.city === cityName) {
                    cityLabel.label.style('font-size', '14px').style('opacity', 1);
                } else {
                    cityLabel.label.style('font-size', '10px').style('opacity', 0.3);
                }
            });
        }

        if (this.dots) {
            this.dots.style('opacity', (d) => (d.city === cityName ? 1 : 0.3));
        }
    }

    showAllCities() {
        if (this.linePaths) {
            this.linePaths.forEach((linePath) => {
                linePath.path.attr('stroke-width', 2.5).attr('opacity', 0.9);
            });
        }

        if (this.cityLabels) {
            this.cityLabels.forEach((cityLabel) => {
                cityLabel.label.style('font-size', '12px').style('opacity', 1);
            });
        }

        if (this.dots) {
            this.dots.style('opacity', null);
        }
    }
}
