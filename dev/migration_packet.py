import csv
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

STUDENT_FIELDS = (
    "source_student_id",
    "student_name",
    "match_key",
    "target_grade",
    "section",
    "status",
    "grade_is_target",
    "section_source",
    "review_required",
)
SECTION_FIELDS = ("grade", "section", "group_label", "active")
TEACHER_FIELDS = ("teacher_profile_id", "teacher_name", "work_email", "grade", "section")
ACTIVE_STATUSES = {"continuing", "new_intake"}
INACTIVE_STATUSES = {"graduated", "retired"}
STATUSES = ACTIVE_STATUSES | INACTIVE_STATUSES
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class PacketValidationError(RuntimeError):
    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


@dataclass(frozen=True)
class MigrationPacket:
    students: list
    sections: list
    teacher_sections: list
    manifest: dict


def _boolean(value):
    normalized = str(value).strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    return None


def _csv_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


def _write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field, "")) for field in fieldnames})


def _read_csv(path, expected_fields):
    errors = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        if len(fieldnames) != len(set(fieldnames)) or set(fieldnames) != set(expected_fields):
            raise PacketValidationError([f"{path.name}: columns must be exactly {', '.join(expected_fields)}"])
        rows = []
        for line_number, row in enumerate(reader, start=2):
            cleaned = {field: (row.get(field) or "").strip() for field in expected_fields}
            if any(cleaned.values()):
                cleaned["_line"] = line_number
                rows.append(cleaned)
        return rows


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_packet(directory, students, sections, teacher_sections, manifest):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    datasets = (
        ("students.csv", STUDENT_FIELDS, students),
        ("sections.csv", SECTION_FIELDS, sections),
        ("teacher_sections.csv", TEACHER_FIELDS, teacher_sections),
    )
    manifest = dict(manifest)
    manifest["files"] = {}
    for filename, fieldnames, rows in datasets:
        path = directory / filename
        _write_csv(path, fieldnames, rows)
        manifest["files"][filename] = {"rows": len(rows), "sha256": _sha256(path)}
    manifest_path = directory / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def validate_packet(students, sections, teacher_sections, manifest, require_ready=True):
    errors = []
    if manifest.get("schema") != "migration-packet-v1":
        errors.append("manifest: schema must be migration-packet-v1")
    if not manifest.get("academic_period"):
        errors.append("manifest: academic_period is required")

    section_keys = set()
    active_section_keys = set()
    for row in sections:
        location = f"sections.csv:{row.get('_line', '?')}"
        grade = row["grade"]
        section = row["section"]
        active = _boolean(row["active"])
        if not grade or not section or not row["group_label"]:
            errors.append(f"{location}: grade, section, and group_label are required")
        if active is None:
            errors.append(f"{location}: active must be true or false")
        key = (grade, section)
        if key in section_keys:
            errors.append(f"{location}: duplicate section {grade} / {section}")
        section_keys.add(key)
        if active:
            active_section_keys.add(key)

    student_ids = set()
    match_keys = set()
    for row in students:
        location = f"students.csv:{row.get('_line', '?')}"
        source_id = row["source_student_id"]
        status = row["status"]
        match_key = row["match_key"].upper()
        grade_is_target = _boolean(row["grade_is_target"])
        review_required = _boolean(row["review_required"])
        if not source_id or not row["student_name"]:
            errors.append(f"{location}: source_student_id and student_name are required")
        if source_id in student_ids:
            errors.append(f"{location}: duplicate source_student_id {source_id}")
        student_ids.add(source_id)
        if match_key and match_key in match_keys:
            errors.append(f"{location}: duplicate match_key {match_key}")
        if match_key:
            match_keys.add(match_key)
        if status not in STATUSES:
            errors.append(f"{location}: invalid status {status}")
            continue
        if grade_is_target is None or review_required is None:
            errors.append(f"{location}: grade_is_target and review_required must be true or false")
        if status in ACTIVE_STATUSES:
            if not row["target_grade"] or not row["section"]:
                errors.append(f"{location}: {status} requires target_grade and section")
            elif (row["target_grade"], row["section"]) not in active_section_keys:
                errors.append(f"{location}: target section does not exist or is inactive")
            if not row["section_source"]:
                errors.append(f"{location}: section_source is required for {status}")
            if status == "continuing" and not match_key and review_required is not True:
                errors.append(f"{location}: continuing student requires match_key or review_required=true")
        else:
            if row["target_grade"] or row["section"]:
                errors.append(f"{location}: {status} cannot have a target grade or section")
        if require_ready and review_required:
            errors.append(f"{location}: student requires manual review")

    teacher_ids = {}
    email_ids = {}
    assignments = set()
    for row in teacher_sections:
        location = f"teacher_sections.csv:{row.get('_line', '?')}"
        teacher_id = row["teacher_profile_id"]
        email = row["work_email"].lower()
        if not teacher_id or not row["teacher_name"]:
            errors.append(f"{location}: teacher_profile_id and teacher_name are required")
        if not EMAIL_PATTERN.match(email):
            errors.append(f"{location}: valid work_email is required")
        if teacher_id in teacher_ids and teacher_ids[teacher_id] != email:
            errors.append(f"{location}: teacher {teacher_id} has inconsistent work_email")
        teacher_ids[teacher_id] = email
        if email in email_ids and email_ids[email] != teacher_id:
            errors.append(f"{location}: work_email {email} is shared by multiple teachers")
        email_ids[email] = teacher_id
        key = (teacher_id, row["grade"], row["section"])
        if key in assignments:
            errors.append(f"{location}: duplicate teacher-section assignment")
        assignments.add(key)
        if (row["grade"], row["section"]) not in active_section_keys:
            errors.append(f"{location}: assigned section does not exist or is inactive")

    if errors:
        raise PacketValidationError(errors)


def validate_local_teacher_links(teacher_sections):
    from models import Usuario

    errors = []
    for email in sorted({row["work_email"].lower() for row in teacher_sections}):
        matches = Usuario.query.filter_by(email=email, rol="profesor", activo=True).count()
        if matches != 1:
            errors.append(f"work_email {email}: expected one active local professor, found {matches}")
    if errors:
        raise PacketValidationError(errors)


def load_packet(directory, require_ready=True):
    directory = Path(directory)
    manifest_path = directory / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PacketValidationError([f"manifest.json: {exc}"]) from exc

    errors = []
    datasets = {}
    for filename, fields in (
        ("students.csv", STUDENT_FIELDS),
        ("sections.csv", SECTION_FIELDS),
        ("teacher_sections.csv", TEACHER_FIELDS),
    ):
        path = directory / filename
        metadata = manifest.get("files", {}).get(filename)
        if not metadata:
            errors.append(f"manifest.json: missing file metadata for {filename}")
            continue
        try:
            if metadata.get("sha256") != _sha256(path):
                errors.append(f"{filename}: SHA-256 does not match manifest")
            datasets[filename] = _read_csv(path, fields)
            if metadata.get("rows") != len(datasets[filename]):
                errors.append(f"{filename}: row count does not match manifest")
        except OSError as exc:
            errors.append(f"{filename}: {exc}")
    if errors:
        raise PacketValidationError(errors)

    packet = MigrationPacket(
        students=datasets["students.csv"],
        sections=datasets["sections.csv"],
        teacher_sections=datasets["teacher_sections.csv"],
        manifest=manifest,
    )
    validate_packet(packet.students, packet.sections, packet.teacher_sections, packet.manifest, require_ready)
    return packet


def synthetic_manifest():
    return {
        "schema": "migration-packet-v1",
        "academic_period": "2026-2027",
        "sources": {
            "students": "synthetic roster",
            "sections": "synthetic Kampus structure",
            "teachers": "synthetic Kampus assignments",
        },
        "schedule_id": "SIM-2627-V1",
        "publishedAt": "2026-09-16T12:00:00Z",
        "extractedAt": "2026-10-16T00:00:00Z",
        "readiness": {
            "structural_valid": True,
            "strict_ready": False,
            "blockers": {},
        },
    }
