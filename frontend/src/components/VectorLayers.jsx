import { useEffect } from 'react';
import maplibregl from 'maplibre-gl';
import { useMapStore } from '../store/mapStore';
import { LAYER_DEFS } from '../config/layers';
import { MARTIN_URL } from '../config/mapConfig';

const OPACITY_KEYS = {
  fill: ['fill-opacity'],
  line: ['line-opacity'],
  circle: ['circle-opacity'],
};

/**
 * Adds each configured layer's Martin vector-tile source to the map (once the map is
 * ready and the source exists in Martin's catalog), then keeps MapLibre visibility +
 * opacity in sync with the layer store. Renders nothing itself.
 */
export default function VectorLayers() {
  const map = useMapStore((s) => s.map);
  const ready = useMapStore((s) => s.ready);
  const layerState = useMapStore((s) => s.layerState);
  const setAvailable = useMapStore((s) => s.setAvailable);

  // Add sources + layers once (gated on Martin catalog).
  useEffect(() => {
    if (!map || !ready) return undefined;
    let cancelled = false;

    (async () => {
      let present = new Set();
      try {
        const cat = await (await fetch(`${MARTIN_URL}/catalog`)).json();
        present = new Set(Object.keys(cat.tiles || cat));
      } catch (e) {
        console.warn('Martin catalog fetch failed — is Martin running?', e);
      }
      if (cancelled) return;

      const avail = {};
      LAYER_DEFS.forEach((def) => {
        avail[def.id] = present.has(def.id);
        if (!present.has(def.id)) return;

        if (!map.getSource(def.id)) {
          map.addSource(def.id, {
            type: 'vector',
            tiles: [`${MARTIN_URL}/${def.id}/{z}/{x}/{y}`],
            minzoom: 0,
            maxzoom: 20,
          });
        }
        def.mapLayers.forEach((ml, i) => {
          const lid = `${def.id}__${i}`;
          if (map.getLayer(lid)) return;
          map.addLayer({
            id: lid,
            type: ml.type,
            source: def.id,
            'source-layer': def.id,
            paint: ml.paint,
            layout: { visibility: layerState[def.id]?.visible ? 'visible' : 'none' },
          });

          // Click-to-inspect popup for point/fill layers.
          if (ml.type !== 'line') {
            map.on('click', lid, (e) => {
              const p = e.features?.[0]?.properties || {};
              const rows = Object.entries(p)
                .filter(([, v]) => v !== null && v !== '' && v !== 'null')
                .slice(0, 8)
                .map(([k, v]) => `<div><b>${k}</b>: ${String(v).slice(0, 40)}</div>`)
                .join('');
              new maplibregl.Popup({ closeButton: true })
                .setLngLat(e.lngLat)
                .setHTML(`<div style="font:12px system-ui;max-width:220px">${rows || 'No attributes'}</div>`)
                .addTo(map);
            });
            map.on('mouseenter', lid, () => (map.getCanvas().style.cursor = 'pointer'));
            map.on('mouseleave', lid, () => (map.getCanvas().style.cursor = ''));
          }
        });
      });
      setAvailable(avail);
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, ready]);

  // Sync visibility + opacity from the store.
  useEffect(() => {
    if (!map || !ready) return;
    LAYER_DEFS.forEach((def) => {
      const st = layerState[def.id];
      if (!st) return;
      def.mapLayers.forEach((ml, i) => {
        const lid = `${def.id}__${i}`;
        if (!map.getLayer(lid)) return;
        map.setLayoutProperty(lid, 'visibility', st.visible ? 'visible' : 'none');
        (OPACITY_KEYS[ml.type] || []).forEach((k) => {
          const base = ml.paint[k];
          if (typeof base === 'number') map.setPaintProperty(lid, k, base * st.opacity);
        });
      });
    });
  }, [map, ready, layerState]);

  return null;
}
