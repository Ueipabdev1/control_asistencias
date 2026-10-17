import copy
from dataclasses import replace
from datetime import date, datetime

import pytest

import window_a_migration as migration


@pytest.fixture(autouse=True)
def rollback_database_changes():
    yield


def column(table, name, data_type="int", nullable=False, length=None, extra="", column_type=None):
    if column_type is None:
        column_type = f"varchar({length})" if data_type == "varchar" else data_type
    return migration.ColumnDefinition(
        table,
        name,
        data_type,
        column_type,
        nullable,
        extra,
        length,
    )


def index(table, name, columns, unique=False):
    return migration.IndexDefinition(table, name, unique, tuple(columns))


def constraint(table, name, kind):
    return migration.ConstraintDefinition(table, name, kind)


def foreign_key(table, name, columns, referenced_table, referenced_columns):
    return migration.ForeignKeyDefinition(
        table,
        name,
        tuple(columns),
        referenced_table,
        tuple(referenced_columns),
        "RESTRICT",
        "RESTRICT",
    )


def add_schema(state, field, definition):
    values = getattr(state.schema, field)
    state.schema = replace(state.schema, **{field: (*values, definition)})


def remove_schema(state, field, predicate):
    values = getattr(state.schema, field)
    state.schema = replace(state.schema, **{field: tuple(row for row in values if not predicate(row))})


def add_primary(schema_parts, table, primary_key):
    schema_parts["indexes"].append(index(table, "PRIMARY", (primary_key,), True))
    schema_parts["constraints"].append(constraint(table, "PRIMARY", "PRIMARY KEY"))


def legacy_schema(tables):
    parts = {"tables": [], "columns": [], "indexes": [], "constraints": [], "foreign_keys": []}
    for table in tables:
        parts["tables"].append(migration.TableDefinition(table, "BASE TABLE", "InnoDB"))
    required_columns = {
        "estudiante": ("id_estudiante", "id_seccion", "activo"),
        "seccion": ("id_seccion", "id_grado", "nombre_seccion"),
        "asistencia_estudiante": ("id_asistencia_estudiante", "id_estudiante", "fecha"),
        "observacion_seccion": ("id_observacion",),
        "profesor_seccion": ("id_profesor_seccion",),
        "grado": ("id_grado",),
    }
    for table, names in required_columns.items():
        for name in names:
            data_type = "varchar" if name == "nombre_seccion" else "date" if name == "fecha" else "tinyint" if name == "activo" else "int"
            parts["columns"].append(column(table, name, data_type, nullable=name == "activo", length=50 if data_type == "varchar" else None))
        add_primary(parts, table, migration.BASE_TABLES[table])
    return migration.Schema(**{key: tuple(value) for key, value in parts.items()})


def academic_year_schema_parts():
    tables = [migration.TableDefinition("anio_escolar", "BASE TABLE", "InnoDB")]
    columns = [
        column("anio_escolar", "id_anio_escolar", extra="auto_increment"),
        column("anio_escolar", "nombre", "varchar", length=9),
        column("anio_escolar", "codigo", "varchar", length=4),
        column("anio_escolar", "fecha_inicio", "date"),
        column("anio_escolar", "fecha_fin", "date"),
        column("anio_escolar", "es_actual", "tinyint"),
        column("anio_escolar", "fecha_creacion", "timestamp", nullable=True),
    ]
    indexes = [
        index("anio_escolar", "PRIMARY", ("id_anio_escolar",), True),
        index("anio_escolar", "unique_anio_escolar_nombre", ("nombre",), True),
        index("anio_escolar", "unique_anio_escolar_codigo", ("codigo",), True),
    ]
    constraints = [
        constraint("anio_escolar", "PRIMARY", "PRIMARY KEY"),
        constraint("anio_escolar", "unique_anio_escolar_nombre", "UNIQUE"),
        constraint("anio_escolar", "unique_anio_escolar_codigo", "UNIQUE"),
    ]
    return tables, columns, indexes, constraints


def enrollment_schema_parts():
    tables = [migration.TableDefinition("inscripcion", "BASE TABLE", "InnoDB")]
    columns = [
        column("inscripcion", "id_inscripcion", extra="auto_increment"),
        column("inscripcion", "id_estudiante"),
        column("inscripcion", "id_seccion"),
        column("inscripcion", "id_anio_escolar"),
        column(
            "inscripcion",
            "estado",
            "enum",
            column_type="enum('activo','promovido','graduado','retirado','inactivo')",
        ),
        column("inscripcion", "origen", "varchar", nullable=True, length=50),
        column("inscripcion", "fecha_registro", "timestamp", nullable=True),
        column("inscripcion", "fecha_actualizacion", "timestamp", nullable=True),
    ]
    indexes = [
        index("inscripcion", "PRIMARY", ("id_inscripcion",), True),
        index("inscripcion", "unique_inscripcion_estudiante_anio", ("id_estudiante", "id_anio_escolar"), True),
        index("inscripcion", "unique_inscripcion_estudiante", ("id_estudiante", "id_inscripcion"), True),
        index("inscripcion", "idx_inscripcion_anio_seccion_estado", ("id_anio_escolar", "id_seccion", "estado")),
        index("inscripcion", "idx_inscripcion_seccion", ("id_seccion",)),
    ]
    constraints = [
        constraint("inscripcion", "PRIMARY", "PRIMARY KEY"),
        constraint("inscripcion", "unique_inscripcion_estudiante_anio", "UNIQUE"),
        constraint("inscripcion", "unique_inscripcion_estudiante", "UNIQUE"),
        constraint("inscripcion", "fk_inscripcion_estudiante", "FOREIGN KEY"),
        constraint("inscripcion", "fk_inscripcion_seccion", "FOREIGN KEY"),
        constraint("inscripcion", "fk_inscripcion_anio", "FOREIGN KEY"),
    ]
    foreign_keys = [
        foreign_key("inscripcion", "fk_inscripcion_estudiante", ("id_estudiante",), "estudiante", ("id_estudiante",)),
        foreign_key("inscripcion", "fk_inscripcion_seccion", ("id_seccion",), "seccion", ("id_seccion",)),
        foreign_key("inscripcion", "fk_inscripcion_anio", ("id_anio_escolar",), "anio_escolar", ("id_anio_escolar",)),
    ]
    return tables, columns, indexes, constraints, foreign_keys


class MemoryState:
    def __init__(self):
        timestamp = datetime(2026, 3, 1, 12, 0, 0)
        self.tables = {
            "grado": [{"id_grado": 10, "nombre_grado": "Fictional grade"}],
            "seccion": [
                {"id_seccion": 100, "id_grado": 10, "nombre_seccion": "A", "activa": 1, "fecha_creacion": timestamp},
                {"id_seccion": 101, "id_grado": 10, "nombre_seccion": "B", "activa": 0, "fecha_creacion": timestamp},
            ],
            "estudiante": [
                {
                    "id_estudiante": 1000,
                    "id_seccion": 100,
                    "activo": 1,
                    "nombre": "Fictional Active",
                    "cedula": "FICTIONAL-1",
                    "fecha_actualizacion": timestamp,
                },
                {
                    "id_estudiante": 1001,
                    "id_seccion": 101,
                    "activo": 0,
                    "nombre": "Fictional Inactive",
                    "cedula": "FICTIONAL-2",
                    "fecha_actualizacion": timestamp,
                },
            ],
            "asistencia_estudiante": [
                {
                    "id_asistencia_estudiante": 5000,
                    "id_estudiante": 1000,
                    "fecha": date(2026, 3, 2),
                    "bloque": "completo",
                    "presente": 1,
                    "observaciones": "Fictional active note",
                    "id_usuario": 900,
                    "fecha_registro": timestamp,
                },
                {
                    "id_asistencia_estudiante": 5001,
                    "id_estudiante": 1001,
                    "fecha": date(2026, 3, 3),
                    "bloque": "bloque_1",
                    "presente": 0,
                    "observaciones": "Fictional inactive note",
                    "id_usuario": 900,
                    "fecha_registro": timestamp,
                },
            ],
            "observacion_seccion": [
                {
                    "id_observacion": 7000,
                    "id_seccion": 100,
                    "fecha": date(2026, 3, 2),
                    "observaciones": "Fictional section note",
                    "id_usuario": 900,
                },
            ],
            "profesor_seccion": [
                {"id_profesor_seccion": 8000, "id_profesor": 900, "id_seccion": 100, "fecha_asignacion": timestamp},
            ],
            "asistencia": [],
            "asistencia_legacy": [{"id_asistencia": 1, "fecha": date(2026, 3, 2), "asistentes_h": 1, "asistentes_m": 0}],
            "matricula": [],
            "secciones": [],
            "profesor_secciones": [],
        }
        self.schema = legacy_schema(self.tables)
        self.operations = []
        self.connection_modes = []
        self.commits = 0


class MemoryDatabase:
    def __init__(self, shared, read_only):
        self.shared = shared
        self.read_only = read_only
        self.pending_tables = None
        shared.connection_modes.append(read_only)

    def schema(self):
        return self.shared.schema

    def table_rows(self, table):
        return copy.deepcopy(self.shared.tables[table])

    def table_count(self, table):
        return len(self.shared.tables[table])

    def duplicate_section_group_count(self):
        groups = {}
        for row in self.shared.tables["seccion"]:
            name = row["nombre_seccion"]
            key = (row["id_grado"], name.casefold().rstrip() if name is not None else None)
            groups[key] = groups.get(key, 0) + 1
        return sum(count > 1 for count in groups.values())

    def execute(self, operation, source_year_id=None):
        if self.read_only:
            raise migration.DatabaseOperationError("Read-only fake refused a write")
        self.shared.operations.append(operation)
        if operation not in migration.DDL_OPERATIONS and self.pending_tables is None:
            self.pending_tables = copy.deepcopy(self.shared.tables)
        affected = self._apply(operation, source_year_id)
        if operation in migration.DDL_OPERATIONS:
            self.pending_tables = None
            self.shared.commits += 1
        return affected

    def _apply(self, operation, source_year_id):
        tables = self.shared.tables
        if operation == "create_anio_escolar":
            tables["anio_escolar"] = []
            new_tables, columns, indexes, constraints = academic_year_schema_parts()
            for definition in new_tables:
                add_schema(self.shared, "tables", definition)
            for definition in columns:
                add_schema(self.shared, "columns", definition)
            for definition in indexes:
                add_schema(self.shared, "indexes", definition)
            for definition in constraints:
                add_schema(self.shared, "constraints", definition)
            return 0
        if operation == "add_seccion_year":
            for row in tables["seccion"]:
                row["id_anio_escolar"] = None
            add_schema(self.shared, "columns", column("seccion", "id_anio_escolar", nullable=True))
            return 0
        if operation == "add_asistencia_enrollment":
            for row in tables["asistencia_estudiante"]:
                row["id_inscripcion"] = None
            add_schema(self.shared, "columns", column("asistencia_estudiante", "id_inscripcion", nullable=True))
            return 0
        if operation == "create_inscripcion":
            tables["inscripcion"] = []
            new_tables, columns, indexes, constraints, foreign_keys = enrollment_schema_parts()
            for definition in new_tables:
                add_schema(self.shared, "tables", definition)
            for definition in columns:
                add_schema(self.shared, "columns", definition)
            for definition in indexes:
                add_schema(self.shared, "indexes", definition)
            for definition in constraints:
                add_schema(self.shared, "constraints", definition)
            for definition in foreign_keys:
                add_schema(self.shared, "foreign_keys", definition)
            return 0
        if operation == "create_asistencia_enrollment_index":
            add_schema(self.shared, "indexes", index("asistencia_estudiante", "idx_asistencia_inscripcion", ("id_inscripcion",)))
            return 0
        if operation == "insert_years":
            tables["anio_escolar"].extend([
                {
                    "id_anio_escolar": 1,
                    "nombre": "2025-2026",
                    "codigo": "2526",
                    "fecha_inicio": date(2025, 9, 1),
                    "fecha_fin": date(2026, 8, 31),
                    "es_actual": 1,
                    "fecha_creacion": datetime(2026, 9, 1, 8, 0, 0),
                },
                {
                    "id_anio_escolar": 2,
                    "nombre": "2026-2027",
                    "codigo": "2627",
                    "fecha_inicio": date(2026, 9, 1),
                    "fecha_fin": date(2027, 8, 31),
                    "es_actual": 0,
                    "fecha_creacion": datetime(2026, 9, 1, 8, 0, 0),
                },
            ])
            return 2
        if operation == "backfill_sections":
            for row in tables["seccion"]:
                row["id_anio_escolar"] = source_year_id
            return len(tables["seccion"])
        if operation == "backfill_enrollments":
            for enrollment_id, student in enumerate(tables["estudiante"], start=1):
                tables["inscripcion"].append({
                    "id_inscripcion": enrollment_id,
                    "id_estudiante": student["id_estudiante"],
                    "id_seccion": student["id_seccion"],
                    "id_anio_escolar": source_year_id,
                    "estado": "activo" if student["activo"] == 1 else "retirado",
                    "origen": "legacy",
                    "fecha_registro": datetime(2026, 9, 1, 8, 0, 0),
                    "fecha_actualizacion": datetime(2026, 9, 1, 8, 0, 0),
                })
            return len(tables["estudiante"])
        if operation == "backfill_attendance":
            enrollments = {row["id_estudiante"]: row["id_inscripcion"] for row in tables["inscripcion"]}
            for row in tables["asistencia_estudiante"]:
                row["id_inscripcion"] = enrollments[row["id_estudiante"]]
            return len(tables["asistencia_estudiante"])
        if operation in {"set_seccion_year_not_null", "set_asistencia_enrollment_not_null"}:
            table, name = ("seccion", "id_anio_escolar") if operation == "set_seccion_year_not_null" else ("asistencia_estudiante", "id_inscripcion")
            remove_schema(self.shared, "columns", lambda row: row.table == table and row.name == name)
            add_schema(self.shared, "columns", column(table, name))
            return 0
        if operation == "add_seccion_year_fk":
            add_schema(self.shared, "constraints", constraint("seccion", "fk_seccion_anio", "FOREIGN KEY"))
            add_schema(self.shared, "foreign_keys", foreign_key("seccion", "fk_seccion_anio", ("id_anio_escolar",), "anio_escolar", ("id_anio_escolar",)))
            add_schema(self.shared, "indexes", index("seccion", "fk_seccion_anio", ("id_anio_escolar",)))
            return 0
        if operation == "drop_legacy_seccion_unique":
            remove_schema(self.shared, "indexes", lambda row: row.table == "seccion" and row.name == "unique_seccion_grado")
            remove_schema(self.shared, "constraints", lambda row: row.table == "seccion" and row.name == "unique_seccion_grado")
            return 0
        if operation == "add_seccion_year_unique":
            add_schema(self.shared, "indexes", index("seccion", "unique_seccion_anio_grado_nombre", ("id_anio_escolar", "id_grado", "nombre_seccion"), True))
            add_schema(self.shared, "constraints", constraint("seccion", "unique_seccion_anio_grado_nombre", "UNIQUE"))
            return 0
        if operation == "add_asistencia_enrollment_fk":
            add_schema(self.shared, "constraints", constraint("asistencia_estudiante", "fk_asistencia_inscripcion_estudiante", "FOREIGN KEY"))
            add_schema(
                self.shared,
                "foreign_keys",
                foreign_key(
                    "asistencia_estudiante",
                    "fk_asistencia_inscripcion_estudiante",
                    ("id_estudiante", "id_inscripcion"),
                    "inscripcion",
                    ("id_estudiante", "id_inscripcion"),
                ),
            )
            add_schema(
                self.shared,
                "indexes",
                index("asistencia_estudiante", "fk_asistencia_inscripcion_estudiante", ("id_estudiante", "id_inscripcion")),
            )
            return 0
        raise AssertionError(f"Unimplemented fake operation {operation}")

    def commit(self):
        self.pending_tables = None
        self.shared.commits += 1

    def rollback(self):
        if self.pending_tables is not None:
            self.shared.tables = self.pending_tables
            self.pending_tables = None

    def close(self):
        return None


@pytest.fixture
def shared():
    return MemoryState()


def factory(shared):
    return lambda read_only: MemoryDatabase(shared, read_only)


def apply_successfully(shared):
    return migration.WindowARunner(factory(shared)).apply()


def apply_arguments(database="control_asistencias", extra=()):
    return migration.build_parser().parse_args([
        "--apply",
        "--confirm-database", database,
        "--confirm-release",
        "--confirm-backup",
        "--confirm-write-freeze",
        *extra,
    ])


def test_legacy_to_final_migration_and_independent_verification(shared):
    before_students = copy.deepcopy(shared.tables["estudiante"])
    before_attendance = copy.deepcopy(shared.tables["asistencia_estudiante"])
    runner = migration.WindowARunner(factory(shared))

    preflight = runner.preflight()
    result = runner.apply()
    verified = runner.verify()

    assert preflight.status == "legacy_ready"
    assert result.status == "migrated_verified"
    assert verified.status == "verified"
    assert result.counts["students"] == 2
    assert result.counts["inactive_students"] == 1
    assert result.counts["enrollments"] == 2
    assert result.counts["attendance"] == 2
    for before, after in zip(before_students, shared.tables["estudiante"]):
        assert after == before
    for before, after in zip(before_attendance, shared.tables["asistencia_estudiante"]):
        assert after["id_inscripcion"] is not None
        assert {key: value for key, value in after.items() if key != "id_inscripcion"} == before
    original_sections = {row["id_estudiante"]: row["id_seccion"] for row in before_students}
    for attendance in shared.tables["asistencia_estudiante"]:
        enrollment = next(row for row in shared.tables["inscripcion"] if row["id_inscripcion"] == attendance["id_inscripcion"])
        assert attendance["id_estudiante"] == enrollment["id_estudiante"]
        assert enrollment["id_seccion"] == original_sections[attendance["id_estudiante"]]


def test_complete_state_apply_is_read_only_noop(shared):
    apply_successfully(shared)
    shared.operations.clear()
    shared.connection_modes.clear()

    result = migration.WindowARunner(factory(shared)).apply()

    assert result.status == "already_migrated_noop"
    assert shared.operations == []
    assert shared.connection_modes == [True]


def test_partial_window_a_objects_are_rejected(shared):
    apply_successfully(shared)
    remove_schema(shared, "columns", lambda row: row.table == "asistencia_estudiante" and row.name == "id_inscripcion")

    with pytest.raises(migration.StateError, match="Partial or unexpected"):
        migration.WindowARunner(factory(shared)).preflight()


def test_unexpected_academic_year_object_is_rejected(shared):
    MemoryDatabase(shared, False).execute("create_anio_escolar")

    with pytest.raises(migration.StateError, match="Partial or unexpected"):
        migration.WindowARunner(factory(shared)).preflight()


def test_conflicting_academic_year_rows_are_rejected(shared):
    apply_successfully(shared)
    shared.tables["anio_escolar"][1]["nombre"] = "2027-2028"

    with pytest.raises(migration.VerificationError, match="Conflicting or unexpected"):
        migration.WindowARunner(factory(shared)).preflight()


def test_no_rollover_or_period_activation(shared):
    apply_successfully(shared)
    years = {row["nombre"]: row for row in shared.tables["anio_escolar"]}

    assert years["2025-2026"]["es_actual"] == 1
    assert years["2026-2027"]["es_actual"] == 0
    assert all(row["id_anio_escolar"] == years["2025-2026"]["id_anio_escolar"] for row in shared.tables["seccion"])
    assert all(row["id_anio_escolar"] == years["2025-2026"]["id_anio_escolar"] for row in shared.tables["inscripcion"])
    assert not [row for row in shared.tables["seccion"] if row["id_anio_escolar"] == years["2026-2027"]["id_anio_escolar"]]
    assert not [row for row in shared.tables["inscripcion"] if row["id_anio_escolar"] == years["2026-2027"]["id_anio_escolar"]]
    assert {row["estado"] for row in shared.tables["inscripcion"]} == {"activo", "retirado"}
    inactive = next(row for row in shared.tables["estudiante"] if row["activo"] == 0)
    inactive_enrollment = next(row for row in shared.tables["inscripcion"] if row["id_estudiante"] == inactive["id_estudiante"])
    assert inactive_enrollment["estado"] == "retirado"


def test_immutable_student_pointer_and_active_snapshots(shared):
    runner = migration.WindowARunner(factory(shared))
    before = runner._read_only_inspection().data.snapshot
    apply_successfully(shared)
    student = shared.tables["estudiante"][0]
    enrollment = next(row for row in shared.tables["inscripcion"] if row["id_estudiante"] == student["id_estudiante"])
    student["id_seccion"] = 101
    student["activo"] = 0
    enrollment["id_seccion"] = 101
    enrollment["estado"] = "retirado"

    with pytest.raises(migration.VerificationError, match="Immutable students"):
        migration.WindowARunner(factory(shared)).verify(expected_immutable=before)


@pytest.mark.parametrize(
    "table,key,field,value",
    [
        ("asistencia_estudiante", "id_asistencia_estudiante", "presente", 0),
        ("asistencia_estudiante", "id_asistencia_estudiante", "observaciones", "Changed fictional note"),
        ("observacion_seccion", "id_observacion", "observaciones", "Changed section note"),
        ("profesor_seccion", "id_profesor_seccion", "id_seccion", 101),
        ("seccion", "id_seccion", "activa", 0),
    ],
)
def test_immutable_payload_snapshots(shared, table, key, field, value):
    runner = migration.WindowARunner(factory(shared))
    before = runner._read_only_inspection().data.snapshot
    apply_successfully(shared)
    row = shared.tables[table][0]
    assert row[key] is not None
    row[field] = value

    with pytest.raises(migration.VerificationError, match="Immutable"):
        migration.WindowARunner(factory(shared)).verify(expected_immutable=before)


@pytest.mark.parametrize("definition_kind", ["foreign_key", "index", "delete_rule"])
def test_constraint_and_index_definitions_are_validated(shared, definition_kind):
    apply_successfully(shared)
    if definition_kind == "foreign_key":
        shared.schema = replace(
            shared.schema,
            foreign_keys=tuple(
                replace(row, referenced_columns=("id_inscripcion", "id_estudiante"))
                if row.name == "fk_asistencia_inscripcion_estudiante" else row
                for row in shared.schema.foreign_keys
            ),
        )
        message = "wrong referenced columns"
    elif definition_kind == "delete_rule":
        shared.schema = replace(
            shared.schema,
            foreign_keys=tuple(
                replace(row, delete_rule="CASCADE") if row.name == "fk_seccion_anio" else row
                for row in shared.schema.foreign_keys
            ),
        )
        message = "ON DELETE RESTRICT"
    else:
        shared.schema = replace(
            shared.schema,
            indexes=tuple(
                replace(row, columns=("id_inscripcion", "id_estudiante"))
                if row.name == "unique_inscripcion_estudiante" else row
                for row in shared.schema.indexes
            ),
        )
        message = "wrong columns"

    with pytest.raises(migration.VerificationError, match=message):
        migration.WindowARunner(factory(shared)).preflight()


@pytest.mark.parametrize("attendance_date", [date(2026, 9, 1), date(2025, 8, 31), None])
def test_attendance_date_preflight_rejects_out_of_window_or_null(shared, attendance_date):
    shared.tables["asistencia_estudiante"][0]["fecha"] = attendance_date

    with pytest.raises(migration.StateError, match="attendance date|Attendance outside"):
        migration.WindowARunner(factory(shared)).preflight()
    assert shared.operations == []
    assert shared.connection_modes == [True]


def test_duplicate_sections_and_orphaned_references_are_rejected(shared):
    shared.tables["seccion"][1]["nombre_seccion"] = "a"
    with pytest.raises(migration.StateError, match="Duplicate current"):
        migration.WindowARunner(factory(shared)).preflight()

    other = MemoryState()
    other.tables["estudiante"][0]["id_seccion"] = 999
    with pytest.raises(migration.StateError, match="student-section"):
        migration.WindowARunner(factory(other)).preflight()

    third = MemoryState()
    third.tables["asistencia_estudiante"][0]["id_estudiante"] = 999
    with pytest.raises(migration.StateError, match="attendance-student"):
        migration.WindowARunner(factory(third)).preflight()


def test_production_apply_requires_all_authorization_guards():
    url = migration._parse_database_url("mysql+pymysql://fictional:fictional_password@database.example:3306/control_asistencias")
    arguments = apply_arguments()
    environment = {
        "APP_ENV": "production",
        migration.PRODUCTION_AUTHORIZATION_VARIABLE: migration.PRODUCTION_AUTHORIZATION_VALUE,
        "ENABLE_ACADEMIC_PERIOD_ADMIN": "0",
    }
    migration._authorize_apply(url, arguments, environment)

    for key, value in (
        (migration.PRODUCTION_AUTHORIZATION_VARIABLE, None),
        ("APP_ENV", "staging"),
        ("ENABLE_ACADEMIC_PERIOD_ADMIN", "1"),
    ):
        changed = dict(environment)
        if value is None:
            changed.pop(key)
        else:
            changed[key] = value
        with pytest.raises(migration.AuthorizationError):
            migration._authorize_apply(url, arguments, changed)

    with pytest.raises(migration.AuthorizationError, match="exact database-name"):
        migration._authorize_apply(url, apply_arguments(database="wrong_name"), environment)
    for flag in ("--confirm-release", "--confirm-backup", "--confirm-write-freeze"):
        incomplete = apply_arguments()
        setattr(incomplete, flag.removeprefix("--").replace("-", "_"), False)
        with pytest.raises(migration.AuthorizationError):
            migration._authorize_apply(url, incomplete, environment)
    with pytest.raises(migration.AuthorizationError, match="Forced failures"):
        migration._authorize_apply(url, apply_arguments(extra=("--rehearsal-fail-after", "create_inscripcion")), environment)


def test_rehearsal_apply_is_local_named_and_environment_specific():
    url = migration._parse_database_url("mysql+pymysql://fictional:fictional_password@127.0.0.1:3306/control_asistencias_dev")
    arguments = apply_arguments(database="control_asistencias_dev")
    environment = {
        "APP_ENV": "development",
        migration.REHEARSAL_AUTHORIZATION_VARIABLE: "APPLY_WINDOW_A_DEVELOPMENT",
    }
    migration._authorize_apply(url, arguments, environment)

    wrong_environment = dict(environment, **{migration.REHEARSAL_AUTHORIZATION_VARIABLE: "APPLY_WINDOW_A_TESTING"})
    with pytest.raises(migration.AuthorizationError, match="environment-specific"):
        migration._authorize_apply(url, arguments, wrong_environment)
    remote_url = migration._parse_database_url("mysql+pymysql://fictional:fictional_password@database.example:3306/control_asistencias_dev")
    with pytest.raises(migration.AuthorizationError, match="local database host"):
        migration._authorize_apply(remote_url, arguments, environment)
    wrong_name_url = migration._parse_database_url("mysql+pymysql://fictional:fictional_password@127.0.0.1:3306/control_asistencias")
    with pytest.raises(migration.AuthorizationError):
        migration._authorize_apply(wrong_name_url, apply_arguments(database="control_asistencias"), environment)


def test_read_only_default_needs_url_but_no_apply_authorization():
    url_text = "mysql+pymysql://fictional:fictional_password@database.example:3306/control_asistencias"
    arguments = migration.build_parser().parse_args([])
    url = migration._validate_arguments(arguments, {"DATABASE_URL": url_text})
    assert url.database == "control_asistencias"

    with pytest.raises(migration.AuthorizationError, match="DATABASE_URL is required"):
        migration._validate_arguments(arguments, {})
    with pytest.raises(migration.AuthorizationError, match="invalid in read-only"):
        migration._validate_arguments(migration.build_parser().parse_args(["--confirm-database", "control_asistencias"]), {"DATABASE_URL": url_text})


def test_argument_errors_are_sanitized():
    with pytest.raises(migration.AuthorizationError, match="safe usage"):
        migration.build_parser().parse_args(["--database-url", "mysql+pymysql://fictional:do_not_echo@database.example/control_asistencias"])


def test_forced_rehearsal_failure_leaves_detectable_partial_ddl(shared):
    runner = migration.WindowARunner(factory(shared), rehearsal_fail_after="set_seccion_year_not_null")

    with pytest.raises(migration.WindowAError, match="implicitly committed"):
        runner.apply()
    assert "create_anio_escolar" in shared.operations
    assert "set_seccion_year_not_null" in shared.operations
    with pytest.raises(migration.StateError, match="Partial or unexpected"):
        migration.WindowARunner(factory(shared)).preflight()


def test_migration_sql_does_not_hide_conflicts_or_disable_foreign_keys():
    for sql in migration.OPERATIONS.values():
        normalized = " ".join(sql.upper().split())
        assert "INSERT IGNORE" not in normalized
        assert "IF NOT EXISTS" not in normalized
        assert "FOREIGN_KEY_CHECKS" not in normalized
