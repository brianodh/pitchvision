"use client";
import { useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";

/** Hover/focus tooltip. Opens on pointer hover and on keyboard focus; content is linked with
 * aria-describedby so it is announced, not just shown. Only rendered while open (a hidden box would still
 * widen the page on a phone), and nudged back inside the viewport when it would spill over an edge. */
export function Hint({
  content,
  children,
  side = "top",
  align = "center",
  className = "",
  width = 260,
}: {
  content: ReactNode;
  children: ReactNode;
  side?: "top" | "bottom";
  align?: "start" | "center" | "end";
  className?: string;
  width?: number;
}) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [shift, setShift] = useState(0);
  const tip = useRef<HTMLSpanElement>(null);

  useLayoutEffect(() => {
    if (!open || !tip.current) {
      setShift(0);
      return;
    }
    const r = tip.current.getBoundingClientRect();
    const vw = document.documentElement.clientWidth;
    const margin = 8;
    if (r.right > vw - margin) setShift(vw - margin - r.right);
    else if (r.left < margin) setShift(margin - r.left);
  }, [open]);

  const pos = align === "start" ? "left-0" : align === "end" ? "right-0" : "left-1/2";
  const baseX = align === "center" ? "-50%" : "0px";
  const w = typeof window !== "undefined" ? Math.min(width, document.documentElement.clientWidth - 16) : width;

  return (
    <span
      className={`relative inline-flex ${className}`}
      onPointerEnter={() => setOpen(true)}
      onPointerLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
      aria-describedby={open ? id : undefined}
    >
      {children}
      {open && (
        <span
          ref={tip}
          id={id}
          role="tooltip"
          style={{ width: w, transform: `translateX(calc(${baseX} + ${shift}px))` }}
          className={`pointer-events-none absolute z-50 ${pos} ${
            side === "top" ? "bottom-full mb-2" : "top-full mt-2"
          } rounded-md border border-line-strong bg-s3 px-3 py-2 text-left text-[12.5px] leading-snug font-normal normal-case tracking-normal text-ink-2 shadow-xl shadow-black/40`}
        >
          {content}
        </span>
      )}
    </span>
  );
}
