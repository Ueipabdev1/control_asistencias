"""Window B "as-is" production rollover runner (executed once, 2026-11-03).

Applies the real 2026-2027 draft packet in ``dev/backups/real_2026_2027`` using the
tested ``dev.apply_migration_packet.apply_packet`` transaction, with two deliberate,
user-authorized relaxations of the normal Window B gates:

* ``strict_ready`` is not required: the 47 review-flagged students are applied at
  their draft destinations; corrections are made afterwards in the application.
* Teacher-section pairs whose ``work_email`` has no single active local professor
  are skipped instead of failing (on 2026-11-03 all 86 pairs matched; none skipped).

All other guards in ``preflight_packet``/``apply_packet`` still apply: target year
must be planned and empty, every active source student must be in the packet, and
student/attendance counts plus every attendance-to-enrollment link are asserted
before commit.

Usage (writers must be frozen and a fresh backup taken before --apply):

    DATABASE_URL=... venv/bin/python window_b_asis_migration.py <expected_db_name>          # preflight only
    DATABASE_URL=... venv/bin/python window_b_asis_migration.py <expected_db_name> --apply  # apply

This runner has already been applied to production; rerunning it fails preflight
because 2026-2027 is now current. Keep it as the record of what was executed.
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from sqlalchemy.engine import make_url

PACKET_DIRECTORY = PROJECT_ROOT / "dev" / "backups" / "real_2026_2027"


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    expected_db = sys.argv[1]
    do_apply = "--apply" in sys.argv[2:]
    url = make_url(os.environ["DATABASE_URL"])
    if url.database != expected_db:
        raise SystemExit(f"DATABASE_URL points at {url.database}, expected {expected_db}")

    from dev.apply_migration_packet import apply_packet, preflight_packet
    from dev.migration_packet import load_packet

    packet = load_packet(PACKET_DIRECTORY, require_ready=False)

    from app import app
    from models import Usuario

    with app.app_context():
        kept, skipped = [], []
        for row in packet.teacher_sections:
            matches = Usuario.query.filter_by(
                email=row["work_email"].lower(), rol="profesor", activo=True
            ).count()
            (kept if matches == 1 else skipped).append(row)
        packet.teacher_sections[:] = kept
        print(
            f"teacher pairs kept={len(kept)} skipped={len(skipped)} "
            f"(skipped teachers={len({r['work_email'].lower() for r in skipped})})"
        )
        context = preflight_packet(packet)
        print(
            "preflight OK:", context["counts"],
            "source", context["source_year"].nombre,
            "-> target", context["target_year"].nombre,
        )
        if do_apply:
            print("APPLIED:", apply_packet(packet))
        else:
            print("preflight only; no changes")


if __name__ == "__main__":
    main()
