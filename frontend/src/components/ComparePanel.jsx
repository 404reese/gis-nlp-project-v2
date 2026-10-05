import React, { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import { useMapStore } from '../store/mapStore';
import { siteEval, businessEstimate } from '../services/api';

const PIN_COLORS = { A: '#c2652a', B: '#2a7ac2', C: '#2a9d6a' };

const inr = (v) => {
  if (v == null) return '—';
  const sign = v < 0 ? '-' : '';
  const a = Math.abs(v);
  if (a >= 1e7) return `${sign}₹${(a / 1e7).toFixed(2)} Cr`;
  if (a >= 1e5) return `${sign}₹${(a / 1e5).toFixed(1)} L`;
  return `${sign}₹${Math.round(a).toLocaleString('en-IN')}`;
};
const dist = (m) => (m == null ? '—' : m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toFixed(1)} km`);

const baseScenario = (est) => est?.revenue?.scenarios?.find((s) => s.name === 'Base');
const nearest = (site, modes) => {
  const t = (site?.transit || []).filter((x) => modes.includes(x.mode)).sort((a, b) => a.distance_m - b.distance_m)[0];
  return t ? t.distance_m : null;
};
const rentOf = (est) => est?.monthly?.find((x) => x.item === 'Rent')?.amount ?? null;

// better: 'high' | 'low' — which direction wins. value: number used for ranking (null = unranked).
const ROWS = [
  { label: 'Median ₹/sqft (sale)', better: 'low', num: (r) => r.site?.comps?.median_psf,
    show: (r) => (r.site?.comps?.median_psf != null ? `₹${r.site.comps.median_psf.toLocaleString('en-IN')}` : '—') },
  { label: 'vs city median', better: 'low', num: (r) => r.site?.vs_city?.delta_pct,
    show: (r) => (r.site?.vs_city ? `${r.site.vs_city.delta_pct > 0 ? '+' : ''}${r.site.vs_city.delta_pct}%` : '—') },
  { label: 'Nearest metro / rail', better: 'low', num: (r) => nearest(r.site, ['metro', 'rail']), show: (r) => dist(nearest(r.site, ['metro', 'rail'])) },
  { label: 'Amenities within radius', better: 'high',
    num: (r) => (r.site ? Object.values(r.site.amenities || {}).reduce((a, b) => a + b, 0) : null),
    show: (r) => (r.site ? Object.values(r.site.amenities || {}).reduce((a, b) => a + b, 0) : '—') },
  { label: 'Safety score', better: 'high', num: (r) => r.site?.safety?.safety_score, show: (r) => (r.site?.safety?.safety_score ?? '—') },
  { label: 'Competitors within 1 km', better: 'low', num: (r) => r.est?.revenue?.drivers?.competitors_1km,
    show: (r) => r.est?.revenue?.drivers?.competitors_1km ?? '—', group: 'Business' },
  { label: 'Monthly rent (est.)', better: 'low', num: (r) => rentOf(r.est), show: (r) => inr(rentOf(r.est)) },
  { label: 'Total to start', better: 'low', num: (r) => r.est?.totals?.startup_total, show: (r) => inr(r.est?.totals?.startup_total) },
  { label: 'Revenue / month (base)', better: 'high', num: (r) => baseScenario(r.est)?.monthly_revenue, show: (r) => inr(baseScenario(r.est)?.monthly_revenue) },
  { label: 'Profit / month (base)', better: 'high', num: (r) => baseScenario(r.est)?.monthly_profit, show: (r) => inr(baseScenario(r.est)?.monthly_profit) },
  { label: 'Payback (base)', better: 'low', num: (r) => baseScenario(r.est)?.payback_months,
    show: (r) => { const s = baseScenario(r.est); return !s ? '—' : s.payback_months != null ? `${s.payback_months} mo` : 'not reached'; } },
];

function winners(row, results) {
  const vals = results.map((r) => row.num(r));
  const valid = vals.filter((v) => typeof v === 'number');
  if (valid.length < 2) return new Set();
  const best = row.better === 'high' ? Math.max(...valid) : Math.min(...valid);
  if (valid.every((v) => v === best)) return new Set();
  return new Set(vals.map((v, i) => (v === best ? i : -1)).filter((i) => i >= 0));
}

export default function ComparePanel() {
  const map = useMapStore((s) => s.map);
  const pins = useMapStore((s) => s.pins);
  const removePin = useMapStore((s) => s.removePin);
  const clearPins = useMapStore((s) => s.clearPins);

  const [open, setOpen] = useState(false);
  const [type, setType] = useState('cafe');
  const [tier, setTier] = useState('standard');
  const [results, setResults] = useState({}); // label -> {site, est, error}
  const [loading, setLoading] = useState(false);
  const markers = useRef({});

  // Numbered map markers for each pinned spot.
  useEffect(() => {
    if (!map) return;
    const live = new Set(pins.map((p) => p.label));
    Object.keys(markers.current).forEach((l) => {
      if (!live.has(l)) {
        markers.current[l].remove();
        delete markers.current[l];
      }
    });
    pins.forEach((p) => {
      if (markers.current[p.label]) return;
      const el = document.createElement('div');
      el.textContent = p.label;
      el.style.cssText = `width:26px;height:26px;border-radius:50%;background:${PIN_COLORS[p.label]};color:#fff;
        font:700 13px system-ui;display:flex;align-items:center;justify-content:center;border:2px solid #fff;
        box-shadow:0 1px 4px rgba(0,0,0,.4)`;
      markers.current[p.label] = new maplibregl.Marker({ element: el }).setLngLat([p.lng, p.lat]).addTo(map);
    });
  }, [map, pins]);

  useEffect(() => () => Object.values(markers.current).forEach((m) => m.remove()), []);

  // Pins change, or business type/tier change -> results are stale.
  useEffect(() => { setResults({}); }, [type, tier]);

  const run = async () => {
    if (loading || pins.length < 2) return;
    setLoading(true);
    const out = {};
    await Promise.all(
      pins.map(async (p) => {
        try {
          const [site, est] = await Promise.all([
            siteEval({ lat: p.lat, lng: p.lng }),
            businessEstimate({ businessType: type.trim() || 'cafe', lat: p.lat, lng: p.lng, tier }),
          ]);
          out[p.label] = { site, est };
        } catch (e) {
          out[p.label] = { error: true };
        }
      })
    );
    setResults(out);
    setLoading(false);
  };

  // Drop results of removed pins.
  useEffect(() => {
    setResults((r) => Object.fromEntries(Object.entries(r).filter(([l]) => pins.some((p) => p.label === l))));
  }, [pins]);

  if (pins.length === 0) return null;

  const rows = pins.map((p) => results[p.label] || {});
  const haveResults = pins.every((p) => results[p.label] && !results[p.label].error);

  return (
    <>
      {/* Tray */}
      <div className="absolute bottom-4 left-1/2 z-20 flex -translate-x-1/2 items-center gap-2 rounded-full border border-outline-variant/50 bg-surface/95 px-3 py-2 shadow-soft backdrop-blur">
        <span className="text-xs font-body text-on-surface-variant">Compare</span>
        {pins.map((p) => (
          <span
            key={p.label}
            className="flex items-center gap-1 rounded-full border border-outline-variant/50 py-0.5 pl-1 pr-2 text-xs font-body text-on-surface"
          >
            <span className="flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-bold text-white" style={{ background: PIN_COLORS[p.label] }}>
              {p.label}
            </span>
            <span className="max-w-[110px] truncate">{p.locality}</span>
            <button onClick={() => removePin(p.label)} className="text-on-surface-variant hover:text-on-surface">✕</button>
          </span>
        ))}
        <button
          onClick={() => setOpen(true)}
          disabled={pins.length < 2}
          title={pins.length < 2 ? 'Pin at least 2 locations' : ''}
          className="rounded-full bg-primary px-3 py-1 text-xs font-body text-on-primary disabled:opacity-40"
        >
          Compare ({pins.length})
        </button>
        <button onClick={clearPins} className="text-xs font-body text-on-surface-variant hover:text-on-surface">Clear</button>
      </div>

      {/* Modal */}
      {open && (
        <div className="absolute inset-0 z-30 flex items-center justify-center bg-black/30 p-4" onClick={() => setOpen(false)}>
          <div
            className="flex max-h-full w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-outline-variant/50 bg-surface shadow-soft"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="flex items-center justify-between gap-3 border-b border-outline-variant/40 px-5 py-3">
              <div className="font-headline text-lg text-on-surface">Compare locations</div>
              <div className="flex items-center gap-2">
                <input
                  value={type}
                  onChange={(e) => setType(e.target.value)}
                  placeholder="business type"
                  className="w-36 rounded-lg border border-outline-variant/50 bg-surface px-2 py-1 text-sm font-body text-on-surface outline-none focus:border-primary"
                />
                <select
                  value={tier}
                  onChange={(e) => setTier(e.target.value)}
                  className="rounded-lg border border-outline-variant/50 bg-surface px-2 py-1 text-sm font-body text-on-surface outline-none"
                >
                  <option value="economy">economy</option>
                  <option value="standard">standard</option>
                  <option value="premium">premium</option>
                </select>
                <button
                  onClick={run}
                  disabled={loading}
                  className="rounded-lg bg-primary px-3 py-1 text-sm font-body text-on-primary disabled:opacity-50"
                >
                  {loading ? 'Analysing…' : haveResults ? 'Re-run' : 'Run comparison'}
                </button>
                <button onClick={() => setOpen(false)} className="px-1 text-on-surface-variant hover:text-on-surface">✕</button>
              </div>
            </header>

            <div className="overflow-auto px-5 py-3">
              <table className="w-full text-sm font-body">
                <thead>
                  <tr>
                    <th className="w-48 py-2 text-left font-normal text-on-surface-variant"></th>
                    {pins.map((p) => (
                      <th key={p.label} className="py-2 text-left">
                        <span className="mr-1.5 inline-flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-bold text-white" style={{ background: PIN_COLORS[p.label] }}>
                          {p.label}
                        </span>
                        <span className="font-headline text-on-surface">{p.locality}</span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {ROWS.map((row) => {
                    const win = winners(row, rows);
                    return (
                      <React.Fragment key={row.label}>
                        {row.group && (
                          <tr>
                            <td colSpan={pins.length + 1} className="pt-3 text-[11px] uppercase tracking-wide text-on-surface-variant">
                              {row.group} — {type || 'cafe'} · {tier}
                            </td>
                          </tr>
                        )}
                        <tr className="border-t border-outline-variant/30">
                          <td className="py-1.5 text-on-surface-variant">{row.label}</td>
                          {pins.map((p, i) => (
                            <td key={p.label} className={`py-1.5 tabular-nums ${win.has(i) ? 'font-semibold text-emerald-600' : 'text-on-surface'}`}>
                              {results[p.label]?.error ? 'failed' : results[p.label] ? row.show(results[p.label]) : '—'}
                              {win.has(i) && ' ★'}
                            </td>
                          ))}
                        </tr>
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
              {!Object.keys(results).length && !loading && (
                <p className="py-4 text-center text-sm font-body text-on-surface-variant">
                  Pick a business type and run the comparison.
                </p>
              )}
              <p className="mt-3 text-[11px] font-body italic text-on-surface-variant">
                ★ marks the best value in each row. Site rows are measured from the loaded data (1.5 km radius);
                rent, revenue and payback are modeled estimates — see the cost-to-open tab for assumptions.
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
