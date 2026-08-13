import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_BASE || "";

const SUGGESTIONS = [
  "What undergraduate programs does UET Mardan offer?",
  "What is the admission criteria?",
  "What are the semester fees?",
  "Is hostel accommodation available?",
];

function ThinkingCard() {
  return (
    <div className="msg-row assistant">
      <div className="card thinking-card">
        <span className="tab">PROSPECTUS</span>
        <div className="thinking-dots" aria-live="polite" aria-label="Consulting the prospectus">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </div>
  );
}

function Message({ role, content, isError }) {
  if (role === "user") {
    return (
      <div className="msg-row user">
        <div className="bubble user-bubble">{content}</div>
      </div>
    );
  }
  return (
    <div className="msg-row assistant">
      <div className={`card ${isError ? "error-card" : ""}`}>
        <span className="tab">{isError ? "NOTE" : "PROSPECTUS"}</span>
        <p className="card-text">{content}</p>
      </div>
    </div>
  );
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  async function send(question) {
    const q = (question ?? input).trim();
    if (!q || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.detail || "Something went wrong.");
      }

      setMessages((prev) => [...prev, { role: "assistant", content: data.answer }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: err.message || "The assistant is unreachable.", isError: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div className="page">
      <header className="letterhead">
        <div className="monogram">UM</div>
        <div className="letterhead-text">
          <h1>UET Mardan</h1>
          <p>Undergraduate Prospectus Assistant</p>
        </div>
      </header>
      <hr className="brass-rule" />

      <main className="chat-shell">
        <div className="chat-thread">
          {messages.length === 0 && (
            <div className="empty-state">
              <p>Ask anything found in the undergraduate prospectus — programs, fees, admissions, hostels.</p>
              <div className="chips">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="chip" onClick={() => send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <Message key={i} role={m.role} content={m.content} isError={m.isError} />
          ))}

          {loading && <ThinkingCard />}
          <div ref={scrollRef} />
        </div>

        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about programs, admissions, fees..."
            rows={1}
          />
          <button type="submit" className="send-btn" disabled={loading || !input.trim()} aria-label="Send question">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M4 12L20 4L13 20L11 13L4 12Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
            </svg>
          </button>
        </form>
      </main>
    </div>
  );
}
