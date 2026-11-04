import { useCallback, useEffect, useState } from "react";
import { Stage } from "./stage";
import type { Alternative, Brief, Build, Decisions, Hardware, Language } from "./types";

type Pose = "extended" | "folded";
type Phase = "editing" | "generating" | "failed";

const LABELS: Record<string, string> = {
  profile: "Profile",
  fullness: "Fullness",
  taper: "Taper",
  "end-coverage": "End coverage",
  "panel-layout": "Panel layout",
  seam: "Seam",
  "access-panel": "Access panel",
  finish: "Finish",
  rounded: "Rounded",
  oval: "Oval",
  faceted: "Faceted",
  close: "Close",
  balanced: "Balanced",
  generous: "Generous",
  none: "None",
  "toward-end": "Toward the end",
  "toward-base": "Toward the base",
  short: "Short",
  standard: "Standard",
  long: "Long",
  "single-shell": "One shell",
  "lengthwise-split": "Lengthwise split",
  "band-and-body": "Band and body",
  tight: "Tight",
  shadow: "Shadow gap",
  open: "Open",
  side: "Side",
  end: "End",
  "matte-white": "Warm white",
  "matte-black": "Black",
  "soft-gray": "Soft gray",
  "quiet-silhouette": "Quiet silhouette",
  "smooth-transitions": "Smooth transitions",
  "concealed-mechanics": "Concealed mechanics",
  paneled: "Purposeful panels",
  "exposed-mechanism": "Exposed mechanism",
  "easy-access": "Easy access",
  approachable: "Approachable",
  "rounded-transitions": "Rounded transitions",
  "maintenance-panel": "Maintenance panel",
};

function label(value: string) {
  return LABELS[value] ?? value;
}

async function failure(response: Response) {
  const body = (await response.json().catch(() => ({}))) as { detail?: string };
  throw new Error(body.detail || "The design could not be built.");
}

export default function App() {
  const [hardware, setHardware] = useState<Hardware | null>(null);
  const [language, setLanguage] = useState<Language | null>(null);
  const [briefs, setBriefs] = useState<Brief[]>([]);
  const [attributes, setAttributes] = useState<string[]>([]);
  const [brief, setBrief] = useState("");
  const [locks, setLocks] = useState<string[]>([]);
  const [alternatives, setAlternatives] = useState<Alternative[]>([]);
  const [selected, setSelected] = useState(0);
  const [phase, setPhase] = useState<Phase>("editing");
  const [error, setError] = useState("");
  const [pose, setPose] = useState<Pose>("extended");
  const [showHardware, setShowHardware] = useState(true);
  const [showExterior, setShowExterior] = useState(true);
  const [ghost, setGhost] = useState(false);
  const [showKeep, setShowKeep] = useState(false);
  const [frame, setFrame] = useState(0);
  const [previous, setPrevious] = useState<Build | null>(null);
  const [compare, setCompare] = useState(false);
  const [ask, setAsk] = useState("");
  const [reply, setReply] = useState("");
  const [past, setPast] = useState<string[]>([]);
  const [future, setFuture] = useState<string[]>([]);
  const [bootError, setBootError] = useState("");

  useEffect(() => {
    Promise.all([
      fetch("/api/hardware").then((response) => response.json()),
      fetch("/api/language").then((response) => response.json()),
      fetch("/api/briefs").then((response) => response.json()),
    ])
      .then(([nextHardware, nextLanguage, nextBriefs]) => {
        setHardware(nextHardware as Hardware);
        setLanguage(nextLanguage as Language);
        setBriefs((nextBriefs as { briefs: Brief[] }).briefs);
      })
      .catch(() => setBootError("The design service is not responding."));
  }, []);

  const current = alternatives[selected]?.build ?? null;

  const remember = useCallback((previousId: string | undefined) => {
    if (!previousId) return;
    setPast((items) => [...items, previousId]);
    setFuture([]);
  }, []);

  const explore = useCallback(
    async (nextAttributes: string[], nextLocks: string[], nextBrief: string) => {
      setPhase("generating");
      setError("");
      setReply("");
      const response = await fetch("/api/explore", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ attributes: nextAttributes, locks: nextLocks, brief: nextBrief }),
      });
      if (!response.ok) await failure(response);
      const body = (await response.json()) as { alternatives: Alternative[] };
      remember(current?.id);
      setPrevious(current);
      setAlternatives(body.alternatives);
      setSelected(0);
      setPhase("editing");
    },
    [current, remember],
  );

  async function chooseBrief(item: Brief) {
    setAttributes(item.attributes);
    setBrief(item.text);
    try {
      await explore(item.attributes, locks, item.text);
    } catch (reason) {
      setPhase("failed");
      setError(reason instanceof Error ? reason.message : "Generation failed.");
    }
  }

  async function toggleAttribute(id: string) {
    const next = attributes.includes(id) ? attributes.filter((item) => item !== id) : [...attributes, id];
    setAttributes(next);
    try {
      await explore(next, locks, brief);
    } catch (reason) {
      setPhase("failed");
      setError(reason instanceof Error ? reason.message : "Generation failed.");
    }
  }

  async function editDecision(id: keyof Decisions, value: string) {
    if (!current) return;
    const decisions = { ...current.decisions, [id]: value };
    setPhase("generating");
    setError("");
    const response = await fetch("/api/builds", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decisions,
        locks,
        attributes,
        brief,
        parentId: current.id,
        summary: `${label(id)} set to ${label(value)}.`,
      }),
    });
    if (!response.ok) {
      setPhase("failed");
      setError(await failureText(response));
      return;
    }
    const build = (await response.json()) as Build;
    remember(current.id);
    setPrevious(current);
    setAlternatives((items) => items.map((item, index) => (index === selected ? { ...item, ok: true, build } : item)));
    setPhase("editing");
  }

  async function runAction(action: string) {
    if (!current) return;
    setPhase("generating");
    const response = await fetch(`/api/builds/${current.id}/actions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });
    if (!response.ok) {
      setPhase("failed");
      setError(await failureText(response));
      return;
    }
    const body = (await response.json()) as { changed: boolean; summary: string; build: Build };
    setReply(body.summary);
    if (body.changed) {
      remember(current.id);
      setPrevious(current);
      setLocks(body.build.locks);
      setAlternatives((items) =>
        items.map((item, index) => (index === selected ? { ...item, ok: true, build: body.build } : item)),
      );
    } else {
      setLocks(body.build.locks);
    }
    setPhase("editing");
  }

  async function restore(id: string) {
    const response = await fetch(`/api/builds/${id}`);
    if (!response.ok) return;
    const build = (await response.json()) as Build;
    setAlternatives([{ ok: true, name: build.name, rationale: build.summary, applied: [], build }]);
    setSelected(0);
    setLocks(build.locks);
    setAttributes(build.attributes);
    setBrief(build.brief);
  }

  const activeBrief = briefs.find((item) => item.attributes.join() === attributes.join())?.id;
  const status = !hardware
    ? "Editing"
    : phase === "generating"
      ? "Generating"
      : phase === "failed"
        ? "Failed"
        : current?.check.blocksExport
          ? "Interference found"
          : current
            ? "Ready for review"
            : "Editing";

  const parts = current?.parts ?? [];

  return (
    <div className="app">
      <header>
        <div className="brand">
          <strong>Mantle</strong>
          <span>Moveo forearm · Guided design</span>
        </div>
        <div className="header-actions">
          <button className="ghost" type="button" disabled={!past.length} onClick={() => {
            const id = past[past.length - 1];
            if (!current) return;
            setFuture((items) => [current.id, ...items]);
            setPast((items) => items.slice(0, -1));
            void restore(id);
          }}>Undo</button>
          <button className="ghost" type="button" disabled={!future.length} onClick={() => {
            const [id, ...rest] = future;
            if (!id || !current) return;
            setPast((items) => [...items, current.id]);
            setFuture(rest);
            void restore(id);
          }}>Redo</button>
          <a className={current ? "ghost" : "ghost"} href={current?.project ?? "#"} aria-disabled={!current} onClick={(event) => { if (!current) event.preventDefault(); }}>Project</a>
          <a className="solid" href={current && !current.check.blocksExport ? current.exportStep : "#"} onClick={(event) => { if (!current || current.check.blocksExport) event.preventDefault(); }}>Export STEP</a>
        </div>
      </header>

      <aside className="panel">
        <h2>Around this link</h2>
        <p className="lede">{hardware?.canDesign ?? "Loading the prepared arm."}</p>
        <p className="quiet">{hardware?.quality}</p>
        <h2>Brief</h2>
        <div className="briefs" role="group" aria-label="Example briefs">
          {briefs.map((item) => (
            <button key={item.id} type="button" aria-pressed={activeBrief === item.id} onClick={() => void chooseBrief(item)}>
              {item.name}
            </button>
          ))}
        </div>
        <div className="attrs" aria-label="Brief attributes">
          {["quiet-silhouette", "smooth-transitions", "concealed-mechanics", "paneled", "exposed-mechanism", "easy-access", "approachable", "rounded-transitions", "maintenance-panel"].map((id) => (
            <button key={id} type="button" aria-pressed={attributes.includes(id)} onClick={() => void toggleAttribute(id)}>
              {label(id)}
            </button>
          ))}
        </div>
        <textarea aria-label="Written brief" value={brief} placeholder="A note to keep with this design." onChange={(event) => setBrief(event.target.value)} />
        <p className="quiet">The note is saved. Only the selected attributes change the shape.</p>
        {!!current && (
          <ul className="applied">
            {alternatives[selected]?.applied.map((item) => (
              <li key={item.decision} className="quiet">{label(item.decision)} · {label(item.value)} · {item.source}</li>
            ))}
          </ul>
        )}
        <h2>Alternatives</h2>
        <div className="alts">
          {alternatives.map((item, index) => (
            <button key={`${item.name}-${index}`} className="alt" type="button" aria-pressed={index === selected} onClick={() => setSelected(index)}>
              <strong>{item.name}</strong>
              <span className="quiet">{item.ok ? item.rationale : item.error}</span>
            </button>
          ))}
          {!alternatives.length && <p className="quiet">Choose a brief to generate three covers.</p>}
        </div>
      </aside>

      <main className="stage">
        {hardware && (
          <Stage
            hardware={hardware}
            parts={parts}
            previousParts={compare && previous ? previous.parts : []}
            finish={current?.decisions.finish ?? "matte-white"}
            pose={pose}
            showHardware={showHardware}
            showExterior={showExterior && (parts.length > 0 || (compare && !!previous))}
            ghost={ghost}
            showKeep={showKeep || Boolean(current?.check.blocksExport)}
            frame={frame}
          />
        )}
        <div className="stage-tools">
          <button className="ghost" type="button" aria-pressed={showHardware} onClick={() => setShowHardware((value) => !value)}>Machinery</button>
          <button className="ghost" type="button" aria-pressed={showExterior} onClick={() => setShowExterior((value) => !value)}>Exterior</button>
          <button className="ghost" type="button" aria-pressed={ghost} onClick={() => setGhost((value) => !value)}>Ghost</button>
          <button className="ghost" type="button" aria-pressed={compare} disabled={!previous} onClick={() => setCompare((value) => !value)}>Previous</button>
          <button className="ghost" type="button" aria-pressed={pose === "folded"} onClick={() => setPose((value) => (value === "extended" ? "folded" : "extended"))}>{pose === "extended" ? "Extended" : "Folded"}</button>
          <button className="ghost" type="button" onClick={() => setFrame((value) => value + 1)}>Frame</button>
        </div>
        {!current && <p className="stage-note">The gray part is the official Moveo link. A cover appears here after you choose a brief.</p>}
        {bootError && <p className="stage-note">{bootError}</p>}
      </main>

      <aside className="panel right">
        <h2>Decisions</h2>
        {language?.decisions.map((decision) => (
          <div className="decision" key={decision.id}>
            <p>{decision.label}<span className="quiet affects">{decision.affects === "appearance" ? "Appearance only" : "Changes geometry"}</span></p>
            <div className="segmented" role="radiogroup" aria-label={decision.label}>
              {decision.options.map((option) => (
                <button
                  key={option}
                  type="button"
                  role="radio"
                  aria-checked={current?.decisions[decision.id] === option}
                  disabled={!current || phase === "generating" || (decision.id === "panel-layout" && locks.includes("seam-layout") && current.decisions[decision.id] !== option)}
                  onClick={() => void editDecision(decision.id, option)}
                >
                  {label(option)}
                </button>
              ))}
            </div>
          </div>
        ))}
        <div className="lock">
          <button
            className="ghost"
            type="button"
            disabled={!current}
            aria-pressed={locks.includes("seam-layout")}
            onClick={() => {
              if (locks.includes("seam-layout")) setLocks((items) => items.filter((item) => item !== "seam-layout"));
              else void runAction("preserve-seam-layout");
            }}
          >
            {locks.includes("seam-layout") ? "Seam layout locked" : "Preserve seam layout"}
          </button>
          <p className="quiet">{language?.locks[0]?.meaning}</p>
          <button className="ghost" type="button" disabled={!current || phase === "generating"} onClick={() => void runAction("slimmer")}>Slimmer</button>
          <p className="quiet">Wall 2.6 mm. Clearance to the envelope 3.0 mm. Finish does not claim a material.</p>
        </div>
        <h2>Ask</h2>
        <form className="ask" onSubmit={(event) => {
          event.preventDefault();
          if (!ask.trim()) return;
          setReply("Guided design can't read that sentence. Language interpretation is not connected. Use Slimmer, Preserve seam layout, or the controls on the right.");
        }}>
          <input aria-label="Revision request" value={ask} onChange={(event) => setAsk(event.target.value)} placeholder="Try a sentence" />
          <button className="ghost" type="submit">Send</button>
        </form>
        {reply && <p className="quiet">{reply}</p>}
      </aside>

      <footer>
        <div className={status === "Interference found" || status === "Failed" ? "status bad" : "status"}>
          <b>{status}</b>
          <span className="quiet">
            {phase === "generating" && current ? "Showing the previous revision while this one is built. " : ""}
            {phase === "failed" && current ? "Showing the previous revision. " : ""}
            {error || current?.check.summary || hardware?.attribution || ""}
          </span>
        </div>
        {!!current?.check.findings.length && (
          <div className="findings">
            {current.check.findings.map((finding) => (
              <div className="finding" key={finding.id}>
                <button type="button" onClick={() => {
                  if (finding.pose === "extended" || finding.pose === "folded") setPose(finding.pose);
                  setShowKeep(true);
                  setShowHardware(true);
                }}>{finding.message}</button>
                {finding.id.startsWith("keep-out-") && current.decisions["end-coverage"] !== "short" && (
                  <button
                    type="button"
                    disabled={phase === "generating"}
                    onClick={() => void runAction("reduce-end-coverage")}
                  >
                    Reduce end coverage
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
        {current && <p className="quiet">{current.check.coverage} {current.elapsedMs} ms. {current.check.quality}</p>}
      </footer>
    </div>
  );
}

async function failureText(response: Response) {
  const body = (await response.json().catch(() => ({}))) as { detail?: string };
  return body.detail || "The design could not be built.";
}
