// Single source of truth for the MapLibre map instance and layer UI state.
// Centralizing this (vs. the POC's three uncoordinated Leaflet maps) is what lets
// the layer panel, NL-query results, and tools all talk to one map.
import { create } from 'zustand';
import { LAYER_DEFS } from '../config/layers';

const initialLayerState = {};
LAYER_DEFS.forEach((d) => {
  initialLayerState[d.id] = { visible: d.defaultVisible ?? false, opacity: 1 };
});

export const useMapStore = create((set) => ({
  map: null,
  ready: false,
  setMap: (map) => set({ map }),
  setReady: (ready) => set({ ready }),

  // Site-evaluation "pick a point on the map" mode.
  pickMode: false,
  setPickMode: (pickMode) => set({ pickMode }),
  togglePickMode: () => set((s) => ({ pickMode: !s.pickMode })),

  // Which layer source ids actually exist in Martin's catalog (i.e. have data/tables).
  available: {},
  setAvailable: (available) => set({ available }),

  // Per-layer UI state, keyed by source id.
  layerState: initialLayerState,
  toggle: (id) =>
    set((s) => ({
      layerState: {
        ...s.layerState,
        [id]: { ...s.layerState[id], visible: !s.layerState[id].visible },
      },
    })),
  setOpacity: (id, opacity) =>
    set((s) => ({
      layerState: { ...s.layerState, [id]: { ...s.layerState[id], opacity } },
    })),
}));
