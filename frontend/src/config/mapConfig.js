// Basemap style resolution + shared map constants.
//
// MapTiler gives a Felt-like vector basemap but needs a free API key. When the key
// is absent we fall back to the free, no-signup MapLibre demo style so the app always
// renders something.

const MAPTILER_KEY = import.meta.env.VITE_MAPTILER_KEY?.trim();

// Free no-key fallback: real OpenStreetMap raster tiles. (The MapLibre *demo* style
// only has country outlines and is blank at city zoom — useless here.) This gives full
// street-level detail with no signup; add a MapTiler key for crisper vector tiles.
const OSM_RASTER_STYLE = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      maxzoom: 19,
      attribution: '© OpenStreetMap contributors',
    },
  },
  layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
};

export const HAS_MAPTILER = Boolean(MAPTILER_KEY);

export const BASEMAP_STYLE = MAPTILER_KEY
  ? `https://api.maptiler.com/maps/streets-v2/style.json?key=${MAPTILER_KEY}`
  : OSM_RASTER_STYLE;

export const MARTIN_URL = import.meta.env.VITE_MARTIN_URL?.trim() || 'http://localhost:3001';
export const API_BASE = import.meta.env.VITE_API_BASE?.trim() || 'http://localhost:8000';

// Mumbai — the pre-baked default city.
export const DEFAULT_CENTER = [72.8777, 19.076]; // [lng, lat] for MapLibre
export const DEFAULT_ZOOM = 11;
