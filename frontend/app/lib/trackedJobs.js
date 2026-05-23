const STORAGE_KEY = "tracked_remote_jobs_v1";

export function getJobTrackingId(job) {
  const stableId =
    job?.source_job_id ||
    job?.id ||
    `${job?.title || "unknown"}-${job?.company || "unknown"}-${job?.location || "unknown"}`;

  return String(stableId).toLowerCase();
}

export function loadTrackedJobs() {
  if (typeof window === "undefined") return {};

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return {};
    return parsed;
  } catch {
    return {};
  }
}

export function saveTrackedJobs(map) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
}

export function toggleTrackedJob(job) {
  const map = loadTrackedJobs();
  const key = getJobTrackingId(job);

  if (map[key]) {
    delete map[key];
  } else {
    map[key] = {
      ...job,
      tracked_id: key,
      tracked_at: new Date().toISOString(),
      applied: false
    };
  }

  saveTrackedJobs(map);
  return map;
}

export function removeTrackedJob(trackedId) {
  const map = loadTrackedJobs();
  delete map[String(trackedId)];
  saveTrackedJobs(map);
  return map;
}

export function clearTrackedJobs() {
  saveTrackedJobs({});
  return {};
}

export function toggleAppliedStatus(trackedId) {
  const map = loadTrackedJobs();
  const key = String(trackedId);
  if (!map[key]) return map;

  map[key] = {
    ...map[key],
    applied: !map[key].applied,
    applied_at: !map[key].applied ? new Date().toISOString() : null
  };

  saveTrackedJobs(map);
  return map;
}