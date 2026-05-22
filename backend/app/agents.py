import re
from typing import Any, Dict, List
from urllib.parse import urlparse

from .verifier import check_remote_validity, detect_scam_phrases

SCAM_PATTERN_AGENT_PHRASES = [
    "wire transfer",
    "gift card",
    "upfront payment",
    "no interview needed",
    "immediate start no experience",
    "pay for equipment",
    "send your bank details",
    "contact via telegram",
    "contact via whatsapp",
]

REMOTE_POSITIVE_PHRASES = [
    "fully remote",
    "remote-first",
    "work from home",
    "distributed team",
    "async collaboration",
]

REMOTE_NEGATIVE_PHRASES = [
    "in office",
    "in-office",
    "onsite required",
    "must relocate",
    "hybrid role",
    "this is not a remote position",
]

TRUST_KEYWORDS = [
    "responsibilities",
    "requirements",
    "about the role",
    "equal opportunity",
    "benefits",
    "interview process",
]


def _normalize_text(*parts: str | None) -> str:
    return " ".join([part for part in parts if part]).lower().strip()


def _extract_evidence(text: str, phrases: List[str]) -> List[str]:
    found = []
    for phrase in phrases:
        if phrase in text:
            found.append(phrase)
    return found


def scam_signal_agent(text: str) -> Dict[str, Any]:
    flags = detect_scam_phrases(text)
    extended_hits = _extract_evidence(text, SCAM_PATTERN_AGENT_PHRASES)
    all_hits = list(dict.fromkeys(flags + extended_hits))

    penalty = min(50, len(all_hits) * 10)
    verdict = "clear" if not all_hits else "risk_detected"

    return {
        "agent": "ScamSignalAgent",
        "score_delta": -penalty,
        "verdict": verdict,
        "evidence": all_hits[:6],
        "reason": "Checks common scam patterns and payment/communication traps.",
    }


def remote_authenticity_agent(text: str, location: str | None) -> Dict[str, Any]:
    has_remote_signal = check_remote_validity(text)
    positive_hits = _extract_evidence(text, REMOTE_POSITIVE_PHRASES)
    negative_hits = _extract_evidence(text, REMOTE_NEGATIVE_PHRASES)

    delta = 0
    verdict = "uncertain"
    evidence: List[str] = []

    if has_remote_signal or positive_hits:
        delta += 12
        verdict = "likely_remote"
        evidence.extend(positive_hits[:3] or ["remote language detected"])

    if negative_hits:
        delta -= 20
        verdict = "contradiction_found"
        evidence.extend(negative_hits[:3])

    if location and "remote" in location.lower():
        delta += 4
        evidence.append("location marked as remote")

    return {
        "agent": "RemoteAuthenticityAgent",
        "score_delta": max(-25, min(18, delta)),
        "verdict": verdict,
        "evidence": evidence[:6],
        "reason": "Verifies remote-work consistency across description and location.",
    }


def transparency_agent(text: str, apply_url: str | None) -> Dict[str, Any]:
    keyword_hits = _extract_evidence(text, TRUST_KEYWORDS)
    score_delta = min(18, len(keyword_hits) * 3)
    evidence = keyword_hits[:5]

    if len(text) < 120:
        score_delta -= 10
        evidence.append("description too short")

    if apply_url:
        parsed = urlparse(apply_url)
        if parsed.scheme == "https":
            score_delta += 4
            evidence.append("secure apply URL")
        else:
            score_delta -= 4
            evidence.append("non-https apply URL")

    verdict = "detailed" if score_delta >= 8 else "limited_detail"
    return {
        "agent": "TransparencyAgent",
        "score_delta": max(-15, min(20, score_delta)),
        "verdict": verdict,
        "evidence": evidence[:6],
        "reason": "Rewards detailed, structured postings with safe application links.",
    }


def salary_plausibility_agent(text: str, salary: str | None) -> Dict[str, Any]:
    combined = _normalize_text(text, salary)
    evidence: List[str] = []
    delta = 0

    if "per day" in combined and "$" in combined:
        delta -= 6
        evidence.append("daily pay mention")

    if "unlimited earnings" in combined or "guaranteed income" in combined:
        delta -= 14
        evidence.append("unrealistic income claim")

    salary_range = re.search(r"\$?\d{2,3}[,]?\d{0,3}\s*-\s*\$?\d{2,3}[,]?\d{0,3}", combined)
    if salary_range:
        delta += 6
        evidence.append("clear salary range")

    verdict = "plausible" if delta >= 0 else "suspicious_claims"
    return {
        "agent": "SalaryPlausibilityAgent",
        "score_delta": max(-18, min(10, delta)),
        "verdict": verdict,
        "evidence": evidence[:4],
        "reason": "Looks for unrealistic compensation claims versus transparent ranges.",
    }


def build_agent_report(
    title: str,
    company: str,
    description: str,
    location: str | None = None,
    salary: str | None = None,
    apply_url: str | None = None,
) -> Dict[str, Any]:
    text = _normalize_text(title, company, location, description)

    signals = [
        scam_signal_agent(text),
        remote_authenticity_agent(text, location),
        transparency_agent(text, apply_url),
        salary_plausibility_agent(text, salary),
    ]

    score = 70
    for signal in signals:
        score += int(signal["score_delta"])

    score = max(0, min(100, score))

    risk_level = "high"
    if score >= 80:
        risk_level = "low"
    elif score >= 60:
        risk_level = "medium"

    positives: List[str] = []
    risks: List[str] = []
    for signal in signals:
        if signal["score_delta"] >= 0:
            positives.extend(signal["evidence"])
        else:
            risks.extend(signal["evidence"])

    return {
        "version": "1.0",
        "score": score,
        "risk_level": risk_level,
        "signals": signals,
        "highlights": {
            "positives": list(dict.fromkeys(positives))[:5],
            "risks": list(dict.fromkeys(risks))[:5],
        },
        "summary": (
            f"Score {score}/100 with {risk_level} risk based on scam patterns, "
            "remote consistency, transparency, and compensation plausibility."
        ),
    }