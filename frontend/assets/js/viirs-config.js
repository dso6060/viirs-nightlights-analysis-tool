/**
 * Shared UI thresholds for VIIRS nightlights comparisons.
 * ±40% flags large shocks (e.g. Gaza ~81% drop) while ignoring typical seasonal swings.
 */
export const MOM_CHANGE_THRESHOLD_PCT = 40;

/** Preset clusters (user-request / GDELT) use same-calendar-month baseline across prior years. */
export const SEASONAL_BASELINE_YEARS = 3;

export const PRESET_CLUSTER_SECTIONS = new Set([
    'user-request',
    'gdelt-missile',
    'gdelt-drone',
]);

export function isPresetClusterSection(section) {
    return PRESET_CLUSTER_SECTIONS.has(section);
}
