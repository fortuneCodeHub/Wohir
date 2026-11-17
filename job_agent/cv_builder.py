#!/usr/bin/python3
"""
    CV Builder — Generates a targeted CV for every job application.
    Uses Agent 4 from SKILL.md. Reads config/my_skills.md as the only
    source of facts. Converts output to PDF. Every application gets a
    unique PDF. Recruiter always sees Fortune_Nwohiri_CV.pdf.
    Author: Fortune Nwohiri
"""
import os
import re
import time
import random
from datetime import datetime
from pathlib import Path
from logging_config.logger import get_logger
from job_agent.ai_client import call_ai
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors

logger = get_logger("CVBuilder")

SKILL_MD_PATH = "./job_agent/SKILL.md"
MY_SKILLS_PATH = "./config/my_skills.md"
CV_OUTPUT_DIR = "./generated_cvs"


def load_skill_md() -> str:
    try:
        with open(SKILL_MD_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"SKILL.md not found at {SKILL_MD_PATH}")
        return ""


def load_my_skills() -> str:
    try:
        with open(MY_SKILLS_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"my_skills.md not found at {MY_SKILLS_PATH}")
        return ""


def ensure_cv_output_dir():
    Path(CV_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


def sanitize_filename(text: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", text)
    cleaned = re.sub(r"\s+", "_", cleaned.strip())
    return cleaned[:40]


def strip_gap_report(raw_cv: str) -> tuple:
    separator = "---GAP REPORT---"
    if separator in raw_cv:
        parts = raw_cv.split(separator, 1)
        cv_text = parts[0].strip()
        gap_report = parts[1].strip()
    else:
        cv_text = raw_cv.strip()
        gap_report = ""
    return cv_text, gap_report


def validate_cv(cv_text: str, jd_extraction: dict) -> list:
    warnings = []

    if not cv_text or len(cv_text.strip()) < 100:
        warnings.append("CV is empty or too short")
        return warnings

    word_count = len(cv_text.split())
    if word_count < 200:
        warnings.append(f"CV is suspiciously short: {word_count} words")

    exact_title = jd_extraction.get("exact_job_title", "")
    if exact_title and exact_title.lower() not in cv_text.lower():
        warnings.append(f"Exact job title '{exact_title}' not found in CV")

    must_haves = jd_extraction.get("must_haves", [])
    if must_haves:
        matched = [kw for kw in must_haves if kw.lower() in cv_text.lower()]
        if not matched:
            warnings.append("No must-have keywords found in CV")
        elif len(matched) < len(must_haves) / 2:
            warnings.append(
                f"Only {len(matched)}/{len(must_haves)} must-have keywords found in CV"
            )

    if "\u2014" in cv_text or " -- " in cv_text:
        warnings.append("Em dash detected in CV")

    if "Lagos" not in cv_text:
        warnings.append("Location Lagos State Nigeria not found in CV")

    if "Fortune Nwohiri" not in cv_text:
        warnings.append("Fortune Nwohiri name not found in CV")

    if "3 years" not in cv_text and "three years" not in cv_text.lower():
        warnings.append("Years of experience not found in CV")

    return warnings


def repair_cv(cv_text: str) -> str:
    repaired = cv_text
    repaired = repaired.replace("\u2014", ",")
    repaired = repaired.replace(" -- ", ", ")
    if "Lagos" not in repaired:
        repaired = repaired.replace(
            "fortunenwohiri@gmail.com",
            "fortunenwohiri@gmail.com | Lagos State, Nigeria"
        )
    return repaired


def convert_cv_to_pdf(
    cv_text: str,
    job_id: str,
    job_title: str,
    company: str,
) -> str:
    """
    Convert plain text CV to a properly formatted PDF using ReportLab.

    Saves two files:
    - Audit copy: generated_cvs/{timestamp}_{job_id}_{title}_{company}.pdf
    - Upload copy: generated_cvs/Fortune_Nwohiri_CV.pdf

    The upload copy is always overwritten with the latest CV.
    Recruiter always sees Fortune_Nwohiri_CV.pdf.

    Returns the path to Fortune_Nwohiri_CV.pdf.
    """
    ensure_cv_output_dir()

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    title_slug = sanitize_filename(job_title)
    company_slug = sanitize_filename(company)

    audit_filename = f"{timestamp}_{job_id[:8]}_{title_slug}_{company_slug}.pdf"
    audit_path = os.path.join(CV_OUTPUT_DIR, audit_filename)
    upload_path = os.path.join(CV_OUTPUT_DIR, "Fortune_Nwohiri_CV.pdf")

    # Section headers that trigger bold heading style
    SECTION_HEADERS = [
        "SKILLS", "EXPERIENCE", "PROJECTS", "NOTABLE ACHIEVEMENTS",
        "EDUCATION", "WORK EXPERIENCE", "TECHNICAL SKILLS",
        "ACHIEVEMENTS", "SUMMARY",
    ]

    def build_pdf(output_path: str):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
        )

        name_style = ParagraphStyle(
            "NameStyle",
            fontSize=18,
            fontName="Helvetica-Bold",
            spaceAfter=1 * mm,
            spaceBefore=0,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#111111"),
        )

        headline_style = ParagraphStyle(
            "HeadlineStyle",
            fontSize=11,
            fontName="Helvetica",
            spaceAfter=1 * mm,
            spaceBefore=0,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#333333"),
        )

        contact_style = ParagraphStyle(
            "ContactStyle",
            fontSize=9,
            fontName="Helvetica",
            spaceAfter=3 * mm,
            spaceBefore=0,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#555555"),
        )

        forwarding_style = ParagraphStyle(
            "ForwardingStyle",
            fontSize=10,
            fontName="Helvetica-Oblique",
            spaceAfter=4 * mm,
            spaceBefore=2 * mm,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#222222"),
            leading=15,
        )

        section_header_style = ParagraphStyle(
            "SectionHeaderStyle",
            fontSize=10,
            fontName="Helvetica-Bold",
            spaceBefore=5 * mm,
            spaceAfter=1 * mm,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#111111"),
        )

        role_title_style = ParagraphStyle(
            "RoleTitleStyle",
            fontSize=10,
            fontName="Helvetica-Bold",
            spaceBefore=3 * mm,
            spaceAfter=0.5 * mm,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#111111"),
        )

        body_style = ParagraphStyle(
            "BodyStyle",
            fontSize=9.5,
            fontName="Helvetica",
            spaceAfter=1 * mm,
            spaceBefore=0,
            leading=14,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#222222"),
        )

        bullet_style = ParagraphStyle(
            "BulletStyle",
            fontSize=9.5,
            fontName="Helvetica",
            spaceAfter=1 * mm,
            spaceBefore=0,
            leading=14,
            leftIndent=8 * mm,
            firstLineIndent=-4 * mm,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#222222"),
        )

        story = []
        lines = cv_text.split("\n")

        # Track parsing state
        line_index = 0
        past_header = False
        found_forwarding = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            if not stripped:
                story.append(Spacer(1, 1.5 * mm))
                continue

            # Line 0: Name
            if i == 0:
                story.append(Paragraph(stripped, name_style))
                continue

            # Line 1: Headline (job title | keywords)
            if i == 1:
                story.append(Paragraph(stripped, headline_style))
                continue

            # Line 2: Contact info (contains @ or |)
            if i == 2:
                story.append(Paragraph(stripped, contact_style))
                story.append(HRFlowable(
                    width="100%",
                    thickness=0.5,
                    color=colors.HexColor("#cccccc"),
                    spaceAfter=3 * mm,
                    spaceBefore=1 * mm,
                ))
                continue

            # Forwarding sentence: first full sentence paragraph after contact
            # Identified by not being a section header and not starting with -
            if not found_forwarding and not stripped.startswith("-"):
                upper = stripped.upper()
                is_section = any(
                    upper == h or upper.startswith(h + " ") or upper.startswith(h + ":")
                    for h in SECTION_HEADERS
                )
                if not is_section:
                    story.append(Paragraph(stripped, forwarding_style))
                    story.append(HRFlowable(
                        width="100%",
                        thickness=0.5,
                        color=colors.HexColor("#cccccc"),
                        spaceAfter=2 * mm,
                        spaceBefore=1 * mm,
                    ))
                    found_forwarding = True
                    continue

            # Section headers
            upper = stripped.upper()
            is_section_header = any(
                upper == h or upper.startswith(h + " ") or upper.startswith(h + ":")
                for h in SECTION_HEADERS
            )
            if is_section_header:
                story.append(Paragraph(stripped.upper(), section_header_style))
                story.append(HRFlowable(
                    width="100%",
                    thickness=0.3,
                    color=colors.HexColor("#dddddd"),
                    spaceAfter=1 * mm,
                    spaceBefore=0,
                ))
                continue

            # Bullet points
            if stripped.startswith("-"):
                bullet_text = stripped[1:].strip()
                story.append(Paragraph(f"\u2022  {bullet_text}", bullet_style))
                continue

            # Role or project title lines: lines that contain | (Title | Company | Dates)
            if "|" in stripped and not "@" in stripped:
                story.append(Paragraph(stripped, role_title_style))
                continue

            # Everything else: body text
            story.append(Paragraph(stripped, body_style))

        doc.build(story)

    try:
        build_pdf(audit_path)
        build_pdf(upload_path)
        logger.info(f"PDF audit copy: {audit_path}")
        logger.info(f"PDF upload copy: {upload_path}")
        return upload_path
    except Exception as e:
        logger.error(f"PDF conversion failed: {e}", exc_info=True)
        return ""


def build_cover_letter_pdf(cover_letter_text: str) -> str:
    """
    Convert plain text cover letter to a PDF file.
    Saves to generated_cvs/Fortune_Nwohiri_Cover_Letter.pdf.
    This is the upload-ready file for forms that require a
    cover letter as a file rather than a textarea.
    Returns the file path or empty string on failure.
    """
    ensure_cv_output_dir()

    upload_path = os.path.join(CV_OUTPUT_DIR, "Fortune_Nwohiri_Cover_Letter.pdf")

    def build_pdf(output_path: str):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=25 * mm,
            leftMargin=25 * mm,
            topMargin=25 * mm,
            bottomMargin=25 * mm,
        )

        body_style = ParagraphStyle(
            "CLBodyStyle",
            fontSize=10.5,
            fontName="Helvetica",
            spaceAfter=4 * mm,
            leading=16,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#222222"),
        )

        story = []
        lines = cover_letter_text.split("\n")

        for line in lines:
            stripped = line.strip()
            if not stripped:
                story.append(Spacer(1, 3 * mm))
            else:
                story.append(Paragraph(stripped, body_style))

        doc.build(story)

    try:
        build_pdf(upload_path)
        logger.info(f"Cover letter PDF ready: {upload_path}")
        return upload_path
    except Exception as e:
        logger.error(f"Cover letter PDF conversion failed: {e}", exc_info=True)
        return ""

def build_cv(
    jd_extraction: dict,
    job_id: str,
    max_retries: int = 2,
) -> dict:
    """
    Main CV builder function. Called from job_connector.py after
    application_brain.process_listing() returns proceed=True.

    Flow:
    1. Load SKILL.md and my_skills.md
    2. Call Agent 4 via AgentRouter to generate plain text CV
    3. Validate the output
    4. Repair minor issues
    5. Convert to PDF via ReportLab
    6. Save audit copy and upload copy
    7. Return result dict

    Returns:
        dict with keys:
            success: bool
            cv_text: str — plain text CV
            cv_path: str — path to Fortune_Nwohiri_CV.pdf for uploads
            gap_report: str — must-haves Fortune cannot cover
            warnings: list — non-critical validation warnings
            word_count: int
    """
    skill_md = load_skill_md()
    my_skills = load_my_skills()

    if not skill_md:
        logger.error("SKILL.md could not be loaded. Cannot build CV.")
        return {
            "success": False, "cv_text": "", "cv_path": "",
            "gap_report": "", "warnings": [], "word_count": 0,
        }

    if not my_skills:
        logger.error("my_skills.md could not be loaded. Cannot build CV.")
        return {
            "success": False, "cv_text": "", "cv_path": "",
            "gap_report": "", "warnings": [], "word_count": 0,
        }

    job_title = jd_extraction.get("exact_job_title", "Unknown Role")
    company = jd_extraction.get("company_name", "Unknown Company")
    must_haves = jd_extraction.get("must_haves", [])
    nice_to_haves = jd_extraction.get("nice_to_haves", [])
    domain = jd_extraction.get("domain", "other")
    role_type = jd_extraction.get("role_type", "fullstack")

    logger.info(f"Building CV: '{job_title}' @ {company}")
    logger.info(f"Must-haves: {must_haves}")

    system_prompt = f"""You are Agent 4: CV BUILDER in a job application automation system.

{skill_md}

Your ONLY job right now is to act as AGENT 4: CV BUILDER.

The complete contents of config/my_skills.md follow below.
Every fact in the CV must come from this file and nowhere else.
No invented facts. No invented metrics. No invented projects. No em dashes.

--- START OF my_skills.md ---
{my_skills}
--- END OF my_skills.md ---

Return the CV text first.
Then on a new line output the separator: ---GAP REPORT---
Then list any must-haves the portfolio cannot cover, one per line.
If no gaps write: None

Plain text only. No markdown. No bold markers. No asterisks.
Use simple hyphens for bullet points.
Use pipe characters to separate role title, company, and dates on one line."""

    user_prompt = f"""Build a targeted CV for Fortune Nwohiri for this specific job.

Exact job title from the ad: {job_title}
Company: {company}
Domain: {domain}
Role type: {role_type}
Must-have keywords (use EXACT wording): {must_haves}
Nice-to-have keywords (use EXACT wording): {nice_to_haves}

Full JD extraction:
{jd_extraction}

Follow the complete workflow in Part 3 of my_skills.md exactly.
Step 1: Confirm exact job title and must-haves from above
Step 2: Identify role type and select projects using role-type routing
Step 3: Map every must-have to evidence in Part 2
Step 4: Write the forwarding sentence using Rule 3.2
Step 5: Select and order entries by relevance to this ad
Step 6: Build skills section with ad keywords first in ad exact wording
Step 7: Run the Final Checklist
Step 8: Deliver in the output format from Part 3

Output the CV then ---GAP REPORT--- then the gaps."""

    for attempt in range(max_retries):
        if attempt > 0:
            logger.info(f"CV rebuild attempt {attempt + 1} for '{job_title}' @ {company}")
            time.sleep(random.uniform(2, 5))

        try:
            raw = call_ai(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
                json_response=False,
            )

            cv_text, gap_report = strip_gap_report(raw)

            if not cv_text or len(cv_text.strip()) < 100:
                logger.warning(f"Empty CV output on attempt {attempt + 1}")
                continue

            # Repair minor issues
            cv_text = repair_cv(cv_text)

            # Validate
            warnings = validate_cv(cv_text, jd_extraction)

            # Critical failures that require a retry
            critical_failures = [w for w in warnings if any(
                keyword in w for keyword in [
                    "empty", "too short", "name not found", "No must-have keywords"
                ]
            )]

            if critical_failures and attempt < max_retries - 1:
                logger.warning(
                    f"Critical failures on attempt {attempt + 1}: "
                    f"{critical_failures}. Retrying."
                )
                continue

            for warning in warnings:
                logger.warning(f"CV warning: {warning}")

            # Convert to PDF
            pdf_path = convert_cv_to_pdf(cv_text, job_id, job_title, company)

            if not pdf_path:
                logger.error("PDF conversion failed")
                if attempt < max_retries - 1:
                    continue
                return {
                    "success": False, "cv_text": cv_text, "cv_path": "",
                    "gap_report": gap_report, "warnings": warnings + ["PDF conversion failed"],
                    "word_count": len(cv_text.split()),
                }

            word_count = len(cv_text.split())
            logger.info(
                f"CV complete: {word_count} words, "
                f"{len(warnings)} warnings, "
                f"gaps: {gap_report if gap_report and gap_report.lower() != 'none' else 'none'}"
            )

            return {
                "success": True,
                "cv_text": cv_text,
                "cv_path": pdf_path,
                "gap_report": gap_report,
                "warnings": warnings,
                "word_count": word_count,
            }

        except Exception as e:
            logger.error(f"CV builder failed on attempt {attempt + 1}: {e}", exc_info=True)
            if attempt < max_retries - 1:
                time.sleep(random.uniform(3, 8))
            continue

    logger.error(f"CV builder failed after {max_retries} attempts for '{job_title}' @ {company}")
    return {
        "success": False, "cv_text": "", "cv_path": "",
        "gap_report": "", "warnings": ["All generation attempts failed"],
        "word_count": 0,
    }


def get_fallback_resume_path(agent_profile: dict) -> str:
    """
    Returns the fallback generic resume PDF path.
    Used only when cv_builder fails or when a platform requires
    a file upload before the full JD is visible.
    """
    fallback = agent_profile.get("fallback_resume_path", "./assets/fortune_nwohiri_resume.pdf")
    if os.path.exists(fallback):
        return fallback
    logger.warning(f"Fallback resume not found at: {fallback}")
    return ""