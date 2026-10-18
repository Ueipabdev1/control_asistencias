from copy import deepcopy
import hashlib
import json

import pytest

from dev.build_synthetic_packet import OUTPUT_DIRECTORY, synthetic_rows
from dev.migration_packet import (
    PacketValidationError,
    load_packet,
    synthetic_manifest,
    validate_local_teacher_links,
    write_packet,
)


def write_test_packet(directory, students=None, sections=None, teacher_sections=None, manifest=None):
    default_students, default_sections, default_teachers = synthetic_rows()
    return write_packet(
        directory,
        deepcopy(students if students is not None else default_students),
        deepcopy(sections if sections is not None else default_sections),
        deepcopy(teacher_sections if teacher_sections is not None else default_teachers),
        deepcopy(manifest if manifest is not None else synthetic_manifest()),
    )


def test_synthetic_packet_structure_and_section_rules():
    packet = load_packet(OUTPUT_DIRECTORY)
    assert len(packet.students) == 30
    assert len(packet.sections) == 15
    assert len(packet.teacher_sections) == 15
    assert sum(row["status"] == "continuing" for row in packet.students) == 28
    assert sum(row["status"] == "graduated" for row in packet.students) == 2

    section_keys = {(row["grade"], row["section"]) for row in packet.sections}
    assert ("1er año secundaria", "A") in section_keys
    assert ("1er año secundaria", "B") not in section_keys
    assert ("4to año secundaria", "A") in section_keys
    assert ("4to año secundaria", "B") in section_keys
    assert all(row["target_grade"] == "" and row["section"] == "" for row in packet.students if row["status"] == "graduated")


def test_manifest_counts_and_hashes():
    packet = load_packet(OUTPUT_DIRECTORY)
    assert packet.manifest["schema"] == "migration-packet-v1"
    assert packet.manifest["academic_period"] == "2026-2027"
    assert packet.manifest["schedule_id"] == "SIM-2627-V1"
    assert packet.manifest["readiness"]["strict_ready"] is False
    assert packet.manifest["readiness"]["blockers"] == {}
    for filename, rows in (
        ("students.csv", 30),
        ("sections.csv", 15),
        ("teacher_sections.csv", 15),
    ):
        assert packet.manifest["files"][filename]["rows"] == rows
        assert len(packet.manifest["files"][filename]["sha256"]) == 64


def test_teacher_emails_match_one_local_professor():
    packet = load_packet(OUTPUT_DIRECTORY)
    validate_local_teacher_links(packet.teacher_sections)


def test_duplicate_student_id_is_rejected(tmp_path):
    students, _, _ = synthetic_rows()
    students[1]["source_student_id"] = students[0]["source_student_id"]
    write_test_packet(tmp_path, students=students)
    with pytest.raises(PacketValidationError, match="duplicate source_student_id"):
        load_packet(tmp_path)


def test_duplicate_match_key_is_rejected(tmp_path):
    students, _, _ = synthetic_rows()
    students[1]["match_key"] = students[0]["match_key"]
    write_test_packet(tmp_path, students=students)
    with pytest.raises(PacketValidationError, match="duplicate match_key"):
        load_packet(tmp_path)


def test_unknown_target_section_is_rejected(tmp_path):
    students, _, _ = synthetic_rows()
    students[0]["section"] = "Z"
    write_test_packet(tmp_path, students=students)
    with pytest.raises(PacketValidationError, match="target section does not exist"):
        load_packet(tmp_path)


def test_shared_teacher_email_is_rejected(tmp_path):
    _, _, teacher_sections = synthetic_rows()
    teacher_sections[1]["teacher_profile_id"] = "SIM-T999"
    write_test_packet(tmp_path, teacher_sections=teacher_sections)
    with pytest.raises(PacketValidationError, match="shared by multiple teachers"):
        load_packet(tmp_path)


def test_unexpected_personal_data_column_is_rejected(tmp_path):
    write_test_packet(tmp_path)
    path = tmp_path / "students.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[0] += ",rep_cedula"
    for index in range(1, len(lines)):
        lines[index] += ",unexpected"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["students.csv"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(PacketValidationError, match="columns must be exactly"):
        load_packet(tmp_path)


def test_missing_local_teacher_is_rejected():
    _, _, teacher_sections = synthetic_rows()
    teacher_sections[0]["work_email"] = "missing@dev.test"
    with pytest.raises(PacketValidationError, match="found 0"):
        validate_local_teacher_links(teacher_sections)


def test_modified_manifest_hash_is_rejected(tmp_path):
    write_test_packet(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["students.csv"]["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(PacketValidationError, match="SHA-256 does not match"):
        load_packet(tmp_path)


def test_review_required_student_is_not_migration_ready(tmp_path):
    students, _, _ = synthetic_rows()
    students[0]["review_required"] = True
    write_test_packet(tmp_path, students=students)
    with pytest.raises(PacketValidationError, match="requires manual review"):
        load_packet(tmp_path)
