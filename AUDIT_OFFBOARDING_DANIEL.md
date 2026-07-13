# Audit — Offboarding: Daniel Bongianni

**App:** control_asistencias (`/control_asistencias/`, port 5006)
**Date:** 2026-07-13
**Performed by:** Gustavo Perdomo (gustavo.perdomo@ueipab.edu.ve) — administrador
**Reason:** User no longer works with the organization. Access revocation + audit record prior to password rotation.

## Subject
| Field | Value |
|---|---|
| Name | Daniel Bongianni |
| Email | daniel.bongianni@ueipab.edu.ve |
| `id_usuario` | 2 |
| Role | profesor |
| Linux/OS account | `dbongianni` (owns app source on disk; handled separately) |

## Access footprint found (authoritative = DB record ownership; no auth log exists)
- Section assignments (`profesor_seccion`): 2 → `id_seccion` 6 and 14 ("Única").
- Attendance authored (`asistencia_estudiante`): 132 records, 2026-03-05 → 2026-06-18.
- Observations authored (`observacion_seccion`): 1 record, 2026-03-12.
- Last data-writing activity: **2026-06-18**.
- Note: nginx logs record IPs/URLs only (no in-app username); neither Flask app nor gunicorn writes an auth log. No `last_login` column exists on `usuario`.

## Action taken — account disabled
```sql
-- BEFORE: activo = 1
UPDATE usuario SET activo = 0 WHERE id_usuario = 2;
-- AFTER:  activo = 0  (verified)
```
Historical records authored by this user are **retained** (not deleted) for audit integrity; only login access was revoked.

## Follow-up (tracked separately)
- [ ] Rotate shared/generic admin password: `admin@ueipab.edu.ve`.
- [ ] Rotate app secrets exposed to former user's filesystem access (`SECRET_KEY`, DB credentials in `.env`).
- [ ] Lock OS account `dbongianni` and review `webdev` group membership (write access to prod code).

---

## Status recap — 2026-07-13 (cross-app offboarding)

### Daniel — application account access
| App | Account | Status |
|---|---|---|
| control_asistencias | profesor `id_usuario=2` | ✅ DISABLED (`activo=0`) |
| control_minutas | none | ✅ N/A — no account |
| bischeduler (horarios) | none | ✅ N/A — no account |
| scheduler (`gestion_horarios`) | no auth (decommissioned) | ✅ N/A |

### ✅ Completed 2026-07-13
- **OS account `dbongianni`** — LOCKED: login shell set to `/usr/sbin/nologin` and account locked (`passwd -S` → `L`). `webdev` group membership retained by decision. Verified no processes/cron/services/sessions ran as this user.
- **Shared/generic admin password rotated** — `admin@ueipab.edu.ve` (this app) re-hashed with bcrypt; new hash verified against the app's auth check. Distinct from bischeduler's password (cross-app reuse eliminated). Plaintext delivered out-of-band; **not recorded here**.

### Still pending
- Named/personal admin accounts — intentionally **not** rotated (scope limited to shared accounts by decision).
- App secrets exposed to prior filesystem access (`SECRET_KEY`, DB creds in `.env`) — not yet rotated.
- MySQL `root` has no password.
- Rotate the `infornet1` GitHub PAT exposed during this work.
