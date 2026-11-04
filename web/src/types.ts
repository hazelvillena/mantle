export type Decisions = {
  profile: string;
  fullness: string;
  taper: string;
  "end-coverage": string;
  "panel-layout": string;
  seam: string;
  "access-panel": string;
  finish: string;
};

export type Applied = { decision: string; value: string; source: string };

export type Finding = {
  id: string;
  severity: string;
  pose: string | null;
  parts: string[];
  method: string;
  threshold: number;
  measured: number | null;
  quality: string;
  message: string;
};

export type Build = {
  id: string;
  name: string;
  parentId: string | null;
  decisions: Decisions;
  locks: string[];
  attributes: string[];
  brief: string;
  summary: string;
  parts: { name: string; url: string }[];
  check: {
    buildId: string;
    coverage: string;
    quality: string;
    summary: string;
    blocksExport: boolean;
    findings: Finding[];
    poses: { pose: string; label: string; clear: boolean; message?: string }[];
  };
  elapsedMs: number;
  exportStep: string;
  project: string;
};

export type Alternative = {
  ok: boolean;
  name: string;
  rationale: string;
  applied: Applied[];
  build?: Build;
  error?: string;
};

export type Hardware = {
  name: string;
  part: string;
  units: string;
  mesh: string;
  quality: string;
  assumptions: string[];
  attribution: string;
  canDesign: string;
  center: [number, number, number];
  pivot: [number, number, number];
  keepOut: { id: string; label: string; center: number[]; size: number[] };
};

export type Language = {
  locks: { id: string; label: string; meaning: string }[];
  decisions: { id: keyof Decisions; label: string; affects: string; options: string[] }[];
};

export type Brief = { id: string; name: string; text: string; attributes: string[] };
