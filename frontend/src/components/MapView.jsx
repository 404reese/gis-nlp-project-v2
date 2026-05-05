import React, { useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.heat';
import 'leaflet/dist/leaflet.css';

const mumbaiCenter = [19.076, 72.8777];

const heatGradients = {
  footfall: {
    0.15: '#fff1e8',
    0.4: '#f6b27b',
    0.7: '#d96e2a',
    1.0: '#8f3d12',
  },
  youth: {
    0.15: '#ecfdf5',
    0.4: '#6ee7b7',
    0.7: '#16a34a',
    1.0: '#14532d',
  },
  rent: {
    0.15: '#f5f3ff',
    0.4: '#c4b5fd',
    0.7: '#8b5cf6',
    1.0: '#5b21b6',
  },
  access: {
    0.15: '#e0f2fe',
    0.4: '#7dd3fc',
    0.7: '#0284c7',
    1.0: '#0c4a6e',
  },
  competition: {
    0.15: '#fef2f2',
    0.4: '#fca5a5',
    0.7: '#dc2626',
    1.0: '#7f1d1d',
  },
  flood: {
    0.15: '#f0fdfa',
    0.4: '#5eead4',
    0.7: '#0f766e',
    1.0: '#134e4a',
  },
  traffic: {
    0.15: '#fff7ed',
    0.4: '#fdba74',
    0.7: '#d97706',
    1.0: '#7c2d12',
  },
};

const HeatLayer = ({ points, factorKey }) => {
  const map = useMap();

  useEffect(() => {
    let heatLayer;
    let frameId;

    const validPoints = points.filter((point) => {
      if (!Array.isArray(point) || point.length < 3) {
        return false;
      }

      const [lat, lng, intensity] = point;
      return Number.isFinite(lat) && Number.isFinite(lng) && Number.isFinite(intensity);
    });

    if (!validPoints.length) {
      return undefined;
    }

    frameId = window.requestAnimationFrame(() => {
      const size = map.getSize();

      if (!size.x || !size.y) {
        return;
      }

      heatLayer = L.heatLayer(validPoints, {
        radius: 30,
        blur: 20,
        minOpacity: 0.5,
        maxZoom: 17,
        gradient: heatGradients[factorKey] || heatGradients.footfall,
      });

      heatLayer.addTo(map);
    });

    return () => {
      if (frameId) {
        window.cancelAnimationFrame(frameId);
      }

      if (heatLayer) {
        map.removeLayer(heatLayer);
      }
    };
  }, [factorKey, map, points]);

  return null;
};

const MapView = ({ areas, heatPoints, heatFactorKey, heatFactorLabel, heatFactorColor, heatmapEnabled }) => {
  const hasHeatPoints = heatmapEnabled && heatPoints && heatPoints.length > 0;

  return (
    <div className="w-full h-full relative rounded-2xl overflow-hidden shadow-soft border border-outline-variant/30">
      <MapContainer
        center={mumbaiCenter}
        zoom={11}
        scrollWheelZoom={true}
        className="w-full h-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        {hasHeatPoints && <HeatLayer points={heatPoints} factorKey={heatFactorKey} />}
        {areas && areas.map((area, index) => {
          const lat = area.lat || mumbaiCenter[0] + (Math.random() - 0.5) * 0.1;
          const lng = area.lng || area.lon || mumbaiCenter[1] + (Math.random() - 0.5) * 0.1;
          const score = area.score || 0;
          const scale = 200;

          return (
            <CircleMarker
              key={index}
              center={[lat, lng]}
              radius={(score * scale) / 10}
              pathOptions={{
                color: '#c2652a',
                fillColor: '#e08850',
                fillOpacity: 0.6,
                weight: 2
              }}
            >
              <Popup>
                <div className="font-body text-on-surface">
                  <h3 className="font-headline font-bold text-lg mb-1">{area.name || `Area ${index + 1}`}</h3>
                  <p className="text-sm"><span className="font-semibold">Score:</span> {(score * 100).toFixed(1)}%</p>
                  {area.reason && <p className="text-xs mt-2 text-on-surface-variant line-clamp-3">{area.reason}</p>}
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
      <div className="absolute left-4 bottom-4 z-20 flex items-center gap-2 rounded-full px-3 py-2 text-[11px] font-body text-on-surface shadow-soft border-2 border-white/70 backdrop-blur-md" style={{ backgroundColor: `${heatFactorColor || '#c2652a'}E6`, opacity: heatmapEnabled ? 1 : 0.75 }}>
        <span
          className="h-2.5 w-2.5 rounded-full ring-2 ring-white/80"
          style={{ backgroundColor: heatFactorColor || '#c2652a' }}
        />
        <span className="font-semibold">Heatmap:</span>
        <span>{heatmapEnabled ? heatFactorLabel : 'Hidden'}</span>
      </div>
    </div>
  );
};

export default MapView;
