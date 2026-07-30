import React, { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { BASEMAP_STYLE, DEFAULT_CENTER, DEFAULT_ZOOM } from '../config/mapConfig';
import { useMapStore } from '../store/mapStore';

/**
 * The single MapLibre GL map instance for the whole studio.
 * Registers itself in the map store so layer controls / NL-query results can
 * manipulate one shared map.
 */
const MapCanvas = () => {
  const containerRef = useRef(null);
  const setMap = useMapStore((s) => s.setMap);
  const setReady = useMapStore((s) => s.setReady);

  useEffect(() => {
    if (!containerRef.current) return undefined;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASEMAP_STYLE,
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      attributionControl: { compact: true },
    });

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right');
    map.addControl(new maplibregl.ScaleControl({ maxWidth: 120, unit: 'metric' }), 'bottom-right');

    map.on('load', () => setReady(true));
    setMap(map);

    return () => {
      setReady(false);
      setMap(null);
      map.remove();
    };
  }, [setMap, setReady]);

  return <div ref={containerRef} className="absolute inset-0" />;
};

export default MapCanvas;
