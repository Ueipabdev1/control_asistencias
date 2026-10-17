from copy import deepcopy
import json

import pytest

from dev.extract_real_rollover_packet import (
    COMBINED_MATERNAL_GROUP,
    GRADE_LABELS,
    GRADE_NAMES,
    OUTPUT_DIRECTORY,
    ExtractionBlocked,
    build_aggregate_summary,
    exact_match,
    extract_teacher_sections,
    map_student,
    progression,
    readiness_blockers,
    target_sections,
    validate_output_destination,
    validation_error_categories,
)


def local_student(grade=12, section="A"):
    return {
        "source_student_id": "fictional-1",
        "student_name": "Alumno Ficticio",
        "match_key": "FICTION0001",
        "current_grade_id": grade,
        "current_grade_name": GRADE_NAMES[grade - 1],
        "current_section": section,
    }


def unique_sources(local, target_section="A"):
    target_grade_id = local["current_grade_id"] + 1
    graduating = local["current_grade_id"] == 14
    odoo_row = {
        "name": local["student_name"],
        "grade_next": "" if graduating else GRADE_LABELS[target_grade_id - 1],
        "grade_is_target": False,
        "is_graduating": graduating,
        "section": "" if graduating else target_section,
        "section_source": "roster",
        "_population": "continuing_confirmed",
    }
    akdemia_row = {
        "_status": "approved",
        "grade_target": "" if graduating else GRADE_LABELS[target_grade_id - 1],
        "cedula_kind": "nacional",
    }
    excel_row = {
        "student_name": local["student_name"],
        "current_grade": GRADE_LABELS[local["current_grade_id"] - 1],
        "current_section": local["current_section"],
    }
    return {
        "odoo": {"state": "unique", "row": odoo_row},
        "akdemia": {"state": "unique", "row": akdemia_row},
        "excel": {"state": "unique", "row": excel_row},
    }


def test_normal_progression_and_section_contract():
    assert progression(12, "A") == {
        "status": "continuing",
        "target_grade_id": 13,
        "default_section": "A",
    }
    assert progression(12, "B")["default_section"] == "B"
    assert progression(13, "Única") == {
        "status": "continuing",
        "target_grade_id": 14,
        "default_section": "A",
    }
    assert progression(14, "Única") == {
        "status": "graduated",
        "target_grade_id": None,
        "default_section": "",
    }
    sections = target_sections()
    assert len(sections) == 15
    assert {(row["grade"], row["section"]) for row in sections} == {
        (grade, section)
        for grade in GRADE_NAMES
        for section in (("A", "B") if grade == "4to año secundaria" else ("A",))
    }


def test_exact_id_collision_is_reviewed_and_name_hint_does_not_map():
    local = local_student()
    sources = unique_sources(local)
    sources["odoo"] = {
        "state": "missing",
        "row": None,
        "name_only_hint": "unique",
    }
    row, reconciliation = map_student(
        local,
        sources,
        {"state": "unique", "section": "A"},
    )
    assert row["review_required"] is True
    assert row["target_grade"] == "4to año secundaria"
    assert "odoo_missing_exact_id" in reconciliation["reasons"]
    assert reconciliation["source_matches"]["odoo"]["name_only_hint"] == "unique"

    sources["odoo"] = {"state": "collision", "row": None}
    _, reconciliation = map_student(local, sources, {"state": "unique", "section": "A"})
    assert "odoo_identifier_collision" in reconciliation["reasons"]


def test_staff_override_is_preserved_without_forcing_ready():
    local = local_student(section="A")
    sources = unique_sources(local, target_section="B")
    sources["odoo"]["row"]["section_source"] = "staff"
    row, reconciliation = map_student(local, sources, {"state": "unique", "section": "B"})
    assert row["section"] == "B"
    assert row["section_source"] == "odoo_staff"
    assert "odoo_section_conflict" not in reconciliation["reasons"]

    sources["akdemia"]["row"]["grade_target"] = GRADE_LABELS[11]
    row, reconciliation = map_student(local, sources, {"state": "unique", "section": "B"})
    assert row["review_required"] is False
    assert "akdemia_target_grade_conflict" in reconciliation["warnings"]


def test_odoo_authority_downgrades_only_secondary_conflicts():
    local = local_student(section="A")
    sources = unique_sources(local)
    sources["akdemia"]["row"]["grade_target"] = GRADE_LABELS[11]
    sources["excel"] = {"state": "missing", "row": None}
    row, reconciliation = map_student(local, sources, {"state": "unique", "section": "A"})
    assert row["review_required"] is False
    assert reconciliation["authority"] == "odoo_enrollment_journey"
    assert "akdemia_target_grade_conflict" in reconciliation["warnings"]
    assert "excel_missing_exact_id" in reconciliation["warnings"]

    sources["odoo"]["row"]["_population"] = "unconfirmed_journey"
    row, reconciliation = map_student(local, sources, {"state": "unique", "section": "A"})
    assert row["review_required"] is True
    assert reconciliation["authority"] == "local_progression_with_review"
    assert "odoo_population_mismatch" in reconciliation["reasons"]
    assert "akdemia_target_grade_conflict" in reconciliation["reasons"]
    assert "excel_missing_exact_id" in reconciliation["reasons"]


def test_missing_identifier_and_source_failures_have_secure_reason_codes():
    local = local_student()
    sources = unique_sources(local)
    row, reconciliation = map_student(
        local,
        sources,
        {"state": "missing"},
        local_identity_issue="local_identifier_collision",
    )
    assert row["review_required"] is True
    assert reconciliation["reasons"] == ["local_identifier_collision"]
    assert "FICTION" not in json.dumps(reconciliation["reasons"])

    sources = {
        name: {"state": "unavailable", "row": None}
        for name in ("odoo", "akdemia", "excel")
    }
    _, reconciliation = map_student(local, sources, {"state": "unavailable"})
    assert set(reconciliation["reasons"]) == {
        "odoo_source_unavailable",
        "akdemia_source_unavailable",
        "excel_source_unavailable",
        "roster_section_hint_unavailable",
    }


def test_teacher_dedup_and_combined_maternal_expansion():
    block = {
        "groupLabel": COMBINED_MATERNAL_GROUP,
        "teachers": [{"id": "FICTION-TEACHER-1"}],
    }
    published = {"blocks": [deepcopy(block), deepcopy(block), deepcopy(block)]}
    profiles = [{
        "_id": "FICTION-TEACHER-1",
        "name": "Docente",
        "lastName": "Ficticio",
        "email": " Teacher@Example.Test ",
    }]
    rows, issues, stats = extract_teacher_sections(
        published,
        profiles,
        [{"id_usuario": 1, "email": "teacher@example.test"}],
    )
    assert issues == []
    assert len(rows) == 2
    assert {(row["grade"], row["section"]) for row in rows} == {
        ("Nivel 1 maternal", "A"),
        ("Nivel 2 maternal", "A"),
    }
    assert rows[0]["work_email"] == "teacher@example.test"
    assert stats["teacher_group_pairs"] == 1
    assert stats["combined_maternal_expanded_assignments"] == 2


def test_unmatched_and_colliding_teacher_emails_are_not_guessed():
    published = {
        "blocks": [
            {"groupLabel": "4to año · A", "teachers": [{"id": "FICTION-T1"}]},
            {"groupLabel": "4to año · B", "teachers": [{"id": "FICTION-T2"}]},
        ]
    }
    profiles = [
        {"_id": "FICTION-T1", "name": "Uno", "lastName": "Ficticio", "email": "shared@example.test"},
        {"_id": "FICTION-T2", "name": "Dos", "lastName": "Ficticio", "email": "shared@example.test"},
    ]
    local_professors = [
        {"id_usuario": 1, "email": "shared@example.test"},
        {"id_usuario": 2, "email": "SHARED@example.test"},
    ]
    rows, issues, _ = extract_teacher_sections(published, profiles, local_professors)
    assert rows == []
    reasons = {issue["reason"] for issue in issues}
    assert "kampus_email_shared_by_profiles" in reasons
    assert "teacher_email_collision_local" in reasons

    profiles[1]["email"] = "unmatched@example.test"
    local_professors = [{"id_usuario": 1, "email": "shared@example.test"}]
    rows, issues, _ = extract_teacher_sections(published, profiles, local_professors)
    assert len(rows) == 1
    assert {issue["reason"] for issue in issues} == {"teacher_email_unmatched_local"}


def test_readiness_and_aggregate_report_are_counts_only():
    local = local_student()
    student, reconciliation = map_student(local, unique_sources(local), {"state": "missing"})
    teachers = [{
        "teacher_profile_id": "FICTION-TEACHER-1",
        "teacher_name": "Docente Ficticio",
        "work_email": "teacher@example.test",
        "grade": "Nivel 1 maternal",
        "section": "A",
    }]
    blockers = readiness_blockers(
        [reconciliation],
        [{"reason": "teacher_email_unmatched_local"}],
        [{"category": "kampus_expected_group_missing", "count": 2}],
    )
    assert blockers["student.roster_section_hint_missing"] == 1
    assert blockers["teacher.teacher_email_unmatched_local"] == 1
    assert blockers["source.kampus_expected_group_missing"] == 2
    summary = build_aggregate_summary(
        [student],
        target_sections(),
        teachers,
        {"students": 1, "active_students": 1, "attendance_rows": 0},
        {"local_inactive_students": 0},
        {"kampus_group_count": 14},
        {"structural_valid": True, "strict_ready": False, "blockers": blockers},
    )
    serialized = json.dumps(summary)
    assert summary["packet"]["review_required"] == 1
    assert summary["packet"]["new_intake"] == 0
    assert "Alumno Ficticio" not in serialized
    assert "FICTION0001" not in serialized
    assert "teacher@example.test" not in serialized


def test_validation_categories_do_not_echo_row_values():
    categories = validation_error_categories([
        "students.csv:2: student requires manual review",
        "students.csv:3: duplicate match_key FICTION-SECRET",
        "teacher_sections.csv:4: work_email private@example.test is shared by multiple teachers",
    ])
    assert categories == {
        "duplicate_match_key": 1,
        "shared_teacher_email": 1,
        "student_review_required": 1,
    }
    assert "FICTION-SECRET" not in json.dumps(categories)
    assert "private@example.test" not in json.dumps(categories)


def test_real_output_destination_requires_exact_ignored_directory():
    assert validate_output_destination(OUTPUT_DIRECTORY, ignore_checker=lambda path: True) == OUTPUT_DIRECTORY
    with pytest.raises(ExtractionBlocked, match="real_output_not_git_ignored"):
        validate_output_destination(OUTPUT_DIRECTORY, ignore_checker=lambda path: False)
    synthetic = OUTPUT_DIRECTORY.parent.parent / "packets" / "synthetic_2026_2027"
    with pytest.raises(ExtractionBlocked, match="unsafe_real_output_destination"):
        validate_output_destination(synthetic, ignore_checker=lambda path: True)


def test_exact_match_requires_one_nonempty_identifier():
    index = {"123": [{"id": "fictional-a"}, {"id": "fictional-b"}]}
    assert exact_match(index, "123")["state"] == "collision"
    assert exact_match(index, "999")["state"] == "missing"
    assert exact_match(index, "")["state"] == "not_attempted"
    assert exact_match(index, "123", available=False)["state"] == "unavailable"
