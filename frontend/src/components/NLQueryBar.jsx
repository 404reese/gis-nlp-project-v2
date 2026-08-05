import React, { useState } from 'react';
import maplibregl from 'maplibre-gl';
import { useMapStore } from '../store/mapStore';
import { nlQuery } from '../services/api';

const SRC = 'nl-answer';
const ANSWER_LAYERS = ['nl-answer-pt', 'nl-answer-ln', 'nl-answer-fill', 'nl-answer-outline'];

function fcBounds(fc) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  const walk = (c) => {
    if (typeof c[0] === 'number') {
      const [x, y] = c;
      if (x < minX) minX = x;
      if (y < minY) minY = y;
      if (x > maxX) maxX = x;
      if (y > maxY) maxY = y;
    } else c.forEach(walk);
  };
  (fc.features || []).forEach((f) => f.geometry && walk(f.geometry.coordinates));
  return minX === Infinity ? null : [[minX, minY], [maxX, maxY]];
}

function clearAnswer(map) {
  if (!map) return;
  ANSWER_LAYERS.forEach((id) => map.getLayer(id) && map.removeLayer(id));
  if (map.getSource(SRC)) map.removeSource(SRC);
}

function renderAnswer(map, fc) {
  const type = fc.features?.[0]?.geometry?.type || 'Point';
  ANSWER_LAYERS.forEach((id) => map.getLayer(id) && map.removeLayer(id));
  if (map.getSource(SRC)) map.getSource(SRC).setData(fc);
  else map.addSource(SRC, { type: 'geojson', data: fc });

  if (type.includes('Point')) {
    map.addLayer({
      id: 'nl-answer-pt', type: 'circle', source: SRC,
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 11, 5, 16, 9],
        'circle-color': '#1a1a1a', 'circle-opacity': 0.9,
        'circle-stroke-width': 2.5, 'circle-stroke-color': '#ffd400',
      },
    });
  } else if (type.includes('LineString')) {
    map.addLayer({ id: 'nl-answer-ln', type: 'line', source: SRC,
      paint: { 'line-color': '#ffd400', 'line-width': 3.5, 'line-opacity': 0.9 } });
  } else {
    map.addLayer({ id: 'nl-answer-fill', type: 'fill', source: SRC,
      paint: { 'fill-color': '#ffd400', 'fill-opacity': 0.3 } });
    map.addLayer({ id: 'nl-answer-outline', type: 'line', source: SRC,
      paint: { 'line-color': '#1a1a1a', 'line-width': 1.5 } });
  }

  const b = fcBounds(fc);
  if (b) map.fitBounds(b, { padding: 90, maxZoom: 15, duration: 800 });
}

export default function NLQueryBar() {
  const map = useMapStore((s) => s.map);
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [showSql, setShowSql] = useState(false);

  const submit = async (e) => {
    e?.preventDefault();
    if (!q.trim() || loading) return;
    setLoading(true);
    setResult(null);
    try {
      const r = await nlQuery({ question: q.trim(), cityId: 1 });
      setResult(r);
      if (r.ok && r.answer && map) renderAnswer(map, r.answer);
    } catch (err) {
      setResult({ ok: false, is_clear: true, message: 'Query failed — is the backend running?' });
    } finally {
      setLoading(false);
    }
  };

  const clear = () => {
    setResult(null);
    setQ('');
    clearAnswer(map);
  };

  return (
    <div className="w-[min(620px,72vw)]">
      <form
        onSubmit={submit}
        className="flex items-center gap-2 rounded-full border border-outline-variant/50 bg-surface/95 shadow-soft backdrop-blur px-4 py-2.5"
      >
        <span className="text-on-surface-variant">⌕</span>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Ask a spatial question — e.g. hospitals within 1 km of a metro station"
          className="flex-1 bg-transparent outline-none text-sm font-body text-on-surface placeholder:text-on-surface-variant/70"
        />
        {result && (
          <button type="button" onClick={clear} className="text-xs text-on-surface-variant hover:text-on-surface">
            clear
          </button>
        )}
        <button
          type="submit"
          disabled={loading}
          className="rounded-full bg-primary text-on-primary text-sm font-body px-4 py-1.5 disabled:opacity-50"
        >
          {loading ? '…' : 'Ask'}
        </button>
      </form>

      {result && (
        <div className="mt-2 rounded-2xl border border-outline-variant/50 bg-surface/97 shadow-soft backdrop-blur px-4 py-3">
          {!result.is_clear ? (
            <p className="text-sm font-body text-on-surface">{result.message}</p>
          ) : !result.ok ? (
            <p className="text-sm font-body text-error">{result.message}</p>
          ) : (
            <>
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-body text-on-surface-variant">
                  {result.count} result{result.count === 1 ? '' : 's'} · {result.task_type}
                </span>
                <button
                  onClick={() => setShowSql((v) => !v)}
                  className="text-xs font-body text-primary hover:underline"
                >
                  {showSql ? 'hide SQL' : 'how it was computed'}
                </button>
              </div>
              {result.explanation && (
                <p className="mt-1.5 text-sm font-body text-on-surface leading-relaxed">
                  {result.explanation}
                </p>
              )}
              {showSql && (
                <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-surface-container-highest/70 p-2 text-[11px] leading-snug text-on-surface-variant whitespace-pre-wrap">
                  {result.sql}
                </pre>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
