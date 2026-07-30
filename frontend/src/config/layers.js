// Registry of data layers served by Martin (source id == PostGIS schema.table).
// Each def maps to one or more MapLibre layers + a legend. The layer panel and the
// map wiring both read from here, so adding a layer is a one-object change.

export const LAYER_DEFS = [
  {
    id: 'admin.boundary',
    label: 'Admin boundaries',
    group: 'Administrative',
    defaultVisible: true,
    mapLayers: [
      { type: 'fill', paint: { 'fill-color': '#c2652a', 'fill-opacity': 0.05 } },
      { type: 'line', paint: { 'line-color': '#c2652a', 'line-width': 1.1, 'line-opacity': 0.7 } },
    ],
    legend: [{ color: '#c2652a', label: 'Ward / city boundary' }],
  },
  {
    id: 'roads.segment',
    label: 'Road network',
    group: 'Roads & Transport',
    defaultVisible: true,
    mapLayers: [
      {
        type: 'line',
        paint: {
          'line-color': '#7a5c34',
          'line-opacity': 0.75,
          'line-width': ['interpolate', ['linear'], ['zoom'], 10, 0.4, 14, 1.2, 17, 3],
        },
      },
    ],
    legend: [{ color: '#7a5c34', label: 'Major road' }],
  },
  {
    id: 'transport.stop',
    label: 'Transit stops',
    group: 'Roads & Transport',
    defaultVisible: false,
    mapLayers: [
      {
        type: 'circle',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 11, 3, 16, 6],
          'circle-opacity': 0.9,
          'circle-stroke-width': 1,
          'circle-stroke-color': '#ffffff',
          'circle-color': [
            'match', ['get', 'mode'],
            'metro', '#7b2ff7', 'rail', '#1f77b4', 'bus', '#2ca02c', 'tram', '#ff7f0e',
            '#888888',
          ],
        },
      },
    ],
    legend: [
      { color: '#7b2ff7', label: 'Metro' },
      { color: '#1f77b4', label: 'Rail' },
      { color: '#2ca02c', label: 'Bus' },
    ],
  },
  {
    id: 'poi.place',
    label: 'Businesses / POIs',
    group: 'Businesses & POIs',
    defaultVisible: false,
    mapLayers: [
      {
        type: 'circle',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 11, 2, 16, 5],
          'circle-opacity': 0.85,
          'circle-color': [
            'match', ['get', 'category'],
            'restaurant', '#e4572e', 'cafe', '#f3a712', 'fast_food', '#e4572e',
            'bank', '#3f88c5', 'atm', '#3f88c5',
            'hospital', '#d7263d', 'clinic', '#d7263d', 'doctors', '#d7263d',
            'pharmacy', '#00a878',
            'school', '#8e44ad', 'college', '#8e44ad', 'university', '#8e44ad',
            'shop', '#2e86ab', 'hotel', '#c06c84', 'place_of_worship', '#b8860b',
            '#8a8a8a',
          ],
        },
      },
    ],
    legend: [
      { color: '#e4572e', label: 'Food & drink' },
      { color: '#3f88c5', label: 'Bank / ATM' },
      { color: '#d7263d', label: 'Healthcare' },
      { color: '#00a878', label: 'Pharmacy' },
      { color: '#8e44ad', label: 'Education' },
      { color: '#2e86ab', label: 'Shop' },
    ],
  },
  {
    id: 'realestate.listing',
    label: 'Real estate',
    group: 'Real Estate',
    defaultVisible: false,
    mapLayers: [
      {
        type: 'circle',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 11, 2, 16, 4],
          'circle-opacity': 0.5,
          'circle-color': '#6a4c93',
        },
      },
    ],
    legend: [{ color: '#6a4c93', label: 'Property listing' }],
  },
  {
    id: 'crime.area',
    label: 'Safety score',
    group: 'Crime & Environment',
    defaultVisible: false,
    mapLayers: [
      {
        type: 'circle',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 11, 6, 15, 12],
          'circle-opacity': 0.8,
          'circle-stroke-width': 1,
          'circle-stroke-color': '#ffffff',
          'circle-color': [
            'interpolate', ['linear'], ['coalesce', ['get', 'safety_score'], 50],
            40, '#d7263d', 60, '#f3a712', 80, '#00a878',
          ],
        },
      },
    ],
    legend: [
      { color: '#d7263d', label: 'Lower safety' },
      { color: '#f3a712', label: 'Medium' },
      { color: '#00a878', label: 'Higher safety' },
    ],
  },
];

export const LAYER_GROUPS = [...new Set(LAYER_DEFS.map((d) => d.group))];
