import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "../types";
import { SourcesPanel } from "./SourcesPanel";

const markdownComponents = {
  table: ({ ...props }) => (
    <div className="md-table-wrap">
      <table {...props} />
    </div>
  ),
};

// Models often emit literal <br> tags inside GFM table cells (the only way to
// break lines within a cell in plain markdown). We don't parse raw HTML here
// (that would mean trusting arbitrary LLM/document-sourced content with real
// HTML injection), so swap it for a plain separator instead of leaving the
// literal tag text visible.
function stripLineBreakTags(content: string): string {
  return content.replace(/<br\s*\/?>/gi, " ");
}

export function ChatBubble({ message }: { message: Message }) {
  const isAssistant = message.role === "assistant";

  if (message.role === "system") {
    return (
      <div className="bubble-row system">
        <div className="bubble system">{message.content}</div>
      </div>
    );
  }

  return (
    <div className={`bubble-row ${message.role}`}>
      <div className={`bubble ${message.role}`}>
        {isAssistant ? (
          <div className="markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
              {stripLineBreakTags(message.content)}
            </ReactMarkdown>
          </div>
        ) : (
          <p>{message.content}</p>
        )}
        {isAssistant && message.tools_used && message.tools_used.length > 0 && (
          <div className="tools-used">Tools used: {message.tools_used.join(", ")}</div>
        )}
        {isAssistant && (
          <SourcesPanel
            kbSources={message.kb_sources ?? []}
            webSources={message.web_sources ?? []}
          />
        )}
      </div>
    </div>
  );
}
