import React from 'react';
import { useMapStore } from '../store/mapStore';
import { LAYER_DEFS, LAYER_GROUPS } from '../config/layers';

function LayerRow({ def }) {
  const st = useMapStore((s) => s.layerState[def.id]);
  const available = useMapStore((s) => s.available[def.id]);
  const toggle = useMapStore((s) => s.toggle);
  const setOpacity = useMapStore((s) => s.setOpacity);
  const catalogLoaded = useMapStore((s) => Object.keys(s.available).length > 0);

  const disabled = catalogLoaded && !available;

  return (
    <div className={`rounded-xl border border-outline-variant/40 p-2.5 ${disabled ? 'opacity-40' : ''}`}>
      <div className="flex items-center justify-between gap-2">
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={!!st?.visible}
            disabled={disabled}
            onChange={() => toggle(def.id)}
            className="accent-primary"
          />
          <span className="text-sm font-body text-on-surface">{def.label}</span>
        </label>
        {disabled && <span className="text-[10px] text-on-surface-variant">no data</span>}
      </div>

      {st?.visible && !disabled && (
        <>
          <input
            type="range"
            min="0.1"
            max="1"
            step="0.05"
            value={st.opacity}
            onChange={(e) => setOpacity(def.id, parseFloat(e.target.value))}
            className="w-full mt-2 accent-primary"
          />
          <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1.5">
            {def.legend.map((l) => (
              <span key={l.label} className="inline-flex items-center gap-1 text-[11px] text-on-surface-variant">
                <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: l.color }} />
                {l.label}
              </span>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default function LayerPanel() {
  return (
    <div className="space-y-4">
      {LAYER_GROUPS.map((group) => (
        <div key={group}>
          <div className="text-xs uppercase tracking-wide text-on-surface-variant mb-2">{group}</div>
          <div className="space-y-2">
            {LAYER_DEFS.filter((d) => d.group === group).map((def) => (
              <LayerRow key={def.id} def={def} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
