// Basemap style resolution + shared map constants.
//
// MapTiler gives a Felt-like vector basemap but needs a free API key. When the key
// is absent we fall back to the free, no-signup MapLibre demo style so the app always
// renders something.

const MAPTILER_KEY = import.meta.env.VITE_MAPTILER_KEY?.trim();

// Free fallback: MapLibre's hosted demo vector style (no key required).
const FALLBACK_STYLE = 'https://demotiles.maplibre.org/style.json';

export const HAS_MAPTILER = Boolean(MAPTILER_KEY);

export const BASEMAP_STYLE = MAPTILER_KEY
  ? `https://api.maptiler.com/maps/streets-v2/style.json?key=${MAPTILER_KEY}`
  : FALLBACK_STYLE;

export const MARTIN_URL = import.meta.env.VITE_MARTIN_URL?.trim() || 'http://localhost:3001';
export const API_BASE = import.meta.env.VITE_API_BASE?.trim() || 'http://localhost:8000';

// Mumbai — the pre-baked default city.
export const DEFAULT_CENTER = [72.8777, 19.076]; // [lng, lat] for MapLibre
export const DEFAULT_ZOOM = 11;
