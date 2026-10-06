"use client";

import { useState, useEffect } from "react";

type SvgLine = {
  id: number;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  dur: number;
  delay: number;
  strokeW: number;
  opacity: number;
};

function seededRand(seed: number) {
  let s = seed;
  return () => {
    s = (s * 1664525 + 1013904223) & 0xffffffff;
    return (s >>> 0) / 0xffffffff;
  };
}

function buildLines(W: number, H: number, count: number, seed: number): SvgLine[] {
  const rand = seededRand(seed);
  const lines: SvgLine[] = [];

  for (let i = 0; i < count; i++) {
    const edge = i % 4;
    const lengthFactor = 0.35 + rand() * 0.6;
    const angleOffset = (rand() - 0.5) * 70;

    let x1: number, y1: number, x2: number, y2: number;

    if (edge === 0) {
      x1 = rand() * W;
      y1 = -20;
      const len = H * lengthFactor;
      const angle = (90 + angleOffset) * (Math.PI / 180);
      x2 = x1 + Math.cos(angle) * len;
      y2 = y1 + Math.sin(angle) * len;
    } else if (edge === 1) {
      x1 = W + 20;
      y1 = rand() * H;
      const len = W * lengthFactor;
      const angle = (180 + angleOffset) * (Math.PI / 180);
      x2 = x1 + Math.cos(angle) * len;
      y2 = y1 + Math.sin(angle) * len;
    } else if (edge === 2) {
      x1 = rand() * W;
      y1 = H + 20;
      const len = H * lengthFactor;
      const angle = (-90 + angleOffset) * (Math.PI / 180);
      x2 = x1 + Math.cos(angle) * len;
      y2 = y1 + Math.sin(angle) * len;
    } else {
      x1 = -20;
      y1 = rand() * H;
      const len = W * lengthFactor;
      const angle = (0 + angleOffset) * (Math.PI / 180);
      x2 = x1 + Math.cos(angle) * len;
      y2 = y1 + Math.sin(angle) * len;
    }

    lines.push({
      id: i,
      x1,
      y1,
      x2,
      y2,
      dur: 7 + rand() * 13,
      delay: -(rand() * 20),
      strokeW: 0.3 + rand() * 0.7,
      opacity: 0.06 + rand() * 0.12,
    });
  }
  return lines;
}

/**
 * AnimatedLines — full-viewport SVG field of lines that sweep in from
 * all four edges at random angles. Intensity controls how many lines
 * are rendered (default 40 for interior pages, use 52 for entry page).
 */
export function AnimatedLines({
  count = 40,
  seed = 0xdeadbeef,
}: {
  count?: number;
  seed?: number;
}) {
  const [lines, setLines] = useState<SvgLine[]>([]);
  const [dim, setDim] = useState({ w: 1440, h: 900 });

  useEffect(() => {
    const measure = () => setDim({ w: window.innerWidth, h: window.innerHeight });
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  useEffect(() => {
    setLines(buildLines(dim.w, dim.h, count, seed));
  }, [dim.w, dim.h, count, seed]);

  return (
    <svg
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 h-full w-full"
      style={{ zIndex: 0 }}
      viewBox={`0 0 ${dim.w} ${dim.h}`}
      preserveAspectRatio="xMidYMid slice"
    >
      <defs>
        {lines.map((l) => (
          <linearGradient
            key={`g${l.id}`}
            id={`agl${seed}-${l.id}`}
            gradientUnits="userSpaceOnUse"
            x1={l.x1}
            y1={l.y1}
            x2={l.x2}
            y2={l.y2}
          >
            <stop offset="0%" stopColor="var(--ink)" stopOpacity="0" />
            <stop offset="30%" stopColor="var(--ink)" stopOpacity={l.opacity} />
            <stop offset="70%" stopColor="var(--ink)" stopOpacity={l.opacity} />
            <stop offset="100%" stopColor="var(--ink)" stopOpacity="0" />
          </linearGradient>
        ))}
      </defs>

      {lines.map((l) => {
        const len = Math.hypot(l.x2 - l.x1, l.y2 - l.y1);
        return (
          <line
            key={l.id}
            x1={l.x1}
            y1={l.y1}
            x2={l.x2}
            y2={l.y2}
            stroke={`url(#agl${seed}-${l.id})`}
            strokeWidth={l.strokeW}
            strokeLinecap="round"
          >
            <animate
              attributeName="stroke-dasharray"
              from={`0 ${len}`}
              to={`${len} 0`}
              dur={`${l.dur}s`}
              begin={`${l.delay}s`}
              repeatCount="indefinite"
              calcMode="linear"
            />
            <animate
              attributeName="opacity"
              values="0;1;1;0"
              keyTimes="0;0.1;0.9;1"
              dur={`${l.dur}s`}
              begin={`${l.delay}s`}
              repeatCount="indefinite"
            />
          </line>
        );
      })}
    </svg>
  );
}
