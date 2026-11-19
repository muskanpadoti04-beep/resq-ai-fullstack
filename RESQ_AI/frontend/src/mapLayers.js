import { useSyncExternalStore } from "react";

/**
 * Shared Map Layers state.
 * The sidebar (toggle switches) and the 3D building both read this same store,
 * so flipping a switch immediately shows / hides that layer in the 3D scene.
 * (A tiny external store is used so no page needs to pass props around.)
 */

const DEFAULT_LAYERS = {
  occupants: true,
  fire: true,
  heatmap: false,
  routes: true,
  blocked: true,
};

let state = { ...DEFAULT_LAYERS };
const listeners = new Set();

const subscribe = (fn) => {
  listeners.add(fn);
  return () => listeners.delete(fn);
};
const getSnapshot = () => state;

export function toggleMapLayer(key) {
  state = { ...state, [key]: !state[key] };
  listeners.forEach((fn) => fn());
}

export function useMapLayers() {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}
