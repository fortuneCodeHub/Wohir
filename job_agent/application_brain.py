#!/usr/bin/python3
"""
    Application Brain — AI decision layer for the job application agent.
    Handles scoring, JD extraction, CV building, cover letter generation,
    custom question answering, and email body generation.
    Uses AgentRouter API with SKILL.md instructions for every AI call.
    Author: Fortune Nwohiri
"""
import json
import os
import time
import random
from pathlib import Path
from logging_config.logger import get_logger
from job_agent.ai_client import call_ai

logger = get_logger("ApplicationBrain")

SKILL_MD_PATH = "./job_agent/SKILL.md"
MY_SKILLS_PATH = "./config/my_skills.md"
STATE_PATH = "./state/applied_jobs.json"


def load_skill_md() -> str:
    """Load SKILL.md once and cache it. Every AI call gets the full instructions."""
    try:
        with open(SKILL_MD_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"SKILL.md not found at {SKILL_MD_PATH}")
        return ""


def load_my_skills() -> str:
    """Load my_skills.md — the only source of truth for the CV builder."""
    try:
        with open(MY_SKILLS_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"my_skills.md not found at {MY_SKILLS_PATH}")
        return ""


def load_state() -> dict:
    """Load applied_jobs.json state file."""
    if not os.path.exists(STATE_PATH):
        return {"applied": [], "skipped": [], "failed": [], "manual_queue": []}
    try:
        with open(STATE_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load state: {e}")
        return {"applied": [], "skipped": [], "failed": [], "manual_queue": []}


def save_state(state: dict):
    """Save state back to applied_jobs.json."""
    try:
        with open(STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save state: {e}")


def already_seen(job_id: str, state: dict) -> bool:
    """Check if this job_id has already been processed in any category."""
    for category in ["applied", "skipped", "failed", "manual_queue"]:
        for entry in state.get(category, []):
            if entry.get("job_id") == job_id:
                return True
    return False


def parse_json_response(raw: str, agent_name: str) -> dict:
    """
    Parse a JSON response from an AI agent.
    Strips markdown fences if present.
    Returns empty dict on failure.
    """
    try:
        cleaned = raw.strip()
        # Strip markdown code fences if the model added them despite instructions
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            ).strip()
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"{agent_name} JSON parse failed: {e}")
        logger.error(f"Raw response was: {raw[:500]}")
        return {}


# ── AGENT 1: PAGE CLASSIFIER ──────────────────────────────────────────────────

def classify_page(
    url: str,
    page_title: str,
    visible_text: str,
    form_count: int,
    input_count: int,
    button_texts: list,
    h1_texts: list,
) -> dict:
    """
    Classify what page the bot has landed on.
    Called by job_connector.py before any interaction.

    Returns classification dict with page_type, obstruction info,
    apply_button_exists, apply_opens_modal, post_click_action, and reasoning.
    """
    skill_md = load_skill_md()

    system_prompt = f"""You are Agent 1: PAGE CLASSIFIER in a job application automation system.

{skill_md}

Your ONLY job right now is to act as AGENT 1: PAGE CLASSIFIER.
Return ONLY valid JSON. No markdown. No explanation. No preamble.

IMPORTANT — when classifying a job_listing page, you MUST also return:
  "apply_opens_modal": true if clicking the apply button will likely open a modal
    or overlay on the SAME page. Look for: button onclick handlers mentioning 'modal',
    'dialog', 'overlay', 'popup', or 'open'; data attributes like data-toggle='modal',
    data-bs-toggle='modal'; buttons that do NOT have an href pointing to another page;
    class names containing 'modal-trigger', 'js-modal', 'dialog-trigger'.
    Return false if the button href points to an external URL or ATS platform.
  "post_click_action": predict what clicking Apply will do. Must be one of:
    "modal" — opens a form overlay on the same page
    "redirect" — navigates to a new page (ATS, company careers page)
    "new_tab" — opens in a new browser tab
    "nothing" — decorative or broken button
    "unknown" — cannot determine from DOM signals
Return these two fields on EVERY classification, not just job_listing."""

    user_prompt = f"""Classify this page.

URL: {url}
Page title: {page_title}
Visible text (first 1000 chars): {visible_text[:1000]}
Number of forms on page: {form_count}
Number of input fields on page: {input_count}
Button texts visible: {json.dumps(button_texts[:15])}
H1 headings: {json.dumps(h1_texts[:5])}

Return the JSON classification object exactly as specified in your instructions."""

    try:
        raw = call_ai(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500,
            json_response=True,
        )
        result = parse_json_response(raw, "PageClassifier")
        if result:
            logger.info(
                f"Page classified: {result.get('page_type')} "
                f"(confidence: {result.get('confidence')}) "
                f"obstruction: {result.get('obstruction_type')} "
                f"apply_opens_modal: {result.get('apply_opens_modal')} "
                f"post_click_action: {result.get('post_click_action')} "
                f"— {url}"
            )
            return result
    except Exception as e:
        logger.error(f"Page classifier failed: {e}")

    # Fallback — unknown
    return {
        "page_type": "unknown",
        "confidence": 0,
        "apply_button_exists": False,
        "apply_button_text": "",
        "apply_opens_modal": False,
        "post_click_action": "unknown",
        "obstruction_detected": False,
        "obstruction_type": "none",
        "obstruction_action": "none",
        "reasoning": "classifier failed",
    }


# ── AGENT 2: JOB SCORER ───────────────────────────────────────────────────────

def score_listing(
    job_title: str,
    company: str,
    description: str,
    agent_profile: dict,
) -> dict:
    """
    Score a job listing 0-100 against Fortune's profile.
    Returns scoring dict with score, reason, matched/missing keywords, role_type.
    Score below agent_profile['min_score_threshold'] means skip.
    """
    skill_md = load_skill_md()
    threshold = agent_profile.get("min_score_threshold", 72)

    system_prompt = f"""You are Agent 2: JOB SCORER in a job application automation system.

{skill_md}

Your ONLY job right now is to act as AGENT 2: JOB SCORER.
Return ONLY valid JSON. No markdown. No explanation. No preamble."""

    user_prompt = f"""Score this job listing for Fortune Nwohiri.

Job title: {job_title}
Company: {company}
Score threshold to pass: {threshold}

Full job description:
{description[:3000]}

---
FORTUNE NWOHIRI — PROFILE SUMMARY

3 years of full-stack development experience. Computer Science graduate, Nnamdi Azikiwe University, 2026.

CORE STACK:
TypeScript, NestJS, Node.js, Next.js, React, React Native, PostgreSQL, Redis, BullMQ, Laravel, PHP, Python, Docker, Tailwind CSS, TypeORM

WHAT HE HAS BUILT AND SHIPPED:
- Phlox: AI-native influencer marketing platform built solo. NestJS backend, Next.js frontend, PostgreSQL, Redis, BullMQ. Full escrow payment system with double-entry ledger, idempotency keys, NUBAN verification, 24-hour cooling-off period, Flutterwave webhook signature verification, automated daily reconciliation. Five AI agents using Claude API: creator sourcing, contract generation, content review, competitor conflict detection, per-brand learning. pgvector semantic search. Pre-seed raise structured at $150k SAFE, $1.2M post-money cap.
- GatePass: event ticketing platform, Laravel, React, MySQL. 900+ tickets sold, 30+ organizers. Flutterwave integration with idempotency and webhook verification. Diagnosed and stopped a live bot registration attack same day using honeypot, timestamp guard, and IP-level rate limiting at 3 attempts per minute.
- FortunePay: Bybit P2P crypto trading bot. NestJS, TypeScript, PostgreSQL, Redis, BullMQ, Puppeteer. Monitors Bybit via headless browser, handles 4 payment rails, real-time Telegram notifications.
- Ubuxa: enterprise energy management platform. NestJS, Next.js, TypeScript, PostgreSQL.
- LocIQ: spatial intelligence platform. Built full WhatsApp Business API automation pipeline: webhook ingestion, conversation state machine, signature verification, idempotency, automated Meta Send API replies.
- YieldNvest: Next.js blog with custom MongoDB CMS built from scratch. Full technical SEO, Google AdSense approved.
- OnDicts: AI sports betting analysis Telegram bot. NestJS, TypeScript, Telegraf, 6 leagues, full multi-service architecture.
- AI Email Rewriter + Chrome Extension: built in 7 days. MutationObserver Gmail DOM injection, synthetic event system compatibility, Next.js web app.
- Vikmid: creator management platform, NestJS, Next.js, TypeScript, Tailwind CSS. Built in cross-functional agile team.
- JTHUB: recruitment ops platform for a Vietnam-based recruiter. NestJS, Next.js, TypeScript, PostgreSQL.
- PadiDrive: driving school management system deployed on self-managed VPS with Nginx, Certbot SSL, PM2.
- adrxp.com: complete e-commerce platform, Core PHP/Laravel, MySQL. Built 2022, hand-written, no AI tools.

AUTOMATION AND BOT ENGINEERING:
- Google Traffic Generation Bot: Python, SeleniumBase. Full anti-detection: TLS fingerprint profiling, canvas/WebGL spoofing, WebRTC leak prevention, residential proxy rotation, human-like mouse movement, variable scroll velocity, isolated Chrome profiles.
- YouTube CTR Bot: same anti-detection stack. Runs multiple Gmail profiles in isolation.
- Pi Network Multi-Transaction Bot: Python. Reverse-engineered the closed Pi Network blockchain node transaction protocol with zero public documentation through network traffic analysis. Fires thousands of concurrent withdrawal transactions. Understands wallet-level race conditions, concurrent transaction sequencing, rate-limiting node infrastructure.
- Crypto Multi-Currency Auto-Transfer Bot: Python. Parallel wallet sweep across multiple currencies using private key authorization.

FRAMEWORK ENGINEERING:
- Built Frames, a custom PHP MVC framework from scratch at age 19: regex routing engine, CLI scaffolding, session management, pagination class, HTML component library, hand-written image/video compression algorithm. Installable via Composer.

PAYMENTS AND FINTECH:
Double-entry ledger, idempotency keys, escrow logic, NUBAN verification, webhook signature verification, cooling-off period controls, automated reconciliation, Flutterwave, Paystack, Bybit P2P.

AI AND AGENTS:
Anthropic Claude API, multi-agent orchestration, pgvector semantic search, prompt engineering, adversarial prompt testing.

COMMUNITY AND CONTENT:
Grew LinkedIn from 100 to 430+ followers in 2 weeks, 10,000+ weekly impressions at zero spend.

---

SCORING RULES — follow these exactly:

1. SCORE BASED ON TECH STACK MATCH ONLY. If the job requires technologies Fortune knows and has shipped with, score high. If it requires completely foreign tech (Java enterprise, .NET, iOS Swift, embedded C, hardware engineering, data science with no dev component), score low.

2. NEVER penalise for years of experience requirements. "8 years required", "senior level", "10+ years" do not reduce the score. They are aspirational. Ignore them completely.

3. SCORE GUIDE:
   - 85-100: Strong match. The job uses TypeScript, Node.js, NestJS, React, Next.js, PostgreSQL, Redis, Python, Laravel, or any combination. Fortune has shipped production systems with these. Apply.
   - 72-84: Partial match. Some known tech, some learnable overlap (Go, Vue, MongoDB, Django). The domain is relevant. Apply.
   - 50-71: Weak match. Mostly unfamiliar tech or domain. Skip.
   - 0-49: No match. Completely different domain or stack. Skip.

4. REMOTE BONUS: If the role is remote or remote-friendly, add 5 to 10 points.

5. DOMAIN BONUS: Fintech, payments, crypto, AI agents, automation, full-stack web, event platforms, creator tools, any startup or agency context — add 5 points. These are Fortune's native domains.

Return the JSON scoring object exactly as specified in your instructions."""

    
    try:
        raw = call_ai(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=600,
            json_response=True,
        )
        result = parse_json_response(raw, "JobScorer")
        if not result and raw:
            # Try to salvage score from truncated response
            import re as _re
            score_match = _re.search(r'"score"\s*:\s*(\d+)', raw)
            if score_match:
                score_val = int(score_match.group(1))
                logger.warning(f"Salvaged score {score_val} from truncated JSON response")
                result = {"score": score_val, "reason": "truncated response", "must_haves_matched": [], "must_haves_missing": [], "nice_to_haves_matched": [], "nice_to_haves_missing": [], "role_type": "other", "remote_status": "not_mentioned", "years_required": 0, "skip_reason": ""}
        if result:
            score = result.get("score", 0)
            reason = result.get("reason", "")
            role_type = result.get("role_type", "other")
            logger.info(
                f"Score: {score}/100 [{role_type}] — "
                f"{job_title} @ {company} — {reason}"
            )
            return result
    except Exception as e:
        logger.error(f"Job scorer failed: {e}")

    # Fallback — score 0, skip
    return {
        "score": 0,
        "reason": "scorer failed",
        "must_haves_matched": [],
        "must_haves_missing": [],
        "nice_to_haves_matched": [],
        "nice_to_haves_missing": [],
        "role_type": "other",
        "remote_status": "not_mentioned",
        "years_required": 0,
        "skip_reason": "scorer API call failed",
    }


# ── AGENT 3: JD EXTRACTOR ────────────────────────────────────────────────────

def extract_jd(description: str) -> dict:
    """
    Extract structured data from a job description.
    Called after scoring passes threshold.
    Returns extraction dict used by cv_builder.py and application_actions.py.
    """
    skill_md = load_skill_md()

    system_prompt = f"""You are Agent 3: JD EXTRACTOR in a job application automation system.

{skill_md}

Your ONLY job right now is to act as AGENT 3: JD EXTRACTOR.
Return ONLY valid JSON. No markdown. No explanation. No preamble."""

    user_prompt = f"""Extract structured data from this job description.

Full job description:
{description[:3000]}

Return the JSON extraction object exactly as specified in your instructions."""

    try:
        raw = call_ai(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=800,
            json_response=True,
        )
        result = parse_json_response(raw, "JDExtractor")
        if result:
            logger.info(
                f"JD extracted: '{result.get('exact_job_title')}' @ "
                f"{result.get('company_name')} — "
                f"{len(result.get('must_haves', []))} must-haves, "
                f"{len(result.get('nice_to_haves', []))} nice-to-haves"
            )
            return result
    except Exception as e:
        logger.error(f"JD extractor failed: {e}")

    return {}


# ── AGENT 5: COVER LETTER GENERATOR ──────────────────────────────────────────

def generate_cover_letter(
    jd_extraction: dict,
    cv_text: str,
) -> str:
    """
    Generate a cover letter for this specific application.
    Called ONLY when page_intelligence_agent.py confirms a cover letter
    field exists in the form map.
    Returns plain text cover letter string.
    """
    skill_md = load_skill_md()

    system_prompt = f"""You are Agent 5: COVER LETTER GENERATOR in a job application automation system.

{skill_md}

Your ONLY job right now is to act as AGENT 5: COVER LETTER GENERATOR.
Return ONLY the cover letter text. No markdown. No subject line. No labels."""

    user_prompt = f"""Write a cover letter for this job application.

JD extraction data:
{json.dumps(jd_extraction, indent=2)}

CV text generated for this application:
{cv_text[:2000]}

Write the cover letter exactly as specified in your instructions.
Maximum 250 words. Plain text only."""

    try:
        raw = call_ai(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=600,
            json_response=False,
        )
        cover_letter = raw.strip()
        word_count = len(cover_letter.split())
        logger.info(
            f"Cover letter generated: {word_count} words for "
            f"'{jd_extraction.get('exact_job_title')}' @ "
            f"{jd_extraction.get('company_name')}"
        )
        return cover_letter
    except Exception as e:
        logger.error(f"Cover letter generation failed: {e}")
        return ""


# ── AGENT 6: CUSTOM QUESTION ANSWERER ────────────────────────────────────────

def answer_custom_question(
    question: str,
    jd_extraction: dict,
    agent_profile: dict,
    cv_text: str,
) -> str:
    """
    Answer a custom application question on Fortune's behalf.
    Called ONLY when page_intelligence_agent.py confirms custom question
    fields exist in the form map.
    Returns plain text answer string.
    """
    skill_md = load_skill_md()

    system_prompt = f"""You are Agent 6: CUSTOM QUESTION ANSWERER in a job application automation system.

{skill_md}

Your ONLY job right now is to act as AGENT 6: CUSTOM QUESTION ANSWERER.
Return ONLY the answer text. No markdown. No labels. No preamble."""

    user_prompt = f"""Answer this custom application question for Fortune Nwohiri.

Question: {question}

JD extraction data:
{json.dumps(jd_extraction, indent=2)}

Fortune's profile summary:
Name: {agent_profile.get('name')}
Email: {agent_profile.get('email')}
Location: {agent_profile.get('location')}
Years experience: {agent_profile.get('years_experience')}
LinkedIn: {agent_profile.get('linkedin')}
GitHub: {agent_profile.get('github')}
Portfolio: {agent_profile.get('portfolio')}

CV text generated for this application (use this as your source of facts):
{cv_text[:2000]}

Answer exactly as specified in your instructions.
Plain text only. First person. Maximum 150 words unless the question requires more."""

    try:
        raw = call_ai(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=400,
            json_response=False,
        )
        answer = raw.strip()
        logger.info(
            f"Custom question answered: '{question[:60]}...' "
            f"({len(answer.split())} words)"
        )
        return answer
    except Exception as e:
        logger.error(f"Custom question answer failed: {e}")
        return ""


# ── AGENT 7: EMAIL BODY GENERATOR ────────────────────────────────────────────

def generate_email_body(
    jd_extraction: dict,
    cv_text: str,
) -> dict:
    """
    Generate subject line and email body for email-only applications.
    Called by email_sender.py when job_connector.py classifies a listing
    as email-only.
    Returns dict with 'subject' and 'body' keys.
    """
    skill_md = load_skill_md()

    system_prompt = f"""You are Agent 7: EMAIL BODY GENERATOR in a job application automation system.

{skill_md}

Your ONLY job right now is to act as AGENT 7: EMAIL BODY GENERATOR.
Return ONLY the subject and body in the exact separator format specified.
No markdown. No extra text."""

    user_prompt = f"""Generate the subject line and email body for this job application.

JD extraction data:
{json.dumps(jd_extraction, indent=2)}

CV text generated for this application (use this as your source of facts):
{cv_text[:2000]}

Return the output in this exact format:
---SUBJECT---
[subject line]
---BODY---
[email body]"""

    try:
        raw = call_ai(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500,
            json_response=False,
        )

        # Parse the separator format
        subject = ""
        body = ""

        if "---SUBJECT---" in raw and "---BODY---" in raw:
            parts = raw.split("---BODY---")
            body = parts[1].strip() if len(parts) > 1 else ""
            subject_part = parts[0].split("---SUBJECT---")
            subject = subject_part[1].strip() if len(subject_part) > 1 else ""
        else:
            # Fallback subject if parsing fails
            role_title = jd_extraction.get("exact_job_title", "Software Engineer")
            subject = f"Application, {role_title}, Fortune Nwohiri"
            body = raw.strip()

        logger.info(
            f"Email generated: '{subject}' — "
            f"{len(body.split())} words"
        )
        return {"subject": subject, "body": body}

    except Exception as e:
        logger.error(f"Email body generation failed: {e}")
        role_title = jd_extraction.get("exact_job_title", "Software Engineer")
        return {
            "subject": f"Application, {role_title}, Fortune Nwohiri",
            "body": "",
        }


# ── AGENT 8: SALARY ADVISOR ───────────────────────────────────────────────────

def get_salary_expectation(
    jd_extraction: dict,
    agent_profile: dict,
    field_label: str = "salary expectation",
) -> str:
    """
    Determine the appropriate salary answer for this specific job.
    Called by application_actions.py when a salary field is detected.
    Returns a single string to fill into the salary field.
    """
    skill_md = load_skill_md()
    salary_expectations = agent_profile.get("salary_expectations", {})
    fallback = salary_expectations.get(
        "fallback",
        "Open to discussion based on scope and responsibilities"
    )

    system_prompt = f"""You are Agent 8: SALARY ADVISOR in a job application automation system.

{skill_md}

Your ONLY job right now is to act as AGENT 8: SALARY ADVISOR.
Return ONLY the salary string. One line. Nothing else. No explanation."""

    user_prompt = f"""Determine the salary answer for this job application.

Field label on the form: {field_label}

JD extraction data:
{jd_extraction}

Salary ranges to use:
NGN monthly min: {salary_expectations.get('ngn_monthly_min', 300000)}
NGN monthly max: {salary_expectations.get('ngn_monthly_max', 800000)}
USD annual min: {salary_expectations.get('usd_annual_min', 60000)}
USD annual max: {salary_expectations.get('usd_annual_max', 80000)}
GBP annual min: {salary_expectations.get('gbp_annual_min', 45000)}
GBP annual max: {salary_expectations.get('gbp_annual_max', 60000)}
EUR annual min: {salary_expectations.get('eur_annual_min', 50000)}
EUR annual max: {salary_expectations.get('eur_annual_max', 65000)}
Fallback: {fallback}

Follow the decision process in your instructions exactly.
Return only the salary string."""

    try:
        raw = call_ai(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=50,
            json_response=False,
        )
        answer = raw.strip()

        if answer.upper() == "SKIP":
            logger.info("Salary field flagged as SKIP by Agent 8")
            return "SKIP"

        logger.info(f"Salary answer: '{answer}' for '{jd_extraction.get('company_name')}'")
        return answer

    except Exception as e:
        logger.error(f"Salary advisor failed: {e}")
        return fallback

# ── MAIN BRAIN ORCHESTRATOR ───────────────────────────────────────────────────

class ApplicationBrain:
    """
    Orchestrates the full AI decision pipeline for one job listing.

    Flow:
    1. score_listing() — Agent 2
    2. If score passes threshold: extract_jd() — Agent 3
    3. cv_builder.build_cv() — Agent 4 (called from cv_builder.py)
    4. If form has cover letter field: generate_cover_letter() — Agent 5
    5. If form has custom questions: answer_custom_question() — Agent 6
    6. If email-only: generate_email_body() — Agent 7
    """

    def __init__(self, agent_profile: dict):
        self.agent_profile = agent_profile
        self.threshold = agent_profile.get("min_score_threshold", 72)
        self.state = load_state()
        self.session_applied = []
        self.session_skipped = []
        self.session_failed = []
        self.session_manual = []

    def already_seen(self, job_id: str) -> bool:
        return already_seen(job_id, self.state)

    def _detect_platform_name(self, url: str) -> str:
        """Detect human-readable platform name from URL."""
        url_lower = url.lower()

        # ATS platforms
        if "greenhouse.io" in url_lower:
            return "Greenhouse"
        if "lever.co" in url_lower:
            return "Lever"
        if "ashbyhq.com" in url_lower:
            return "Ashby"
        if "smartrecruiters.com" in url_lower:
            return "SmartRecruiters"
        if "workable.com" in url_lower:
            return "Workable"
        if "jobvite.com" in url_lower:
            return "Jobvite"
        if "icims.com" in url_lower:
            return "iCIMS"
        if "taleo.net" in url_lower:
            return "Taleo"
        if "myworkdayjobs.com" in url_lower or "workday.com" in url_lower:
            return "Workday"
        if "successfactors.com" in url_lower:
            return "SAP SuccessFactors"
        if "bamboohr.com" in url_lower:
            return "BambooHR"
        if "recruitee.com" in url_lower:
            return "Recruitee"
        if "pinpointhq.com" in url_lower:
            return "Pinpoint"
        if "dover.com" in url_lower:
            return "Dover"
        if "rippling.com" in url_lower:
            return "Rippling"
        if "freshteam.com" in url_lower:
            return "Freshteam"
        if "teamtailor.com" in url_lower:
            return "Teamtailor"
        if "personio.com" in url_lower:
            return "Personio"
        if "breezy.hr" in url_lower:
            return "Breezy HR"
        if "jazz.co" in url_lower or "jazzhr.com" in url_lower:
            return "JazzHR"
        if "zohorecruit" in url_lower:
            return "Zoho Recruit"
        if "recruitcrm.io" in url_lower:
            return "RecruitCRM"
        if "comeet.co" in url_lower:
            return "Comeet"
        if "homerun.hr" in url_lower:
            return "Homerun"
        if "polymer.co" in url_lower:
            return "Polymer"
        if "jobscore.com" in url_lower:
            return "JobScore"
        if "hire.trakstar.com" in url_lower:
            return "Trakstar"
        if "crelate.com" in url_lower:
            return "Crelate"
        if "workstream.us" in url_lower:
            return "Workstream"

        # Job boards and aggregators
        if "wellfound.com" in url_lower or "angel.co" in url_lower:
            return "Wellfound"
        if "contra.com" in url_lower:
            return "Contra"
        if "remoteok.com" in url_lower:
            return "RemoteOK"
        if "himalayas.app" in url_lower:
            return "Himalayas"
        if "remotive.com" in url_lower:
            return "Remotive"
        if "weworkremotely.com" in url_lower:
            return "WeWorkRemotely"
        if "jobgether.com" in url_lower:
            return "Jobgether"
        if "4dayweek.io" in url_lower:
            return "4DayWeek"
        if "workatastartup.com" in url_lower:
            return "Work at a Startup"
        if "ycombinator.com" in url_lower:
            return "YCombinator"
        if "producthunt.com" in url_lower:
            return "Product Hunt"
        if "startupjobs.com" in url_lower:
            return "StartupJobs"
        if "nodesk.co" in url_lower:
            return "Nodesk"
        if "remoteleaf.com" in url_lower:
            return "RemoteLeaf"
        if "remoteco.com" in url_lower or "remote.co" in url_lower:
            return "Remote.co"
        if "justremote.co" in url_lower:
            return "JustRemote"
        if "flexjobs.com" in url_lower:
            return "FlexJobs"
        if "remote.com" in url_lower:
            return "Remote.com"
        if "arc.dev" in url_lower:
            return "Arc.dev"
        if "toptal.com" in url_lower:
            return "Toptal"
        if "gun.io" in url_lower:
            return "Gun.io"
        if "lemon.io" in url_lower:
            return "Lemon.io"
        if "landing.jobs" in url_lower:
            return "Landing.jobs"
        if "relocate.me" in url_lower:
            return "Relocate.me"
        if "jobspresso.co" in url_lower:
            return "Jobspresso"
        if "authentic.jobs" in url_lower:
            return "Authentic Jobs"
        if "smashingmagazine.com/jobs" in url_lower:
            return "Smashing Magazine Jobs"
        if "stackoverflow.com/jobs" in url_lower or "jobs.stackoverflow.com" in url_lower:
            return "Stack Overflow Jobs"
        if "dice.com" in url_lower:
            return "Dice"
        if "hired.com" in url_lower:
            return "Hired"
        if "triplebyte.com" in url_lower:
            return "Triplebyte"
        if "andela.com" in url_lower:
            return "Andela"
        if "turing.com" in url_lower:
            return "Turing"
        if "crossover.com" in url_lower:
            return "Crossover"
        if "deel.com" in url_lower:
            return "Deel"
        if "braintrust.tools" in url_lower:
            return "Braintrust"
        if "workana.com" in url_lower:
            return "Workana"
        if "jooble.org" in url_lower:
            return "Jooble"
        if "simplyhired.com" in url_lower:
            return "SimplyHired"
        if "careerjet.com" in url_lower:
            return "CareerJet"
        if "ziprecruiter.com" in url_lower:
            return "ZipRecruiter"
        if "monster.com" in url_lower:
            return "Monster"
        if "glassdoor.com" in url_lower:
            return "Glassdoor"
        if "builtinnyc.com" in url_lower or "builtin.com" in url_lower:
            return "Built In"
        if "cwjobs.co.uk" in url_lower:
            return "CWJobs"
        if "totaljobs.com" in url_lower:
            return "TotalJobs"
        if "reed.co.uk" in url_lower:
            return "Reed"
        if "jobsite.co.uk" in url_lower:
            return "Jobsite"
        if "technojobs.co.uk" in url_lower:
            return "TechnoJobs"
        if "nigerianjobs.com" in url_lower:
            return "NigerianJobs"
        if "jobberman.com" in url_lower:
            return "Jobberman"
        if "myjobmag.com" in url_lower:
            return "MyJobMag"
        if "naijahotjobs.com" in url_lower:
            return "NaijaHotJobs"
        if "hotnigerianjobs.com" in url_lower:
            return "HotNigerianJobs"
        if "ngcareers.com" in url_lower:
            return "NGCareers"

        # Email application
        if "mailto:" in url_lower:
            return "Email"

        return "Direct"
    
    def process_listing(
        self,
        job: dict,
        description: str,
    ) -> dict:
        """
        Run the full scoring and extraction pipeline for one listing.

        Args:
            job: dict with job_id, url, platform_type, query
            description: full job description text extracted from the page

        Returns:
            dict with keys:
                proceed: bool — whether to continue to form filling
                score: int
                score_data: full scoring result from Agent 2
                jd_extraction: full extraction result from Agent 3
                skip_reason: str if not proceeding
        """
        job_id = job.get("job_id", "")
        url = job.get("url", "")

        # Deduplication check
        if self.already_seen(job_id):
            logger.info(f"Already seen: {url}")
            return {
                "proceed": False,
                "score": 0,
                "score_data": {},
                "jd_extraction": {},
                "skip_reason": "already_seen",
            }

        if not description or len(description.strip()) < 50:
            logger.warning(f"Description too short to score: {url}")
            self._record(job, "skipped", 0, {}, {}, "description_too_short")
            return {
                "proceed": False,
                "score": 0,
                "score_data": {},
                "jd_extraction": {},
                "skip_reason": "description_too_short",
            }

        # Natural pause before AI call — does not look like instant machine behavior
        time.sleep(random.uniform(1.5, 3.5))

        # Agent 2: Score the listing
        score_data = score_listing(
            job_title=job.get("title", "Unknown"),
            company=job.get("company", "Unknown"),
            description=description,
            agent_profile=self.agent_profile,
        )
        score = score_data.get("score", 0)

        if score < self.threshold:
            skip_reason = score_data.get("skip_reason") or f"score_{score}_below_threshold"
            logger.info(f"Score {score} below threshold {self.threshold} — skipping: {url}")
            self._record(job, "skipped", score, score_data, {}, skip_reason)
            return {
                "proceed": False,
                "score": score,
                "score_data": score_data,
                "jd_extraction": {},
                "skip_reason": skip_reason,
            }

        # Agent 3: Extract JD data
        time.sleep(random.uniform(1.0, 2.5))
        jd_extraction = extract_jd(description)

        if not jd_extraction:
            logger.warning(f"JD extraction failed for: {url}")
            self._record(job, "failed", score, score_data, {}, "jd_extraction_failed")
            return {
                "proceed": False,
                "score": score,
                "score_data": score_data,
                "jd_extraction": {},
                "skip_reason": "jd_extraction_failed",
            }

        logger.info(
            f"Listing passed: score {score}/100 "
            f"[{score_data.get('role_type')}] — "
            f"'{jd_extraction.get('exact_job_title')}' @ "
            f"{jd_extraction.get('company_name')}"
        )

        return {
            "proceed": True,
            "score": score,
            "score_data": score_data,
            "jd_extraction": jd_extraction,
            "skip_reason": "",
        }

    def record_applied(
        self,
        job: dict,
        score: int,
        score_data: dict,
        jd_extraction: dict,
        apply_method: str,
        cv_gap_report: str = "",
        had_cover_letter: bool = False,
        had_custom_questions: bool = False,
        honeypots_detected: int = 0,
    ):
        """Record a successful application to state."""
        self._record(
            job=job,
            status="applied",
            score=score,
            score_data=score_data,
            jd_extraction=jd_extraction,
            skip_reason="",
            apply_method=apply_method,
            cv_gap_report=cv_gap_report,
            had_cover_letter=had_cover_letter,
            had_custom_questions=had_custom_questions,
            honeypots_detected=honeypots_detected,
        )

    def record_failed(self, job: dict, score: int, reason: str):
        """Record a failed application attempt to state."""
        self._record(job, "failed", score, {}, {}, reason)

    def record_manual_queue(
        self,
        job: dict,
        score: int,
        jd_extraction: dict,
        cv_text: str,
        reason: str,
    ):
        """
        Record a listing to the manual queue.
        The CV is pre-generated and saved so Fortune can paste it manually.
        """
        from datetime import datetime
        entry = {
            "job_id": job.get("job_id"),
            "url": job.get("url"),
            "company": job.get("company", jd_extraction.get("company_name", "Unknown")),
            "title": job.get("title", jd_extraction.get("exact_job_title", "Unknown")),
            "platform_type": job.get("platform_type"),
            "score": score,
            "reason": reason,
            "cv_text": cv_text,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.state["manual_queue"].append(entry)
        self.session_manual.append(entry)
        save_state(self.state)
        logger.info(f"Added to manual queue: {job.get('url')} — {reason}")

    def _record(
        self,
        job: dict,
        status: str,
        score: int,
        score_data: dict,
        jd_extraction: dict,
        skip_reason: str,
        apply_method: str = "",
        cv_gap_report: str = "",
        had_cover_letter: bool = False,
        had_custom_questions: bool = False,
        honeypots_detected: int = 0,
    ):
        """Write a result entry to applied_jobs.json."""
        from datetime import datetime

        entry = {
            "job_id": job.get("job_id"),
            "url": job.get("url"),
            "company": job.get("company", jd_extraction.get("company_name", "Unknown")),
            "title": job.get("title", jd_extraction.get("exact_job_title", "Unknown")),
            "platform_type": job.get("platform_type"),
            "platform": self._detect_platform_name(job.get("url", "")),
            "score": score,
            "role_type": score_data.get("role_type", ""),
            "must_haves_matched": score_data.get("must_haves_matched", []),
            "must_haves_missing": score_data.get("must_haves_missing", []),
            "nice_to_haves_matched": score_data.get("nice_to_haves_matched", []),
            "remote_status": score_data.get("remote_status", ""),
            "apply_method": apply_method,
            "cv_gap_report": cv_gap_report,
            "had_cover_letter": had_cover_letter,
            "had_custom_questions": had_custom_questions,
            "honeypots_detected": honeypots_detected,
            "skip_reason": skip_reason,
            "failure_reason": skip_reason if status in ["failed", "skipped"] else "",
            "timestamp": datetime.utcnow().isoformat(),
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "status": status,
            "query": job.get("query", ""),
        }

        category = {
            "applied": "applied",
            "skipped": "skipped",
            "failed": "failed",
            "manual_queue": "manual_queue",
        }.get(status, "failed")

        self.state[category].append(entry)
        save_state(self.state)

        if status == "applied":
            self.session_applied.append(entry)
        elif status == "skipped":
            self.session_skipped.append(entry)
        elif status == "failed":
            self.session_failed.append(entry)

    def get_session_summary(self) -> dict:
        """Return summary of this session's results for the report generator."""
        return {
            "applied_count": len(self.session_applied),
            "skipped_count": len(self.session_skipped),
            "failed_count": len(self.session_failed),
            "manual_queue_count": len(self.session_manual),
            "applied": self.session_applied,
            "skipped": self.session_skipped,
            "failed": self.session_failed,
            "manual_queue": self.session_manual,
            "total_lifetime_applied": len(self.state.get("applied", [])),
        }