export interface KBSource {
  file: string;
  snippet: string;
  score: number | null;
}

export interface WebSource {
  title: string | null;
  url: string | null;
}

export interface ChatResponse {
  answer: string;
  tools_used: string[];
  kb_sources: KBSource[];
  web_sources: WebSource[];
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  tools_used?: string[];
  kb_sources?: KBSource[];
  web_sources?: WebSource[];
}
