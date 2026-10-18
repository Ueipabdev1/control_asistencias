from datetime import datetime, timezone
import secrets

from dev.apply_migration_packet import packet_fingerprint, preflight_packet
from dev.migration_packet import PacketValidationError, load_packet, validate_packet, write_packet


class DraftApprovalError(RuntimeError):
    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def load_draft(directory):
    return load_packet(directory, require_ready=False)


def _require_fingerprint(packet, supplied):
    expected = packet_fingerprint(packet)
    if not supplied or not secrets.compare_digest(expected, supplied):
        raise ValueError("El borrador cambió desde su revisión; recárgalo antes de guardar")


def _write(directory, packet):
    write_packet(
        directory,
        packet.students,
        packet.sections,
        packet.teacher_sections,
        packet.manifest,
    )
    return load_draft(directory)


def _invalidate(packet):
    readiness = dict(packet.manifest.get("readiness") or {})
    readiness["structural_valid"] = True
    readiness["strict_ready"] = False
    readiness.pop("validated_by", None)
    readiness.pop("validated_at_utc", None)
    packet.manifest["readiness"] = readiness


def _validate_structure(packet):
    validate_packet(
        packet.students,
        packet.sections,
        packet.teacher_sections,
        packet.manifest,
        require_ready=False,
    )


def _save_edit(directory, packet, supplied_fingerprint):
    _require_fingerprint(packet, supplied_fingerprint)
    _validate_structure(packet)
    _invalidate(packet)
    return _write(directory, packet)


def edit_student(directory, packet, supplied_fingerprint, source_student_id, status, target_grade, section, review_required):
    _require_fingerprint(packet, supplied_fingerprint)
    if status not in {"continuing", "graduated", "retired"}:
        raise ValueError("Estado de estudiante no permitido")
    matches = [row for row in packet.students if row["source_student_id"] == source_student_id]
    if len(matches) != 1:
        raise ValueError("Estudiante del borrador no encontrado")
    row = matches[0]
    if status == "continuing":
        target_grade = target_grade.strip()
        section = section.strip()
        if not target_grade or not section:
            raise ValueError("Un estudiante promovido requiere grado y sección de destino")
        changed_destination = (row["target_grade"], row["section"]) != (target_grade, section)
        row["target_grade"] = target_grade
        row["section"] = section
        if changed_destination or not row["section_source"]:
            row["section_source"] = "manual_review"
    else:
        row["target_grade"] = ""
        row["section"] = ""
        row["section_source"] = ""
    row["status"] = status
    row["review_required"] = bool(review_required)
    return _save_edit(directory, packet, supplied_fingerprint)


def save_section(
    directory,
    packet,
    supplied_fingerprint,
    original_grade,
    original_section,
    grade,
    section,
    group_label,
    active,
):
    _require_fingerprint(packet, supplied_fingerprint)
    grade = grade.strip()
    section = section.strip()
    group_label = group_label.strip()
    if not grade or not section or not group_label:
        raise ValueError("Grado, sección y etiqueta de grupo son obligatorios")
    duplicate = [
        row for row in packet.sections
        if (row["grade"], row["section"]) == (grade, section)
        and (row["grade"], row["section"]) != (original_grade, original_section)
    ]
    if duplicate:
        raise ValueError("Ya existe esa sección en el borrador")
    if original_grade or original_section:
        matches = [
            row for row in packet.sections
            if (row["grade"], row["section"]) == (original_grade, original_section)
        ]
        if len(matches) != 1:
            raise ValueError("Sección del borrador no encontrada")
        if original_grade != grade:
            raise ValueError("El grado de una sección existente no se puede cambiar")
        row = matches[0]
        renamed = original_section != section
        row["section"] = section
        row["group_label"] = group_label
        row["active"] = bool(active)
        if renamed:
            for student in packet.students:
                if (student["target_grade"], student["section"]) == (original_grade, original_section):
                    student["section"] = section
                    student["section_source"] = "manual_review"
            for assignment in packet.teacher_sections:
                if (assignment["grade"], assignment["section"]) == (original_grade, original_section):
                    assignment["section"] = section
    else:
        packet.sections.append({
            "grade": grade,
            "section": section,
            "group_label": group_label,
            "active": bool(active),
        })
    return _save_edit(directory, packet, supplied_fingerprint)


def set_teacher_email(directory, packet, supplied_fingerprint, teacher_profile_id, work_email):
    _require_fingerprint(packet, supplied_fingerprint)
    matches = [row for row in packet.teacher_sections if row["teacher_profile_id"] == teacher_profile_id]
    if not matches:
        raise ValueError("Perfil docente del borrador no encontrado")
    for row in matches:
        row["work_email"] = work_email.strip().lower()
    return _save_edit(directory, packet, supplied_fingerprint)


def save_teacher_assignment(
    directory,
    packet,
    supplied_fingerprint,
    original_teacher_profile_id,
    original_grade,
    original_section,
    teacher_profile_id,
    grade,
    section,
):
    _require_fingerprint(packet, supplied_fingerprint)
    profiles = [row for row in packet.teacher_sections if row["teacher_profile_id"] == teacher_profile_id]
    if not profiles:
        raise ValueError("Selecciona un perfil docente existente en el borrador")
    grade = grade.strip()
    section = section.strip()
    if not grade or not section:
        raise ValueError("Grado y sección son obligatorios")
    duplicate = [
        row for row in packet.teacher_sections
        if (row["teacher_profile_id"], row["grade"], row["section"]) == (teacher_profile_id, grade, section)
        and (row["teacher_profile_id"], row["grade"], row["section"]) != (
            original_teacher_profile_id,
            original_grade,
            original_section,
        )
    ]
    if duplicate:
        raise ValueError("La asignación docente ya existe")
    if original_teacher_profile_id or original_grade or original_section:
        matches = [
            row for row in packet.teacher_sections
            if (row["teacher_profile_id"], row["grade"], row["section"]) == (
                original_teacher_profile_id,
                original_grade,
                original_section,
            )
        ]
        if len(matches) != 1:
            raise ValueError("Asignación docente del borrador no encontrada")
        if original_teacher_profile_id != teacher_profile_id:
            raise ValueError("El perfil de una asignación existente no se puede cambiar")
        row = matches[0]
        row["grade"] = grade
        row["section"] = section
    else:
        profile = profiles[0]
        packet.teacher_sections.append({
            "teacher_profile_id": teacher_profile_id,
            "teacher_name": profile["teacher_name"],
            "work_email": profile["work_email"],
            "grade": grade,
            "section": section,
        })
    return _save_edit(directory, packet, supplied_fingerprint)


def delete_teacher_assignment(directory, packet, supplied_fingerprint, teacher_profile_id, grade, section):
    _require_fingerprint(packet, supplied_fingerprint)
    matches = [
        row for row in packet.teacher_sections
        if (row["teacher_profile_id"], row["grade"], row["section"]) == (teacher_profile_id, grade, section)
    ]
    if len(matches) != 1:
        raise ValueError("Asignación docente del borrador no encontrada")
    packet.teacher_sections.remove(matches[0])
    return _save_edit(directory, packet, supplied_fingerprint)


def validate_draft(directory, packet, supplied_fingerprint, validator):
    _require_fingerprint(packet, supplied_fingerprint)
    errors = []
    try:
        validate_packet(
            packet.students,
            packet.sections,
            packet.teacher_sections,
            packet.manifest,
            require_ready=True,
        )
    except PacketValidationError as exc:
        errors.extend(exc.errors)
    try:
        preflight_packet(packet)
    except Exception as exc:
        errors.append(str(exc))
    readiness = dict(packet.manifest.get("readiness") or {})
    blockers = readiness.get("blockers") or {}
    if not isinstance(blockers, dict):
        raise ValueError("Los bloqueos de reconciliación tienen un formato inválido")
    if blockers:
        errors.append("La reconciliación de fuentes todavía tiene bloqueos pendientes")
    readiness["structural_valid"] = True
    readiness["strict_ready"] = False
    readiness.pop("validated_by", None)
    readiness.pop("validated_at_utc", None)
    packet.manifest["readiness"] = readiness
    if errors:
        packet = _write(directory, packet)
        raise DraftApprovalError(errors)
    readiness["strict_ready"] = True
    readiness["validated_by"] = validator
    readiness["validated_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    packet.manifest["readiness"] = readiness
    return _write(directory, packet)


def require_activation_ready(packet):
    readiness = packet.manifest.get("readiness") or {}
    blockers = readiness.get("blockers") or {}
    if not isinstance(blockers, dict):
        raise RuntimeError("Los bloqueos de reconciliación tienen un formato inválido")
    if blockers:
        raise RuntimeError("La reconciliación de fuentes todavía tiene bloqueos pendientes")
    if readiness.get("strict_ready") is not True:
        raise RuntimeError("El borrador debe validarse antes de activar el período")
    if not readiness.get("validated_by") or not readiness.get("validated_at_utc"):
        raise RuntimeError("La validación del borrador no tiene responsable y fecha registrados")
