"use client";
import { useState, useMemo } from "react";
import Logo from "./Logo";

interface Model {
  id: string;
  name: string;
  provider_logo: string;
}

interface QModel {
  correct: boolean | null;
  answer: string | null;
}

interface QuestionResponse {
  question_id: string;
  specialty: string;
  test_year: number;
  correct_letter: string;
  models: Record<string, QModel>;
}

interface QuestionResponses {
  models: string[];
  questions: QuestionResponse[];
}

export default function QuestionsView({
  qdata,
  models,
}: {
  qdata: QuestionResponses | null;
  models: Model[];
}) {
  const [specialty, setSpecialty] = useState("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const PER_PAGE = 50;

  const specialties = useMemo(() => {
    if (!qdata) return [];
    const s = new Set<string>();
    qdata.questions.forEach((q) => s.add(q.specialty));
    return Array.from(s).sort();
  }, [qdata]);

  const filtered = useMemo(() => {
    if (!qdata) return [];
    let rows = qdata.questions;
    if (specialty !== "all") rows = rows.filter((q) => q.specialty === specialty);
    if (search) {
      const q = search.toLowerCase();
      rows = rows.filter(
        (r) => r.question_id.toLowerCase().includes(q) || r.specialty.toLowerCase().includes(q)
      );
    }
    return rows;
  }, [qdata, specialty, search]);

  // Reset page when filters change
  const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE));
  const safePage = Math.min(page, totalPages - 1);
  const pageRows = filtered.slice(safePage * PER_PAGE, safePage * PER_PAGE + PER_PAGE);

  if (!qdata) {
    return (
      <div className="section">
        <div className="section-body" style={{ textAlign: "center", color: "var(--text-muted)" }}>
          Loading question responses…
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="section">
        <div className="section-header">
          <h2>Question Responses ({filtered.length.toLocaleString()})</h2>
          <div className="filters">
            <select className="spec-select" value={specialty} onChange={(e) => { setSpecialty(e.target.value); setPage(0); }}>
              <option value="all">All Specialties</option>
              {specialties.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <div className="search-wrap">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.35-4.35" />
              </svg>
              <input
                className="search-input"
                placeholder="Search question ID or specialty…"
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(0); }}
              />
            </div>
          </div>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="lb-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Question</th>
                <th>Specialty</th>
                <th>Year</th>
                <th>Correct</th>
                {models.map((m) => (
                  <th key={m.id}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                      <Logo name={m.provider_logo} size={20} />
                      <span style={{ fontSize: "0.62rem", fontWeight: 600 }}>{m.name.split(":")[0]}</span>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pageRows.map((q, i) => (
                <tr key={q.question_id}>
                  <td className="rank-cell">{safePage * PER_PAGE + i + 1}</td>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>{q.question_id}</td>
                  <td>{q.specialty}</td>
                  <td style={{ color: "var(--text-secondary)" }}>SSM {q.test_year}</td>
                  <td style={{ fontWeight: 700, color: "var(--green)" }}>{q.correct_letter}</td>
                  {models.map((m) => {
                    const r = q.models[m.id];
                    const c = r?.correct;
                    return (
                      <td key={m.id} style={{ textAlign: "center" }}>
                        {c === null ? (
                          <span style={{ color: "var(--text-muted)" }}>—</span>
                        ) : c ? (
                          <span style={{ color: "var(--green)", fontWeight: 700 }}>✓</span>
                        ) : (
                          <span style={{ color: "var(--red)", fontWeight: 700 }}>✗</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 16, padding: "14px 20px", borderTop: "1px solid var(--border)" }}>
            <button className="btn-secondary" onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={safePage === 0}>
              ← Prev
            </button>
            <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
              Page {safePage + 1} / {totalPages} · {filtered.length.toLocaleString()} questions
            </span>
            <button className="btn-secondary" onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} disabled={safePage >= totalPages - 1}>
              Next →
            </button>
          </div>
        )}
      </div>
    </>
  );
}
