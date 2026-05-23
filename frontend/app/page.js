"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { getJobTrackingId, loadTrackedJobs, toggleTrackedJob } from "./lib/trackedJobs";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

function parseAiPayload(raw) {
  if (!raw) return { agent_report: null, llm_summary: null, fallback_text: null };

  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object") {
      return {
        agent_report: parsed.agent_report || null,
        llm_summary: parsed.llm_summary || null,
        fallback_text: null
      };
    }
  } catch {
    return { agent_report: null, llm_summary: null, fallback_text: raw };
  }

  return { agent_report: null, llm_summary: null, fallback_text: null };
}

function scoreBand(score) {
  if (score >= 80) return { label: "High Trust", className: "chip chip-safe" };
  if (score >= 60) return { label: "Needs Review", className: "chip chip-review" };
  return { label: "Higher Risk", className: "chip chip-risk" };
}

export default function HomePage() {
  const [jobs, setJobs] = useState([]);
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isScraping, setIsScraping] = useState(false);
  const [trackedJobsMap, setTrackedJobsMap] = useState({});

  const [search, setSearch] = useState("");
  const [minScore, setMinScore] = useState(0);
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [selectedSource, setSelectedSource] = useState("all");
  const [sortBy, setSortBy] = useState("newest");
  const [expandedJobId, setExpandedJobId] = useState(null);

  const loadData = async () => {
    setLoading(true);
    setError("");

    try {
      const [jobsRes, insightsRes] = await Promise.all([
        fetch(`${API_BASE}/jobs/`),
        fetch(`${API_BASE}/jobs/insights`)
      ]);

      if (!jobsRes.ok) throw new Error("Could not load jobs from backend");
      if (!insightsRes.ok) throw new Error("Could not load insights from backend");

      const jobsData = await jobsRes.json();
      const insightsData = await insightsRes.json();

      setJobs(jobsData.jobs || []);
      setInsights(insightsData);
    } catch (loadErr) {
      setError(loadErr.message || "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    setTrackedJobsMap(loadTrackedJobs());

    const onStorage = () => {
      setTrackedJobsMap(loadTrackedJobs());
    };

    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const sourceOptions = useMemo(() => {
    const sources = new Set();
    for (const job of jobs) {
      sources.add(job.source || "Unknown");
    }
    return ["all", ...Array.from(sources)];
  }, [jobs]);

  const filteredJobs = useMemo(() => {
    const text = search.trim().toLowerCase();
    const working = jobs.filter((job) => {
      if (job.legitimacy_score < minScore) return false;
      if (remoteOnly && !job.verified_remote) return false;
      if (selectedSource !== "all" && (job.source || "Unknown") !== selectedSource) return false;

      if (!text) return true;
      const combined = `${job.title} ${job.company} ${job.description}`.toLowerCase();
      return combined.includes(text);
    });

    working.sort((a, b) => {
      if (sortBy === "score") return b.legitimacy_score - a.legitimacy_score;
      if (sortBy === "risk") return (a.scam_flag === b.scam_flag ? 0 : a.scam_flag ? -1 : 1);
      return b.id - a.id;
    });

    return working;
  }, [jobs, minScore, remoteOnly, search, selectedSource, sortBy]);

  const derivedStats = useMemo(() => {
    const total = filteredJobs.length;
    const highTrust = filteredJobs.filter((job) => job.legitimacy_score >= 80 && !job.scam_flag).length;
    const verifiedRemote = filteredJobs.filter((job) => job.verified_remote).length;
    const risky = filteredJobs.filter((job) => job.legitimacy_score < 60 || job.scam_flag).length;
    return { total, highTrust, verifiedRemote, risky };
  }, [filteredJobs]);

  const trackedCount = useMemo(() => Object.keys(trackedJobsMap).length, [trackedJobsMap]);

  const triggerScrape = async () => {
    setIsScraping(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/jobs/scrape/start`, { method: "POST" });
      if (!res.ok) throw new Error("Unable to trigger scraping");
      setTimeout(loadData, 3000);
    } catch (scrapeErr) {
      setError(scrapeErr.message || "Failed to start scraping");
    } finally {
      setIsScraping(false);
    }
  };

  const toggleTrack = (job) => {
    const updatedMap = toggleTrackedJob(job);
    setTrackedJobsMap(updatedMap);
  };

  const isTracked = (job) => {
    const key = getJobTrackingId(job);
    return Boolean(trackedJobsMap[key]);
  };

  return (
    <main className="page-shell">
      <div className="ambient-shape ambient-shape-a" />
      <div className="ambient-shape ambient-shape-b" />

      <header className="top-nav">
        <div>
          <p className="eyebrow">Scale Without Borders Hackathon</p>
          <h1 className="brand-title">VerifyHire</h1>
        </div>
        <nav className="nav-actions">
          <Link href="/" className="nav-pill nav-pill-active">
            Opportunity Feed
          </Link>
          <Link href="/tracked" className="nav-pill">
            Saved Jobs
            <span className="counter">{trackedCount}</span>
          </Link>
        </nav>
      </header>

      <section className="hero-card">
        <h2>Find verified remote roles faster with explainable AI trust signals.</h2>
        <p>
          Each posting is scored with multi-agent checks for scam phrases, remote consistency, transparency, and
          compensation plausibility.
        </p>
        <div className="hero-actions">
          <button className="btn btn-primary" onClick={loadData} disabled={loading}>
            {loading ? "Refreshing..." : "Refresh Jobs"}
          </button>
          <button className="btn btn-secondary" onClick={triggerScrape} disabled={isScraping}>
            {isScraping ? "Running Scraper..." : "Fetch Fresh Jobs"}
          </button>
        </div>
      </section>

      <section className="stats-grid">
        <article className="stat-card">
          <p className="stat-label">Visible Jobs</p>
          <p className="stat-value">{derivedStats.total}</p>
        </article>
        <article className="stat-card">
          <p className="stat-label">High Trust</p>
          <p className="stat-value">{derivedStats.highTrust}</p>
        </article>
        <article className="stat-card">
          <p className="stat-label">Verified Remote</p>
          <p className="stat-value">{derivedStats.verifiedRemote}</p>
        </article>
        <article className="stat-card">
          <p className="stat-label">Potentially Risky</p>
          <p className="stat-value">{derivedStats.risky}</p>
        </article>
      </section>

      <section className="filter-panel">
        <label>
          Search
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Title, company, or keyword"
          />
        </label>

        <label>
          Minimum Score: {minScore}
          <input
            type="range"
            min={0}
            max={100}
            value={minScore}
            onChange={(event) => setMinScore(Number(event.target.value))}
          />
        </label>

        <label>
          Source
          <select value={selectedSource} onChange={(event) => setSelectedSource(event.target.value)}>
            {sourceOptions.map((source) => (
              <option key={source} value={source}>
                {source === "all" ? "All Sources" : source}
              </option>
            ))}
          </select>
        </label>

        <label>
          Sort
          <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
            <option value="newest">Newest</option>
            <option value="score">Highest Score</option>
            <option value="risk">Most Risky First</option>
          </select>
        </label>

        <label className="toggle">
          <input type="checkbox" checked={remoteOnly} onChange={(event) => setRemoteOnly(event.target.checked)} />
          <span>Remote-only Verified</span>
        </label>
      </section>

      {insights ? (
        <section className="insights">
          <p>
            Total jobs in database: <strong>{insights.total_jobs}</strong> | Average trust score:{" "}
            <strong>{insights.average_score}</strong>
          </p>
        </section>
      ) : null}

      {error ? <p className="error-banner">{error}</p> : null}

      <section className="jobs-list">
        {loading ? (
          <p className="empty-state">Loading job opportunities...</p>
        ) : filteredJobs.length === 0 ? (
          <p className="empty-state">No jobs match your filters yet.</p>
        ) : (
          filteredJobs.map((job) => {
            const ai = parseAiPayload(job.ai_analysis_raw);
            const band = scoreBand(job.legitimacy_score);
            const isExpanded = expandedJobId === job.id;
            const tracked = isTracked(job);
            const report = ai.agent_report;

            return (
              <article className="job-card" key={job.id}>
                <div className="job-top">
                  <div>
                    <h3>{job.title}</h3>
                    <p className="meta">
                      {job.company} | {job.location || "Remote"} | {job.source || "Unknown"}
                    </p>
                  </div>
                  <div className="score-wrap">
                    <span className={band.className}>{band.label}</span>
                    <strong>{job.legitimacy_score}/100</strong>
                  </div>
                </div>

                <p className="reason">{job.legitimacy_reason}</p>
                

                <div className="tag-row">
                  <span className={`tag ${job.verified_remote ? "tag-green" : "tag-muted"}`}>
                    {job.verified_remote ? "Remote Verified" : "Remote Unclear"}
                  </span>
                  <span className={`tag ${job.scam_flag ? "tag-red" : "tag-blue"}`}>
                    {job.scam_flag ? "Scam Signals Found" : "No Major Scam Signals"}
                  </span>
                  {job.apply_url ? (
                    <a className="tag tag-link" href={job.apply_url} target="_blank" rel="noreferrer">
                      Apply Link
                    </a>
                  ) : null}
                </div>

                <div className="action-row">
                  <button
                    className="btn btn-tertiary"
                    onClick={() => setExpandedJobId(isExpanded ? null : job.id)}
                    type="button"
                  >
                    {isExpanded ? "Hide Agent Details" : "Show Agent Details"}
                  </button>

                  <button
                    className={`btn track-btn ${tracked ? "track-btn-active" : ""}`}
                    onClick={() => toggleTrack(job)}
                    type="button"
                  >
                    {tracked ? "Saved" : "Save Job"}
                  </button>
                </div>

                {isExpanded ? (
                  <div className="agent-panel">
                    {report ? (
                      <>
                        <p className="agent-summary">{report.summary}</p>
                        <div className="mini-grid">
                          <div>
                            <h4>Positive Signals</h4>
                            {(report.highlights?.positives || []).length > 0 ? (
                              <ul>
                                {report.highlights.positives.map((item) => (
                                  <li key={item}>{item}</li>
                                ))}
                              </ul>
                            ) : (
                              <p className="muted">No strong positives detected yet.</p>
                            )}
                          </div>
                          <div>
                            <h4>Risk Signals</h4>
                            {(report.highlights?.risks || []).length > 0 ? (
                              <ul>
                                {report.highlights.risks.map((item) => (
                                  <li key={item}>{item}</li>
                                ))}
                              </ul>
                            ) : (
                              <p className="muted">No major risk phrases detected.</p>
                            )}
                          </div>
                        </div>

                        <h4>Agent Breakdown</h4>
                        <div className="signals">
                          {(report.signals || []).map((signal) => (
                            <div className="signal" key={`${job.id}-${signal.agent}`}>
                              <p>
                                <strong>{signal.agent}</strong> ({signal.score_delta >= 0 ? "+" : ""}
                                {signal.score_delta})
                              </p>
                              <p className="muted">{signal.reason}</p>
                              {(signal.evidence || []).length > 0 ? (
                                <ul>
                                  {signal.evidence.map((ev) => (
                                    <li key={ev}>{ev}</li>
                                  ))}
                                </ul>
                              ) : (
                                <p className="muted">No specific evidence text captured.</p>
                              )}
                            </div>
                          ))}
                        </div>
                      </>
                    ) : ai.fallback_text ? (
                      <p>{ai.fallback_text}</p>
                    ) : (
                      <p className="muted">No structured AI details available for this record yet.</p>
                    )}

                    {ai.llm_summary ? (
                      <div className="llm-box">
                        <h4>LLM Reviewer Summary</h4>
                        <p>{ai.llm_summary}</p>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </article>
            );
          })
        )}
      </section>
    </main>
  );
}