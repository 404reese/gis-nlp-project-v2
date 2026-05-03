import React from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

const MapView = ({ areas }) => {
  const mumbaiCenter = [19.0760, 72.8777];

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
        {areas && areas.map((area, index) => {
          // Fallback coordinates if backend doesn't provide them yet
          const lat = area.lat || mumbaiCenter[0] + (Math.random() - 0.5) * 0.1;
          const lng = area.lng || mumbaiCenter[1] + (Math.random() - 0.5) * 0.1;
          const score = area.score || 0;
          const scale = 200; // Radius scale factor

          return (
            <CircleMarker
              key={index}
              center={[lat, lng]}
              radius={(score * scale) / 10} // Example scaling
              pathOptions={{
                color: '#c2652a', // Primary color
                fillColor: '#e08850', // Primary container
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
    </div>
  );
};

export default MapView;
