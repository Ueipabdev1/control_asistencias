"""Build a reviewable 2026-2027 packet using read-only real-data sources."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unicodedata

from dev.migration_packet import (
    EMAIL_PATTERN,
    PacketValidationError,
    load_packet,
    validate_packet,
    write_packet,
)
GRADE_NAMES = [
    "Nivel 1 maternal",
    "Nivel 2 maternal",
    "Nivel 3 maternal",
    "1er grado primaria",
    "2do grado primaria",
    "3er grado primaria",
    "4to grado primaria",
    "5to grado primaria",
    "6to grado primaria",
    "1er año secundaria",
    "2do año secundaria",
    "3er año secundaria",
    "4to año secundaria",
    "5to año secundaria",
]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = PROJECT_ROOT / "dev" / "backups" / "real_2026_2027"
REPORT_PATH = PROJECT_ROOT / "dev" / "reports" / "real_2026_2027_extraction.json"
EXCEL_PATH = PROJECT_ROOT / "data_estudiantes_akademia" / "lista_de_estudiantes20260224-1-454yde.xls"
AKDEMIA_DIRECTORY = Path("/opt/odoo-dev/scripts/output/akdemia_admissions")
KAMPUS_DIRECTORY = Path("/opt/odoo-dev/scripts/output/kampus")
ODOO_SCRIPTS_DIRECTORY = Path("/opt/odoo-dev/scripts")
AKDEMIA_PARSER_PATH = ODOO_SCRIPTS_DIRECTORY / "akdemia_admissions_scraper.py"
ACADEMIC_PERIOD = "2026-2027"
EXPECTED_KAMPUS_SCHEDULE = "6aaa86481709b6aa8d7263b7"
EXPECTED_KAMPUS_PUBLISHED = "2026-09-16T12:06:32.334Z"
EXPECTED_PRODUCTION_COUNTS = {
    "students": 227,
    "active_students": 224,
    "attendance_rows": 39009,
}
AKDEMIA_STATUSES = ("approved", "pending", "in_progress", "rejected")
ENROLLING_STATUSES = frozenset(("approved", "pending", "in_progress"))
NEW_INTAKE_JOURNEY_IDS = frozenset(range(174, 195))
GRADE_LABELS = (
    "1er Grupo",
    "2do Grupo",
    "3er Grupo",
    "1er. Grado",
    "2do. Grado",
    "3er. Grado",
    "4to. Grado",
    "5to. Grado",
    "6to. Grado",
    "1er. Año",
    "2do. Año",
    "3er. Año",
    "4to. Año",
    "5to. Año",
)
KAMPUS_GROUP_MAP = {
    "1er grupo // 2do grupo · A": ((1, "A"), (2, "A")),
    "3er grupo · A": ((3, "A"),),
    "1er Grado · A": ((4, "A"),),
    "2do Grado · A": ((5, "A"),),
    "3er Grado · A": ((6, "A"),),
    "4to Grado · A": ((7, "A"),),
    "5to Grado · A": ((8, "A"),),
    "6to Grado · A": ((9, "A"),),
    "1er año · A": ((10, "A"),),
    "2do año · A": ((11, "A"),),
    "3er año · A": ((12, "A"),),
    "4to año · A": ((13, "A"),),
    "4to año · B": ((13, "B"),),
    "5to año · A": ((14, "A"),),
}
COMBINED_MATERNAL_GROUP = "1er grupo // 2do grupo · A"


class ExtractionBlocked(RuntimeError):
    pass


def normalize_identifier(value):
    return re.sub(r"\D", "", str(value or ""))


def normalize_name(value):
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join(
        "".join(character for character in normalized if not unicodedata.combining(character)).split()
    ).upper()


def normalize_grade(value):
    normalized = str(value or "").lower().replace("°", "").replace("º", "").replace(".", "")
    normalized = " ".join(normalized.split())
    for grade_id, label in enumerate(GRADE_LABELS, start=1):
        candidate = label.lower().replace(".", "")
        if normalized == candidate:
            return grade_id
    return None


def normalize_section(value):
    normalized = " ".join(str(value or "").strip().upper().split())
    if normalized in ("U", "UNICA", "ÚNICA"):
        return "A"
    return normalized if normalized in ("A", "B") else ""


def normalize_email(value):
    return str(value or "").strip().lower()


def target_sections():
    rows = []
    for grade_id, grade in enumerate(GRADE_NAMES, start=1):
        for section in (("A", "B") if grade_id == 13 else ("A",)):
            group_label = next(
                label for label, targets in KAMPUS_GROUP_MAP.items() if (grade_id, section) in targets
            )
            rows.append({
                "grade": grade,
                "section": section,
                "group_label": group_label,
                "active": True,
            })
    return rows


def progression(current_grade_id, current_section):
    if current_grade_id == 14:
        return {"status": "graduated", "target_grade_id": None, "default_section": ""}
    if not 1 <= current_grade_id < 14:
        raise ExtractionBlocked("unsupported_current_grade")
    target_grade_id = current_grade_id + 1
    default_section = "A"
    if current_grade_id == 12:
        default_section = normalize_section(current_section)
        if default_section not in ("A", "B"):
            default_section = ""
    return {
        "status": "continuing",
        "target_grade_id": target_grade_id,
        "default_section": default_section,
    }


def index_rows(rows, key_function):
    index = defaultdict(list)
    for row in rows:
        key = key_function(row)
        if key:
            index[key].append(row)
    return index


def exact_match(index, identifier, available=True):
    if not available:
        return {"state": "unavailable", "row": None}
    if not identifier:
        return {"state": "not_attempted", "row": None}
    matches = index.get(identifier, [])
    if len(matches) > 1:
        return {"state": "collision", "row": None}
    if not matches:
        return {"state": "missing", "row": None}
    return {"state": "unique", "row": matches[0]}


def add_name_only_hint(match, name_index, name):
    if match["state"] != "missing":
        return match
    hints = name_index.get(normalize_name(name), []) if normalize_name(name) else []
    match = dict(match)
    match["name_only_hint"] = "unique" if len(hints) == 1 else "ambiguous" if hints else "none"
    return match


def map_student(local, sources, roster_hint, local_identity_issue=""):
    reasons = []
    warnings = []

    def review(reason):
        if reason not in reasons:
            reasons.append(reason)

    def warn(reason):
        if reason not in warnings:
            warnings.append(reason)

    current_grade_id = int(local["current_grade_id"])
    route = progression(current_grade_id, local["current_section"])
    target_grade_id = route["target_grade_id"]
    selected_section = route["default_section"]
    section_source = "target_structure" if route["status"] == "continuing" else ""
    if local.get("current_grade_name") != GRADE_NAMES[current_grade_id - 1]:
        review("local_grade_name_mismatch")
    if local_identity_issue:
        review(local_identity_issue)
    if current_grade_id != 12 and normalize_section(local["current_section"]) != "A":
        review("local_section_unexpected")

    odoo = sources["odoo"]
    akdemia = sources["akdemia"]
    excel = sources["excel"]
    odoo_row = odoo.get("row") if not local_identity_issue else None
    odoo_authoritative = False
    if odoo_row and odoo["state"] == "unique":
        identity_and_population_match = (
            normalize_name(odoo_row.get("name")) == normalize_name(local["student_name"])
            and odoo_row.get("_population") == "continuing_confirmed"
        )
        if identity_and_population_match:
            if route["status"] == "graduated":
                odoo_authoritative = bool(odoo_row.get("is_graduating") and not odoo_row.get("grade_next"))
            else:
                odoo_authoritative = bool(
                    not odoo_row.get("is_graduating")
                    and normalize_grade(odoo_row.get("grade_next")) == target_grade_id
                )

    def secondary_review(reason):
        if odoo_authoritative:
            warn(reason)
        else:
            review(reason)

    if not local_identity_issue:
        for source_name, match in (("odoo", odoo), ("akdemia", akdemia), ("excel", excel)):
            state = match["state"]
            record = review if source_name == "odoo" else secondary_review
            if state == "unavailable":
                record(f"{source_name}_source_unavailable")
            elif state == "collision":
                record(f"{source_name}_identifier_collision")
            elif state == "missing" and not (source_name == "akdemia" and route["status"] == "graduated"):
                record(f"{source_name}_missing_exact_id")
    if odoo_row:
        if normalize_name(odoo_row.get("name")) != normalize_name(local["student_name"]):
            review("odoo_name_mismatch")
        if odoo_row.get("_population") != "continuing_confirmed":
            review("odoo_population_mismatch")
        if route["status"] == "graduated":
            if not odoo_row.get("is_graduating") or odoo_row.get("grade_next"):
                review("odoo_graduation_conflict")
        else:
            if odoo_row.get("is_graduating"):
                review("odoo_graduation_conflict")
            else:
                odoo_grade = normalize_grade(odoo_row.get("grade_next"))
                if not odoo_row.get("grade_next"):
                    review("odoo_target_grade_missing")
                elif odoo_grade is None:
                    review("odoo_target_grade_unmapped")
                elif odoo_grade != target_grade_id:
                    review("odoo_target_grade_conflict")
            if target_grade_id == 13:
                odoo_section = normalize_section(odoo_row.get("section"))
                if odoo_section in ("A", "B"):
                    selected_section = odoo_section
                    source = str(odoo_row.get("section_source") or "record").lower()
                    section_source = f"odoo_{source}"
                    if source != "staff" and odoo_section != route["default_section"]:
                        review("odoo_section_conflict")
                elif not selected_section:
                    raise ExtractionBlocked("unresolved_fourth_year_section")
                elif odoo_row.get("section"):
                    review("odoo_section_invalid")
                else:
                    review("odoo_section_missing")
            elif odoo_row.get("section"):
                odoo_section = normalize_section(odoo_row.get("section"))
                if not odoo_section:
                    review("odoo_section_invalid")
                elif odoo_section != "A":
                    review("odoo_section_conflict")

    akdemia_row = akdemia.get("row") if not local_identity_issue else None
    if akdemia_row:
        if akdemia_row.get("cedula_kind") not in ("nacional", "escolar"):
            secondary_review("akdemia_identifier_malformed")
        if akdemia_row.get("_status") not in ENROLLING_STATUSES:
            secondary_review("akdemia_population_mismatch")
        elif route["status"] == "graduated":
            secondary_review("akdemia_graduation_conflict")
        else:
            akdemia_grade = normalize_grade(akdemia_row.get("grade_target"))
            if not akdemia_row.get("grade_target"):
                secondary_review("akdemia_target_grade_missing")
            elif akdemia_grade is None:
                secondary_review("akdemia_target_grade_unmapped")
            elif akdemia_grade != target_grade_id:
                secondary_review("akdemia_target_grade_conflict")

    excel_row = excel.get("row") if not local_identity_issue else None
    if excel_row:
        if normalize_name(excel_row.get("student_name")) != normalize_name(local["student_name"]):
            secondary_review("excel_name_mismatch")
        excel_grade = normalize_grade(excel_row.get("current_grade"))
        if excel_grade is None:
            secondary_review("excel_current_grade_unmapped")
        elif excel_grade != current_grade_id:
            secondary_review("excel_current_grade_conflict")
        excel_section = normalize_section(excel_row.get("current_section"))
        if not excel_section:
            secondary_review("excel_current_section_unmapped")
        elif excel_section != normalize_section(local["current_section"]):
            secondary_review("excel_current_section_conflict")

    if route["status"] == "continuing" and roster_hint and not local_identity_issue:
        hint_state = roster_hint["state"]
        if hint_state == "unique":
            if roster_hint.get("section") != selected_section:
                review("roster_section_conflict")
        elif target_grade_id == 13:
            review(f"roster_section_hint_{hint_state}")
    if route["status"] == "continuing" and selected_section not in ("A", "B"):
        raise ExtractionBlocked("unresolved_target_section")

    source_student_id = str(local["source_student_id"])
    row = {
        "source_student_id": source_student_id,
        "student_name": local["student_name"],
        "match_key": str(local["match_key"] or "").strip(),
        "target_grade": GRADE_NAMES[target_grade_id - 1] if target_grade_id else "",
        "section": selected_section,
        "status": route["status"],
        "grade_is_target": bool(odoo_row and odoo_row.get("grade_is_target")),
        "section_source": section_source,
        "review_required": bool(reasons),
    }
    reconciliation = {
        "source_student_id": source_student_id,
        "match_key": row["match_key"],
        "authority": "odoo_enrollment_journey" if odoo_authoritative else "local_progression_with_review",
        "reasons": reasons,
        "warnings": warnings,
        "source_matches": {
            name: {
                "state": match["state"],
                "name_only_hint": match.get("name_only_hint", "not_applicable"),
            }
            for name, match in sources.items()
        },
        "odoo_population": odoo_row.get("_population") if odoo_row else "not_matched",
        "roster_hint": roster_hint or {"state": "not_applicable"},
    }
    return row, reconciliation


def roster_section_hint(roster_rows, student_name, target_grade_id, ambiguous_name=False):
    if roster_rows is None or target_grade_id is None:
        return {"state": "unavailable" if roster_rows is None else "not_applicable"}
    if ambiguous_name:
        return {"state": "ambiguous"}
    matches = [
        row for row in roster_rows
        if normalize_name(row.get("student")) == normalize_name(student_name)
        and normalize_grade(row.get("grade")) == target_grade_id
    ]
    if not matches:
        return {"state": "missing"}
    sections = {normalize_section(row.get("section")) for row in matches}
    if len(sections) == 1 and "" not in sections:
        return {"state": "unique", "section": sections.pop()}
    return {"state": "ambiguous"}


def extract_teacher_sections(published, teacher_profiles, local_professors):
    profile_index = index_rows(teacher_profiles, lambda row: str(row.get("_id") or ""))
    professor_index = index_rows(local_professors, lambda row: normalize_email(row.get("email")))
    pairs = sorted({
        (str(teacher.get("id") or ""), str(block.get("groupLabel") or ""))
        for block in published.get("blocks", [])
        for teacher in block.get("teachers") or []
    })
    used_profile_ids = {teacher_id for teacher_id, _ in pairs if teacher_id}
    email_profile_ids = defaultdict(set)
    for teacher_id in used_profile_ids:
        profiles = profile_index.get(teacher_id, [])
        if len(profiles) == 1:
            email = normalize_email(profiles[0].get("email"))
            if email:
                email_profile_ids[email].add(teacher_id)

    rows = []
    issues = []
    combined_emitted = 0
    for teacher_id, group_label in pairs:
        targets = KAMPUS_GROUP_MAP.get(group_label, ())
        profiles = profile_index.get(teacher_id, []) if teacher_id else []
        profile = profiles[0] if len(profiles) == 1 else None
        email = normalize_email(profile.get("email")) if profile else ""
        pair_reasons = []
        if not teacher_id:
            pair_reasons.append("missing_teacher_profile_id")
        elif len(profiles) != 1:
            pair_reasons.append("teacher_profile_collision" if profiles else "teacher_profile_unmatched")
        if not targets:
            pair_reasons.append("kampus_group_unmapped")
        if profile:
            if not EMAIL_PATTERN.fullmatch(email):
                pair_reasons.append("teacher_email_invalid")
            else:
                if len(email_profile_ids[email]) != 1:
                    pair_reasons.append("kampus_email_shared_by_profiles")
                local_matches = len(professor_index.get(email, []))
                if local_matches == 0:
                    pair_reasons.append("teacher_email_unmatched_local")
                elif local_matches > 1:
                    pair_reasons.append("teacher_email_collision_local")
        for reason in dict.fromkeys(pair_reasons):
            issues.append({
                "reason": reason,
                "teacher_profile_id": teacher_id,
                "work_email": email,
                "group_label": group_label,
                "affected_local_assignments": len(targets),
            })
        if pair_reasons:
            continue
        teacher_name = " ".join(
            part for part in (str(profile.get("name") or "").strip(), str(profile.get("lastName") or "").strip())
            if part
        )
        for grade_id, section in targets:
            rows.append({
                "teacher_profile_id": teacher_id,
                "teacher_name": teacher_name,
                "work_email": email,
                "grade": GRADE_NAMES[grade_id - 1],
                "section": section,
            })
        if group_label == COMBINED_MATERNAL_GROUP:
            combined_emitted += len(targets)

    unique_rows = {
        (row["teacher_profile_id"], row["grade"], row["section"]): row
        for row in rows
    }
    rows = [unique_rows[key] for key in sorted(unique_rows)]
    group_labels = {str(block.get("groupLabel") or "") for block in published.get("blocks", [])}
    stats = {
        "kampus_group_count": len(group_labels),
        "kampus_block_count": len(published.get("blocks", [])),
        "kampus_blocks_without_teacher": sum(
            not (block.get("teachers") or []) for block in published.get("blocks", [])
        ),
        "teacher_profile_count": len(teacher_profiles),
        "teacher_group_pairs": len(pairs),
        "teacher_group_pairs_blocked": len({(issue["teacher_profile_id"], issue["group_label"]) for issue in issues}),
        "blocked_local_assignments": sum(issue["affected_local_assignments"] for issue in issues),
        "combined_maternal_teacher_groups": sum(group == COMBINED_MATERNAL_GROUP for _, group in pairs),
        "combined_maternal_expanded_assignments": combined_emitted,
        "missing_expected_groups": len(set(KAMPUS_GROUP_MAP) - group_labels),
        "unexpected_groups": len(group_labels - set(KAMPUS_GROUP_MAP)),
    }
    return rows, issues, stats


def validation_error_categories(errors):
    categories = Counter()
    for error in errors:
        if "student requires manual review" in error:
            categories["student_review_required"] += 1
        elif "duplicate match_key" in error:
            categories["duplicate_match_key"] += 1
        elif "shared by multiple teachers" in error:
            categories["shared_teacher_email"] += 1
        elif "target section does not exist" in error or "assigned section does not exist" in error:
            categories["missing_target_section"] += 1
        else:
            categories["other_packet_validation"] += 1
    return dict(sorted(categories.items()))


def readiness_blockers(student_reconciliation, teacher_issues, global_issues):
    blockers = Counter()
    for entry in student_reconciliation:
        for reason in entry["reasons"]:
            blockers[f"student.{reason}"] += 1
    for issue in teacher_issues:
        blockers[f"teacher.{issue['reason']}"] += 1
    for issue in global_issues:
        blockers[f"source.{issue['category']}"] += int(issue.get("count", 1))
    return dict(sorted(blockers.items()))


def validate_output_destination(directory, repo_root=PROJECT_ROOT, ignore_checker=None):
    repo_root = Path(repo_root)
    directory = Path(directory)
    expected = repo_root / "dev" / "backups" / "real_2026_2027"
    if Path(os.path.abspath(directory)) != Path(os.path.abspath(expected)) or directory.is_symlink():
        raise ExtractionBlocked("unsafe_real_output_destination")
    relative = directory.relative_to(repo_root) / "students.csv"
    if ignore_checker is None:
        def ignore_checker(path):
            return subprocess.run(
                ["git", "-C", str(repo_root), "check-ignore", "-q", "--", str(path)],
                check=False,
            ).returncode == 0
    if not ignore_checker(relative):
        raise ExtractionBlocked("real_output_not_git_ignored")
    return directory


def validate_report_destination(path=REPORT_PATH, repo_root=PROJECT_ROOT):
    path = Path(path)
    expected = repo_root / "dev" / "reports" / "real_2026_2027_extraction.json"
    if Path(os.path.abspath(path)) != Path(os.path.abspath(expected)) or path.is_symlink():
        raise ExtractionBlocked("unsafe_report_destination")
    relative = path.relative_to(repo_root)
    ignored = subprocess.run(
        ["git", "-C", str(repo_root), "check-ignore", "-q", "--", str(relative)],
        check=False,
    ).returncode == 0
    if not ignored:
        raise ExtractionBlocked("report_not_git_ignored")
    return path


def secure_write_text(path, content):
    path = Path(path)
    if path.is_symlink():
        raise ExtractionBlocked("refusing_symlink_output")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(content)
    os.chmod(path, 0o600)


def write_secure_packet(students, sections, teacher_sections, manifest):
    validate_output_destination(OUTPUT_DIRECTORY)
    previous_umask = os.umask(0o077)
    try:
        OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(OUTPUT_DIRECTORY, 0o700)
        written = write_packet(OUTPUT_DIRECTORY, students, sections, teacher_sections, manifest)
        for filename in ("students.csv", "sections.csv", "teacher_sections.csv", "manifest.json"):
            os.chmod(OUTPUT_DIRECTORY / filename, 0o600)
    finally:
        os.umask(previous_umask)
    return written


def file_source(path):
    path = Path(path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path), "sha256": digest.hexdigest()}


def configured_database_url():
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    env_path = PROJECT_ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("DATABASE_URL="):
                value = stripped.split("=", 1)[1].strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                    value = value[1:-1]
                if value:
                    return value
    return "mysql+pymysql://root:0000@localhost:3306/control_asistencias?charset=utf8mb4"


def read_local_database():
    import pymysql
    from pymysql.cursors import DictCursor
    from sqlalchemy.engine import make_url

    url = make_url(configured_database_url())
    if url.drivername != "mysql+pymysql":
        raise ExtractionBlocked("unsupported_application_database_driver")
    connection = pymysql.connect(
        host=url.host or "localhost",
        port=url.port or 3306,
        user=url.username,
        password=url.password or "",
        database=url.database,
        charset="utf8mb4",
        autocommit=False,
        cursorclass=DictCursor,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET SESSION TRANSACTION READ ONLY")
            cursor.execute("START TRANSACTION READ ONLY")
            cursor.execute("SELECT @@transaction_read_only AS read_only")
            read_only = bool(cursor.fetchone()["read_only"])
            cursor.execute(
                "SELECT e.id_estudiante, e.cedula, e.nombre, e.apellido, e.activo, "
                "s.nombre_seccion, g.id_grado, g.nombre_grado "
                "FROM estudiante e "
                "JOIN seccion s ON s.id_seccion = e.id_seccion "
                "JOIN grado g ON g.id_grado = s.id_grado "
                "ORDER BY e.id_estudiante"
            )
            students = cursor.fetchall()
            cursor.execute(
                "SELECT id_usuario, email FROM usuario "
                "WHERE rol = 'profesor' AND activo = 1 ORDER BY id_usuario"
            )
            professors = cursor.fetchall()
            cursor.execute(
                "SELECT COUNT(*) AS students, "
                "COALESCE(SUM(CASE WHEN activo = 1 THEN 1 ELSE 0 END), 0) AS active_students "
                "FROM estudiante"
            )
            counts = dict(cursor.fetchone())
            cursor.execute("SELECT COUNT(*) AS attendance_rows FROM asistencia_estudiante")
            counts.update(cursor.fetchone())
    finally:
        connection.rollback()
        connection.close()
    if not read_only:
        raise ExtractionBlocked("application_database_transaction_not_read_only")
    counts = {key: int(value) for key, value in counts.items()}
    return {
        "students": students,
        "professors": professors,
        "counts": counts,
        "database_name": url.database,
        "transaction_read_only": read_only,
    }


def load_odoo_module():
    sys.path.insert(0, str(ODOO_SCRIPTS_DIRECTORY))
    import enrollment_section_import

    return enrollment_section_import


class ReadOnlyOdoo:
    ALLOWED_METHODS = frozenset(("fields_get", "search_read", "read"))

    def __init__(self, module):
        self.client = module.Odoo("production")
        self.methods_called = set()

    def call(self, model, method, *args, **kwargs):
        if method not in self.ALLOWED_METHODS:
            raise ExtractionBlocked("odoo_write_method_refused")
        self.methods_called.add(method)
        return self.client(model, method, *args, **kwargs)


def read_odoo_students():
    module = load_odoo_module()
    odoo = ReadOnlyOdoo(module)
    journey_fields = (
        "id", "active", "is_merged", "continuation_status", "confirmation_date", "student_ids",
    )
    student_fields = (
        "id", "name", "cedula", "active", "grade_next", "grade_is_target",
        "is_graduating", "section", "section_source", "journey_id",
    )
    journey_schema = odoo.call("enrollment.journey", "fields_get", [], attributes=["string"])
    student_schema = odoo.call("enrollment.journey.student", "fields_get", [], attributes=["string"])
    if set(journey_fields) - set(journey_schema) or set(student_fields) - set(student_schema):
        raise ExtractionBlocked("odoo_required_fields_missing")
    journeys = odoo.call(
        "enrollment.journey", "search_read", [],
        fields=list(journey_fields), context={"active_test": False},
    )
    students = odoo.call(
        "enrollment.journey.student", "search_read", [],
        fields=list(student_fields), context={"active_test": False},
    )
    journey_index = {row["id"]: row for row in journeys}
    for student in students:
        journey_reference = student.get("journey_id")
        journey = journey_index.get(journey_reference[0]) if journey_reference else None
        if not student.get("active"):
            population = "inactive_student"
        elif not journey:
            population = "journey_missing"
        elif journey.get("is_merged"):
            population = "merged_journey"
        elif not journey.get("active"):
            population = "inactive_journey"
        elif journey.get("continuation_status") != "confirmed":
            population = "unconfirmed_journey"
        elif journey["id"] in NEW_INTAKE_JOURNEY_IDS or not journey.get("confirmation_date"):
            population = "new_intake"
        else:
            population = "continuing_confirmed"
        student["_population"] = population
    return {
        "students": students,
        "journey_count": len(journeys),
        "methods_called": sorted(odoo.methods_called),
    }


def read_academic_roster():
    return load_odoo_module().read_roster()


def read_excel_students():
    import xlrd

    workbook = xlrd.open_workbook(str(EXCEL_PATH))
    sheet = workbook.sheet_by_index(0)
    header_row = None
    headers = []
    for row_index in range(min(sheet.nrows, 10)):
        candidate = [str(sheet.cell_value(row_index, column)).strip() for column in range(sheet.ncols)]
        if "Grado" in candidate and "Nombre" in candidate:
            header_row = row_index
            headers = candidate
            break
    required = ("Grado", "Sección", "Nombre", "Apellido", "Cédula de identidad")
    if header_row is None or any(header not in headers for header in required):
        raise ExtractionBlocked("excel_layout_changed")

    def cell(row_index, header):
        value = sheet.cell_value(row_index, headers.index(header))
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return str(value or "").strip()

    rows = []
    for row_index in range(header_row + 1, sheet.nrows):
        values = [cell(row_index, header) for header in required]
        if not any(values):
            continue
        grade, section, first_name, last_name, identifier = values
        rows.append({
            "cedula": identifier,
            "student_name": " ".join(part for part in (first_name, last_name) if part),
            "current_grade": grade,
            "current_section": section,
        })
    return {"students": rows, "source": file_source(EXCEL_PATH)}


def load_akdemia_parser():
    spec = importlib.util.spec_from_file_location("akdemia_offline_parser", AKDEMIA_PARSER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_akdemia_students():
    parser = load_akdemia_parser()
    rows = []
    sources = []
    metadata = {}
    for status in AKDEMIA_STATUSES:
        files = sorted(AKDEMIA_DIRECTORY.glob(f"admissions_{status}_2026_2027_*.xls"))
        if not files:
            raise ExtractionBlocked("akdemia_latest_export_missing")
        path = files[-1]
        parsed, meta = parser.parse_admissions_xls(str(path), status=status)
        for row in parsed:
            row["_status"] = status
        rows.extend(parsed)
        sources.append(file_source(path))
        metadata[status] = {
            "rows": len(parsed),
            "warnings": len(meta.get("warnings") or []),
            "layout": str(meta.get("layout") or ""),
        }
    return {"students": rows, "sources": sources, "metadata": metadata}


def read_kampus_cache():
    documents = {}
    sources = []
    for name in ("meta", "published", "teachers"):
        path = KAMPUS_DIRECTORY / f"{name}.json"
        with path.open(encoding="utf-8") as handle:
            documents[name] = json.load(handle)
        sources.append(file_source(path))
    meta = documents["meta"]
    published = documents["published"]
    teachers = documents["teachers"]
    if not isinstance(published.get("blocks"), list) or not isinstance(teachers, list):
        raise ExtractionBlocked("kampus_cache_layout_changed")
    identity_matches = (
        meta.get("_id") == EXPECTED_KAMPUS_SCHEDULE
        and meta.get("publishedAt") == EXPECTED_KAMPUS_PUBLISHED
        and published.get("_id") == EXPECTED_KAMPUS_SCHEDULE
    )
    return {
        "meta": meta,
        "published": published,
        "teachers": teachers,
        "sources": sources,
        "identity_matches": identity_matches,
    }


def population_counts(records, active_keys, inactive_keys):
    counts = Counter()
    for record in records:
        counts["rows"] += 1
        identifier = normalize_identifier(record.get("cedula"))
        if not identifier:
            counts["missing_identifier"] += 1
        elif identifier in active_keys:
            counts["current_active"] += 1
        elif identifier in inactive_keys:
            counts["inactive_local"] += 1
        else:
            counts["unmatched_new_intake_candidates"] += 1
    return dict(sorted(counts.items()))


def source_failure(category, exception):
    return {"category": category, "exception_type": type(exception).__name__}


def build_aggregate_summary(
    packet_students,
    sections,
    teacher_sections,
    production_counts,
    populations,
    kampus_stats,
    readiness,
):
    return {
        "production_counts": production_counts,
        "packet": {
            "students": len(packet_students),
            "continuing": sum(row["status"] == "continuing" for row in packet_students),
            "graduated": sum(row["status"] == "graduated" for row in packet_students),
            "new_intake": sum(row["status"] == "new_intake" for row in packet_students),
            "review_required": sum(
                str(row["review_required"]).strip().lower() == "true" for row in packet_students
            ),
            "sections": len(sections),
            "teacher_assignments": len(teacher_sections),
            "teacher_profiles": len({row["teacher_profile_id"] for row in teacher_sections}),
        },
        "populations": populations,
        "kampus": kampus_stats,
        "readiness": readiness,
    }


def run_extraction():
    validate_output_destination(OUTPUT_DIRECTORY)
    validate_report_destination(REPORT_PATH)
    extracted_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    global_issues = []

    try:
        local = read_local_database()
    except Exception as exception:
        raise ExtractionBlocked("application_database_read_failed") from exception

    sources = {}
    loaders = {
        "odoo": ("odoo_source_unavailable", read_odoo_students),
        "excel": ("excel_source_unavailable", read_excel_students),
        "akdemia": ("akdemia_source_unavailable", read_akdemia_students),
        "roster": ("roster_source_unavailable", read_academic_roster),
        "kampus": ("kampus_source_unavailable", read_kampus_cache),
    }
    for name, (category, loader) in loaders.items():
        try:
            sources[name] = loader()
        except Exception as exception:
            sources[name] = None
            global_issues.append(source_failure(category, exception))

    local_students = local["students"]
    active_local = [row for row in local_students if row["activo"]]
    inactive_local = [row for row in local_students if not row["activo"]]
    local_index = index_rows(local_students, lambda row: normalize_identifier(row.get("cedula")))
    active_keys = {
        normalize_identifier(row.get("cedula")) for row in active_local if normalize_identifier(row.get("cedula"))
    }
    inactive_keys = {
        normalize_identifier(row.get("cedula")) for row in inactive_local if normalize_identifier(row.get("cedula"))
    }

    odoo_rows = sources["odoo"]["students"] if sources["odoo"] else []
    excel_rows = sources["excel"]["students"] if sources["excel"] else []
    akdemia_rows = sources["akdemia"]["students"] if sources["akdemia"] else []
    roster_rows = sources["roster"] if sources["roster"] is not None else None
    odoo_index = index_rows(odoo_rows, lambda row: normalize_identifier(row.get("cedula")))
    excel_index = index_rows(excel_rows, lambda row: normalize_identifier(row.get("cedula")))
    akdemia_index = index_rows(akdemia_rows, lambda row: normalize_identifier(row.get("cedula")))
    odoo_names = index_rows(odoo_rows, lambda row: normalize_name(row.get("name")))
    excel_names = index_rows(excel_rows, lambda row: normalize_name(row.get("student_name")))
    akdemia_names = index_rows(akdemia_rows, lambda row: normalize_name(row.get("nombre_completo")))

    packet_students = []
    student_reconciliation = []
    active_name_counts = Counter(
        (normalize_name(f"{row['nombre']} {row['apellido']}"), int(row["id_grado"]) + 1)
        for row in active_local if int(row["id_grado"]) != 14
    )
    for local_row in active_local:
        identifier = normalize_identifier(local_row.get("cedula"))
        identity_issue = ""
        if not identifier:
            identity_issue = "local_identifier_missing"
        elif len(local_index.get(identifier, [])) != 1:
            identity_issue = "local_identifier_collision"
        available = not identity_issue
        local_name = f"{local_row['nombre']} {local_row['apellido']}".strip()
        matches = {
            "odoo": exact_match(odoo_index, identifier, available and sources["odoo"] is not None),
            "akdemia": exact_match(akdemia_index, identifier, available and sources["akdemia"] is not None),
            "excel": exact_match(excel_index, identifier, available and sources["excel"] is not None),
        }
        if identity_issue:
            for name, source_available in (
                ("odoo", sources["odoo"] is None),
                ("akdemia", sources["akdemia"] is None),
                ("excel", sources["excel"] is None),
            ):
                if source_available:
                    matches[name] = {"state": "unavailable", "row": None}
        matches["odoo"] = add_name_only_hint(matches["odoo"], odoo_names, local_name)
        matches["akdemia"] = add_name_only_hint(matches["akdemia"], akdemia_names, local_name)
        matches["excel"] = add_name_only_hint(matches["excel"], excel_names, local_name)
        current_grade_id = int(local_row["id_grado"])
        target_grade_id = current_grade_id + 1 if current_grade_id != 14 else None
        hint = roster_section_hint(
            roster_rows,
            local_name,
            target_grade_id,
            ambiguous_name=bool(target_grade_id and active_name_counts[(normalize_name(local_name), target_grade_id)] > 1),
        )
        normalized_local = {
            "source_student_id": f"production-{local_row['id_estudiante']}",
            "student_name": local_name,
            "match_key": local_row["cedula"],
            "current_grade_id": current_grade_id,
            "current_grade_name": local_row["nombre_grado"],
            "current_section": local_row["nombre_seccion"],
        }
        packet_row, reconciliation = map_student(normalized_local, matches, hint, identity_issue)
        packet_students.append(packet_row)
        student_reconciliation.append(reconciliation)

    sections = target_sections()
    teacher_sections = []
    teacher_issues = []
    kampus_stats = {
        "schedule_id": EXPECTED_KAMPUS_SCHEDULE,
        "publishedAt": EXPECTED_KAMPUS_PUBLISHED,
        "identity_matches": False,
    }
    if sources["kampus"]:
        kampus = sources["kampus"]
        kampus_stats["identity_matches"] = kampus["identity_matches"]
        if not kampus["identity_matches"]:
            global_issues.append({"category": "kampus_identity_mismatch"})
        teacher_sections, teacher_issues, extracted_stats = extract_teacher_sections(
            kampus["published"], kampus["teachers"], local["professors"]
        )
        kampus_stats.update(extracted_stats)
        if extracted_stats["missing_expected_groups"]:
            global_issues.append({
                "category": "kampus_expected_group_missing",
                "count": extracted_stats["missing_expected_groups"],
            })

    for key, expected in EXPECTED_PRODUCTION_COUNTS.items():
        if local["counts"].get(key) != expected:
            global_issues.append({
                "category": f"production_baseline_{key}_mismatch",
                "observed": local["counts"].get(key),
                "expected": expected,
            })

    populations = {
        "local_inactive_students": len(inactive_local),
        "akdemia_by_status": {
            status: population_counts(
                [row for row in akdemia_rows if row.get("_status") == status], active_keys, inactive_keys
            )
            for status in AKDEMIA_STATUSES
        },
        "akdemia_enrolling_total": population_counts(
            [row for row in akdemia_rows if row.get("_status") in ENROLLING_STATUSES],
            active_keys,
            inactive_keys,
        ),
        "odoo_by_journey_population": dict(sorted(Counter(
            row["_population"] for row in odoo_rows
        ).items())),
        "odoo_unmatched_to_local": population_counts(odoo_rows, active_keys, inactive_keys),
        "excel": population_counts(excel_rows, active_keys, inactive_keys),
        "academic_roster_rows": len(roster_rows) if roster_rows is not None else 0,
    }

    source_metadata = {
        "application_database": {
            "type": "mysql-read-only-transaction",
            "database": local["database_name"],
            "transaction_read_only": local["transaction_read_only"],
        },
        "odoo": {
            "type": "xmlrpc-read-only",
            "environment": "production",
            "methods": sources["odoo"]["methods_called"] if sources["odoo"] else [],
        },
        "academic_roster": {
            "type": "google-sheets-read-only",
            "scope": "https://www.googleapis.com/auth/spreadsheets.readonly",
        },
        "student_excel": sources["excel"]["source"] if sources["excel"] else None,
        "akdemia_exports": sources["akdemia"]["sources"] if sources["akdemia"] else [],
        "kampus_cache": sources["kampus"]["sources"] if sources["kampus"] else [],
    }
    manifest = {
        "schema": "migration-packet-v1",
        "academic_period": ACADEMIC_PERIOD,
        "schedule_id": EXPECTED_KAMPUS_SCHEDULE,
        "publishedAt": EXPECTED_KAMPUS_PUBLISHED,
        "extractedAt": extracted_at,
        "sources": source_metadata,
        "readiness": {"structural_valid": False, "strict_ready": False},
    }
    write_secure_packet(packet_students, sections, teacher_sections, manifest)
    try:
        packet = load_packet(OUTPUT_DIRECTORY, require_ready=False)
    except PacketValidationError as exception:
        categories = validation_error_categories(exception.errors)
        raise ExtractionBlocked(f"draft_packet_structural_invalid:{json.dumps(categories, sort_keys=True)}") from exception

    try:
        validate_packet(
            packet.students,
            packet.sections,
            packet.teacher_sections,
            packet.manifest,
            require_ready=True,
        )
        strict_errors = []
    except PacketValidationError as exception:
        strict_errors = exception.errors
    strict_categories = validation_error_categories(strict_errors)
    blockers = readiness_blockers(student_reconciliation, teacher_issues, global_issues)
    strict_ready = not strict_categories and not blockers
    readiness = {
        "structural_valid": True,
        "strict_ready": strict_ready,
        "strict_validation_errors": strict_categories,
        "blockers": blockers,
    }
    manifest["readiness"] = readiness
    write_secure_packet(packet_students, sections, teacher_sections, manifest)
    load_packet(OUTPUT_DIRECTORY, require_ready=False)

    secure_reconciliation = {
        "schema": "real-rollover-reconciliation-v1",
        "extractedAt": extracted_at,
        "students": student_reconciliation,
        "teacher_issues": teacher_issues,
        "global_issues": global_issues,
    }
    secure_write_text(
        OUTPUT_DIRECTORY / "reconciliation.json",
        json.dumps(secure_reconciliation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    os.chmod(OUTPUT_DIRECTORY / "reconciliation.json", 0o600)

    aggregate = build_aggregate_summary(
        packet.students,
        packet.sections,
        packet.teacher_sections,
        local["counts"],
        populations,
        kampus_stats,
        readiness,
    )
    aggregate.update({
        "schema": "real-rollover-extraction-summary-v1",
        "extractedAt": extracted_at,
        "packet_directory": "dev/backups/real_2026_2027",
        "student_reconciliation": {
            "authority": dict(sorted(Counter(
                entry["authority"] for entry in student_reconciliation
            ).items())),
            "warnings": dict(sorted(Counter(
                warning for entry in student_reconciliation for warning in entry["warnings"]
            ).items())),
        },
        "source_metadata": source_metadata,
        "akdemia_source_metadata": sources["akdemia"]["metadata"] if sources["akdemia"] else {},
        "read_only_evidence": {
            "application_transaction_read_only": local["transaction_read_only"],
            "odoo_methods": source_metadata["odoo"]["methods"],
            "kampus_cache_only": True,
            "akdemia_offline_only": True,
        },
    })
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    secure_write_text(REPORT_PATH, json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return aggregate


def main():
    try:
        summary = run_extraction()
    except Exception as exception:
        message = str(exception) if isinstance(exception, ExtractionBlocked) else type(exception).__name__
        if not re.fullmatch(r"[a-zA-Z0-9_:,{}\[\]\" -]+", message):
            message = type(exception).__name__
        print(f"Real extraction blocked: {message}")
        return 1
    packet = summary["packet"]
    print(
        "Real draft extraction complete: "
        f"students={packet['students']} continuing={packet['continuing']} "
        f"graduated={packet['graduated']} review_required={packet['review_required']} "
        f"sections={packet['sections']} teacher_assignments={packet['teacher_assignments']} "
        f"teacher_profiles={packet['teacher_profiles']}"
    )
    print(
        "Production read-only counts: "
        + " ".join(f"{key}={value}" for key, value in sorted(summary["production_counts"].items()))
    )
    print(f"Structural valid: yes; strict ready: {'yes' if summary['readiness']['strict_ready'] else 'no'}")
    print("Blockers: " + json.dumps(summary["readiness"]["blockers"], sort_keys=True))
    print(f"Secure packet: {OUTPUT_DIRECTORY}; aggregate report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
