import React from 'react';
import { Link } from 'react-router-dom';
import MapCanvas from '../components/MapCanvas';
import { useMapStore } from '../store/mapStore';
import { HAS_MAPTILER } from '../config/mapConfig';

/**
 * Studio — the Felt-like workspace shell (M0).
 * A single full-screen MapLibre map, a layer panel (populated in M1+),
 * and an NL query bar (wired to the engine in M2). Structure is in place now
 * so later phases only fill panels, not rebuild layout.
 */
const Studio = () => {
  const ready = useMapStore((s) => s.ready);
  const layers = useMapStore((s) => s.layers);

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-surface">
      {/* Map fills the whole viewport */}
      <MapCanvas />

      {/* Left: layer panel */}
      <aside className="absolute top-4 left-4 bottom-4 z-10 w-72 flex flex-col rounded-2xl border border-outline-variant/50 bg-surface/95 shadow-soft backdrop-blur">
        <header className="flex items-center justify-between px-4 py-3 border-b border-outline-variant/40">
          <Link to="/" className="font-headline text-lg text-on-surface">Sentinel</Link>
          <span className="text-xs font-body text-on-surface-variant">Studio</span>
        </header>

        <div className="px-4 py-3 border-b border-outline-variant/40">
          <div className="text-xs uppercase tracking-wide text-on-surface-variant mb-1">City</div>
          <div className="font-body text-on-surface font-medium">Mumbai, India</div>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-3">
          <div className="text-xs uppercase tracking-wide text-on-surface-variant mb-2">Layers</div>
          {layers.length === 0 ? (
            <div className="rounded-xl border border-dashed border-outline-variant/60 p-4 text-sm font-body text-on-surface-variant">
              No data layers yet. Real layers (admin boundaries, roads, POIs,
              real-estate) load in the next phase.
            </div>
          ) : (
            <ul className="space-y-2">
              {layers.map((l) => (
                <li key={l.id} className="text-sm font-body text-on-surface">{l.label}</li>
              ))}
            </ul>
          )}
        </div>

        <footer className="px-4 py-3 border-t border-outline-variant/40 text-xs font-body text-on-surface-variant">
          Basemap: {HAS_MAPTILER ? 'MapTiler' : 'MapLibre demo (no key)'} ·{' '}
          {ready ? 'ready' : 'loading…'}
        </footer>
      </aside>

      {/* Top-center: NL query bar (wired to the engine in M2) */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 w-[min(560px,60vw)]">
        <div className="flex items-center gap-2 rounded-full border border-outline-variant/50 bg-surface/95 shadow-soft backdrop-blur px-4 py-2.5">
          <span className="text-on-surface-variant">⌕</span>
          <input
            disabled
            placeholder="Ask a spatial question… (enabled in the query-engine phase)"
            className="flex-1 bg-transparent outline-none text-sm font-body text-on-surface placeholder:text-on-surface-variant/70"
          />
        </div>
      </div>
    </div>
  );
};

export default Studio;
