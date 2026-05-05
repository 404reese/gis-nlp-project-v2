import React, { useEffect, useMemo, useRef, useState } from 'react';
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { getLocations } from '../services/api';

type CrimeData = {
  eow_cases?: number;
  ndps_cases?: number;
  cyber_crime_cases?: number;
  cheating_fraud?: number;
  credit_card_fraud?: number;
  sextortion?: number;
  brothel_cases?: number;
  safety_score?: number;
  risk_level?: string;
};

type LocationRecord = {
  name?: string;
  lat?: number;
  lng?: number;
  lon?: number;
  zone?: string;
  area_type?: string;
  footfall?: number;
  youth?: number;
  rent?: number;
  access?: number;
  competition?: number;
  flood?: number;
  traffic?: number;
  crime_data?: CrimeData;
};

type MapPoint = LocationRecord & {
  lat: number;
  lng: number;
  crime_data: CrimeData;
};

const mumbaiCenter: [number, number] = [19.076, 72.8777];

const riskStyles: Record<string, { color: string; fillColor: string; text: string }> = {
  low: { color: '#14532d', fillColor: '#22c55e', text: 'Low' },
  medium: { color: '#d97706', fillColor: '#f59e0b', text: 'Medium' },
  high: { color: '#c2410c', fillColor: '#ea580c', text: 'High' },
  critical: { color: '#7f1d1d', fillColor: '#dc2626', text: 'Critical' },
};

const defaultRiskStyle = riskStyles.medium;

const formatValue = (value?: number) => (Number.isFinite(value) ? value : '-');

const getRiskStyle = (riskLevel?: string) => {
  return riskStyles[String(riskLevel || '').toLowerCase()] || defaultRiskStyle;
};

const crimeSummary = (crimeData?: CrimeData) => {
  if (!crimeData) {
    return 'No crime data available.';
  }

  return [
    `EOW ${formatValue(crimeData.eow_cases)}`,
    `NDPS ${formatValue(crimeData.ndps_cases)}`,
    `Cyber ${formatValue(crimeData.cyber_crime_cases)}`,
    `Fraud ${formatValue(crimeData.cheating_fraud)}`,
  ].join(' | ');
};

const calculateWomenSafetyScore = (location: LocationRecord) => {
  const crimeData = location.crime_data || {};
  const areaType = String(location.area_type || '').toLowerCase();
  const footfall = Number(location.footfall || 0);
  const youth = Number(location.youth || 0);
  const access = Number(location.access || 0);
  const traffic = Number(location.traffic || 0);

  const violentCrimeEstimate = (Number(crimeData.ndps_cases || 0) * 0.05) + (Number(crimeData.eow_cases || 0) * 0.02);
  const harassmentEstimate = Number(crimeData.cheating_fraud || 0) * 0.3;
  const kidnappingEstimate = 0;
  const cyberCrimeEstimate = (Number(crimeData.sextortion || 0) * 2) + (Number(crimeData.cyber_crime_cases || 0) * 0.1);
  const ndpsEstimate = Number(crimeData.ndps_cases || 0);
  const brothelEstimate = Number(crimeData.brothel_cases || 0);

  const weightedPenalty =
    (violentCrimeEstimate * 0.35) +
    (harassmentEstimate * 0.25) +
    (kidnappingEstimate * 0.2) +
    (cyberCrimeEstimate * 0.12) +
    (ndpsEstimate * 0.05) +
    (brothelEstimate * 0.03);

  let areaModifier = 0;
  const modifierNotes: string[] = [];

  if (areaType === 'commercial') {
    areaModifier -= 5;
    modifierNotes.push('Commercial area: -5');
  }

  if (footfall >= 8) {
    areaModifier -= 3;
    modifierNotes.push('High footfall: -3');
  }

  if (youth >= 8) {
    areaModifier -= 2;
    modifierNotes.push('High youth population: -2');
  }

  if (access <= 6) {
    areaModifier -= 4;
    modifierNotes.push('Poor police access: -4');
  }

  if (traffic >= 8) {
    areaModifier += 2;
    modifierNotes.push('High traffic: +2');
  }

  const score = Math.max(0, Math.min(100, 100 - weightedPenalty + areaModifier));

  return {
    score,
    weightedPenalty,
    areaModifier,
    violentCrimeEstimate,
    harassmentEstimate,
    kidnappingEstimate,
    cyberCrimeEstimate,
    ndpsEstimate,
    brothelEstimate,
    modifierNotes,
  };
};

const scoreBand = (score: number) => {
  if (score >= 80) return { label: 'Safer', color: '#14532d', fillColor: '#22c55e' };
  if (score >= 60) return { label: 'Moderate', color: '#d97706', fillColor: '#f59e0b' };
  if (score >= 40) return { label: 'Caution', color: '#c2410c', fillColor: '#ea580c' };
  return { label: 'High risk', color: '#7f1d1d', fillColor: '#dc2626' };
};

const MapFocus = ({
  selectedPoint,
  markerRefMap,
}: {
  selectedPoint: MapPoint | null;
  markerRefMap: React.MutableRefObject<Record<string, L.CircleMarker | null>>;
}) => {
  const map = useMap();

  useEffect(() => {
    if (!selectedPoint) return;

    map.flyTo([selectedPoint.lat, selectedPoint.lng], 13, { animate: true, duration: 1.1 });
    const marker = markerRefMap.current[selectedPoint.name || ''];
    const timeoutId = window.setTimeout(() => marker?.openPopup(), 320);

    return () => window.clearTimeout(timeoutId);
  }, [map, markerRefMap, selectedPoint]);

  return null;
};

const MapSizeWatcher = () => {
  const map = useMap();

  useEffect(() => {
    const container = map.getContainer();
    const handleResize = () => map.invalidateSize();
    const resizeObserver = new ResizeObserver(handleResize);
    const timeoutId = window.setTimeout(handleResize, 0);

    resizeObserver.observe(container);
    window.addEventListener('resize', handleResize);

    return () => {
      window.clearTimeout(timeoutId);
      resizeObserver.disconnect();
      window.removeEventListener('resize', handleResize);
    };
  }, [map]);

  return null;
};

const DetailValue = ({ label, value }: { label: string; value: React.ReactNode }) => (
  <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low px-3 py-2">
    <div className="text-[11px] uppercase tracking-wide text-on-surface-variant font-body">{label}</div>
    <div className="mt-1 text-sm font-semibold text-on-surface break-words">{value}</div>
  </div>
);

const SafetyMap = () => {
  const [locations, setLocations] = useState<LocationRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLocationName, setSelectedLocationName] = useState('');
  const markerRefMap = useRef<Record<string, L.CircleMarker | null>>({});

  useEffect(() => {
    const fetchLocations = async () => {
      setLoading(true);
      try {
        const data = await getLocations();
        setLocations(Array.isArray(data) ? data : []);
      } catch (error) {
        console.error('Error loading safety locations:', error);
        setLocations([]);
      } finally {
        setLoading(false);
      }
    };

    fetchLocations();
  }, []);

  const mapPoints = useMemo<MapPoint[]>(() => {
    return locations
      .map((location) => {
        const lat = Number(location.lat);
        const lng = Number(location.lng ?? location.lon);

        if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;

        return {
          ...location,
          lat,
          lng,
          crime_data: location.crime_data || {},
        };
      })
      .filter((location): location is MapPoint => Boolean(location));
  }, [locations]);

  const filteredLocations = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();
    if (!query) return mapPoints;

    return mapPoints.filter((location) => {
      const riskLevel = String(location.crime_data?.risk_level || '').toLowerCase();
      return [location.name, location.area_type, riskLevel].some((value) =>
        String(value || '').toLowerCase().includes(query),
      );
    });
  }, [mapPoints, searchTerm]);

  const selectedPoint = useMemo(
    () => filteredLocations.find((location) => location.name === selectedLocationName) || null,
    [filteredLocations, selectedLocationName],
  );

  const selectedWomenSafety = useMemo(() => {
    return selectedPoint ? calculateWomenSafetyScore(selectedPoint) : null;
  }, [selectedPoint]);

  useEffect(() => {
    if (selectedLocationName && !filteredLocations.some((location) => location.name === selectedLocationName)) {
      setSelectedLocationName('');
    }
  }, [filteredLocations, selectedLocationName]);

  return (
    <div className="h-full w-full min-h-0 grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-4">
      <aside className="h-full min-h-0 rounded-2xl border border-outline-variant/40 bg-surface-container-low shadow-soft overflow-hidden flex flex-col">
        <div className="p-5 border-b border-outline-variant/30 bg-gradient-to-b from-surface-container-low to-surface/70">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-on-surface-variant font-body">Safety map</p>
              <h2 className="font-headline text-2xl font-bold text-on-surface">Mumbai locations</h2>
            </div>
            <div className="rounded-full bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary">
              {loading ? 'Loading...' : `${filteredLocations.length} shown`}
            </div>
          </div>

          <label className="flex items-center gap-3 rounded-2xl border border-outline-variant/40 bg-surface px-4 py-3 shadow-sm focus-within:border-primary/50">
            <span className="material-symbols-outlined text-primary text-xl">search</span>
            <input
              type="text"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Search name, risk level, or area type"
              className="w-full bg-transparent outline-none font-body text-sm text-on-surface placeholder:text-on-surface-variant"
            />
          </label>

          <div className="mt-4 grid grid-cols-2 gap-3 text-xs font-body">
            <div className="rounded-xl border border-outline-variant/30 bg-surface p-3">
              <div className="text-on-surface-variant">Total</div>
              <div className="mt-1 text-lg font-bold text-on-surface">{mapPoints.length}</div>
            </div>
            <div className="rounded-xl border border-outline-variant/30 bg-surface p-3">
              <div className="text-on-surface-variant">Filtered</div>
              <div className="mt-1 text-lg font-bold text-on-surface">{filteredLocations.length}</div>
            </div>
          </div>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto p-3 pb-6 space-y-4">
          {selectedPoint ? (
            <div className="rounded-2xl border border-primary/20 bg-primary/5 p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.18em] text-primary font-body">Selected location</p>
                  <h3 className="mt-1 font-headline text-xl font-bold text-on-surface">{selectedPoint.name}</h3>
                  <p className="mt-1 text-xs font-body text-on-surface-variant capitalize">
                    {selectedPoint.area_type || 'Unknown type'}{selectedPoint.zone ? ` · ${selectedPoint.zone}` : ''}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedLocationName('')}
                  className="rounded-full border border-outline-variant/30 bg-surface px-3 py-1 text-xs font-semibold text-on-surface-variant hover:text-on-surface hover:border-primary/30 transition-colors"
                >
                  Clear
                </button>
              </div>

              {selectedWomenSafety && (
                <div className="mt-4 rounded-2xl border border-outline-variant/20 bg-surface p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-[11px] uppercase tracking-[0.18em] text-primary font-body">Women safety score</p>
                      <h4 className="mt-1 font-headline text-lg font-bold text-on-surface">{scoreBand(selectedWomenSafety.score).label}</h4>
                    </div>
                    <div
                      className="rounded-full px-3 py-1.5 text-xs font-bold"
                      style={{ backgroundColor: `${scoreBand(selectedWomenSafety.score).fillColor}22`, color: scoreBand(selectedWomenSafety.score).color }}
                    >
                      {selectedWomenSafety.score.toFixed(1)} / 100
                    </div>
                  </div>

                  <div className="mt-3 h-3 overflow-hidden rounded-full bg-surface-variant/40">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${selectedWomenSafety.score}%`, backgroundColor: scoreBand(selectedWomenSafety.score).fillColor }}
                    />
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-2 text-xs font-body">
                    <DetailValue label="Base score" value="100" />
                    <DetailValue label="Weighted penalty" value={selectedWomenSafety.weightedPenalty.toFixed(1)} />
                    <DetailValue label="Area modifier" value={selectedWomenSafety.areaModifier >= 0 ? `+${selectedWomenSafety.areaModifier}` : selectedWomenSafety.areaModifier.toFixed(1)} />
                    <DetailValue label="Final score" value={selectedWomenSafety.score.toFixed(1)} />
                  </div>

                  <div className="mt-4 space-y-2 text-xs leading-relaxed text-on-surface-variant">
                    <p><span className="font-semibold text-on-surface">Violent crimes proxy:</span> ndps_cases and eow_cases produce an estimate of {selectedWomenSafety.violentCrimeEstimate.toFixed(2)}, then weighted at 0.35.</p>
                    <p><span className="font-semibold text-on-surface">Harassment proxy:</span> cheating_fraud contributes {selectedWomenSafety.harassmentEstimate.toFixed(2)} from 30% of fraud cases, weighted at 0.25.</p>
                    <p><span className="font-semibold text-on-surface">Kidnapping / abduction:</span> no direct field exists in the dataset, so this component is held at 0.</p>
                    <p><span className="font-semibold text-on-surface">Cyber crimes against women:</span> sextortion and general cyber crime estimate {selectedWomenSafety.cyberCrimeEstimate.toFixed(2)}, weighted at 0.12.</p>
                    <p><span className="font-semibold text-on-surface">NDPS / drug cases:</span> ndps_cases contributes {selectedWomenSafety.ndpsEstimate.toFixed(2)} with a 0.05 weight.</p>
                    <p><span className="font-semibold text-on-surface">Brothel / prostitution cases:</span> {selectedWomenSafety.brothelEstimate.toFixed(2)} cases weighted at 0.03.</p>
                    <p><span className="font-semibold text-on-surface">Area modifiers:</span> {selectedWomenSafety.modifierNotes.length > 0 ? selectedWomenSafety.modifierNotes.join(', ') : 'No area modifier applied.'}</p>
                  </div>
                </div>
              )}

              <div className="rounded-2xl border border-outline-variant/30 bg-surface p-4 text-sm text-on-surface-variant font-body">
                Click a location in the list or on the map to see full details here.
              </div>

              <div className="mt-4 grid grid-cols-2 gap-2">
                <DetailValue label="Safety score" value={formatValue(selectedPoint.crime_data?.safety_score)} />
                <DetailValue label="Risk level" value={getRiskStyle(selectedPoint.crime_data?.risk_level).text} />
                <DetailValue label="Footfall" value={formatValue(selectedPoint.footfall)} />
                <DetailValue label="Access" value={formatValue(selectedPoint.access)} />
                <DetailValue label="Youth" value={formatValue(selectedPoint.youth)} />
                <DetailValue label="Rent" value={formatValue(selectedPoint.rent)} />
              </div>

              <div className="mt-3 rounded-xl border border-outline-variant/20 bg-surface-container-low p-3 text-xs leading-relaxed text-on-surface-variant">
                <p className="font-semibold text-on-surface mb-1">Crime summary</p>
                <p>{crimeSummary(selectedPoint.crime_data)}</p>
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <DetailValue label="NDPS cases" value={formatValue(selectedPoint.crime_data?.ndps_cases)} />
                  <DetailValue label="Cyber cases" value={formatValue(selectedPoint.crime_data?.cyber_crime_cases)} />
                  <DetailValue label="Fraud cases" value={formatValue(selectedPoint.crime_data?.cheating_fraud)} />
                  <DetailValue label="Credit card fraud" value={formatValue(selectedPoint.crime_data?.credit_card_fraud)} />
                </div>
              </div>

              <div className="mt-3 grid grid-cols-2 gap-2 text-xs font-body">
                <DetailValue label="Latitude" value={selectedPoint.lat.toFixed(4)} />
                <DetailValue label="Longitude" value={selectedPoint.lng.toFixed(4)} />
                <DetailValue label="Flood" value={formatValue(selectedPoint.flood)} />
                <DetailValue label="Traffic" value={formatValue(selectedPoint.traffic)} />
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-outline-variant/30 bg-surface p-4 text-sm text-on-surface-variant font-body">
              Click a location in the list or on the map to see full details here.
            </div>
          )}

          {loading ? (
            <div className="rounded-2xl border border-outline-variant/30 bg-surface p-5 text-sm text-on-surface-variant font-body">
              Loading locations from the crime dataset...
            </div>
          ) : filteredLocations.length === 0 ? (
            <div className="rounded-2xl border border-outline-variant/30 bg-surface p-5 text-sm text-on-surface-variant font-body">
              No locations match your search.
            </div>
          ) : (
            filteredLocations.map((location) => {
              const riskStyle = getRiskStyle(location.crime_data?.risk_level);
              const isSelected = selectedLocationName === location.name;

              return (
                <button
                  key={location.name}
                  type="button"
                  onClick={() => setSelectedLocationName(location.name || '')}
                  className={`w-full rounded-2xl border p-4 text-left transition-all duration-200 ${
                    isSelected
                      ? 'border-primary/60 bg-primary/10 shadow-md'
                      : 'border-outline-variant/30 bg-surface hover:border-primary/30 hover:shadow-sm'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="font-headline text-base font-bold text-on-surface">{location.name || 'Unknown location'}</h3>
                      <p className="mt-1 text-xs font-body text-on-surface-variant capitalize">{location.area_type || 'Unknown type'}</p>
                    </div>
                    <div
                      className="rounded-full px-3 py-1 text-[11px] font-semibold"
                      style={{ backgroundColor: `${riskStyle.fillColor}22`, color: riskStyle.color }}
                    >
                      {riskStyle.text}
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-2 text-xs font-body">
                    <div className="rounded-xl bg-surface-container-low px-3 py-2 border border-outline-variant/20">
                      <div className="text-on-surface-variant">Safety score</div>
                      <div className="mt-1 text-sm font-bold text-on-surface">{formatValue(location.crime_data?.safety_score)}</div>
                    </div>
                    <div className="rounded-xl bg-surface-container-low px-3 py-2 border border-outline-variant/20">
                      <div className="text-on-surface-variant">Risk level</div>
                      <div className="mt-1 text-sm font-bold" style={{ color: riskStyle.color }}>{riskStyle.text}</div>
                    </div>
                  </div>

                  <p className="mt-3 text-xs leading-relaxed text-on-surface-variant">{crimeSummary(location.crime_data)}</p>
                </button>
              );
            })
          )}
        </div>
      </aside>

      <section className="relative h-full min-h-[560px] rounded-2xl overflow-hidden border border-outline-variant/30 shadow-soft bg-surface">
        <MapContainer center={mumbaiCenter} zoom={11} scrollWheelZoom className="w-full h-full">
          <MapSizeWatcher />
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          />

          <MapFocus selectedPoint={selectedPoint} markerRefMap={markerRefMap} />

          {filteredLocations.map((location) => {
            const riskStyle = getRiskStyle(location.crime_data?.risk_level);
            const isSelected = selectedLocationName === location.name;
            const markerRadius = isSelected ? 12 : 9;

            return (
              <CircleMarker
                key={location.name}
                center={[location.lat as number, location.lng as number]}
                radius={markerRadius}
                ref={(marker) => {
                  if (location.name) {
                    markerRefMap.current[location.name] = marker;
                  }
                }}
                eventHandlers={{
                  click: () => setSelectedLocationName(location.name || ''),
                }}
                pathOptions={{
                  color: riskStyle.color,
                  fillColor: riskStyle.fillColor,
                  fillOpacity: isSelected ? 0.9 : 0.7,
                  weight: isSelected ? 3 : 2,
                }}
              >
                <Popup>
                  <div className="min-w-[220px] font-body text-on-surface">
                    <h3 className="font-headline text-lg font-bold mb-1">{location.name}</h3>
                    <p className="text-sm text-on-surface-variant capitalize">{location.area_type || 'Unknown type'}</p>
                    <div className="mt-3 space-y-1.5 text-sm">
                      <p><span className="font-semibold">Safety score:</span> {formatValue(location.crime_data?.safety_score)}</p>
                      <p><span className="font-semibold">Risk level:</span> {riskStyle.text}</p>
                      <p className="text-xs leading-relaxed text-on-surface-variant mt-2">{crimeSummary(location.crime_data)}</p>
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>

        <div className="absolute left-4 top-4 z-20 rounded-2xl border border-white/70 bg-surface/90 px-4 py-3 shadow-soft backdrop-blur-md">
          <p className="text-[11px] uppercase tracking-[0.18em] text-on-surface-variant font-body">Risk legend</p>
          <div className="mt-2 space-y-2 text-xs font-body text-on-surface">
            {Object.entries(riskStyles).map(([riskLevel, style]) => (
              <div key={riskLevel} className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: style.fillColor }} />
                <span className="capitalize">{riskLevel}</span>
              </div>
            ))}
          </div>
        </div>

        <div
          className="absolute left-4 bottom-4 z-20 flex items-center gap-2 rounded-full px-3 py-2 text-[11px] font-body text-on-surface shadow-soft border-2 border-white/70 backdrop-blur-md"
          style={{ backgroundColor: '#e08850E6' }}
        >
          <span className="h-2.5 w-2.5 rounded-full ring-2 ring-white/80" style={{ backgroundColor: '#c2652a' }} />
          <span className="font-semibold">Locations:</span>
          <span>{loading ? 'Loading' : `${filteredLocations.length} shown`}</span>
        </div>
      </section>
    </div>
  );
};

export default SafetyMap;
