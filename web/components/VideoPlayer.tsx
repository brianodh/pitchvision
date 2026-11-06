"use client";
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import type { TimeStore } from "@/lib/time-store";

export interface PlayerHandle {
  seek(t: number): void;
  toggle(): void;
  hasVideo(): boolean;
}

/**
 * Native <video> with the time store wired in. Native controls are kept on purpose: coaches already know
 * them, and they are accessible out of the box. While playing, time is read every animation frame so the
 * timeline playhead moves smoothly rather than in 250 ms `timeupdate` steps.
 *
 * If the bundle's video is missing (a broken symlink, a moved drive), the operator can point the player at
 * a local copy. That file is played straight from disk via an object URL — it is never uploaded anywhere.
 */
export const VideoPlayer = forwardRef<PlayerHandle, { src: string | null; store: TimeStore; duration: number }>(
  function VideoPlayer({ src, store, duration }, ref) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [localSrc, setLocalSrc] = useState<string | null>(null);
    const [failed, setFailed] = useState(false);
    const effective = localSrc ?? (failed ? null : src);

    useEffect(() => () => {
      if (localSrc) URL.revokeObjectURL(localSrc);
    }, [localSrc]);

    useEffect(() => {
      const v = videoRef.current;
      if (!v) return;
      let raf = 0;
      const tick = () => {
        store.set(v.currentTime);
        raf = requestAnimationFrame(tick);
      };
      const onPlay = () => {
        store.setPlaying(true);
        cancelAnimationFrame(raf);
        raf = requestAnimationFrame(tick);
      };
      const onStop = () => {
        store.setPlaying(false);
        cancelAnimationFrame(raf);
        store.set(v.currentTime);
      };
      const onSeek = () => store.set(v.currentTime);
      v.addEventListener("play", onPlay);
      v.addEventListener("pause", onStop);
      v.addEventListener("ended", onStop);
      v.addEventListener("seeked", onSeek);
      v.addEventListener("seeking", onSeek);
      return () => {
        cancelAnimationFrame(raf);
        v.removeEventListener("play", onPlay);
        v.removeEventListener("pause", onStop);
        v.removeEventListener("ended", onStop);
        v.removeEventListener("seeked", onSeek);
        v.removeEventListener("seeking", onSeek);
      };
    }, [store, effective]);

    useImperativeHandle(
      ref,
      () => ({
        seek(t) {
          const clamped = Math.max(0, Math.min(duration, t));
          const v = videoRef.current;
          if (v && effective) v.currentTime = clamped;
          store.set(clamped); // timeline stays navigable even without video
        },
        toggle() {
          const v = videoRef.current;
          if (!v || !effective) return;
          if (v.paused) void v.play();
          else v.pause();
        },
        hasVideo: () => Boolean(effective),
      }),
      [store, duration, effective],
    );

    if (!effective) {
      return (
        <div className="relative flex aspect-video w-full flex-col items-center justify-center gap-3 overflow-hidden rounded-[10px] border border-line bg-s1 p-6 text-center">
          <div className="absolute inset-0 hatch opacity-60" aria-hidden />
          <div className="relative max-w-sm">
            <p className="font-display text-xl font-semibold text-ink-1">
              {failed ? "This video can't be played" : "No video attached to this match"}
            </p>
            <p className="mt-1 text-sm text-ink-2">
              {failed
                ? "The file is missing or in a format this browser can't decode (MP4/H.264 is safest)."
                : "The timeline, list and thumbnails still work."}{" "}
              Point the player at your local copy — it plays straight from disk and isn&apos;t uploaded.
            </p>
            <label className="mt-4 inline-flex cursor-pointer items-center gap-2 rounded-md bg-accent px-3.5 py-2 text-sm font-semibold text-accent-ink hover:brightness-110">
              Choose video file…
              <input
                type="file"
                accept="video/*"
                className="sr-only"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) {
                    setFailed(false);
                    setLocalSrc(URL.createObjectURL(f));
                  }
                }}
              />
            </label>
          </div>
        </div>
      );
    }

    return (
      <div className="overflow-hidden rounded-[10px] border border-line bg-black">
        <video
          ref={videoRef}
          src={effective}
          controls
          playsInline
          preload="metadata"
          className="block aspect-video w-full bg-black"
          onError={() => {
            if (!localSrc) setFailed(true);
          }}
        />
      </div>
    );
  },
);
