"use client";

import Link from "next/link";

const teamMembers = [
  {
    name: "Andrea Causio, MD",
    role: "Project Lead (up to July 2025)",
    image: "/team/acausio.jpg",
    link: "https://causio.xyz/",
    bio: "Medical doctor and software engineer leading the MedBench initiative. Developing standardized evaluation frameworks for medical AI systems across European healthcare contexts.",
  },
  {
    name: "Dr. Sarah Mitchell",
    role: "Principal Investigator & Clinical Lead",
    image: "/team/member1.png",
    bio: "Oversees clinical validation and ensures evaluation methodologies align with real-world medical practice standards.",
  },
  {
    name: "Dr. Arthur Chen",
    role: "Head of Medical Research & Strategy",
    image: "/team/member2.png",
    bio: "Leads the research strategy for cross-lingual medical AI evaluation and curates examination datasets.",
  },
  {
    name: "Elena Rodriguez",
    role: "Lead Data Scientist & ML Engineer",
    image: "/team/member3.png",
    bio: "Architects the evaluation pipeline, model inference infrastructure, and automated result aggregation systems.",
  },
];

export default function TeamPage() {
  return (
    <>
      {/* ─── Header ────────────────────────────────── */}
      <header className="header">
        <div className="header-inner">
          <Link href="/" className="logo" style={{ textDecoration: "none" }}>
            <div className="logo-mark">MB</div>
            MedBench
          </Link>
          <nav className="header-nav">
            <Link href="/">
              <button>Leaderboard</button>
            </Link>
            <button className="active">Team</button>
          </nav>
        </div>
      </header>

      <main className="main">
        {/* ─── Hero ───────────────────────────────── */}
        <div className="hero">
          <h1>Team</h1>
          <p>
            The researchers and engineers behind the Medical AI Evaluation
            Leaderboard.
          </p>
        </div>

        {/* ─── Team Grid ─────────────────────────── */}
        <div className="team-grid">
          {teamMembers.map((member) => (
            <div key={member.name} className="team-card">
              <div className="team-card-top">
                <div className="team-avatar-wrap">
                  <img
                    src={member.image}
                    alt={member.name}
                    className="team-avatar"
                  />
                </div>
                <div className="team-card-name">
                  {member.link ? (
                    <a
                      href={member.link}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {member.name}
                    </a>
                  ) : (
                    member.name
                  )}
                </div>
                <div className="team-card-role">{member.role}</div>
              </div>
              <div className="team-card-bottom">
                <p>{member.bio}</p>
              </div>
            </div>
          ))}
        </div>

        {/* ─── Open Contributions ────────────────── */}
        <div className="section" style={{ marginTop: 32 }}>
          <div className="section-header">
            <h2>Contributing</h2>
          </div>
          <div className="section-body">
            <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", maxWidth: 640, lineHeight: 1.6 }}>
              MedBench is an open project. We welcome contributions including
              new medical examination datasets, model evaluation results,
              methodology improvements, and frontend enhancements. See the{" "}
              <code
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.82rem",
                  background: "var(--bg-hover)",
                  padding: "2px 6px",
                  borderRadius: 4,
                }}
              >
                docs/
              </code>{" "}
              directory for data format specifications and contribution guidelines.
            </p>
          </div>
        </div>
      </main>

      {/* ─── Footer ──────────────────────────────── */}
      <footer className="footer">
        <p>
          MedBench — Medical AI Evaluation Leaderboard. Data sourced from
          European medical residency examinations.
        </p>
      </footer>
    </>
  );
}
