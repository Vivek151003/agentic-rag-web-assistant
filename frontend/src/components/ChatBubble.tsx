import type { Message } from "../types";
import { SourcesPanel } from "./SourcesPanel";

export function ChatBubble({ message }: { message: Message }) {
  const isAssistant = message.role === "assistant";

  return (
    <div className={`bubble-row ${message.role}`}>
      <div className={`bubble ${message.role}`}>
        <p>{message.content}</p>
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
