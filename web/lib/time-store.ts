"use client";
import { useSyncExternalStore } from "react";

// The playhead changes ~60 times a second. Keeping it in React state would re-render the whole workspace,
// including ~2,000 timeline markers, every frame. A tiny external store lets each consumer pick its own
// resolution: the playhead reads every frame, the event list only cares about quarter-seconds.

export interface TimeStore {
  get(): number;
  set(t: number): void;
  subscribe(fn: () => void): () => void;
  playing(): boolean;
  setPlaying(p: boolean): void;
}

export function createTimeStore(): TimeStore {
  let t = 0;
  let playing = false;
  const subs = new Set<() => void>();
  const emit = () => subs.forEach((f) => f());
  return {
    get: () => t,
    set(v) {
      if (v !== t) {
        t = v;
        emit();
      }
    },
    subscribe(fn) {
      subs.add(fn);
      return () => subs.delete(fn);
    },
    playing: () => playing,
    setPlaying(p) {
      if (p !== playing) {
        playing = p;
        emit();
      }
    },
  };
}

/** Current time, quantised to `step` seconds so the caller only re-renders when it moves a step. */
export function useTime(store: TimeStore, step = 0.25): number {
  return useSyncExternalStore(
    store.subscribe,
    () => Math.floor(store.get() / step) * step,
    () => 0,
  );
}

export function usePlaying(store: TimeStore): boolean {
  return useSyncExternalStore(store.subscribe, store.playing, () => false);
}
