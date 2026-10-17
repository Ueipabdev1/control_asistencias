import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal

import pymysql
from pymysql.cursors import DictCursor
from sqlalchemy.engine import make_url

SOURCE_YEAR = "2025-2026"
TARGET_YEAR = "2026-2027"
SOURCE_START = date(2025, 9, 1)
SOURCE_END = date(2026, 8, 31)
TARGET_START = date(2026, 9, 1)
TARGET_END = date(2027, 8, 31)
REHEARSAL_DATABASES = {"control_asistencias_dev", "control_asistencias_test"}
LOCAL_HOSTS = {"db", "localhost", "127.0.0.1", "::1"}
PRODUCTION_AUTHORIZATION_VARIABLE = "WINDOW_A_PRODUCTION_AUTHORIZATION"
REHEARSAL_AUTHORIZATION_VARIABLE = "WINDOW_A_REHEARSAL_AUTHORIZATION"
PRODUCTION_AUTHORIZATION_VALUE = "APPLY_WINDOW_A_PRODUCTION"

BASE_TABLES = {
    "estudiante": "id_estudiante",
    "seccion": "id_seccion",
    "asistencia_estudiante": "id_asistencia_estudiante",
    "observacion_seccion": "id_observacion",
    "profesor_seccion": "id_profesor_seccion",
    "grado": "id_grado",
}
LEGACY_TABLES = ("asistencia", "asistencia_legacy", "matricula", "secciones", "profesor_secciones")
ALL_TABLES = frozenset((*BASE_TABLES, *LEGACY_TABLES, "anio_escolar", "inscripcion"))
REQUIRED_BASE_COLUMNS = {
    "estudiante": {"id_estudiante", "id_seccion", "activo"},
    "seccion": {"id_seccion", "id_grado", "nombre_seccion"},
    "asistencia_estudiante": {"id_asistencia_estudiante", "id_estudiante", "fecha"},
    "observacion_seccion": {"id_observacion"},
    "profesor_seccion": {"id_profesor_seccion"},
    "grado": {"id_grado"},
}

PRE_BACKFILL_DDL = (
    "create_anio_escolar",
    "add_seccion_year",
    "add_asistencia_enrollment",
    "create_inscripcion",
    "create_asistencia_enrollment_index",
)
POST_BACKFILL_DDL = (
    "set_seccion_year_not_null",
    "set_asistencia_enrollment_not_null",
    "add_seccion_year_fk",
    "add_seccion_year_unique",
    "add_asistencia_enrollment_fk",
)
DDL_OPERATIONS = frozenset((*PRE_BACKFILL_DDL, *POST_BACKFILL_DDL, "drop_legacy_seccion_unique"))

OPERATIONS = {
    "create_anio_escolar": """
        CREATE TABLE `anio_escolar` (
            `id_anio_escolar` INT(11) NOT NULL AUTO_INCREMENT,
            `nombre` VARCHAR(9) NOT NULL,
            `codigo` VARCHAR(4) NOT NULL,
            `fecha_inicio` DATE NOT NULL,
            `fecha_fin` DATE NOT NULL,
            `es_actual` BOOLEAN NOT NULL DEFAULT FALSE,
            `fecha_creacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (`id_anio_escolar`),
            UNIQUE KEY `unique_anio_escolar_nombre` (`nombre`),
            UNIQUE KEY `unique_anio_escolar_codigo` (`codigo`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    "add_seccion_year": "ALTER TABLE `seccion` ADD COLUMN `id_anio_escolar` INT(11) NULL",
    "add_asistencia_enrollment": "ALTER TABLE `asistencia_estudiante` ADD COLUMN `id_inscripcion` INT(11) NULL",
    "create_inscripcion": """
        CREATE TABLE `inscripcion` (
            `id_inscripcion` INT(11) NOT NULL AUTO_INCREMENT,
            `id_estudiante` INT(11) NOT NULL,
            `id_seccion` INT(11) NOT NULL,
            `id_anio_escolar` INT(11) NOT NULL,
            `estado` ENUM('activo', 'promovido', 'graduado', 'retirado', 'inactivo') NOT NULL DEFAULT 'activo',
            `origen` VARCHAR(50) DEFAULT NULL,
            `fecha_registro` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            `fecha_actualizacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (`id_inscripcion`),
            UNIQUE KEY `unique_inscripcion_estudiante_anio` (`id_estudiante`, `id_anio_escolar`),
            UNIQUE KEY `unique_inscripcion_estudiante` (`id_estudiante`, `id_inscripcion`),
            KEY `idx_inscripcion_anio_seccion_estado` (`id_anio_escolar`, `id_seccion`, `estado`),
            KEY `idx_inscripcion_seccion` (`id_seccion`),
            CONSTRAINT `fk_inscripcion_estudiante` FOREIGN KEY (`id_estudiante`)
                REFERENCES `estudiante` (`id_estudiante`) ON DELETE RESTRICT,
            CONSTRAINT `fk_inscripcion_seccion` FOREIGN KEY (`id_seccion`)
                REFERENCES `seccion` (`id_seccion`) ON DELETE RESTRICT,
            CONSTRAINT `fk_inscripcion_anio` FOREIGN KEY (`id_anio_escolar`)
                REFERENCES `anio_escolar` (`id_anio_escolar`) ON DELETE RESTRICT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    "create_asistencia_enrollment_index":
        "CREATE INDEX `idx_asistencia_inscripcion` ON `asistencia_estudiante` (`id_inscripcion`)",
    "insert_years": """
        INSERT INTO `anio_escolar` (`nombre`, `codigo`, `fecha_inicio`, `fecha_fin`, `es_actual`) VALUES
            ('2025-2026', '2526', '2025-09-01', '2026-08-31', TRUE),
            ('2026-2027', '2627', '2026-09-01', '2027-08-31', FALSE)
    """,
    "backfill_sections": "UPDATE `seccion` SET `id_anio_escolar` = %(source_year_id)s",
    "backfill_enrollments": """
        INSERT INTO `inscripcion`
            (`id_estudiante`, `id_seccion`, `id_anio_escolar`, `estado`, `origen`)
        SELECT `id_estudiante`, `id_seccion`, %(source_year_id)s,
            CASE WHEN `activo` = 1 THEN 'activo' ELSE 'retirado' END, 'legacy'
        FROM `estudiante`
    """,
    "backfill_attendance": """
        UPDATE `asistencia_estudiante` AS a
        JOIN `inscripcion` AS i
            ON i.`id_estudiante` = a.`id_estudiante`
            AND i.`id_anio_escolar` = %(source_year_id)s
        SET a.`id_inscripcion` = i.`id_inscripcion`
        WHERE a.`id_inscripcion` IS NULL
    """,
    "set_seccion_year_not_null": "ALTER TABLE `seccion` MODIFY `id_anio_escolar` INT(11) NOT NULL",
    "set_asistencia_enrollment_not_null":
        "ALTER TABLE `asistencia_estudiante` MODIFY `id_inscripcion` INT(11) NOT NULL",
    "add_seccion_year_fk": """
        ALTER TABLE `seccion`
        ADD CONSTRAINT `fk_seccion_anio` FOREIGN KEY (`id_anio_escolar`)
        REFERENCES `anio_escolar` (`id_anio_escolar`) ON DELETE RESTRICT
    """,
    "drop_legacy_seccion_unique": "ALTER TABLE `seccion` DROP INDEX `unique_seccion_grado`",
    "add_seccion_year_unique": """
        ALTER TABLE `seccion`
        ADD CONSTRAINT `unique_seccion_anio_grado_nombre`
        UNIQUE (`id_anio_escolar`, `id_grado`, `nombre_seccion`)
    """,
    "add_asistencia_enrollment_fk": """
        ALTER TABLE `asistencia_estudiante`
        ADD CONSTRAINT `fk_asistencia_inscripcion_estudiante`
        FOREIGN KEY (`id_estudiante`, `id_inscripcion`)
        REFERENCES `inscripcion` (`id_estudiante`, `id_inscripcion`) ON DELETE RESTRICT
    """,
}


class WindowAError(RuntimeError):
    pass


class AuthorizationError(WindowAError):
    pass


class StateError(WindowAError):
    pass


class VerificationError(WindowAError):
    pass


class DatabaseOperationError(WindowAError):
    pass


@dataclass(frozen=True)
class TableDefinition:
    name: str
    table_type: str
    engine: str | None


@dataclass(frozen=True)
class ColumnDefinition:
    table: str
    name: str
    data_type: str
    column_type: str
    nullable: bool
    extra: str = ""
    character_length: int | None = None


@dataclass(frozen=True)
class IndexDefinition:
    table: str
    name: str
    unique: bool
    columns: tuple


@dataclass(frozen=True)
class ConstraintDefinition:
    table: str
    name: str
    kind: str


@dataclass(frozen=True)
class ForeignKeyDefinition:
    table: str
    name: str
    columns: tuple
    referenced_table: str
    referenced_columns: tuple
    update_rule: str
    delete_rule: str


@dataclass(frozen=True)
class Schema:
    tables: tuple
    columns: tuple
    indexes: tuple
    constraints: tuple
    foreign_keys: tuple

    def table(self, name):
        return _find(self.tables, lambda row: row.name == name)

    def column(self, table, name):
        return _find(self.columns, lambda row: row.table == table and row.name == name)

    def table_columns(self, table):
        return {row.name for row in self.columns if row.table == table}

    def index(self, table, name):
        return _find(self.indexes, lambda row: row.table == table and row.name == name)

    def constraint(self, table, name):
        return _find(self.constraints, lambda row: row.table == table and row.name == name)

    def foreign_key(self, table, name):
        return _find(self.foreign_keys, lambda row: row.table == table and row.name == name)


@dataclass(frozen=True)
class TableSnapshot:
    rows: tuple
    count: int
    digest: str


@dataclass(frozen=True)
class ImmutableSnapshot:
    students: TableSnapshot
    sections: TableSnapshot
    attendance: TableSnapshot
    observations: TableSnapshot
    teacher_assignments: TableSnapshot
    grades: TableSnapshot
    legacy_counts: tuple


@dataclass(frozen=True)
class RowData:
    students: tuple
    sections: tuple
    attendance: tuple
    observations: tuple
    teacher_assignments: tuple
    grades: tuple
    years: tuple
    enrollments: tuple
    duplicate_section_groups: int
    snapshot: ImmutableSnapshot


@dataclass(frozen=True)
class Inspection:
    status: str
    data: RowData
    counts: dict


@dataclass(frozen=True)
class RunResult:
    status: str
    counts: dict


def _find(rows, predicate):
    for row in rows:
        if predicate(row):
            return row
    return None


def _require(condition, message, exception=WindowAError):
    if not condition:
        raise exception(message)


def _canonical_value(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, datetime):
        return {"datetime": value.isoformat(timespec="microseconds")}
    if isinstance(value, date):
        return {"date": value.isoformat()}
    if isinstance(value, Decimal):
        return {"decimal": str(value)}
    if isinstance(value, bytes):
        return {"bytes": value.hex()}
    raise VerificationError("Unsupported database value type in immutable snapshot")


def _snapshot_table(rows, primary_key, exclude=()):
    for row in rows:
        _require(primary_key in row, f"Snapshot primary key is missing from {primary_key}", VerificationError)
        _require(row[primary_key] is not None, f"Snapshot primary key {primary_key} is null", VerificationError)
    ordered = sorted(rows, key=lambda row: row[primary_key])
    frozen_rows = []
    previous_key = object()
    for row in ordered:
        current_key = row[primary_key]
        _require(current_key != previous_key, "Duplicate primary key in immutable snapshot", VerificationError)
        previous_key = current_key
        frozen_rows.append(tuple(sorted(
            (key, _canonical_value(value))
            for key, value in row.items()
            if key not in exclude
        )))
    frozen = tuple(frozen_rows)
    payload = json.dumps(frozen, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return TableSnapshot(frozen, len(frozen), hashlib.sha256(payload.encode("utf-8")).hexdigest())


def _read_data(database, schema):
    students = tuple(database.table_rows("estudiante"))
    sections = tuple(database.table_rows("seccion"))
    attendance = tuple(database.table_rows("asistencia_estudiante"))
    observations = tuple(database.table_rows("observacion_seccion"))
    teacher_assignments = tuple(database.table_rows("profesor_seccion"))
    grades = tuple(database.table_rows("grado"))
    years = tuple(database.table_rows("anio_escolar")) if schema.table("anio_escolar") else ()
    enrollments = tuple(database.table_rows("inscripcion")) if schema.table("inscripcion") else ()
    legacy_counts = tuple(
        (table, database.table_count(table))
        for table in LEGACY_TABLES
        if schema.table(table) and schema.table(table).table_type.upper() == "BASE TABLE"
    )
    snapshot = ImmutableSnapshot(
        students=_snapshot_table(students, "id_estudiante"),
        sections=_snapshot_table(sections, "id_seccion", exclude=("id_anio_escolar",)),
        attendance=_snapshot_table(attendance, "id_asistencia_estudiante", exclude=("id_inscripcion",)),
        observations=_snapshot_table(observations, "id_observacion"),
        teacher_assignments=_snapshot_table(teacher_assignments, "id_profesor_seccion"),
        grades=_snapshot_table(grades, "id_grado"),
        legacy_counts=legacy_counts,
    )
    return RowData(
        students=students,
        sections=sections,
        attendance=attendance,
        observations=observations,
        teacher_assignments=teacher_assignments,
        grades=grades,
        years=years,
        enrollments=enrollments,
        duplicate_section_groups=database.duplicate_section_group_count(),
        snapshot=snapshot,
    )


def _compare_immutable(before, after):
    for name in (
        "students",
        "sections",
        "attendance",
        "observations",
        "teacher_assignments",
        "grades",
        "legacy_counts",
    ):
        before_value = getattr(before, name)
        after_value = getattr(after, name)
        _require(before_value == after_value, f"Immutable {name} changed during Window A", VerificationError)
    for name in ("students", "sections", "attendance", "observations", "teacher_assignments", "grades"):
        _require(
            getattr(before, name).digest == getattr(after, name).digest,
            f"Immutable {name} digest changed during Window A",
            VerificationError,
        )


def _require_base_table(schema, table):
    definition = schema.table(table)
    _require(definition is not None, f"Required base table {table} is absent", StateError)
    _require(definition.table_type.upper() == "BASE TABLE", f"{table} must be a base table", StateError)
    _require((definition.engine or "").lower() == "innodb", f"{table} must use InnoDB", StateError)


def _require_index(schema, table, name, columns, unique):
    index = schema.index(table, name)
    _require(index is not None, f"Required index {table}.{name} is absent", VerificationError)
    _require(index.columns == tuple(columns), f"Index {table}.{name} has the wrong columns", VerificationError)
    _require(index.unique == unique, f"Index {table}.{name} has the wrong uniqueness", VerificationError)
    if unique:
        constraint = schema.constraint(table, name)
        _require(constraint is not None, f"Unique constraint {table}.{name} is absent", VerificationError)
        _require(
            constraint.kind.upper() == ("PRIMARY KEY" if name == "PRIMARY" else "UNIQUE"),
            f"Constraint {table}.{name} has the wrong type",
            VerificationError,
        )


def _require_column(schema, table, name, data_type, nullable, length=None, extra=None, column_type=None):
    column = schema.column(table, name)
    _require(column is not None, f"Required column {table}.{name} is absent", VerificationError)
    _require(column.data_type.lower() == data_type, f"Column {table}.{name} has the wrong type", VerificationError)
    _require(column.nullable == nullable, f"Column {table}.{name} has the wrong nullability", VerificationError)
    if length is not None:
        _require(column.character_length == length, f"Column {table}.{name} has the wrong length", VerificationError)
    if extra is not None:
        _require(extra in column.extra.lower(), f"Column {table}.{name} has the wrong extra definition", VerificationError)
    if column_type is not None:
        normalized = column.column_type.lower().replace(" ", "")
        _require(normalized == column_type.lower().replace(" ", ""), f"Column {table}.{name} has the wrong definition", VerificationError)


def _require_foreign_key(schema, table, name, columns, referenced_table, referenced_columns):
    foreign_key = schema.foreign_key(table, name)
    _require(foreign_key is not None, f"Required foreign key {table}.{name} is absent", VerificationError)
    _require(foreign_key.columns == tuple(columns), f"Foreign key {table}.{name} has the wrong local columns", VerificationError)
    _require(
        foreign_key.referenced_table == referenced_table,
        f"Foreign key {table}.{name} references the wrong table",
        VerificationError,
    )
    _require(
        foreign_key.referenced_columns == tuple(referenced_columns),
        f"Foreign key {table}.{name} has the wrong referenced columns",
        VerificationError,
    )
    _require(foreign_key.delete_rule.upper() == "RESTRICT", f"Foreign key {table}.{name} must use ON DELETE RESTRICT", VerificationError)
    _require(foreign_key.update_rule.upper() == "RESTRICT", f"Foreign key {table}.{name} must use ON UPDATE RESTRICT", VerificationError)
    _require(
        any(
            index.table == table and index.columns[:len(columns)] == tuple(columns)
            for index in schema.indexes
        ),
        f"Foreign key {table}.{name} lacks a supporting local index",
        VerificationError,
    )
    _require(
        any(
            index.table == referenced_table and index.unique and index.columns == tuple(referenced_columns)
            for index in schema.indexes
        ),
        f"Foreign key {table}.{name} lacks a unique referenced index",
        VerificationError,
    )


def _validate_reserved_foreign_key_names(schema):
    expected_tables = {
        "fk_seccion_anio": "seccion",
        "fk_asistencia_inscripcion_estudiante": "asistencia_estudiante",
        "fk_inscripcion_estudiante": "inscripcion",
        "fk_inscripcion_seccion": "inscripcion",
        "fk_inscripcion_anio": "inscripcion",
    }
    for constraint in schema.constraints:
        if constraint.name in expected_tables and constraint.kind.upper() == "FOREIGN KEY":
            _require(
                constraint.table == expected_tables[constraint.name],
                f"Reserved foreign key {constraint.name} is on an unexpected table",
                StateError,
            )


def _validate_base_schema(schema):
    for table, primary_key in BASE_TABLES.items():
        _require_base_table(schema, table)
        _require(
            REQUIRED_BASE_COLUMNS[table].issubset(schema.table_columns(table)),
            f"Required base columns are absent from {table}",
            StateError,
        )
        primary = schema.index(table, "PRIMARY")
        _require(primary is not None and primary.unique and primary.columns == (primary_key,), f"{table} has an invalid primary key", StateError)
    _validate_reserved_foreign_key_names(schema)


def _migration_markers(schema):
    return (
        schema.table("anio_escolar") is not None,
        schema.table("inscripcion") is not None,
        schema.column("seccion", "id_anio_escolar") is not None,
        schema.column("asistencia_estudiante", "id_inscripcion") is not None,
        schema.foreign_key("seccion", "fk_seccion_anio") is not None
        or schema.constraint("seccion", "fk_seccion_anio") is not None,
        schema.index("seccion", "unique_seccion_anio_grado_nombre") is not None
        or schema.constraint("seccion", "unique_seccion_anio_grado_nombre") is not None,
        schema.foreign_key("asistencia_estudiante", "fk_asistencia_inscripcion_estudiante") is not None
        or schema.constraint("asistencia_estudiante", "fk_asistencia_inscripcion_estudiante") is not None,
        schema.index("asistencia_estudiante", "idx_asistencia_inscripcion") is not None,
    )


def _classify_state(schema):
    _validate_base_schema(schema)
    markers = _migration_markers(schema)
    if not any(markers):
        return "legacy"
    if all(markers):
        return "migrated"
    raise StateError("Partial or unexpected Window A objects detected; refusing to continue")


def _validate_legacy_schema(schema):
    legacy_name = "unique_seccion_grado"
    legacy_index = schema.index("seccion", legacy_name)
    legacy_constraint = schema.constraint("seccion", legacy_name)
    if legacy_index is not None or legacy_constraint is not None:
        _require_index(schema, "seccion", legacy_name, ("id_grado", "nombre_seccion"), True)
    for index in schema.indexes:
        if index.table == "seccion" and index.unique and index.columns == ("id_grado", "nombre_seccion"):
            _require(index.name == legacy_name, "Unexpected legacy section uniqueness object", StateError)


def _validate_final_schema(schema):
    for table in ("anio_escolar", "inscripcion", "seccion", "asistencia_estudiante"):
        _require_base_table(schema, table)
    _require(
        schema.table_columns("anio_escolar") == {
            "id_anio_escolar", "nombre", "codigo", "fecha_inicio", "fecha_fin", "es_actual", "fecha_creacion",
        },
        "anio_escolar has missing or unexpected columns",
        VerificationError,
    )
    _require(
        schema.table_columns("inscripcion") == {
            "id_inscripcion", "id_estudiante", "id_seccion", "id_anio_escolar", "estado", "origen",
            "fecha_registro", "fecha_actualizacion",
        },
        "inscripcion has missing or unexpected columns",
        VerificationError,
    )
    for name, data_type, nullable, length, extra in (
        ("id_anio_escolar", "int", False, None, "auto_increment"),
        ("nombre", "varchar", False, 9, None),
        ("codigo", "varchar", False, 4, None),
        ("fecha_inicio", "date", False, None, None),
        ("fecha_fin", "date", False, None, None),
        ("es_actual", "tinyint", False, None, None),
    ):
        _require_column(schema, "anio_escolar", name, data_type, nullable, length, extra)
    for name, data_type, nullable, length, extra in (
        ("id_inscripcion", "int", False, None, "auto_increment"),
        ("id_estudiante", "int", False, None, None),
        ("id_seccion", "int", False, None, None),
        ("id_anio_escolar", "int", False, None, None),
        ("estado", "enum", False, None, None),
        ("origen", "varchar", True, 50, None),
    ):
        _require_column(schema, "inscripcion", name, data_type, nullable, length, extra)
    _require_column(
        schema,
        "inscripcion",
        "estado",
        "enum",
        False,
        column_type="enum('activo','promovido','graduado','retirado','inactivo')",
    )
    _require_column(schema, "seccion", "id_anio_escolar", "int", False)
    _require_column(schema, "asistencia_estudiante", "id_inscripcion", "int", False)

    _require_index(schema, "anio_escolar", "PRIMARY", ("id_anio_escolar",), True)
    _require_index(schema, "anio_escolar", "unique_anio_escolar_nombre", ("nombre",), True)
    _require_index(schema, "anio_escolar", "unique_anio_escolar_codigo", ("codigo",), True)
    _require_index(schema, "inscripcion", "PRIMARY", ("id_inscripcion",), True)
    _require_index(schema, "inscripcion", "unique_inscripcion_estudiante_anio", ("id_estudiante", "id_anio_escolar"), True)
    _require_index(schema, "inscripcion", "unique_inscripcion_estudiante", ("id_estudiante", "id_inscripcion"), True)
    _require_index(schema, "inscripcion", "idx_inscripcion_anio_seccion_estado", ("id_anio_escolar", "id_seccion", "estado"), False)
    _require_index(schema, "inscripcion", "idx_inscripcion_seccion", ("id_seccion",), False)
    _require_index(schema, "seccion", "unique_seccion_anio_grado_nombre", ("id_anio_escolar", "id_grado", "nombre_seccion"), True)
    _require_index(schema, "asistencia_estudiante", "idx_asistencia_inscripcion", ("id_inscripcion",), False)

    for foreign_key in (
        ("inscripcion", "fk_inscripcion_estudiante", ("id_estudiante",), "estudiante", ("id_estudiante",)),
        ("inscripcion", "fk_inscripcion_seccion", ("id_seccion",), "seccion", ("id_seccion",)),
        ("inscripcion", "fk_inscripcion_anio", ("id_anio_escolar",), "anio_escolar", ("id_anio_escolar",)),
        ("seccion", "fk_seccion_anio", ("id_anio_escolar",), "anio_escolar", ("id_anio_escolar",)),
        (
            "asistencia_estudiante",
            "fk_asistencia_inscripcion_estudiante",
            ("id_estudiante", "id_inscripcion"),
            "inscripcion",
            ("id_estudiante", "id_inscripcion"),
        ),
    ):
        _require_foreign_key(schema, *foreign_key)

    allowed_window_fks = {
        (row[0], row[1]) for row in (
            ("inscripcion", "fk_inscripcion_estudiante"),
            ("inscripcion", "fk_inscripcion_seccion"),
            ("inscripcion", "fk_inscripcion_anio"),
            ("seccion", "fk_seccion_anio"),
            ("asistencia_estudiante", "fk_asistencia_inscripcion_estudiante"),
        )
    }
    for foreign_key in schema.foreign_keys:
        is_window_object = (
            foreign_key.table == "inscripcion"
            or foreign_key.referenced_table in {"anio_escolar", "inscripcion"}
            or (foreign_key.table == "seccion" and "id_anio_escolar" in foreign_key.columns)
            or (foreign_key.table == "asistencia_estudiante" and "id_inscripcion" in foreign_key.columns)
        )
        if is_window_object:
            _require(
                (foreign_key.table, foreign_key.name) in allowed_window_fks,
                f"Unexpected Window A foreign key {foreign_key.name}",
                VerificationError,
            )
    for constraint in schema.constraints:
        if constraint.table == "anio_escolar" and constraint.kind.upper() == "UNIQUE":
            _require(constraint.name in {"unique_anio_escolar_nombre", "unique_anio_escolar_codigo"}, "Unexpected academic-year unique constraint", VerificationError)
        if constraint.table == "inscripcion" and constraint.kind.upper() == "UNIQUE":
            _require(constraint.name in {"unique_inscripcion_estudiante_anio", "unique_inscripcion_estudiante"}, "Unexpected enrollment unique constraint", VerificationError)
    _require(schema.index("seccion", "unique_seccion_grado") is None, "Legacy section uniqueness remains", VerificationError)
    _require(schema.constraint("seccion", "unique_seccion_grado") is None, "Legacy section uniqueness constraint remains", VerificationError)
    for index in schema.indexes:
        _require(
            not (index.table == "seccion" and index.unique and index.columns == ("id_grado", "nombre_seccion")),
            "A legacy section uniqueness definition remains",
            VerificationError,
        )


def _rows_by_id(rows, key, label):
    result = {}
    for row in rows:
        _require(key in row and row[key] is not None, f"Null or missing {label} identifier", StateError)
        _require(row[key] not in result, f"Duplicate {label} identifiers", StateError)
        result[row[key]] = row
    return result


def _validate_common_data(data):
    students = _rows_by_id(data.students, "id_estudiante", "student")
    sections = _rows_by_id(data.sections, "id_seccion", "section")
    grades = _rows_by_id(data.grades, "id_grado", "grade")
    _rows_by_id(data.attendance, "id_asistencia_estudiante", "attendance")
    _require(data.duplicate_section_groups == 0, "Duplicate current (id_grado, nombre_seccion) values detected", StateError)
    for section in sections.values():
        _require(section.get("id_grado") in grades, "Orphaned or null section-grade reference detected", StateError)
        _require(section.get("nombre_seccion") is not None, "Null section name detected", StateError)
    for student in students.values():
        _require(student.get("id_seccion") in sections, "Orphaned or null student-section reference detected", StateError)
        _require(student.get("activo") in (0, 1), "Null or invalid student active flag detected", StateError)
    for attendance in data.attendance:
        _require(attendance.get("id_estudiante") in students, "Orphaned or null attendance-student reference detected", StateError)
        attendance_date = attendance.get("fecha")
        _require(type(attendance_date) is date, "Null or invalid attendance date detected", StateError)
        _require(SOURCE_START <= attendance_date <= SOURCE_END, "Attendance outside 2025-2026 detected", StateError)


def _validate_year_rows(rows):
    _require(len(rows) == 2, "Academic-year table must contain exactly the two Window A rows", VerificationError)
    years = _rows_by_id(rows, "id_anio_escolar", "academic-year")
    by_name = {row.get("nombre"): row for row in rows}
    _require(set(by_name) == {SOURCE_YEAR, TARGET_YEAR}, "Conflicting or unexpected academic-year rows detected", VerificationError)
    source = by_name[SOURCE_YEAR]
    target = by_name[TARGET_YEAR]
    expected = {
        SOURCE_YEAR: ("2526", SOURCE_START, SOURCE_END, 1),
        TARGET_YEAR: ("2627", TARGET_START, TARGET_END, 0),
    }
    for name, row in ((SOURCE_YEAR, source), (TARGET_YEAR, target)):
        code, starts, ends, current = expected[name]
        _require(row.get("codigo") == code, f"Academic year {name} has a conflicting code", VerificationError)
        _require(row.get("fecha_inicio") == starts, f"Academic year {name} has a conflicting start date", VerificationError)
        _require(row.get("fecha_fin") == ends, f"Academic year {name} has a conflicting end date", VerificationError)
        _require(row.get("es_actual") == current, f"Academic year {name} has a conflicting current flag", VerificationError)
    _require(sum(row.get("es_actual") == 1 for row in rows) == 1, "Exactly one current academic year is required", VerificationError)
    _require(source["id_anio_escolar"] != target["id_anio_escolar"], "Academic-year identifiers conflict", VerificationError)
    return source, target


def _validate_final_data(data):
    _validate_common_data(data)
    source, target = _validate_year_rows(data.years)
    source_id = source["id_anio_escolar"]
    target_id = target["id_anio_escolar"]
    students = _rows_by_id(data.students, "id_estudiante", "student")
    sections = _rows_by_id(data.sections, "id_seccion", "section")
    enrollments = _rows_by_id(data.enrollments, "id_inscripcion", "enrollment")
    for section in sections.values():
        _require(section.get("id_anio_escolar") == source_id, "A section is outside the original 2025-2026 year", VerificationError)
    _require(
        sum(section.get("id_anio_escolar") == target_id for section in sections.values()) == 0,
        "Target-year sections are forbidden in Window A",
        VerificationError,
    )
    _require(len(enrollments) == len(students), "Enrollment count does not equal student count", VerificationError)
    _require(
        sum(row.get("id_anio_escolar") == target_id for row in enrollments.values()) == 0,
        "Target-year enrollments are forbidden in Window A",
        VerificationError,
    )
    _require(
        sum(row.get("estado") in {"promovido", "graduado"} for row in enrollments.values()) == 0,
        "Promoted or graduated results are forbidden in Window A",
        VerificationError,
    )
    students_with_enrollment = set()
    for enrollment in enrollments.values():
        student_id = enrollment.get("id_estudiante")
        _require(student_id in students, "Orphaned or null enrollment-student reference detected", VerificationError)
        _require(student_id not in students_with_enrollment, "Duplicate current-year student enrollment detected", VerificationError)
        students_with_enrollment.add(student_id)
        student = students[student_id]
        section = sections.get(enrollment.get("id_seccion"))
        _require(section is not None, "Orphaned or null enrollment-section reference detected", VerificationError)
        _require(enrollment.get("id_anio_escolar") == source_id, "Enrollment outside 2025-2026 detected", VerificationError)
        _require(section.get("id_anio_escolar") == source_id, "Enrollment section is outside 2025-2026", VerificationError)
        _require(enrollment.get("id_seccion") == student.get("id_seccion"), "Enrollment does not match the student's original section", VerificationError)
        expected_status = "activo" if student.get("activo") == 1 else "retirado"
        _require(enrollment.get("estado") == expected_status, "Enrollment status conflicts with the student active flag", VerificationError)
        _require(enrollment.get("origen") == "legacy", "Window A enrollment origin must be legacy", VerificationError)
    _require(students_with_enrollment == set(students), "A student is missing a 2025-2026 enrollment", VerificationError)
    for attendance in data.attendance:
        enrollment = enrollments.get(attendance.get("id_inscripcion"))
        _require(enrollment is not None, "Null or orphaned attendance-enrollment link detected", VerificationError)
        _require(attendance.get("id_estudiante") == enrollment.get("id_estudiante"), "Attendance link belongs to a different student", VerificationError)
        student = students[attendance["id_estudiante"]]
        _require(enrollment.get("id_seccion") == student.get("id_seccion"), "Attendance link does not retain the original section", VerificationError)
        _require(enrollment.get("id_anio_escolar") == source_id, "Attendance link is outside 2025-2026", VerificationError)
    return {
        "students": len(students),
        "inactive_students": sum(student.get("activo") == 0 for student in students.values()),
        "sections": len(sections),
        "enrollments": len(enrollments),
        "attendance": len(data.attendance),
        "observations": len(data.observations),
        "teacher_assignments": len(data.teacher_assignments),
        "target_sections": 0,
        "target_enrollments": 0,
        "promoted_or_graduated": 0,
    }


def _legacy_counts(data):
    return {
        "students": len(data.students),
        "inactive_students": sum(row.get("activo") == 0 for row in data.students),
        "sections": len(data.sections),
        "attendance": len(data.attendance),
        "observations": len(data.observations),
        "teacher_assignments": len(data.teacher_assignments),
    }


class WindowARunner:
    def __init__(self, database_factory, rehearsal_fail_after=None):
        self.database_factory = database_factory
        self.rehearsal_fail_after = rehearsal_fail_after

    def _inspect(self, database):
        schema = database.schema()
        state = _classify_state(schema)
        if state == "legacy":
            _validate_legacy_schema(schema)
        else:
            _validate_final_schema(schema)
        data = _read_data(database, schema)
        if state == "legacy":
            _validate_common_data(data)
            return Inspection("legacy_ready", data, _legacy_counts(data))
        counts = _validate_final_data(data)
        return Inspection("migrated_valid", data, counts)

    def _read_only_inspection(self):
        database = self.database_factory(read_only=True)
        try:
            return self._inspect(database)
        finally:
            database.close()

    def preflight(self):
        inspection = self._read_only_inspection()
        return RunResult(inspection.status, inspection.counts)

    def verify(self, expected_immutable=None):
        inspection = self._read_only_inspection()
        _require(inspection.status == "migrated_valid", "Independent verification requires a complete Window A state", VerificationError)
        if expected_immutable is not None:
            _compare_immutable(expected_immutable, inspection.data.snapshot)
        return RunResult("verified", inspection.counts)

    def _forced_failure(self, operation):
        if self.rehearsal_fail_after == operation:
            raise WindowAError(f"Forced rehearsal failure after {operation}")

    def apply(self):
        initial = self._read_only_inspection()
        if initial.status == "migrated_valid":
            return RunResult("already_migrated_noop", initial.counts)
        before = initial.data.snapshot
        database = self.database_factory(read_only=False)
        ddl_started = False
        try:
            current = self._inspect(database)
            _require(current.status == "legacy_ready", "Database changed before Window A apply", StateError)
            _compare_immutable(before, current.data.snapshot)
            for operation in PRE_BACKFILL_DDL:
                ddl_started = True
                database.execute(operation)
                self._forced_failure(operation)
            inserted = database.execute("insert_years")
            _require(inserted == 2, "Academic-year insert did not create exactly two rows", DatabaseOperationError)
            self._forced_failure("insert_years")
            source, _ = _validate_year_rows(tuple(database.table_rows("anio_escolar")))
            source_id = source["id_anio_escolar"]
            for operation, expected in (
                ("backfill_sections", before.sections.count),
                ("backfill_enrollments", before.students.count),
                ("backfill_attendance", before.attendance.count),
            ):
                affected = database.execute(operation, source_year_id=source_id)
                _require(affected == expected, f"{operation} affected an unexpected row count", DatabaseOperationError)
                self._forced_failure(operation)
            backfilled = _read_data(database, database.schema())
            _validate_final_data(backfilled)
            _compare_immutable(before, backfilled.snapshot)
            database.commit()
            final_ddl = list(POST_BACKFILL_DDL)
            if database.schema().index("seccion", "unique_seccion_grado") is not None:
                final_ddl.insert(3, "drop_legacy_seccion_unique")
            for operation in final_ddl:
                ddl_started = True
                database.execute(operation)
                self._forced_failure(operation)
        except Exception as exc:
            try:
                database.rollback()
            except Exception:
                pass
            if ddl_started:
                detail = str(exc) if isinstance(exc, WindowAError) else "unexpected database or driver failure"
                raise WindowAError(
                    f"Window A failed after DDL may have implicitly committed: {detail}. "
                    "Keep the write freeze and use the verified backup recovery procedure; "
                    "do not rerun or apply reverse changes until independent inspection."
                ) from None
            raise
        finally:
            database.close()
        try:
            result = self.verify(expected_immutable=before)
        except Exception as exc:
            detail = str(exc) if isinstance(exc, WindowAError) else "unexpected database or driver failure"
            raise WindowAError(
                f"Independent post-migration verification failed: {detail}. "
                "Keep the write freeze and use verified backup recovery if the state cannot be accepted."
            ) from None
        return replace(result, status="migrated_verified")


class MariaDBDatabase:
    def __init__(self, url, read_only):
        self.read_only = read_only
        try:
            self.connection = pymysql.connect(
                host=url.host,
                port=url.port or 3306,
                user=url.username,
                password=url.password,
                database=url.database,
                charset="utf8mb4",
                autocommit=False,
                cursorclass=DictCursor,
                connect_timeout=15,
                read_timeout=180,
                write_timeout=180,
            )
            with self.connection.cursor() as cursor:
                if read_only:
                    cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                    cursor.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY")
                else:
                    cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
                    cursor.execute("SELECT GET_LOCK(CONCAT('window_a_migration:', DATABASE()), 0) AS lock_acquired")
                    row = cursor.fetchone()
                    _require(row and row["lock_acquired"] == 1, "Another Window A runner holds the database lock", StateError)
        except WindowAError:
            self.connection.close()
            raise
        except Exception as exc:
            connection = getattr(self, "connection", None)
            if connection is not None:
                connection.close()
            raise DatabaseOperationError("Secure database connection or session setup failed") from exc

    def _fetch(self, sql, parameters=None):
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, parameters or ())
                return tuple(cursor.fetchall())
        except Exception as exc:
            raise DatabaseOperationError("Database metadata or data read failed") from exc

    def schema(self):
        table_rows = self._fetch(
            "SELECT TABLE_NAME, TABLE_TYPE, ENGINE FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() ORDER BY TABLE_NAME"
        )
        column_rows = self._fetch(
            "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, IS_NULLABLE, EXTRA, "
            "CHARACTER_MAXIMUM_LENGTH FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() ORDER BY TABLE_NAME, ORDINAL_POSITION"
        )
        index_rows = self._fetch(
            "SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME "
            "FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() "
            "ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX"
        )
        constraint_rows = self._fetch(
            "SELECT TABLE_NAME, CONSTRAINT_NAME, CONSTRAINT_TYPE "
            "FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = DATABASE() "
            "ORDER BY TABLE_NAME, CONSTRAINT_NAME"
        )
        foreign_key_rows = self._fetch(
            "SELECT k.TABLE_NAME, k.CONSTRAINT_NAME, k.COLUMN_NAME, "
            "k.REFERENCED_TABLE_NAME, k.REFERENCED_COLUMN_NAME, r.UPDATE_RULE, r.DELETE_RULE "
            "FROM information_schema.KEY_COLUMN_USAGE AS k "
            "JOIN information_schema.REFERENTIAL_CONSTRAINTS AS r "
            "ON r.CONSTRAINT_SCHEMA = k.CONSTRAINT_SCHEMA "
            "AND r.CONSTRAINT_NAME = k.CONSTRAINT_NAME "
            "AND r.TABLE_NAME = k.TABLE_NAME "
            "WHERE k.CONSTRAINT_SCHEMA = DATABASE() AND k.REFERENCED_TABLE_NAME IS NOT NULL "
            "ORDER BY k.TABLE_NAME, k.CONSTRAINT_NAME, k.ORDINAL_POSITION"
        )
        tables = tuple(
            TableDefinition(row["TABLE_NAME"], row["TABLE_TYPE"], row["ENGINE"])
            for row in table_rows
        )
        columns = tuple(
            ColumnDefinition(
                row["TABLE_NAME"],
                row["COLUMN_NAME"],
                row["DATA_TYPE"],
                row["COLUMN_TYPE"],
                row["IS_NULLABLE"].upper() == "YES",
                row["EXTRA"] or "",
                row["CHARACTER_MAXIMUM_LENGTH"],
            )
            for row in column_rows
        )
        grouped_indexes = {}
        for row in index_rows:
            key = (row["TABLE_NAME"], row["INDEX_NAME"])
            grouped_indexes.setdefault(key, {"unique": not row["NON_UNIQUE"], "columns": []})["columns"].append(row["COLUMN_NAME"])
        indexes = tuple(
            IndexDefinition(table, name, values["unique"], tuple(values["columns"]))
            for (table, name), values in grouped_indexes.items()
        )
        constraints = tuple(
            ConstraintDefinition(row["TABLE_NAME"], row["CONSTRAINT_NAME"], row["CONSTRAINT_TYPE"])
            for row in constraint_rows
        )
        grouped_foreign_keys = {}
        for row in foreign_key_rows:
            key = (row["TABLE_NAME"], row["CONSTRAINT_NAME"])
            foreign_key = grouped_foreign_keys.setdefault(key, {
                "columns": [],
                "referenced_table": row["REFERENCED_TABLE_NAME"],
                "referenced_columns": [],
                "update_rule": row["UPDATE_RULE"],
                "delete_rule": row["DELETE_RULE"],
            })
            foreign_key["columns"].append(row["COLUMN_NAME"])
            foreign_key["referenced_columns"].append(row["REFERENCED_COLUMN_NAME"])
        foreign_keys = tuple(
            ForeignKeyDefinition(
                table,
                name,
                tuple(values["columns"]),
                values["referenced_table"],
                tuple(values["referenced_columns"]),
                values["update_rule"],
                values["delete_rule"],
            )
            for (table, name), values in grouped_foreign_keys.items()
        )
        return Schema(tables, columns, indexes, constraints, foreign_keys)

    def table_rows(self, table):
        _require(table in ALL_TABLES, "Unexpected internal table read", DatabaseOperationError)
        primary_key = BASE_TABLES.get(table, {
            "anio_escolar": "id_anio_escolar",
            "inscripcion": "id_inscripcion",
            "asistencia": "id_asistencia",
            "asistencia_legacy": "id_asistencia",
            "matricula": "id_matricula",
            "secciones": "id_seccion",
            "profesor_secciones": "id_profesor_seccion",
        }.get(table))
        _require(primary_key is not None, "Missing internal primary-key mapping", DatabaseOperationError)
        return self._fetch(f"SELECT * FROM `{table}` ORDER BY `{primary_key}`")

    def table_count(self, table):
        _require(table in LEGACY_TABLES, "Unexpected internal count", DatabaseOperationError)
        return self._fetch(f"SELECT COUNT(*) AS row_count FROM `{table}`")[0]["row_count"]

    def duplicate_section_group_count(self):
        rows = self._fetch(
            "SELECT COUNT(*) AS duplicate_count FROM ("
            "SELECT 1 FROM `seccion` GROUP BY `id_grado`, `nombre_seccion` HAVING COUNT(*) > 1"
            ") AS duplicates"
        )
        return rows[0]["duplicate_count"]

    def execute(self, operation, source_year_id=None):
        _require(not self.read_only, "Read-only mode refused a write", DatabaseOperationError)
        _require(operation in OPERATIONS, "Unexpected internal migration operation", DatabaseOperationError)
        parameters = {"source_year_id": source_year_id} if source_year_id is not None else None
        try:
            with self.connection.cursor() as cursor:
                affected = cursor.execute(OPERATIONS[operation], parameters)
            if operation in DDL_OPERATIONS:
                self.connection.commit()
            return affected
        except Exception as exc:
            raise DatabaseOperationError(f"Database operation {operation} failed") from exc

    def commit(self):
        try:
            self.connection.commit()
        except Exception as exc:
            raise DatabaseOperationError("Database commit failed") from exc

    def rollback(self):
        self.connection.rollback()

    def close(self):
        connection = getattr(self, "connection", None)
        if connection is None:
            return
        try:
            if not self.read_only:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT RELEASE_LOCK(CONCAT('window_a_migration:', DATABASE()))")
        except Exception:
            pass
        finally:
            connection.close()


def _parse_database_url(database_url):
    _require(bool(database_url), "DATABASE_URL is required; no fallback credentials are available", AuthorizationError)
    try:
        url = make_url(database_url)
    except Exception:
        raise AuthorizationError("DATABASE_URL is not a valid database URL") from None
    _require(url.drivername == "mysql+pymysql", "DATABASE_URL must use mysql+pymysql", AuthorizationError)
    _require(bool(url.host and url.database and url.username), "DATABASE_URL must include host, database, and username", AuthorizationError)
    _require(bool(url.password), "DATABASE_URL must explicitly include a non-empty password", AuthorizationError)
    return url


def _authorize_apply(url, arguments, environment):
    _require(arguments.confirm_database == url.database, "Apply requires the exact database-name confirmation", AuthorizationError)
    _require(arguments.confirm_release, "Apply requires release authorization confirmation", AuthorizationError)
    _require(arguments.confirm_backup, "Apply requires fresh backup and isolated-restore verification confirmation", AuthorizationError)
    _require(arguments.confirm_write_freeze, "Apply requires confirmation that every writer is stopped", AuthorizationError)
    _require(
        environment.get("ENABLE_ACADEMIC_PERIOD_ADMIN", "0") in {"", "0"},
        "ENABLE_ACADEMIC_PERIOD_ADMIN must be unset or 0 during Window A",
        AuthorizationError,
    )
    app_env = environment.get("APP_ENV")
    if app_env == "production":
        _require(not arguments.rehearsal_fail_after, "Forced failures are forbidden against production", AuthorizationError)
        _require(
            environment.get(PRODUCTION_AUTHORIZATION_VARIABLE) == PRODUCTION_AUTHORIZATION_VALUE,
            "Production apply requires its separate explicit authorization variable",
            AuthorizationError,
        )
        return
    if app_env in {"development", "testing"}:
        _require(url.host in LOCAL_HOSTS, "Rehearsal apply requires a local database host", AuthorizationError)
        _require(url.database in REHEARSAL_DATABASES, "Rehearsal apply targets only control_asistencias_dev or control_asistencias_test", AuthorizationError)
        expected = f"APPLY_WINDOW_A_{app_env.upper()}"
        _require(
            environment.get(REHEARSAL_AUTHORIZATION_VARIABLE) == expected,
            "Rehearsal apply requires the environment-specific authorization value",
            AuthorizationError,
        )
        return
    raise AuthorizationError("Apply requires APP_ENV=production, development, or testing")


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise AuthorizationError("Invalid command-line arguments; use --help for safe usage")


def build_parser():
    parser = SafeArgumentParser(description="Window A schema and 2025-2026 backfill; default mode is read-only preflight")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Apply after all explicit guards pass")
    mode.add_argument("--verify", action="store_true", help="Independently verify the complete state using a read-only session")
    parser.add_argument("--confirm-database")
    parser.add_argument("--confirm-release", action="store_true")
    parser.add_argument("--confirm-backup", action="store_true")
    parser.add_argument("--confirm-write-freeze", action="store_true")
    parser.add_argument("--rehearsal-fail-after", choices=tuple(OPERATIONS))
    return parser


def _validate_arguments(arguments, environment):
    url = _parse_database_url(environment.get("DATABASE_URL"))
    apply_only_values = (
        arguments.confirm_database,
        arguments.confirm_release,
        arguments.confirm_backup,
        arguments.confirm_write_freeze,
        arguments.rehearsal_fail_after,
    )
    if not arguments.apply:
        _require(not any(apply_only_values), "Apply confirmations are invalid in read-only modes", AuthorizationError)
        return url
    _authorize_apply(url, arguments, environment)
    return url


def main(argv=None, environment=None):
    environment = os.environ if environment is None else environment
    try:
        arguments = build_parser().parse_args(argv)
        url = _validate_arguments(arguments, environment)
        runner = WindowARunner(
            lambda read_only: MariaDBDatabase(url, read_only),
            rehearsal_fail_after=arguments.rehearsal_fail_after,
        )
        if arguments.apply:
            result = runner.apply()
        elif arguments.verify:
            result = runner.verify()
        else:
            result = runner.preflight()
        counts = " ".join(f"{key}={value}" for key, value in sorted(result.counts.items()))
        print(f"Window A {result.status}" + (f" {counts}" if counts else ""))
        return 0
    except WindowAError as exc:
        print(f"Window A refused or failed: {exc}", file=sys.stderr)
        return 1
    except Exception:
        print("Window A failed unexpectedly; no URL, credentials, SQL values, or row data were logged", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
