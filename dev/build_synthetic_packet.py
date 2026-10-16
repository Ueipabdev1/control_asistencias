from pathlib import Path

from dev.migration_packet import load_packet, synthetic_manifest, write_packet
from dev.synthetic_data import GRADE_NAMES

OUTPUT_DIRECTORY = Path(__file__).resolve().parent / "packets" / "synthetic_2026_2027"
KAMPUS_GRADE_LABELS = [
    "1er grupo",
    "2do grupo",
    "3er grupo",
    "1er Grado",
    "2do Grado",
    "3er Grado",
    "4to Grado",
    "5to Grado",
    "6to Grado",
    "1er Año",
    "2do Año",
    "3er Año",
    "4to Año",
    "5to Año",
]
TARGET_GRADE_BY_SOURCE_SECTION = {
    1: 2,
    2: 3,
    3: 4,
    4: 5,
    5: 6,
    6: 7,
    7: 8,
    8: 9,
    9: 10,
    10: 11,
    11: 12,
    12: 13,
    13: 13,
    14: 14,
}


def synthetic_rows():
    sections = []
    for grade_id, (grade, group) in enumerate(zip(GRADE_NAMES, KAMPUS_GRADE_LABELS), start=1):
        section_codes = ("A", "B") if grade_id == 13 else ("A",)
        for section_code in section_codes:
            sections.append({
                "grade": grade,
                "section": section_code,
                "group_label": f"{group} · {section_code}",
                "active": True,
            })

    students = []
    for source_section in range(1, 16):
        for offset in range(2):
            number = (source_section - 1) * 2 + offset + 1
            row = {
                "source_student_id": f"SIM-STU-{number:04d}",
                "student_name": f"Estudiante{number:02d} Sintético",
                "match_key": f"TEST{number:04d}",
                "target_grade": "",
                "section": "",
                "status": "continuing",
                "grade_is_target": False,
                "section_source": "",
                "review_required": False,
            }
            if source_section == 15:
                row["status"] = "graduated"
            else:
                target_grade_id = TARGET_GRADE_BY_SOURCE_SECTION[source_section]
                row.update({
                    "target_grade": GRADE_NAMES[target_grade_id - 1],
                    "section": "B" if source_section == 13 else "A",
                    "section_source": "roster" if target_grade_id == 13 else "kampus",
                })
            students.append(row)

    teacher_sections = []
    for index, section in enumerate(sections, start=1):
        if index <= 8:
            teacher_id = "SIM-T001"
            teacher_name = "Profesora Synthetic"
            work_email = "teacher1@dev.test"
        else:
            teacher_id = "SIM-T002"
            teacher_name = "Profesor Synthetic"
            work_email = "teacher2@dev.test"
        teacher_sections.append({
            "teacher_profile_id": teacher_id,
            "teacher_name": teacher_name,
            "work_email": work_email,
            "grade": section["grade"],
            "section": section["section"],
        })
    return students, sections, teacher_sections


def main():
    students, sections, teacher_sections = synthetic_rows()
    write_packet(OUTPUT_DIRECTORY, students, sections, teacher_sections, synthetic_manifest())
    packet = load_packet(OUTPUT_DIRECTORY)
    continuing = sum(row["status"] == "continuing" for row in packet.students)
    graduated = sum(row["status"] == "graduated" for row in packet.students)
    print(
        f"Validated {OUTPUT_DIRECTORY}: students={len(packet.students)} "
        f"continuing={continuing} graduated={graduated} sections={len(packet.sections)} "
        f"teacher_sections={len(packet.teacher_sections)}"
    )


if __name__ == "__main__":
    main()
