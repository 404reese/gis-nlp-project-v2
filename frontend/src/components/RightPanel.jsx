import React from 'react';

const RightPanel = ({ areas, explanation, loadingExplanation }) => {
  return (
    <div className="h-full flex flex-col gap-6 p-6 bg-surface-container-low rounded-2xl border border-outline-variant/50 shadow-soft overflow-y-auto">
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
                
                {/* Progress Bar */}
                <div className="w-full bg-surface-variant rounded-full h-2 mb-3 overflow-hidden">
                  <div
                    className="bg-primary h-2 rounded-full transition-all duration-1000"
                    style={{ width: `${Math.min(100, Math.max(0, area.score * 100))}%` }}
                  ></div>
                </div>
                
                <p className="font-body text-xs text-on-surface-variant leading-relaxed">
                  {area.reason || "High compatibility based on spatial parameters."}
                </p>
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

export default RightPanel;
