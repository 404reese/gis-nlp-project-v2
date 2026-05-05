import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { getLocationInsight, getPropertiesByLocation } from '../services/api';

// Helper component to fly/zoom the map to a specific location
const MapFlyTo = ({ center, zoom }) => {
  const map = useMap();
  useEffect(() => {
    if (center) {
      map.flyTo(center, zoom, { duration: 1.2 });
    }
  }, [center, zoom, map]);
  return null;
};

const LocationDetailPanel = ({ area, onClose, query, conversation }) => {
  // Handle both 'lng' and 'lon' keys from API
  const lat = area.lat || 19.076;
  const lng = area.lng || area.lon || 72.8777;
  const score = area.score || 0;

  // LLM insight state
  const [insight, setInsight] = useState('');
  const [loadingInsight, setLoadingInsight] = useState(false);

  // Properties state
  const [showProperties, setShowProperties] = useState(false);
  const [properties, setProperties] = useState([]);
  const [loadingProperties, setLoadingProperties] = useState(false);

  useEffect(() => {
    const fetchInsight = async () => {
      setLoadingInsight(true);
      try {
        const result = await getLocationInsight({
          location: area,
          query: query || '',
          conversation: conversation || [],
        });
        setInsight(result.insight || '');
      } catch (err) {
        console.error('Error fetching location insight:', err);
        setInsight('Unable to generate insight at this time.');
      } finally {
        setLoadingInsight(false);
      }
    };

    fetchInsight();
  }, [area, query, conversation]);

  const handleViewProperties = async () => {
    if (showProperties) {
      setShowProperties(false);
      setProperties([]);
      return;
    }

    setShowProperties(true);
    setLoadingProperties(true);
    try {
      const result = await getPropertiesByLocation(area.region || area.name);
      setProperties(result.properties || []);
    } catch (err) {
      console.error('Error fetching properties:', err);
      setProperties([]);
    } finally {
      setLoadingProperties(false);
    }
  };

  const metrics = [
    { label: 'Footfall', value: area.footfall, icon: 'footprint', color: '#c2652a' },
    { label: 'Youth Index', value: area.youth, icon: 'group', color: '#e08850' },
    { label: 'Rent Level', value: area.rent, icon: 'payments', color: '#8c3c3c' },
    { label: 'Accessibility', value: area.access, icon: 'directions_transit', color: '#78706a' },
    { label: 'Competition', value: area.competition, icon: 'storefront', color: '#c2652a' },
    { label: 'Flood Risk', value: area.flood, icon: 'water_damage', color: '#d47070' },
    { label: 'Traffic', value: area.traffic, icon: 'traffic', color: '#8c3c3c' },
    { label: 'Area Type', value: area.area_type, icon: 'location_city', color: '#78706a', isText: true },
  ];

  return (
    <div className="w-full h-full flex flex-col lg:flex-row gap-0 animate-fadeIn">
      {/* Left Half — Location Details */}
      <div className="w-full lg:w-1/2 h-full flex flex-col bg-surface-container-low rounded-l-2xl border border-outline-variant/50 shadow-soft overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-surface-container-low/95 backdrop-blur-sm border-b border-outline-variant/30 p-6 flex items-center justify-between">
          <button
            onClick={onClose}
            className="flex items-center gap-2 text-on-surface-variant hover:text-primary transition-colors font-body text-sm group"
          >
            <span className="material-symbols-outlined text-lg group-hover:-translate-x-1 transition-transform">arrow_back</span>
            Back to Overview
          </button>
          <span className="bg-primary/10 text-primary text-xs font-bold px-3 py-1.5 rounded-full font-body">
            Score: {(score * 100).toFixed(0)}%
          </span>
        </div>

        {/* Location Name & Badge */}
        <div className="p-6 pb-0">
          <div className="flex items-start gap-3 mb-2">
            <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center flex-shrink-0">
              <span className="material-symbols-outlined text-primary text-2xl">location_on</span>
            </div>
            <div>
              <h2 className="font-headline text-3xl font-bold text-on-surface leading-tight">
                {area.name || 'Unknown Location'}
              </h2>
              <span className="inline-block mt-1 bg-surface-container-highest text-on-surface-variant text-xs font-body font-medium px-2.5 py-1 rounded-md capitalize">
                {area.area_type || 'N/A'} zone
              </span>
            </div>
          </div>
        </div>

        {/* Score Bar */}
        <div className="px-6 pt-4 pb-2">
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-body text-xs text-on-surface-variant font-medium">Compatibility Score</span>
            <span className="font-body text-xs text-primary font-bold">{(score * 100).toFixed(1)}%</span>
          </div>
          <div className="w-full bg-surface-variant rounded-full h-3 overflow-hidden">
            <div
              className="bg-gradient-to-r from-primary to-primary-container h-3 rounded-full transition-all duration-1000 ease-out"
              style={{ width: `${Math.min(100, Math.max(0, score * 100))}%` }}
            ></div>
          </div>
        </div>

        {/* Why This Location — LLM Insight */}
        <div className="mx-6 mt-4 p-4 bg-primary/5 border border-primary/10 rounded-xl">
          <div className="flex items-center gap-2 mb-2">
            <span className="material-symbols-outlined text-primary text-base">lightbulb</span>
            <span className="font-body text-xs font-semibold text-primary uppercase tracking-wide">Why this location</span>
          </div>
          {loadingInsight ? (
            <div className="flex items-center gap-2 text-on-surface-variant font-body text-sm py-2">
              <span className="material-symbols-outlined animate-spin text-primary text-base">refresh</span>
              Generating personalized insight...
            </div>
          ) : (
            <p className="font-body text-sm text-on-surface leading-relaxed whitespace-pre-line">{insight}</p>
          )}
        </div>

        {/* View Property Button */}
        <button
          onClick={handleViewProperties}
          disabled={loadingProperties}
          className={`mx-6 mt-4 w-[calc(100%-3rem)] px-4 py-3 rounded-xl font-body font-semibold text-sm transition-all duration-200 flex items-center justify-center gap-2 ${
            showProperties
              ? 'bg-primary text-on-primary hover:shadow-md'
              : 'bg-tertiary/20 text-tertiary hover:bg-tertiary/30 border border-tertiary/30'
          }`}
        >
          {loadingProperties ? (
            <>
              <span className="material-symbols-outlined animate-spin text-base">refresh</span>
              Loading Properties...
            </>
          ) : (
            <>
              <span className="material-symbols-outlined text-base">location_away</span>
              {showProperties ? 'Hide Properties' : 'View Properties'}
            </>
          )}
        </button>

        {/* Properties List */}
        {showProperties && properties.length > 0 && (
          <div className="mx-6 mt-4 p-4 bg-tertiary/5 border border-tertiary/10 rounded-xl max-h-48 overflow-y-auto">
            <h4 className="font-headline font-bold text-sm text-on-surface mb-3">Found {properties.length} Properties</h4>
            <div className="space-y-2">
              {properties.map((prop, idx) => (
                <div key={idx} className="bg-surface p-2 rounded-lg border border-outline-variant/20 text-xs">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <span className="font-semibold text-on-surface">{prop.bhk} BHK {prop.type}</span>
                    <span className="bg-secondary/20 text-secondary font-bold px-2 py-0.5 rounded">
                      {prop.price} {prop.price_unit}
                    </span>
                  </div>
                  <p className="text-on-surface-variant">{prop.locality}</p>
                  <div className="flex gap-2 mt-1 text-xs text-on-surface-variant">
                    <span>📐 {prop.area} sqft</span>
                    <span>🏗️ {prop.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {showProperties && properties.length === 0 && !loadingProperties && (
          <div className="mx-6 mt-4 p-4 bg-error/5 border border-error/10 rounded-xl text-center">
            <p className="font-body text-sm text-on-surface-variant">No properties found for this location</p>
          </div>
        )}

        {/* Metrics Grid */}
        <div className="p-6">
          <h3 className="font-headline text-lg font-bold text-on-surface mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-tertiary text-xl">monitoring</span>
            Location Metrics
          </h3>
          <div className="grid grid-cols-2 gap-3">
            {metrics.map((metric, idx) => (
              <div
                key={idx}
                className="bg-surface p-4 rounded-xl border border-outline-variant/30 hover:border-primary/30 hover:shadow-sm transition-all duration-200 group"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className="material-symbols-outlined text-base"
                    style={{ color: metric.color }}
                  >
                    {metric.icon}
                  </span>
                  <span className="font-body text-xs text-on-surface-variant font-medium">{metric.label}</span>
                </div>
                {metric.isText ? (
                  <p className="font-body text-lg font-bold text-on-surface capitalize">{metric.value || '-'}</p>
                ) : (
                  <div className="flex items-end gap-2">
                    <p className="font-body text-2xl font-bold text-on-surface">{metric.value ?? '-'}</p>
                    <span className="font-body text-xs text-on-surface-variant mb-1">/10</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Coordinates */}
        <div className="px-6 pb-6">
          <div className="bg-surface-container-highest/60 p-3 rounded-xl flex items-center gap-3 font-body text-xs text-on-surface-variant">
            <span className="material-symbols-outlined text-base text-secondary">my_location</span>
            <span>Lat: {lat.toFixed(4)}, Lng: {lng.toFixed(4)}</span>
          </div>
        </div>
      </div>

      {/* Right Half — Zoomed Map */}
      <div className="w-full lg:w-1/2 h-full relative rounded-r-2xl overflow-hidden shadow-soft border border-outline-variant/30 border-l-0">
        <MapContainer
          center={[lat, lng]}
          zoom={15}
          scrollWheelZoom={true}
          className="w-full h-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          />
          <MapFlyTo center={[lat, lng]} zoom={15} />
          <CircleMarker
            center={[lat, lng]}
            radius={18}
            pathOptions={{
              color: '#c2652a',
              fillColor: '#e08850',
              fillOpacity: 0.6,
              weight: 3
            }}
          >
            <Popup>
              <div className="font-body text-on-surface">
                <h3 className="font-headline font-bold text-lg mb-1">{area.name || 'Location'}</h3>
                <p className="text-sm"><span className="font-semibold">Score:</span> {(score * 100).toFixed(1)}%</p>
                {area.reason && <p className="text-xs mt-2 text-on-surface-variant line-clamp-3">{area.reason}</p>}
              </div>
            </Popup>
          </CircleMarker>

          {/* Property Markers */}
          {showProperties && properties.map((prop, idx) => (
            <CircleMarker
              key={`prop-${idx}`}
              center={[
                lat + (Math.random() - 0.5) * 0.02,
                lng + (Math.random() - 0.5) * 0.02
              ]}
              radius={10}
              pathOptions={{
                color: '#6750a4',
                fillColor: '#9a7bc9',
                fillOpacity: 0.7,
                weight: 2
              }}
            >
              <Popup>
                <div className="font-body text-on-surface text-sm">
                  <h4 className="font-headline font-bold mb-1">{prop.bhk} BHK {prop.type}</h4>
                  <p className="font-semibold text-secondary">{prop.price} {prop.price_unit}</p>
                  <p className="text-xs text-on-surface-variant mt-1">{prop.locality}</p>
                  <div className="text-xs text-on-surface-variant mt-2 space-y-1">
                    <p>📐 {prop.area} sqft</p>
                    <p>🏗️ {prop.status}</p>
                    <p>📍 {prop.region}</p>
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>

        {/* Floating Location Label */}
        <div className="absolute top-4 left-4 z-[999] bg-surface-container-low/90 backdrop-blur-sm px-4 py-2 rounded-xl border border-outline-variant/50 shadow-soft pointer-events-none">
          <p className="font-headline text-lg font-bold text-on-surface">{area.name}</p>
          <p className="font-body text-xs text-on-surface-variant">Zoomed view · {area.area_type} zone</p>
        </div>

        {/* Properties Count Badge */}
        {showProperties && properties.length > 0 && (
          <div className="absolute top-4 right-4 z-[999] bg-tertiary/90 backdrop-blur-sm text-on-tertiary px-3 py-1.5 rounded-xl border border-tertiary/50 shadow-soft pointer-events-none">
            <p className="font-body text-xs font-semibold">{properties.length} Properties Found</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default LocationDetailPanel;
