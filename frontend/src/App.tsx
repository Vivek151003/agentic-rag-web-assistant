import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { Layers, MessageSquare, Paperclip, Plus, Send, Upload, UserCircle } from "lucide-react";
import { askQuestion, uploadPdf } from "./api";
import type { Message } from "./types";
import { ChatBubble } from "./components/ChatBubble";
import "./App.css";

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const sessionIdRef = useRef(crypto.randomUUID());

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    function handleWindowKeyDown(e: KeyboardEvent) {
      const active = document.activeElement;
      if (active === inputRef.current || loading) return;
      // Ignore modifier combos (shortcuts) and non-printable keys (Tab, Escape, arrows, etc.)
      if (e.ctrlKey || e.metaKey || e.altKey || e.key.length !== 1) return;
      // Don't hijack typing that's already going into some other focusable field.
      if (active instanceof HTMLElement && (active.tagName === "TEXTAREA" || active.isContentEditable)) return;

      inputRef.current?.focus();
    }

    window.addEventListener("keydown", handleWindowKeyDown);
    return () => window.removeEventListener("keydown", handleWindowKeyDown);
  }, [loading]);

  function handleNewChat() {
    setMessages([]);
    setInput("");
    setError(null);
    setLoading(false);
    sessionIdRef.current = crypto.randomUUID();
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    const requestSessionId = sessionIdRef.current;
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const response = await askQuestion(question, requestSessionId);
      // If "New Chat" started a new session while this request was in flight,
      // this reply belongs to the old conversation — drop it.
      if (sessionIdRef.current !== requestSessionId) return;
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.answer,
          tools_used: response.tools_used,
          kb_sources: response.kb_sources,
          web_sources: response.web_sources,
        },
      ]);
    } catch (err) {
      if (sessionIdRef.current !== requestSessionId) return;
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      if (sessionIdRef.current === requestSessionId) setLoading(false);
    }
  }

  async function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-selecting the same file later
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const result = await uploadPdf(file);
      setMessages((prev) => [
        ...prev,
        {
          role: "system",
          content: `Added "${result.filename}" to the knowledge base (${result.chunks_added} chunk${result.chunks_added === 1 ? "" : "s"}).`,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button type="button" className="new-chat-button" onClick={handleNewChat}>
          <Plus size={16} />
          New Chat
        </button>
        <div className="sidebar-spacer" />
        <button type="button" className="sign-in-button">
          <UserCircle size={18} />
          Sign in
        </button>
      </aside>

      <div className="main">
        <header className="header">
          <div className="brand">
            <Layers className="brand-icon" size={22} />
            <span className="brand-text">
              Agentic <span className="brand-accent">RAG+</span>
            </span>
          </div>
          <button
            type="button"
            className="header-upload-button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            <Upload size={16} />
            {uploading ? "Uploading..." : "Upload PDF"}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            onChange={handleFileChange}
            hidden
          />
        </header>

        <main className="chat">
          <div className="chat-inner">
            {messages.length === 0 && (
              <div className="empty-state">
                <div className="empty-icon">
                  <MessageSquare size={26} />
                </div>
                <h2>How can I help you?</h2>
                <p>Ask any question about your PDFs.</p>
                <p>I&rsquo;ll answer from your documents or search the web if needed.</p>
              </div>
            )}
            {messages.map((m, i) => (
              <ChatBubble key={i} message={m} />
            ))}
            {loading && (
              <div className="bubble-row assistant">
                <div className="bubble assistant loading">Thinking...</div>
              </div>
            )}
            {error && <div className="error-banner">{error}</div>}
            <div ref={bottomRef} />
          </div>
        </main>

        <div className="composer-wrap">
          <form className="composer" onSubmit={handleSubmit}>
            <input
              ref={inputRef}
              className="composer-input"
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your question..."
              disabled={loading}
            />
            <div className="composer-toolbar">
              <button
                type="button"
                className="composer-upload"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
              >
                <Paperclip size={14} />
                Upload PDF
              </button>
              <button type="submit" className="composer-send" disabled={loading || !input.trim()}>
                <Send size={16} />
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

export default App;
