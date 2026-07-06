import { useState } from "react";
import type { KBSource, WebSource } from "../types";

interface Props {
  kbSources: KBSource[];
  webSources: WebSource[];
}

export function SourcesPanel({ kbSources, webSources }: Props) {
  const [open, setOpen] = useState(false);
  const total = kbSources.length + webSources.length;
  if (total === 0) return null;

  return (
    <div className="sources">
      <button
        type="button"
        className="sources-toggle"
        onClick={() => setOpen((o) => !o)}
      >
        {open ? "▾" : "▸"} Sources ({total})
      </button>
      {open && (
        <div className="sources-list">
          {kbSources.map((s, i) => (
            <div key={`kb-${i}`} className="source-item">
              <span className="source-icon" aria-hidden>
                📄
              </span>
              <div>
                <div className="source-title">
                  {s.file}
                  {s.score !== null && (
                    <span className="source-score"> · score {s.score.toFixed(3)}</span>
                  )}
                </div>
                <div className="source-snippet">{s.snippet}</div>
              </div>
            </div>
          ))}
          {webSources.map((s, i) => (
            <div key={`web-${i}`} className="source-item">
              <span className="source-icon" aria-hidden>
                🌐
              </span>
              <div>
                <a
                  className="source-title"
                  href={s.url ?? "#"}
                  target="_blank"
                  rel="noreferrer"
                >
                  {s.title ?? s.url}
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
