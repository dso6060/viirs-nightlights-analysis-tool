/**
 * Shared UI thresholds for VIIRS nightlights comparisons.
 * ±40% flags large shocks (e.g. Gaza ~81% drop) while ignoring typical seasonal swings.
 */
export const MOM_CHANGE_THRESHOLD_PCT = 40;

/** Preset clusters: compare each month to the same month in this calendar year. */
export const PRESET_BASELINE_YEAR = '2024';

/** Preset clusters: chart range starts here through latest available month. */
export const PRESET_RANGE_START = '2024-01';

export const PRESET_CLUSTER_SECTIONS = new Set([
    'user-request',
    'gdelt-missile',
    'gdelt-drone',
]);

export function isPresetClusterSection(section) {
    return PRESET_CLUSTER_SECTIONS.has(section);
}
