import React from 'react';

const heatmapFactors = [
  { key: 'footfall', label: 'Footfall' },
  { key: 'youth', label: 'Youth' },
  { key: 'rent', label: 'Rent' },
  { key: 'access', label: 'Access' },
  { key: 'competition', label: 'Competition' },
  { key: 'flood', label: 'Flood' },
  { key: 'traffic', label: 'Traffic' },
];

const TopLocationsPanel = ({
  areas,
  explanation,
  loadingExplanation,
  onViewDetails,
  heatmapFactors,
  heatmapFactor,
  onHeatmapFactorChange,
  heatmapOpen,
  onToggleHeatmapOpen,
  heatmapEnabled,
  onToggleHeatmapEnabled,
}) => {
  return (
    <div className="h-full flex flex-col gap-6 p-6 bg-surface-container-low rounded-2xl border border-outline-variant/50 shadow-soft overflow-y-auto">
      <div className="bg-surface p-4 rounded-xl border border-outline-variant/30 shadow-sm">
        <button
          type="button"
          onClick={onToggleHeatmapOpen}
          className="w-full flex items-center justify-between gap-3 text-left"
        >
          <div>
            <p className="font-headline text-lg font-semibold text-on-surface">Heatmap Controls</p>
            <p className="text-xs text-on-surface-variant font-body">Click a factor to update the map heat layer.</p>
          </div>
          <span className="material-symbols-outlined text-primary">
            {heatmapOpen ? 'expand_less' : 'expand_more'}
          </span>
        </button>

        {heatmapOpen && (
          <div className="mt-4 space-y-3">
            <button
              type="button"
              onClick={onToggleHeatmapEnabled}
              className={`w-full flex items-center justify-between gap-3 rounded-xl px-3 py-3 text-sm font-body border transition-all duration-200 ${
                heatmapEnabled
                  ? 'bg-emerald-500 text-white border-emerald-500 shadow-md'
                  : 'bg-surface-container-highest text-on-surface border-outline-variant/30 hover:border-outline-variant/60 hover:shadow-sm'
              }`}
            >
              <span className="flex items-center gap-3">
                <span className={`h-3.5 w-3.5 rounded-full ${heatmapEnabled ? 'bg-white' : 'bg-emerald-500'}`} />
                <span className="font-semibold tracking-wide">{heatmapEnabled ? 'Heatmap On' : 'Heatmap Off'}</span>
              </span>
              <span className="material-symbols-outlined text-base">
                {heatmapEnabled ? 'toggle_on' : 'toggle_off'}
              </span>
            </button>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {heatmapFactors.map((factor) => {
              const active = heatmapFactor === factor.key;
              const activeStyle = active
                ? { backgroundColor: factor.color, borderColor: factor.color, boxShadow: `0 10px 24px ${factor.color}33` }
                : undefined;

              return (
                <button
                  key={factor.key}
                  type="button"
                  onClick={() => onHeatmapFactorChange(factor.key)}
                  className={`flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-body border transition-all duration-200 text-left ${
                    active
                      ? 'text-white border-transparent shadow-md ring-2 ring-offset-2 ring-offset-surface-container-low'
                      : 'bg-surface-container-highest text-on-surface border-outline-variant/30 hover:border-outline-variant/60 hover:shadow-sm'
                  }`}
                  style={activeStyle}
                >
                  <span
                    className="h-3.5 w-3.5 rounded-full shrink-0 border border-white/50"
                    style={{ backgroundColor: factor.color }}
                  />
                  <span className="font-semibold tracking-wide">{factor.label}</span>
                </button>
              );
            })}
            </div>
          </div>
        )}
      </div>

      <div>
        <h2 className="font-headline text-2xl font-bold text-on-surface flex items-center gap-2 mb-4">
          <span className="material-symbols-outlined text-primary">analytics</span>
          Top Locations
        </h2>

        {areas && areas.length > 0 ? (
          <div className="space-y-4">
            {areas.slice(0, 3).map((area, idx) => (
              <div key={idx} className="bg-surface p-4 rounded-xl border border-outline-variant/30 shadow-sm">
                <div className="flex justify-between items-center mb-2">
                  <h3 className="font-body font-semibold text-on-surface">
                    {idx + 1}. {area.name || `Location ${idx + 1}`}
                  </h3>
                  <span className="bg-primary/10 text-primary text-xs font-bold px-2 py-1 rounded-md">
                    {(area.score * 100).toFixed(0)}%
                  </span>
                </div>

                <div className="w-full bg-surface-variant rounded-full h-2 mb-3 overflow-hidden">
                  <div
                    className="bg-primary h-2 rounded-full transition-all duration-1000"
                    style={{ width: `${Math.min(100, Math.max(0, area.score * 100))}%` }}
                  ></div>
                </div>

                <p className="font-body text-xs text-on-surface-variant leading-relaxed">
                  {area.reason || 'High compatibility based on spatial parameters.'}
                </p>

                <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] text-on-surface-variant font-body">
                  <div className="flex items-center justify-between bg-surface-container-highest rounded-md px-2 py-1">
                    <span>Footfall</span>
                    <span className="text-on-surface">{area.footfall ?? '-'}</span>
                  </div>
                  <div className="flex items-center justify-between bg-surface-container-highest rounded-md px-2 py-1">
                    <span>Youth</span>
                    <span className="text-on-surface">{area.youth ?? '-'}</span>
                  </div>
                  <div className="flex items-center justify-between bg-surface-container-highest rounded-md px-2 py-1">
                    <span>Rent</span>
                    <span className="text-on-surface">{area.rent ?? '-'}</span>
                  </div>
                  <div className="flex items-center justify-between bg-surface-container-highest rounded-md px-2 py-1">
                    <span>Access</span>
                    <span className="text-on-surface">{area.access ?? '-'}</span>
                  </div>
                  <div className="flex items-center justify-between bg-surface-container-highest rounded-md px-2 py-1">
                    <span>Competition</span>
                    <span className="text-on-surface">{area.competition ?? '-'}</span>
                  </div>
                  <div className="flex items-center justify-between bg-surface-container-highest rounded-md px-2 py-1">
                    <span>Flood</span>
                    <span className="text-on-surface">{area.flood ?? '-'}</span>
                  </div>
                  <div className="flex items-center justify-between bg-surface-container-highest rounded-md px-2 py-1">
                    <span>Traffic</span>
                    <span className="text-on-surface">{area.traffic ?? '-'}</span>
                  </div>
                  <div className="flex items-center justify-between bg-surface-container-highest rounded-md px-2 py-1">
                    <span>Type</span>
                    <span className="text-on-surface">{area.area_type ?? '-'}</span>
                  </div>
                </div>

                {onViewDetails && (
                  <button
                    onClick={() => onViewDetails(area)}
                    className="mt-3 w-full flex items-center justify-center gap-1.5 bg-primary/10 hover:bg-primary/20 text-primary text-xs font-bold font-body py-2 px-3 rounded-lg transition-all duration-200 group"
                  >
                    View Details
                    <span className="material-symbols-outlined text-sm group-hover:translate-x-0.5 transition-transform">arrow_forward</span>
                  </button>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm font-body text-on-surface-variant italic p-4 bg-surface rounded-xl border border-outline-variant/30 text-center">
            No locations identified yet.
          </div>
        )}
      </div>

      <div className="border-t border-outline-variant/30 pt-6">
        <h2 className="font-headline text-2xl font-bold text-on-surface flex items-center gap-2 mb-4">
          <span className="material-symbols-outlined text-tertiary">lightbulb</span>
          Strategic Insight
        </h2>

        <div className="bg-surface p-5 rounded-xl border border-outline-variant/30 shadow-sm font-body text-sm text-on-surface leading-relaxed">
          {loadingExplanation ? (
            <div className="flex items-center gap-2 text-on-surface-variant">
              <span className="material-symbols-outlined animate-spin text-primary">refresh</span>
              Generating insights...
            </div>
          ) : explanation ? (
            <p>{explanation}</p>
          ) : (
            <p className="text-on-surface-variant italic text-center py-4">Waiting for analysis data to generate insights.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default TopLocationsPanel;
