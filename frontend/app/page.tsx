"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import Logo from "./components/Logo";

/* ─── Types ────────────────────────────────────────── */
interface Model {
  id: string;
  name: string;
  provider: string;
  provider_logo: string;
  overall_accuracy: number;
  total_correct: number;
  total_questions: number;
  rank: number;
  specialty_scores: Record<string, number>;
  year_scores: Record<string, number>;
  test_date: string;
}

interface Dataset {
  name: string;
  full_name: string;
  language: string;
  country: string;
  status: "active" | "upcoming";
  description: string;
  question_count: number;
}

interface LeaderboardData {
  last_updated: string;
  version: string;
  datasets: Record<string, Dataset>;
  specialties: Record<string, number>;
  years: string[];
  models: Model[];
}

/* ─── Color palette for models (bar fills) ─────────── */
const MODEL_COLORS: Record<string, string> = {
  "claude-sonnet-4": "#d97706",
  "gemini-2.5-pro": "#2563eb",
  "deepseek-r1": "#4D6BFE",
  "gpt-4o": "#10a37f",
  "claude-haiku-3.5": "#f59e0b",
  "gemini-2.5-flash": "#60a5fa",
  "qwen3-235b": "#FF6A00",
  "mistral-large": "#F70000",
  "gpt-4o-mini": "#6ee7b7",
  "llama-3.3-70b": "#0082FB",
};

function getModelColor(id: string) {
  return MODEL_COLORS[id] || "#6b7280";
}

/* ─── Heatmap color helper ─────────────────────────── */
function scoreColor(score: number): string {
  if (score >= 85) return "#059669";
  if (score >= 75) return "#10b981";
  if (score >= 65) return "#f59e0b";
  if (score >= 55) return "#f97316";
  return "#ef4444";
}

function scoreBg(score: number): string {
  if (score >= 85) return "#d1fae5";
  if (score >= 75) return "#a7f3d0";
  if (score >= 65) return "#fef3c7";
  if (score >= 55) return "#ffedd5";
  return "#fee2e2";
}

/* ─── Main Page ────────────────────────────────────── */
export default function LeaderboardPage() {
  const [data, setData] = useState<LeaderboardData | null>(null);
  const [view, setView] = useState<"leaderboard" | "analysis" | "compare">("leaderboard");
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<"rank" | "name" | "overall_accuracy">("rank");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [selectedSpecialty, setSelectedSpecialty] = useState<string>("all");
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);

  useEffect(() => {
    fetch("/leaderboard_data.json")
      .then((r) => r.json())
      .then(setData);
  }, []);

  const toggleSort = useCallback((key: typeof sortKey) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir(key === "name" ? "asc" : "asc"); }
  }, [sortKey]);

  const sortedModels = useMemo(() => {
    if (!data) return [];
    let models = [...data.models];

    // Filter by search
    if (search) {
      const q = search.toLowerCase();
      models = models.filter(
        (m) => m.name.toLowerCase().includes(q) || m.provider.toLowerCase().includes(q)
      );
    }

    // Sort
    models.sort((a, b) => {
      let cmp = 0;
      if (sortKey === "rank") cmp = a.rank - b.rank;
      else if (sortKey === "name") cmp = a.name.localeCompare(b.name);
      else if (sortKey === "overall_accuracy") cmp = b.overall_accuracy - a.overall_accuracy;
      return sortDir === "asc" ? cmp : -cmp;
    });

    return models;
  }, [data, search, sortKey, sortDir]);

  // Top 10 specialties for the chart
  const topSpecialties = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.specialties)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 15)
      .map(([name]) => name);
  }, [data]);

  const toggleCompare = useCallback((id: string) => {
    setCompareIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : prev.length < 4 ? [...prev, id] : prev
    );
  }, []);

  const compareModels = useMemo(
    () => (data?.models || []).filter((m) => compareIds.includes(m.id)),
    [data, compareIds]
  );

  if (!data) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: "100px 0" }}>
        <div style={{ textAlign: "center", color: "#9ca3af" }}>
          <div style={{ fontSize: "1.5rem", marginBottom: 8 }}>⏳</div>
          <div>Loading leaderboard data…</div>
        </div>
      </div>
    );
  }

  const maxAccuracy = Math.max(...data.models.map((m) => m.overall_accuracy));

  return (
    <>
      {/* ─── Header ────────────────────────────────── */}
      <header className="header">
        <div className="header-inner">
          <div className="logo">
            <div className="logo-mark">MB</div>
            MedBench
          </div>
          <nav className="header-nav">
            <button className={view === "leaderboard" ? "active" : ""} onClick={() => setView("leaderboard")}>
              Leaderboard
            </button>
            <button className={view === "analysis" ? "active" : ""} onClick={() => setView("analysis")}>
              Analysis
            </button>
            <button className={view === "compare" ? "active" : ""} onClick={() => setView("compare")}>
              Compare{compareIds.length > 0 ? ` (${compareIds.length})` : ""}
            </button>
          </nav>
        </div>
      </header>

      <main className="main">
        {/* ─── Hero ───────────────────────────────── */}
        <div className="hero">
          <h1>Medical AI Evaluation Leaderboard</h1>
          <p>
            Benchmarking large language models on European medical residency examinations.
            {data.models.length} models evaluated across {Object.keys(data.specialties).length} specialties.
            Last updated {new Date(data.last_updated).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}.
          </p>
        </div>

        {/* ─── Dataset Cards ──────────────────────── */}
        <div className="datasets-row">
          {Object.entries(data.datasets).map(([key, ds]) => (
            <div key={key} className={`dataset-card ${ds.status === "upcoming" ? "upcoming" : ""}`}>
              <div className="flag">{ds.country.split(" ").slice(-1)[0]}</div>
              <div className="name">{ds.name}</div>
              <div className="detail">{ds.full_name}</div>
              <div className="detail">
                {ds.status === "active"
                  ? `${ds.question_count.toLocaleString()} questions · ${ds.language}`
                  : `${ds.language} · Coming soon`}
              </div>
              <span className={`badge ${ds.status === "active" ? "badge-active" : "badge-upcoming"}`}>
                {ds.status === "active" ? "Active" : "Upcoming"}
              </span>
            </div>
          ))}
        </div>

        {/* ─── LEADERBOARD VIEW ───────────────────── */}
        {view === "leaderboard" && (
          <>
            {/* Compare strip */}
            {compareIds.length > 0 && (
              <div className="compare-strip">
                <span className="label">Compare:</span>
                {compareModels.map((m) => (
                  <span key={m.id} className="compare-chip">
                    <Logo name={m.provider_logo} size={20} />
                    {m.name}
                    <button onClick={() => toggleCompare(m.id)}>×</button>
                  </span>
                ))}
                <div className="compare-actions">
                  <button className="btn-primary" onClick={() => setView("compare")}>
                    View Comparison
                  </button>
                  <button className="btn-secondary" onClick={() => setCompareIds([])}>
                    Clear
                  </button>
                </div>
              </div>
            )}

            {/* Filters */}
            <div className="section">
              <div className="section-header">
                <h2>Models ({sortedModels.length})</h2>
                <div className="filters">
                  <div className="search-wrap">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="11" cy="11" r="8" />
                      <path d="m21 21-4.35-4.35" />
                    </svg>
                    <input
                      className="search-input"
                      placeholder="Search models…"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                  </div>
                </div>
              </div>
              <div style={{ overflowX: "auto" }}>
                <table className="lb-table">
                  <thead>
                    <tr>
                      <th></th>
                      <th onClick={() => toggleSort("rank")} className={sortKey === "rank" ? "sorted" : ""}>
                        #{sortKey === "rank" ? (sortDir === "asc" ? "↑" : "↓") : ""}
                      </th>
                      <th onClick={() => toggleSort("name")} className={sortKey === "name" ? "sorted" : ""}>
                        Model{sortKey === "name" ? (sortDir === "asc" ? "↑" : "↓") : ""}
                      </th>
                      <th>Provider</th>
                      <th onClick={() => toggleSort("overall_accuracy")} className={sortKey === "overall_accuracy" ? "sorted" : ""}>
                        Accuracy{sortKey === "overall_accuracy" ? (sortDir === "asc" ? "↑" : "↓") : ""}
                      </th>
                      <th>
                        {selectedSpecialty === "all" ? "Score" : selectedSpecialty}
                      </th>
                      <th>Compare</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedModels.map((m) => {
                      const specScore = selectedSpecialty === "all"
                        ? m.overall_accuracy
                        : m.specialty_scores[selectedSpecialty] ?? null;
                      return (
                        <tr
                          key={m.id}
                          className={selectedModel?.id === m.id ? "selected" : ""}
                          onClick={() => setSelectedModel(m)}
                          style={{ cursor: "pointer" }}
                        >
                          <td>
                            <div
                              className={`compare-toggle ${compareIds.includes(m.id) ? "checked" : ""}`}
                              onClick={(e) => { e.stopPropagation(); toggleCompare(m.id); }}
                            />
                          </td>
                          <td className={`rank-cell ${m.rank <= 3 ? `rank-${m.rank}` : ""}`}>
                            {m.rank}
                          </td>
                          <td>
                            <div className="model-cell">
                              <Logo name={m.provider_logo} size={26} />
                              <div className="model-info">
                                <span className="model-name">{m.name}</span>
                              </div>
                            </div>
                          </td>
                          <td style={{ color: "#6b7280", fontSize: "0.82rem" }}>{m.provider}</td>
                          <td>
                            <div className="score-bar-wrap">
                              <span className="score-value">{m.overall_accuracy.toFixed(1)}%</span>
                              <div className="score-bar">
                                <div
                                  className="score-bar-fill bar-green"
                                  style={{ width: `${(m.overall_accuracy / 100) * 100}%`, background: getModelColor(m.id) }}
                                />
                              </div>
                            </div>
                          </td>
                          <td>
                            {specScore !== null ? (
                              <div className="score-bar-wrap">
                                <span className="score-value">{specScore.toFixed(1)}%</span>
                                <div className="score-bar">
                                  <div
                                    className="score-bar-fill bar-blue"
                                    style={{ width: `${(specScore / 100) * 100}%`, background: getModelColor(m.id), opacity: 0.7 }}
                                  />
                                </div>
                              </div>
                            ) : (
                              <span style={{ color: "#d1d5db" }}>—</span>
                            )}
                          </td>
                          <td />
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Quick stats bar chart */}
            <div className="chart-grid">
              <div className="chart-card">
                <h3>Overall Accuracy</h3>
                <div className="bar-chart">
                  {[...data.models]
                    .sort((a, b) => b.overall_accuracy - a.overall_accuracy)
                    .map((m) => (
                      <div key={m.id} className="bar-row">
                        <div className="bar-label">{m.name}</div>
                        <div className="bar-track">
                          <div
                            className="bar-fill"
                            style={{
                              width: `${m.overall_accuracy}%`,
                              background: getModelColor(m.id),
                            }}
                          >
                            {m.overall_accuracy.toFixed(1)}
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              <div className="chart-card">
                <h3>Top Specialties by Question Count</h3>
                <div className="bar-chart">
                  {topSpecialties.slice(0, 10).map((spec) => {
                    const count = data.specialties[spec];
                    const maxCount = data.specialties[topSpecialties[0]];
                    return (
                      <div key={spec} className="bar-row">
                        <div className="bar-label">{spec}</div>
                        <div className="bar-track">
                          <div
                            className="bar-fill"
                            style={{
                              width: `${(count / maxCount) * 100}%`,
                              background: "#6b7280",
                            }}
                          >
                            {count}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </>
        )}

        {/* ─── ANALYSIS VIEW ──────────────────────── */}
        {view === "analysis" && (
          <>
            {/* Specialty filter */}
            <div style={{ marginBottom: 16, display: "flex", gap: 6, flexWrap: "wrap" }}>
              <button
                className={`filter-btn ${selectedSpecialty === "all" ? "active" : ""}`}
                onClick={() => setSelectedSpecialty("all")}
              >
                All Specialties
              </button>
              {topSpecialties.map((spec) => (
                <button
                  key={spec}
                  className={`filter-btn ${selectedSpecialty === spec ? "active" : ""}`}
                  onClick={() => setSelectedSpecialty(spec)}
                >
                  {spec}
                </button>
              ))}
            </div>

            {/* Heatmap */}
            <div className="section">
              <div className="section-header">
                <h2>
                  {selectedSpecialty === "all"
                    ? "Performance Heatmap — Models × Specialties"
                    : `Detailed View — ${selectedSpecialty}`}
                </h2>
              </div>
              <div className="section-body">
                <div className="heatmap-wrap">
                  <table className="heatmap-table">
                    <thead>
                      <tr>
                        <th></th>
                        {[...data.models]
                          .sort((a, b) => b.overall_accuracy - a.overall_accuracy)
                          .map((m) => (
                            <th key={m.id} style={{ minWidth: 70 }}>
                              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
                                <Logo name={m.provider_logo} size={18} />
                                <span style={{ fontSize: "0.65rem" }}>{m.name.split(" ").slice(-1)[0]}</span>
                              </div>
                            </th>
                          ))}
                      </tr>
                    </thead>
                    <tbody>
                      {topSpecialties.map((spec) => (
                        <tr key={spec}>
                          <td>{spec}</td>
                          {[...data.models]
                            .sort((a, b) => b.overall_accuracy - a.overall_accuracy)
                            .map((m) => {
                              const score = m.specialty_scores[spec];
                              return (
                                <td
                                  key={m.id}
                                  style={{
                                    background: score != null ? scoreBg(score) : "#f9fafb",
                                    color: score != null ? scoreColor(score) : "#d1d5db",
                                    fontWeight: selectedSpecialty === spec ? 700 : 500,
                                    outline: selectedSpecialty === spec ? "2px solid #2563eb" : "none",
                                  }}
                                >
                                  {score != null ? score.toFixed(0) : "—"}
                                </td>
                              );
                            })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Year-over-year chart */}
            <div className="chart-grid">
              <div className="chart-card">
                <h3>Accuracy by Exam Year</h3>
                <div className="bar-chart">
                  {data.years.map((year) => {
                    const avgScore =
                      data.models.reduce((sum, m) => sum + (m.year_scores[year] || 0), 0) /
                      data.models.length;
                    return (
                      <div key={year} className="bar-row">
                        <div className="bar-label">SSM {year}</div>
                        <div className="bar-track">
                          <div
                            className="bar-fill"
                            style={{
                              width: `${avgScore}%`,
                              background: "#2563eb",
                            }}
                          >
                            {avgScore.toFixed(1)}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="chart-card">
                <h3>Model Consistency (Std Dev across specialties)</h3>
                <div className="bar-chart">
                  {[...data.models]
                    .map((m) => {
                      const scores = Object.values(m.specialty_scores);
                      const mean = scores.reduce((a, b) => a + b, 0) / scores.length;
                      const std = Math.sqrt(scores.reduce((a, b) => a + (b - mean) ** 2, 0) / scores.length);
                      return { ...m, std };
                    })
                    .sort((a, b) => a.std - b.std)
                    .map((m) => (
                      <div key={m.id} className="bar-row">
                        <div className="bar-label">{m.name}</div>
                        <div className="bar-track">
                          <div
                            className="bar-fill"
                            style={{
                              width: `${(m.std / 20) * 100}%`,
                              background: getModelColor(m.id),
                            }}
                          >
                            {m.std.toFixed(1)}
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          </>
        )}

        {/* ─── COMPARE VIEW ───────────────────────── */}
        {view === "compare" && (
          <>
            {compareModels.length === 0 ? (
              <div className="empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M9 17H5a2 2 0 01-2-2V5a2 2 0 012-2h14a2 2 0 012 2v10a2 2 0 01-2 2h-4" />
                  <path d="m12 15 5 6H7Z" />
                </svg>
                <p>Select models from the Leaderboard to compare them side-by-side.</p>
                <button className="btn-primary" style={{ marginTop: 16 }} onClick={() => setView("leaderboard")}>
                  Go to Leaderboard
                </button>
              </div>
            ) : (
              <>
                <div className="section">
                  <div className="section-header">
                    <h2>Overall Comparison</h2>
                    <div style={{ display: "flex", gap: 6 }}>
                      {compareModels.map((m) => (
                        <span key={m.id} className="compare-chip">
                          <Logo name={m.provider_logo} size={20} />
                          {m.name}
                          <button onClick={() => toggleCompare(m.id)}>×</button>
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="section-body">
                    <div className={`compare-grid compare-grid-${Math.min(compareModels.length, 2)}`}>
                      {compareModels.map((m) => (
                        <div key={m.id} className="compare-col">
                          <div className="compare-col-header">
                            <Logo name={m.provider_logo} size={22} />
                            <span>{m.name}</span>
                          </div>
                          <div className="compare-col-body">
                            <div className="compare-metric">
                              <span className="metric-label">Overall Accuracy</span>
                              <span className="metric-value">{m.overall_accuracy.toFixed(1)}%</span>
                            </div>
                            <div className="compare-metric">
                              <span className="metric-label">Rank</span>
                              <span className="metric-value">#{m.rank}</span>
                            </div>
                            <div className="compare-metric">
                              <span className="metric-label">Correct</span>
                              <span className="metric-value">
                                {m.total_correct}/{m.total_questions}
                              </span>
                            </div>
                            <div className="compare-metric">
                              <span className="metric-label">Specialties Evaluated</span>
                              <span className="metric-value">{Object.keys(m.specialty_scores).length}</span>
                            </div>
                            <div className="compare-metric">
                              <span className="metric-label">Best Specialty</span>
                              <span className="metric-value">
                                {Object.entries(m.specialty_scores).sort((a, b) => b[1] - a[1])[0]?.[0]}
                              </span>
                            </div>
                            <div className="compare-metric">
                              <span className="metric-label">Best Score</span>
                              <span className="metric-value metric-winner">
                                {Object.entries(m.specialty_scores).sort((a, b) => b[1] - a[1])[0]?.[1].toFixed(1)}%
                              </span>
                            </div>
                            <div className="compare-metric">
                              <span className="metric-label">Worst Specialty</span>
                              <span className="metric-value">
                                {Object.entries(m.specialty_scores).sort((a, b) => a[1] - b[1])[0]?.[0]}
                              </span>
                            </div>
                            <div className="compare-metric">
                              <span className="metric-label">Worst Score</span>
                              <span className="metric-value" style={{ color: "#dc2626" }}>
                                {Object.entries(m.specialty_scores).sort((a, b) => a[1] - b[1])[0]?.[1].toFixed(1)}%
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Head-to-head specialty comparison */}
                <div className="section">
                  <div className="section-header">
                    <h2>Specialty Head-to-Head</h2>
                  </div>
                  <div className="section-body">
                    <div className="heatmap-wrap">
                      <table className="heatmap-table">
                        <thead>
                          <tr>
                            <th>Specialty</th>
                            {compareModels.map((m) => (
                              <th key={m.id}>
                                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
                                  <Logo name={m.provider_logo} size={18} />
                                  <span style={{ fontSize: "0.65rem" }}>{m.name}</span>
                                </div>
                              </th>
                            ))}
                            <th>Difference</th>
                          </tr>
                        </thead>
                        <tbody>
                          {topSpecialties.map((spec) => {
                            const scores = compareModels.map((m) => m.specialty_scores[spec] ?? 0);
                            const diff = scores.length >= 2 ? scores[0] - scores[1] : 0;
                            return (
                              <tr key={spec}>
                                <td>{spec}</td>
                                {compareModels.map((m, i) => {
                                  const score = m.specialty_scores[spec];
                                  return (
                                    <td
                                      key={m.id}
                                      style={{
                                        background: score != null ? scoreBg(score) : "#f9fafb",
                                        color: score != null ? scoreColor(score) : "#d1d5db",
                                        fontWeight: i === 0 && scores.length >= 2 && diff > 0 ? 700 :
                                                    i === 1 && scores.length >= 2 && diff < 0 ? 700 : 500,
                                      }}
                                    >
                                      {score != null ? score.toFixed(1) : "—"}
                                    </td>
                                  );
                                })}
                                <td
                                  style={{
                                    color: diff > 0 ? "#059669" : diff < 0 ? "#dc2626" : "#6b7280",
                                    fontWeight: 600,
                                  }}
                                >
                                  {scores.length >= 2 ? `${diff > 0 ? "+" : ""}${diff.toFixed(1)}` : "—"}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </>
            )}
          </>
        )}

        {/* ─── Model Detail Panel ─────────────────── */}
        {selectedModel && (
          <div className="detail-overlay" onClick={() => setSelectedModel(null)}>
            <div className="detail-panel" onClick={(e) => e.stopPropagation()}>
              <div className="detail-header">
                <h2>
                  <Logo name={selectedModel.provider_logo} size={28} />
                  {selectedModel.name}
                </h2>
                <button className="detail-close" onClick={() => setSelectedModel(null)}>
                  ×
                </button>
              </div>
              <div className="detail-body">
                <div className="detail-stat-grid">
                  <div className="detail-stat">
                    <div className="value">#{selectedModel.rank}</div>
                    <div className="label">Rank</div>
                  </div>
                  <div className="detail-stat">
                    <div className="value">{selectedModel.overall_accuracy.toFixed(1)}%</div>
                    <div className="label">Accuracy</div>
                  </div>
                  <div className="detail-stat">
                    <div className="value">{selectedModel.total_correct}</div>
                    <div className="label">Correct</div>
                  </div>
                </div>

                <div className="detail-section">
                  <h3>Provider</h3>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.9rem" }}>
                    <Logo name={selectedModel.provider_logo} size={20} />
                    <span style={{ fontWeight: 500 }}>{selectedModel.provider}</span>
                  </div>
                </div>

                <div className="detail-section">
                  <h3>Year Performance</h3>
                  <div className="bar-chart">
                    {Object.entries(selectedModel.year_scores)
                      .sort((a, b) => a[0].localeCompare(b[0]))
                      .map(([year, score]) => (
                        <div key={year} className="bar-row">
                          <div className="bar-label">SSM {year}</div>
                          <div className="bar-track">
                            <div
                              className="bar-fill"
                              style={{ width: `${score}%`, background: getModelColor(selectedModel.id) }}
                            >
                              {score.toFixed(1)}
                            </div>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>

                <div className="detail-section">
                  <h3>All Specialties ({Object.keys(selectedModel.specialty_scores).length})</h3>
                  <div className="spec-grid">
                    {Object.entries(selectedModel.specialty_scores)
                      .sort((a, b) => b[1] - a[1])
                      .map(([spec, score]) => (
                        <div key={spec} className="spec-item">
                          <span className="spec-name">{spec}</span>
                          <span className="spec-score" style={{ color: scoreColor(score) }}>
                            {score.toFixed(1)}%
                          </span>
                        </div>
                      ))}
                  </div>
                </div>

                <div style={{ marginTop: 16 }}>
                  <button
                    className="btn-primary"
                    onClick={() => {
                      toggleCompare(selectedModel.id);
                      setSelectedModel(null);
                    }}
                  >
                    {compareIds.includes(selectedModel.id) ? "Remove from Compare" : "Add to Compare"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ─── Footer ────────────────────────────────── */}
      <footer className="footer">
        <p>
          MedBench — Medical AI Evaluation Leaderboard. Data sourced from European medical residency examinations.
          Evaluation results stored in <code style={{ fontFamily: "var(--font-mono)", fontSize: "0.78rem" }}>results/openrouter/</code>.
          See <a href="https://github.com" target="_blank">docs/</a> for data format specifications.
        </p>
      </footer>
    </>
  );
}
