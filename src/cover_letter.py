"""Generate cover letters: UN style, Jobs.af/ACBAR style, or customized with placeholders.
All personal data (name, email, phone, university, previous employer) comes from config/.env."""
from pathlib import Path
from typing import Optional

from src.sites.base import JobListing
from src.config import (
    ensure_dirs,
    DATA_DIR,
    FULL_NAME,
    SUBMISSION_EMAIL,
    PHONE_COUNTRY_CODE,
    PHONE_NUMBER,
    COVER_LETTER_UNIVERSITY,
    COVER_LETTER_PREVIOUS_ORGANIZATION,
)


def _signature() -> str:
    """Signature block from config (no hardcoded personal data)."""
    name = (FULL_NAME or "Applicant").strip()
    email = (SUBMISSION_EMAIL or "").strip()
    phone = ""
    if PHONE_COUNTRY_CODE or PHONE_NUMBER:
        phone = f"{PHONE_COUNTRY_CODE or ''}{PHONE_NUMBER or ''}".strip()
    lines = [name]
    if email:
        lines.append(email)
    if phone:
        lines.append(phone)
    return "\n".join(lines)


# --- UN jobs (unjobs.org): formal, detailed ---
UN_TEMPLATE = """Dear Hiring Manager,

I am writing to express my interest in contributing to your organization in the area of Information Technology, Digital Systems Support, or Software Development. With a Bachelor's degree in Computer Science from {{UNIVERSITY}} and several years of experience supporting information systems, web platforms, and database-driven applications, I am motivated to apply my technical skills to support programs that create sustainable and measurable impact.

In my previous role as ICT Support Officer and Consultant at {{PREVIOUS_ORGANIZATION}}, I contributed to the redesign and improvement of Management Information Systems (MIS) for organizational clients. My responsibilities included providing technical support, managing databases, troubleshooting system issues, and assisting teams in implementing technology solutions that improve operational efficiency and information management.

Alongside my consulting experience, I have worked as a freelance software developer developing web applications and digital platforms. My work has included developing backend systems using Python, building web interfaces using modern JavaScript frameworks, integrating secure payment gateways, and managing relational databases such as MySQL and PostgreSQL. I have also worked on projects involving generative AI integrations and data analysis tools.

I am particularly interested in applying my skills in environments where technology supports humanitarian programs, data-driven decision making, and efficient service delivery. My experience working with nonprofit organizations and development-related initiatives has strengthened my understanding of accountability, ethical standards, and collaboration in multicultural teams.

I am confident that my background in software development, IT systems support, and digital solutions would allow me to contribute effectively to your organization's mission and operational objectives.

Thank you for considering my application. I look forward to the opportunity to further discuss how my technical expertise and commitment to service can support your programs.

Sincerely,
{{SIGNATURE}}"""

# --- Customized template (placeholders filled from job) ---
CUSTOM_TEMPLATE = """Dear Hiring Manager,

I am writing to apply for the position of {{JOB_TITLE}} at {{ORGANIZATION_NAME}}. With a Bachelor's degree in Computer Science and professional experience in {{PRIMARY_SKILL_AREA}}, I am confident in my ability to contribute effectively to your team.

My background includes experience in {{KEY_SKILLS}}, including software development, IT systems support, and database management. I have worked on projects involving {{TECH_STACK}} and have supported organizations by improving digital systems, developing web applications, and ensuring reliable technical operations.

Previously, I worked with {{PREVIOUS_ORGANIZATION}} where I supported system development and provided technical solutions for operational needs. In addition, my freelance development experience has allowed me to design and implement web platforms, integrate modern technologies, and develop scalable applications.

I am particularly interested in contributing to {{ORGANIZATION_NAME}} because of its work in {{ORGANIZATION_MISSION_OR_FIELD}}. I am confident that my technical expertise, problem-solving skills, and commitment to professional excellence would allow me to contribute positively to your organization.

Thank you for considering my application. I look forward to the opportunity to further discuss my qualifications.

Sincerely,
{{SIGNATURE}}"""


def _fill_common_placeholders(text: str) -> str:
    """Fill {{SIGNATURE}} and optionally {{UNIVERSITY}} / {{PREVIOUS_ORGANIZATION}}.

    When the university or previous-organization fields are empty, the surrounding
    clause is removed entirely so the letter never prints filler like
    "from your university" or "with my previous organization".
    """
    uni = (COVER_LETTER_UNIVERSITY or "").strip()
    org = (COVER_LETTER_PREVIOUS_ORGANIZATION or "").strip()

    if uni:
        text = text.replace("{{UNIVERSITY}}", uni)
    else:
        text = text.replace(" from {{UNIVERSITY}}", "")
        text = text.replace("{{UNIVERSITY}}", "")  # safety net

    if org:
        text = text.replace("{{PREVIOUS_ORGANIZATION}}", org)
    else:
        text = text.replace(" at {{PREVIOUS_ORGANIZATION}}", "")                       # UN: "Consultant, I…"
        text = text.replace("worked with {{PREVIOUS_ORGANIZATION}} as", "worked as")   # General
        text = text.replace("I worked with {{PREVIOUS_ORGANIZATION}} where I", "I")     # Custom: "Previously, I…"
        text = text.replace("{{PREVIOUS_ORGANIZATION}}", "")  # safety net

    return text.replace("{{SIGNATURE}}", _signature())


def _customized_letter(job: JobListing) -> str:
    """Fill customized template with job details."""
    title = (job.title or "the position").strip()
    company = (job.company or "").strip()
    # ACBAR often exposes no real org name (defaults to "ACBAR Member") — avoid a
    # robotic "at ACBAR Member"; address it generically instead.
    if not company or company.lower() in ("acbar member", "acbar"):
        company = "your organization"
    role_lower = title.lower()
    if any(x in role_lower for x in ["engineer", "developer"]):
        primary = "software development and IT systems"
        key_skills = "software development, IT systems support, and database management"
        tech_stack = "Python, JavaScript, MySQL, PostgreSQL, and modern web frameworks"
    elif any(x in role_lower for x in ["data", "analyst"]):
        primary = "data and analytics"
        key_skills = "data management, analysis, and technical support"
        tech_stack = "Python, SQL, databases, and data tools"
    elif any(x in role_lower for x in ["manager", "coordinator", "officer", "lead", "specialist"]):
        primary = "project coordination and IT operations"
        key_skills = "project support, IT systems management, and process improvement"
        tech_stack = "MIS platforms, databases, and web-based tools"
    else:
        primary = "information technology and digital solutions"
        key_skills = "IT support, web development, and database management"
        tech_stack = "Python, JavaScript, MySQL, PostgreSQL, and web technologies"

    return _fill_common_placeholders(
        CUSTOM_TEMPLATE.replace("{{JOB_TITLE}}", title)
        .replace("{{ORGANIZATION_NAME}}", company)
        .replace("{{PRIMARY_SKILL_AREA}}", primary)
        .replace("{{KEY_SKILLS}}", key_skills)
        .replace("{{TECH_STACK}}", tech_stack)
        .replace("{{ORGANIZATION_MISSION_OR_FIELD}}", "development and technology-driven operations")
    )


def generate_cover_letter(job: JobListing) -> str:
    """UN template for UN jobs (formal); a job-tailored letter (names the role and
    organization, role-aware skills) for every other portal so letters are never
    generic."""
    job_id = (job.id or "").lower()
    if job_id.startswith("unjobs") or job_id.startswith("un_careers"):
        return _fill_common_placeholders(UN_TEMPLATE)
    return _customized_letter(job)


def write_cover_letter_for_job(job: JobListing) -> Optional[Path]:
    """
    Generate cover letter for this job and write to a temp file in data/.
    Returns path to the .txt file, or None on error.
    """
    ensure_dirs()
    text = generate_cover_letter(job)
    safe_id = "".join(c if c.isalnum() else "_" for c in job.id)[:32]
    path = DATA_DIR / f"cover_letter_{safe_id}.txt"
    try:
        path.write_text(text, encoding="utf-8")
        return path
    except Exception:
        return None
