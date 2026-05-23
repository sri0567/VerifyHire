"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { clearTrackedJobs, loadTrackedJobs, removeTrackedJob, toggleAppliedStatus } from "../lib/trackedJobs";

function scoreBand(score) {
  if (score >= 80) return { label: "High Trust", className: "chip chip-safe" };
  if (score >= 60) return { label: "Needs Review", className: "chip chip-review" };
  return { label: "Higher Risk", className: "chip chip-risk" };
}

function prettyDate(value) {
  if (!value) return "Not set";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not set";
  return date.toLocaleString();
}

export default function TrackedJobsPage() {
  const [trackedJobsMap, setTrackedJobsMap] = useState({});
  const [search, setSearch] = useState("");

  useEffect(() => {
    setTrackedJobsMap(loadTrackedJobs());

    const onStorage = () => {
      setTrackedJobsMap(loadTrackedJobs());
    };

    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const trackedJobs = useMemo(() => {
    const text = search.trim().toLowerCase();
    const list = Object.values(trackedJobsMap).sort((a, b) => {
      const left = new Date(a.tracked_at || 0).getTime();
      const right = new Date(b.tracked_at || 0).getTime();
      return right - left;
    });

    if (!text) return list;

    return list.filter((job) => {
      const combined = `${job.title || ""} ${job.company || ""} ${job.description || ""}`.toLowerCase();
      return combined.includes(text);
    });
  }, [trackedJobsMap, search]);

  const trackedCount = trackedJobs.length;

  const removeOne = (trackedId) => {
    const updated = removeTrackedJob(trackedId);
    setTrackedJobsMap(updated);
  };

  const clearAll = () => {
    const updated = clearTrackedJobs();
    setTrackedJobsMap(updated);
  };

  const toggleApplied = (trackedId) => {
    const updated = toggleAppliedStatus(trackedId);
    setTrackedJobsMap(updated);
  };

  return (
    <main className="page-shell">
      <div className="ambient-shape ambient-shape-a" />
      <div className="ambient-shape ambient-shape-b" />

      <header className="top-nav">
        <div>
          <p className="eyebrow">Application Tracking</p>
          <h1 className="brand-title">Saved Opportunities</h1>
        </div>
        <nav className="nav-actions">
          <Link href="/" className="nav-pill">
            Opportunity Feed
          </Link>
          <Link href="/tracked" className="nav-pill nav-pill-active">
            Saved Jobs
            <span className="counter">{trackedCount}</span>
          </Link>
        </nav>
      </header>

      <section className="hero-card">
        <h2>Keep high-potential roles organized and move applications forward.</h2>
        <p>Mark jobs as applied, remove outdated ones, and keep your shortlist focused.</p>
        <div className="hero-actions">
          <input
            className="tracked-search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search tracked jobs"
          />
          <button type="button" className="btn btn-outline" onClick={clearAll} disabled={trackedCount === 0}>
            Clear All
          </button>
        </div>
      </section>

      <section className="jobs-list">
        {trackedJobs.length === 0 ? (
          <p className="empty-state">
            You have no saved jobs yet. Go to Opportunity Feed and click <strong>Track Job</strong>.
          </p>
        ) : (
          trackedJobs.map((job) => {
            const band = scoreBand(job.legitimacy_score || 0);
            return (
              <article className="job-card" key={job.tracked_id}>
                <div className="job-top">
                  <div>
                    <h3>{job.title}</h3>
                    <p className="meta">
                      {job.company} | {job.location || "Remote"} | {job.source || "Unknown"}
                    </p>
                  </div>
                  <div className="score-wrap">
                    <span className={band.className}>{band.label}</span>
                    <strong>{job.legitimacy_score || 0}/100</strong>
                  </div>
                </div>

                <p className="description">{job.description || "No description available."}</p>

                <div className="tag-row">
                  <span className={`tag ${job.applied ? "tag-green" : "tag-muted"}`}>
                    {job.applied ? "Applied" : "Saved"}
                  </span>
                  <span className="tag tag-blue">Tracked: {prettyDate(job.tracked_at)}</span>
                  {job.apply_url ? (
                    <a className="tag tag-link" href={job.apply_url} target="_blank" rel="noreferrer">
                      Open Apply Link
                    </a>
                  ) : null}
                </div>

                <div className="action-row">
                  <button
                    type="button"
                    className={`btn ${job.applied ? "btn-secondary" : "btn-primary"}`}
                    onClick={() => toggleApplied(job.tracked_id)}
                  >
                    {job.applied ? "Mark as Not Applied" : "Mark as Applied"}
                  </button>

                  <button type="button" className="btn btn-outline" onClick={() => removeOne(job.tracked_id)}>
                    Remove
                  </button>
                </div>
              </article>
            );
          })
        )}
      </section>
    </main>
  );
}