// Single source of truth for the MapLibre map instance and layer UI state.
// Centralizing this (vs. the POC's three uncoordinated Leaflet maps) is what lets
// the layer panel, NL-query results, and tools all talk to one map.
import { create } from 'zustand';

export const useMapStore = create((set) => ({
  map: null,
  ready: false,
  setMap: (map) => set({ map }),
  setReady: (ready) => set({ ready }),

  // Layer registry (populated in M1+). Shape: { id, label, group, visible, opacity }.
  layers: [],
  setLayers: (layers) => set({ layers }),
}));
