import React, { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import { useMapStore } from '../store/mapStore';
import { siteEval, businessEstimate, competitorAnalysis } from '../services/api';
import { openPlanReport, downloadPlanHTML } from '../utils/businessReport';

/* ---- formatting helpers ---------------------------------------------------- */
const fmtPsf = (v) => (v == null ? '—' : `₹${Number(v).toLocaleString('en-IN')}/sqft`);
const fmtDist = (m) =>
  m == null ? '—' : m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toFixed(1)} km`;
const fmtINR = (v) => {
  if (v == null) return '—';
  if (v >= 1e7) return `₹${(v / 1e7).toFixed(2)} Cr`;
  if (v >= 1e5) return `₹${(v / 1e5).toFixed(1)} L`;
  return `₹${Math.round(v).toLocaleString('en-IN')}`;
};

const BUCKET_META = {
  healthcare: { label: 'Healthcare', icon: '🏥' },
  education: { label: 'Education', icon: '🎓' },
  food: { label: 'Food & cafés', icon: '🍽️' },
  banking: { label: 'Banking', icon: '🏦' },
  shopping: { label: 'Shopping', icon: '🛍️' },
};
const MODE_ICON = { metro: '🚇', rail: '🚆', bus: '🚌', tram: '🚋' };

const RISK_STYLE = {
  low: 'bg-emerald-500/15 text-emerald-600 border-emerald-500/30',
  medium: 'bg-amber-500/15 text-amber-600 border-amber-500/30',
  high: 'bg-rose-500/15 text-rose-600 border-rose-500/30',
};

function Chip({ children, className = '' }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-body ${className}`}>
      {children}
    </span>
  );
}

function Section({ title, children }) {
  return (
    <div className="border-t border-outline-variant/40 px-4 py-3">
      <div className="mb-2 text-xs font-body uppercase tracking-wide text-on-surface-variant">{title}</div>
      {children}
    </div>
  );
}

/* ---- revenue + break-even (modeled) ---------------------------------------- */
function RevenueBlock({ rev }) {
  const d = rev.drivers || {};
  return (
    <div className="rounded-xl border border-outline-variant/40 bg-surface-container-highest/30 px-3 py-2">
      <div className="mb-1 text-[11px] uppercase tracking-wide text-on-surface-variant">
        Revenue &amp; break-even (modeled)
      </div>
      <table className="w-full text-xs font-body">
        <thead>
          <tr className="text-left text-on-surface-variant">
            <th className="py-0.5 font-normal"></th>
            <th className="py-0.5 text-right font-normal">Revenue/mo</th>
            <th className="py-0.5 text-right font-normal">Profit/mo</th>
            <th className="py-0.5 text-right font-normal">Payback</th>
          </tr>
        </thead>
        <tbody>
          {rev.scenarios.map((s) => (
            <tr key={s.name} className={s.name === 'Base' ? 'font-semibold text-on-surface' : 'text-on-surface'}>
              <td className="py-0.5">{s.name}</td>
              <td className="py-0.5 text-right tabular-nums">{fmtINR(s.monthly_revenue)}</td>
              <td className={`py-0.5 text-right tabular-nums ${s.monthly_profit < 0 ? 'text-rose-600' : ''}`}>
                {fmtINR(s.monthly_profit)}
              </td>
              <td className="py-0.5 text-right tabular-nums">
                {s.payback_months != null ? `${s.payback_months} mo` : 'never'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-1.5 text-xs font-body text-on-surface-variant">
        Break-even: {fmtINR(rev.breakeven_revenue)}/mo ≈ {rev.breakeven_daily_customers} customers/day
        at ₹{rev.avg_ticket} avg ticket · {d.competitors_1km ?? 'n/a'} competitors within 1 km
      </div>
      <p className="mt-1 text-[11px] font-body italic text-on-surface-variant">{rev.note}</p>
    </div>
  );
}

/* ---- business "cost to open" mini-tab -------------------------------------- */
function BusinessTab({ point }) {
  const [type, setType] = useState('cafe');
  const [tier, setTier] = useState('standard');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  const run = async () => {
    if (!type.trim() || loading) return;
    setLoading(true);
    setErr(null);
    setData(null);
    try {
      const r = await businessEstimate({
        businessType: type.trim(),
        lat: point.lat,
        lng: point.lng,
        tier,
      });
      setData(r);
    } catch (e) {
      setErr('Estimate failed — is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="px-4 py-3">
      <div className="flex items-center gap-2">
        <input
          value={type}
          onChange={(e) => setType(e.target.value)}
          placeholder="business type (e.g. cafe, gym, clinic)"
          className="flex-1 rounded-lg border border-outline-variant/50 bg-surface px-2.5 py-1.5 text-sm font-body text-on-surface outline-none focus:border-primary"
        />
        <select
          value={tier}
          onChange={(e) => setTier(e.target.value)}
          className="rounded-lg border border-outline-variant/50 bg-surface px-2 py-1.5 text-sm font-body text-on-surface outline-none"
        >
          <option value="economy">economy</option>
          <option value="standard">standard</option>
          <option value="premium">premium</option>
        </select>
      </div>
      <button
        onClick={run}
        disabled={loading}
        className="mt-2 w-full rounded-lg bg-primary px-3 py-1.5 text-sm font-body text-on-primary disabled:opacity-50"
      >
        {loading ? 'Estimating…' : 'Estimate setup cost here'}
      </button>

      {err && <p className="mt-2 text-sm font-body text-error">{err}</p>}

      {data && (
        <div className="mt-3 space-y-3">
          <div className="grid grid-cols-3 gap-2">
            <div className="rounded-xl border border-outline-variant/40 bg-surface-container-highest/40 px-3 py-2">
              <div className="text-xs text-on-surface-variant">Store area</div>
              <div className="text-lg font-headline text-on-surface">
                {data.size_sqft != null ? `${Number(data.size_sqft).toLocaleString('en-IN')} sqft` : '—'}
              </div>
            </div>
            <div className="rounded-xl border border-outline-variant/40 bg-surface-container-highest/40 px-3 py-2">
              <div className="text-xs text-on-surface-variant">Startup total</div>
              <div className="text-lg font-headline text-on-surface">{fmtINR(data.totals?.startup_total)}</div>
            </div>
            <div className="rounded-xl border border-outline-variant/40 bg-surface-container-highest/40 px-3 py-2">
              <div className="text-xs text-on-surface-variant">Monthly opex</div>
              <div className="text-lg font-headline text-on-surface">{fmtINR(data.totals?.monthly)}</div>
            </div>
          </div>
          <div className="text-xs font-body text-on-surface-variant">
            Rent {data.rent_measured ? '(estimated from nearby sale prices)' : '(city default)'}: {data.rent_basis}
          </div>
          {data.summary && (
            <p className="text-sm font-body leading-relaxed text-on-surface">{data.summary}</p>
          )}

          {data.revenue && <RevenueBlock rev={data.revenue} />}

          {/* Detailed line items */}
          {['one_time', 'monthly'].map((key) => (
            <div key={key}>
              <div className="mb-1 text-[11px] uppercase tracking-wide text-on-surface-variant">
                {key === 'one_time' ? 'One-time (setup)' : 'Monthly (running)'}
              </div>
              <div className="space-y-0.5">
                {(data[key] || []).map((x) => (
                  <div key={x.item} className="flex justify-between gap-2 text-xs font-body">
                    <span className="text-on-surface-variant">{x.item}</span>
                    <span className="tabular-nums text-on-surface">₹{Number(x.amount).toLocaleString('en-IN')}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {/* The deliverable the user asked for: a downloadable plan document */}
          <div className="flex gap-2 pt-1">
            <button
              onClick={() => openPlanReport(data)}
              className="flex-1 rounded-lg bg-primary px-3 py-1.5 text-sm font-body text-on-primary"
            >
              📄 Make plan document
            </button>
            <button
              onClick={() => downloadPlanHTML(data)}
              title="Download as .html"
              className="rounded-lg border border-outline-variant/60 px-3 text-on-surface hover:border-primary"
            >
              ⬇
            </button>
          </div>

          <p className="text-[11px] font-body italic text-on-surface-variant">{data.disclaimer}</p>
        </div>
      )}
    </div>
  );
}

/* ---- the site card --------------------------------------------------------- */
function SiteCard({ data }) {
  const comps = data.comps || {};
  const maxSizePsf = Math.max(1, ...(comps.by_size || []).map((b) => b.median_psf || 0));
  const vs = data.vs_city;

  return (
    <>
      <Section title="Property prices (comps)">
        {comps.count > 0 ? (
          <>
            <div className="flex items-end justify-between">
              <div>
                <div className="text-2xl font-headline text-on-surface">{fmtPsf(comps.median_psf)}</div>
                <div className="text-xs font-body text-on-surface-variant">
                  median · {comps.count} nearby listing{comps.count === 1 ? '' : 's'}
                </div>
              </div>
              {vs && (
                <Chip
                  className={
                    vs.label === 'above'
                      ? 'bg-rose-500/15 text-rose-600 border-rose-500/30'
                      : vs.label === 'below'
                      ? 'bg-emerald-500/15 text-emerald-600 border-emerald-500/30'
                      : 'bg-slate-500/15 text-slate-500 border-slate-500/30'
                  }
                >
                  {vs.delta_pct > 0 ? '+' : ''}{vs.delta_pct}% vs city
                </Chip>
              )}
            </div>
            {comps.band_psf && (
              <div className="mt-1 text-xs font-body text-on-surface-variant">
                Typical band {fmtPsf(comps.band_psf.low)} – {fmtPsf(comps.band_psf.high)}
              </div>
            )}
            {comps.by_size?.length > 0 && (
              <div className="mt-3 space-y-1.5">
                {comps.by_size.map((b) => (
                  <div key={b.label} className="flex items-center gap-2">
                    <span className="w-24 text-xs font-body text-on-surface-variant">{b.label}</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-container-highest/60">
                      <div
                        className="h-full rounded-full bg-primary/70"
                        style={{ width: `${((b.median_psf || 0) / maxSizePsf) * 100}%` }}
                      />
                    </div>
                    <span className="w-24 text-right text-xs font-body text-on-surface">{fmtPsf(b.median_psf)}</span>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : (
          <p className="text-sm font-body text-on-surface-variant">
            No listings within {(data.radius_m / 1000).toFixed(1)} km — try a wider radius.
          </p>
        )}
      </Section>

      <Section title="Connectivity">
        {data.transit?.length > 0 ? (
          <div className="space-y-1.5">
            {data.transit.map((t) => (
              <div key={t.mode} className="flex items-center justify-between text-sm font-body">
                <span className="text-on-surface">
                  {MODE_ICON[t.mode] || '📍'} <span className="capitalize">{t.mode}</span> · {t.name}
                </span>
                <span className="text-on-surface-variant">{fmtDist(t.distance_m)}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm font-body text-on-surface-variant">No transit stops nearby.</p>
        )}
      </Section>

      <Section title="Amenities within radius">
        <div className="grid grid-cols-5 gap-1.5 text-center">
          {Object.keys(BUCKET_META).map((k) => (
            <div key={k} className="rounded-lg border border-outline-variant/40 bg-surface-container-highest/30 px-1 py-2">
              <div className="text-base leading-none">{BUCKET_META[k].icon}</div>
              <div className="mt-1 text-sm font-headline text-on-surface">{data.amenities?.[k] ?? 0}</div>
              <div className="text-[10px] leading-tight text-on-surface-variant">{BUCKET_META[k].label}</div>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Safety">
        {data.safety?.safety_score != null ? (
          <div className="flex items-center justify-between">
            <div>
              <div className="text-lg font-headline text-on-surface">{data.safety.safety_score}/100</div>
              <div className="text-xs font-body text-on-surface-variant">
                nearest area: {data.safety.area}
              </div>
            </div>
            {data.safety.risk_level && (
              <Chip className={RISK_STYLE[data.safety.risk_level] || RISK_STYLE.medium}>
                {data.safety.risk_level} risk
              </Chip>
            )}
          </div>
        ) : (
          <p className="text-sm font-body text-on-surface-variant">No safety data for this area.</p>
        )}
      </Section>
    </>
  );
}

/* ---- competitor + catchment analysis --------------------------------------- */
const SAT_STYLE = {
  low: 'bg-emerald-500/15 text-emerald-600 border-emerald-500/30',
  moderate: 'bg-amber-500/15 text-amber-600 border-amber-500/30',
  high: 'bg-orange-500/15 text-orange-600 border-orange-500/30',
  saturated: 'bg-rose-500/15 text-rose-600 border-rose-500/30',
};

function CompetitionTab({ point, radius, onPick }) {
  const map = useMapStore((s) => s.map);
  const [type, setType] = useState('cafe');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [ran, setRan] = useState(false);
  const markers = useRef([]);

  const clearMarkers = () => {
    markers.current.forEach((m) => m.remove());
    markers.current = [];
  };

  const run = async () => {
    if (!type.trim() || loading) return;
    setLoading(true);
    setErr(null);
    try {
      setData(await competitorAnalysis({ lat: point.lat, lng: point.lng, businessType: type.trim(), radiusM: radius }));
      setRan(true);
    } catch (e) {
      setErr('Analysis failed — is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  // Re-run automatically when the spot or radius changes after the first analysis.
  useEffect(() => {
    if (ran) run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [point.lat, point.lng, radius]);

  // Competitors (red dots) + suggested gaps (green numbered) on the map.
  useEffect(() => {
    clearMarkers();
    if (!map || !data) return undefined;
    (data.competitors?.items || []).forEach((c) => {
      const el = document.createElement('div');
      el.title = `${c.name} · ${c.distance_m} m`;
      el.style.cssText = 'width:11px;height:11px;border-radius:50%;background:#dc2626;border:2px solid #fff;box-shadow:0 0 3px rgba(0,0,0,.5)';
      markers.current.push(new maplibregl.Marker({ element: el }).setLngLat([c.lng, c.lat]).addTo(map));
    });
    (data.gaps?.suggestions || []).forEach((g, i) => {
      const el = document.createElement('div');
      el.textContent = i + 1;
      el.title = 'Lower-competition spot';
      el.style.cssText = 'width:22px;height:22px;border-radius:50%;background:#16a34a;color:#fff;font:700 12px system-ui;display:flex;align-items:center;justify-content:center;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.5)';
      markers.current.push(new maplibregl.Marker({ element: el }).setLngLat([g.lng, g.lat]).addTo(map));
    });
    return clearMarkers;
  }, [map, data]);

  useEffect(() => clearMarkers, []);

  const c = data?.competitors;
  const cat = data?.catchment;

  return (
    <div className="px-4 py-3">
      <div className="flex items-center gap-2">
        <input
          value={type}
          onChange={(e) => setType(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && run()}
          placeholder="business type (e.g. cafe, gym, pharmacy)"
          className="flex-1 rounded-lg border border-outline-variant/50 bg-surface px-2.5 py-1.5 text-sm font-body text-on-surface outline-none focus:border-primary"
        />
        <button
          onClick={run}
          disabled={loading}
          className="rounded-lg bg-primary px-3 py-1.5 text-sm font-body text-on-primary disabled:opacity-50"
        >
          {loading ? '…' : 'Analyse'}
        </button>
      </div>
      {err && <p className="mt-2 text-sm font-body text-error">{err}</p>}
      {!data && !loading && !err && (
        <p className="mt-3 text-sm font-body text-on-surface-variant">
          See who competes within {(radius / 1000).toFixed(1)} km, how much demand surrounds this spot,
          and where a better gap is.
        </p>
      )}

      {data && (
        <div className="mt-3 space-y-3">
          <div className="flex items-end justify-between">
            <div>
              <div className="text-2xl font-headline text-on-surface">{c.count} competitor{c.count === 1 ? '' : 's'}</div>
              <div className="text-xs font-body text-on-surface-variant">
                {c.density_per_km2}/km²{c.nearest_m != null ? ` · nearest ${fmtDist(c.nearest_m)}` : ''}
              </div>
            </div>
            <Chip className={SAT_STYLE[data.saturation.label]}>{data.saturation.label}</Chip>
          </div>
          <p className="text-sm font-body text-on-surface">{data.saturation.text}</p>

          <div className="rounded-xl border border-outline-variant/40 bg-surface-container-highest/30 px-3 py-2">
            <div className="mb-1 flex items-baseline justify-between">
              <span className="text-[11px] uppercase tracking-wide text-on-surface-variant">Catchment demand</span>
              <span className="text-lg font-headline text-on-surface">{cat.demand_index}/100</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-surface-container-highest/60">
              <div className="h-full rounded-full bg-primary/70" style={{ width: `${cat.demand_index}%` }} />
            </div>
            <div className="mt-2 grid grid-cols-6 gap-1 text-center">
              {Object.keys(BUCKET_META).map((k) => (
                <div key={k} title={BUCKET_META[k].label}>
                  <div className="text-sm leading-none">{BUCKET_META[k].icon}</div>
                  <div className="text-xs font-headline text-on-surface">{cat.amenities?.[k] ?? 0}</div>
                </div>
              ))}
              <div title="Transit stops">
                <div className="text-sm leading-none">🚏</div>
                <div className="text-xs font-headline text-on-surface">{cat.transit_stops}</div>
              </div>
            </div>
            <div className="mt-1.5 text-xs font-body text-on-surface-variant">
              {cat.demand_per_competitor} demand points per competitor
            </div>
          </div>

          <div>
            <div className="mb-1 text-[11px] uppercase tracking-wide text-on-surface-variant">Better spots nearby</div>
            {data.gaps.suggestions.length ? (
              <div className="space-y-1.5">
                {data.gaps.suggestions.map((g, i) => (
                  <div key={`${g.lat}-${g.lng}`} className="flex items-center gap-2 rounded-lg border border-outline-variant/40 px-2 py-1.5 text-xs font-body">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-[11px] font-bold text-white">{i + 1}</span>
                    <span className="flex-1 text-on-surface">
                      {fmtDist(g.distance_m)} away · demand {g.demand} · {g.competitors} competitor{g.competitors === 1 ? '' : 's'} within 500 m
                    </span>
                    <button onClick={() => onPick(g.lat, g.lng)} className="rounded-full border border-outline-variant/60 px-2 py-0.5 text-on-surface hover:border-primary">
                      Evaluate
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs font-body text-on-surface-variant">
                No clearly better gap within this radius — this spot is already among the best here.
              </p>
            )}
          </div>

          {c.items.length > 0 && (
            <div>
              <div className="mb-1 text-[11px] uppercase tracking-wide text-on-surface-variant">Nearest competitors (red dots on map)</div>
              <div className="space-y-0.5">
                {c.items.slice(0, 8).map((x, i) => (
                  <div key={i} className="flex justify-between gap-2 text-xs font-body">
                    <span className="truncate text-on-surface">{x.name}</span>
                    <span className="shrink-0 text-on-surface-variant">{fmtDist(x.distance_m)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          <p className="text-[11px] font-body italic text-on-surface-variant">{data.note}</p>
        </div>
      )}
    </div>
  );
}

/* ---- panel + map wiring ---------------------------------------------------- */
export default function SiteEvalPanel() {
  const map = useMapStore((s) => s.map);
  const pickMode = useMapStore((s) => s.pickMode);
  const setPickMode = useMapStore((s) => s.setPickMode);
  const pins = useMapStore((s) => s.pins);
  const addPin = useMapStore((s) => s.addPin);

  const [point, setPoint] = useState(null);
  const [radius, setRadius] = useState(1500);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [tab, setTab] = useState('site');
  const markerRef = useRef(null);
  const alreadyPinned = !!point && pins.some((p) => p.lat === point.lat && p.lng === point.lng);

  const fetchFor = async (lat, lng, r) => {
    setLoading(true);
    setData(null);
    try {
      const res = await siteEval({ lat, lng, radiusM: r });
      setData(res);
    } catch (e) {
      setData({ error: 'Site lookup failed — is the backend running?' });
    } finally {
      setLoading(false);
    }
  };

  // Register the click handler while pick mode is on.
  useEffect(() => {
    if (!map || !pickMode) return undefined;
    map.getCanvas().style.cursor = 'crosshair';
    const onClick = (e) => {
      const { lng, lat } = e.lngLat;
      setPoint({ lat, lng });
      setTab('site');
      if (markerRef.current) markerRef.current.setLngLat([lng, lat]);
      else markerRef.current = new maplibregl.Marker({ color: '#ffb300' }).setLngLat([lng, lat]).addTo(map);
      fetchFor(lat, lng, radius);
      setPickMode(false); // one-shot: exit pick mode after a pick
    };
    map.on('click', onClick);
    return () => {
      map.off('click', onClick);
      if (map.getCanvas()) map.getCanvas().style.cursor = '';
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, pickMode, radius]);

  // Move the evaluated point (used by "Evaluate here" on a gap suggestion).
  const pickSpot = (lat, lng) => {
    setPoint({ lat, lng });
    if (markerRef.current) markerRef.current.setLngLat([lng, lat]);
    if (map) map.flyTo({ center: [lng, lat], zoom: Math.max(map.getZoom(), 14) });
    fetchFor(lat, lng, radius);
  };

  const changeRadius = (r) => {
    setRadius(r);
    if (point) fetchFor(point.lat, point.lng, r);
  };

  const close = () => {
    setPoint(null);
    setData(null);
    if (markerRef.current) {
      markerRef.current.remove();
      markerRef.current = null;
    }
  };

  return (
    <>
      {/* Trigger button (top-right, under the nav controls) */}
      <button
        onClick={() => setPickMode(!pickMode)}
        className={`absolute right-4 top-4 z-10 flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-body shadow-soft backdrop-blur transition
          ${pickMode
            ? 'border-primary bg-primary text-on-primary'
            : 'border-outline-variant/50 bg-surface/95 text-on-surface hover:border-primary'}`}
      >
        📍 {pickMode ? 'Click the map…' : 'Evaluate a location'}
      </button>

      {/* Result panel (right side) */}
      {point && (
        <aside className="absolute right-4 top-16 bottom-4 z-20 flex w-[360px] max-w-[85vw] flex-col overflow-hidden rounded-2xl border border-outline-variant/50 bg-surface/95 shadow-soft backdrop-blur">
          <header className="flex items-start justify-between gap-2 px-4 py-3">
            <div className="min-w-0">
              <div className="truncate font-headline text-lg text-on-surface">
                {data?.locality || 'Evaluating…'}
              </div>
              <div className="text-xs font-body text-on-surface-variant">
                {data?.ward ? `${data.ward} · ` : ''}
                {point.lat.toFixed(4)}, {point.lng.toFixed(4)}
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-1">
              <button
                onClick={() => addPin({ lat: point.lat, lng: point.lng, locality: data?.locality || 'Pinned spot' })}
                disabled={!data || data.error || pins.length >= 3 || alreadyPinned}
                title={pins.length >= 3 ? 'Max 3 locations' : 'Add this spot to the comparison'}
                className="rounded-full border border-outline-variant/60 px-2.5 py-0.5 text-xs font-body text-on-surface hover:border-primary disabled:opacity-40"
              >
                {alreadyPinned ? '✓ Pinned' : '＋ Compare'}
              </button>
              <button onClick={close} className="rounded-full px-2 text-on-surface-variant hover:text-on-surface">✕</button>
            </div>
          </header>

          {/* tabs */}
          <div className="flex gap-1 px-4">
            {['site', 'competition', 'business'].map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`rounded-t-lg px-3 py-1.5 text-sm font-body transition
                  ${tab === t ? 'bg-surface-container-highest/50 text-on-surface' : 'text-on-surface-variant hover:text-on-surface'}`}
              >
                {t === 'site' ? 'Site report' : t === 'competition' ? 'Competition' : 'Cost to open'}
              </button>
            ))}
          </div>

          {/* radius control (site tab only) */}
          {(tab === 'site' || tab === 'competition') && (
            <div className="flex items-center gap-2 px-4 py-2 text-xs font-body text-on-surface-variant">
              <span>Radius</span>
              <input
                type="range"
                min="500"
                max="3000"
                step="250"
                value={radius}
                onChange={(e) => changeRadius(Number(e.target.value))}
                className="flex-1 accent-primary"
              />
              <span className="w-12 text-right text-on-surface">{(radius / 1000).toFixed(2)} km</span>
            </div>
          )}

          <div className="flex-1 overflow-y-auto">
            {loading && <div className="px-4 py-6 text-sm font-body text-on-surface-variant">Reading the neighbourhood…</div>}
            {!loading && data?.error && <div className="px-4 py-6 text-sm font-body text-error">{data.error}</div>}
            {!loading && data && !data.error && tab === 'site' && <SiteCard data={data} />}
            {tab === 'competition' && (
              <CompetitionTab point={point} radius={radius} onPick={(lat, lng) => pickSpot(lat, lng)} />
            )}
            {tab === 'business' && <BusinessTab point={point} />}
          </div>

          {tab === 'site' && data?.note && (
            <footer className="border-t border-outline-variant/40 px-4 py-2 text-[11px] font-body italic text-on-surface-variant">
              {data.note}
            </footer>
          )}
        </aside>
      )}
    </>
  );
}
