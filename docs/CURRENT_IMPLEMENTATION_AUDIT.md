# SecureTrack X - Current Implementation Audit

**Audit date:** 2026-10-02  
**Repository:** `smart_attendance`  
**Git branch:** `development/securetrack-v2`  
**Scope:** Read-only inspection of the existing FastAPI attendance project. No application code, schema, authentication, or database changes were made.

Status labels used throughout:

| Label | Meaning |
| --- | --- |
| **CURRENTLY IMPLEMENTED** | Present in code and used by the running app |
| **PARTIALLY IMPLEMENTED** | Present as a table, enum, API, or UI stub, but incomplete vs the target domain |
| **MISSING** | Not found in the repository |
| **RISK / ISSUE** | Verified weakness in the current code |
| **FUTURE REQUIREMENT** | Needed for the SecureTrack X academic model; not claimed as existing |

This document does not claim a feature is implemented unless it was verified in the repository.

---

## 1. Executive Summary

SecureTrack X is already past a “class + date attendance sheet” prototype. The live data model stores attendance against **class sessions**, with timetable as the plan and session generation as the engine. That is closer to the target architecture than a greenfield rebuild would imply.

What exists today:

- FastAPI app with JWT login, bcrypt hashing, SQLAlchemy models, Pydantic schemas, HTML portals (login / admin / teacher / student), Docker, and Render config.
- Layered folders (`routes`, `services`, `repositories`, `models`) exist, but boundaries are leaky: routes query the database, repositories raise HTTP errors, and several services are missing for CRUD modules.
- Academic-adjacent pieces already exist as **partial** implementations: `Timetable`, `ClassSession`, `AcademicEvent`, `LeaveRequest`, `AttendanceCorrection`, `Notice`, session types for cancel/substitute/reschedule/compensatory, and a heuristic “AI assistant” summary (not RAG).

What is not production-quality yet:

- Authorization is mostly **role-based**, not **resource-based**. A logged-in student can read another student’s attendance, analytics, and CSV by changing an ID. Any teacher can mark any session and generate institution-wide sessions.
- Attendance uniqueness is enforced only in application code, not in the database. Percentage is computed from **existing attendance rows**, not from conducted sessions. Absents are not auto-created. Cancelled/future sessions are not excluded from student percentages.
- Schema is managed with `Base.metadata.create_all()` at startup. Alembic is listed in `requirements.txt` but **no Alembic configuration or revision files exist**.
- Open registration can create admin accounts. Default `secret_key` is `"changethis"`. Inactive users are blocked at login but not at token validation. Frontend pages do not enforce JWT role. Demo passwords are hardcoded in the login page.
- There are no GitHub Actions, no `docker-compose`, no README, no pytest in `requirements.txt`, and a single test file covering timetable conflict, holiday cancel, session open/close, notices, and assistant risk math — not authz, duplicate attendance, or reports.

**Do not treat this as a rebuild.** The next phases should harden identity/authorization, introduce Alembic before schema changes, then add missing academic entities (`AcademicYear`, `Department`, `Section`, enrollment, `SubjectAssignment`) while preserving existing `attendance.class_session_id` data.

---

## 2. Current Architecture

### 2.1 Expected vs actual

The prompt expected:

```
Routes → Services → Repositories → SQLAlchemy Models → Database
```

**Verified actual pattern:**

```
FastAPI routes (app/api/v1/routes/*)
    ├── some calls go to services (auth, attendance, analytics, session_engine, schedule, assistant)
    ├── many calls go directly to repositories (students, classes, calendar, timetable, notices, workflows)
    └── some routes query SQLAlchemy models directly (class_session list, timetable /today)
              ↓
Repositories (commit/refresh per operation; HTTPException in several repos)
              ↓
SQLAlchemy models / SQLite or PostgreSQL via DATABASE_URL
```

**PARTIALLY IMPLEMENTED** layered architecture. Folders exist; the dependency rule is not consistently applied.

### 2.2 Application entry

`app/main.py` (title: “SecureTrack X — Academic Attendance Platform”, version `2.0.0`):

- Calls `Base.metadata.create_all(bind=engine)` on import.
- Mounts `/static`.
- Includes API routers under `/api/v1/...`.
- Serves HTML pages: `/` login, `/dashboard` legacy dashboard, `/teacher`, `/student`, `/admin`.
- HTML routes are **not authenticated** on the server. Auth is JavaScript + API tokens only.

### 2.3 Request authentication

- `OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")`.
- `get_current_user` decodes JWT `sub` as email and loads the user from the database.
- Role gates: `require_admin`, `require_teacher` (teacher **or** admin).
- **MISSING:** `require_student`, resource ownership checks, permission objects.

### 2.4 Frontend

Server-rendered HTML templates with inline JavaScript. No SPA framework. Token stored in `sessionStorage`. Role-specific portals assume the user navigated to the correct URL.

---

## 3. Current Directory Structure

Verified tree (application and ops files). Binary/sample assets and `.git` omitted from the meaning discussion below.

```
smart_attendance/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── api/v1/
│   │   ├── __init__.py          (empty)
│   │   └── routes/              (13 route modules; routes/__init__.py empty)
│   ├── core/
│   │   ├── database.py
│   │   ├── security.py
│   │   └── dependencies.py
│   ├── models/                  (8 model modules + __init__.py)
│   ├── schemas/                 (10 schema modules)
│   ├── repositories/            (9 repository modules + __init__.py)
│   └── services/                (auth, attendance, analytics, session_engine, schedule, assistant)
├── templates/                   (login, dashboard, admin, teacher, student)
├── static/portal.css
├── tests/test_phase2.py
├── seed_data.py                 (destructive drop_all + seed)
├── seed_demo_data.py            (additive demo seed)
├── requirements.txt
├── Dockerfile
├── render.yaml
├── .gitignore
├── .claude/agents/enter.agent.md
├── sample_academic_calender_details_2026.pdf
├── SecureTrackX_Sample_Fixed_Timetable_ECE_CSE.xlsx
├── SecureTrackX_Sample_Fixed_Timetable_ECE_CSE.png
└── Minor_Project_25%.pptx.pdf
```

**MISSING (verified absent):**

- `README.md` or other project documentation besides this audit
- `alembic.ini`, `alembic/versions/`
- `docker-compose.yml`
- `.github/workflows/`
- `pyproject.toml`, `pytest.ini`, `conftest.py`
- `.env.example` (`.env` is gitignored; not inspected)
- `Procfile`, `runtime.txt`
- Dedicated `Teacher`, `Department`, `Section`, `AcademicYear`, `Subject`, `Enrollment`, `AuditLog`, `Notification` (per-user), QR, or face modules
- Frontend JS/CSS split beyond `static/portal.css` (most CSS is inline in templates)

---

## 4. Current Database Schema

Schema source of truth: SQLAlchemy models. No migration files. Indexes/uniques/FKs below are those declared on the models. No `ondelete` / `cascade` arguments were found on any `ForeignKey`. No `__table_args__` / `UniqueConstraint` / `Index()` constructs were found.

SQLite (the default engine) does **not** enable `PRAGMA foreign_keys=ON` in `app/core/database.py`. **RISK / ISSUE:** foreign keys may be unenforced on local/default SQLite.

### 4.1 `users` — `User`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `id` | Integer | PK | `index=True` |
| `full_name` | String | no | |
| `email` | String | no | **unique**, indexed |
| `hashed_password` | String | no | bcrypt via passlib |
| `role` | Enum `UserRole` | no | `admin` / `teacher` / `student`; default student |
| `is_active` | Boolean | yes (nullable not set) | default `True` |
| `created_at` | DateTime(timezone=True) | yes | `server_default=func.now()` |

- Relationships: `student` (one-to-one `Student`).
- **No** dedicated teacher profile table. A teacher is a `User` with `role=teacher`.
- Business meaning: login identity and role.

### 4.2 `students` — `Student`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `id` | Integer | PK | |
| `user_id` | Integer FK → `users.id` | no | **unique** (one profile per user) |
| `roll_number` | String | no | **unique** |
| `department` | String | no | free-text, not an entity |
| `semester` | Integer | no | integer, not a semester entity |

- Relationships: `user`, `attendance_records`.
- **MISSING:** section, academic year, enrollment in classes, program/batch.
- Business meaning: academic identity attached to a user.

### 4.3 `classes` — `Class`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `id` | Integer | PK | |
| `name` | String | no | treated as course/subject title |
| `code` | String | no | **unique** (e.g. CS301) |
| `department` | String | no | free-text |
| `teacher_id` | Integer FK → `users.id` | no | single owner teacher |

- Relationships: `teacher` → `User`; `class_sessions` → `ClassSession`.
- Comment in `ClassSession` says class is a “subject/section combination”; **the `Class` model has no section field**.
- Business meaning: a course offering owned by one teacher. This is the closest thing to Subject + assignment, collapsed into one row.

### 4.4 `timetables` — `Timetable`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `id` | Integer | PK | |
| `class_id` | Integer FK → `classes.id` | no | |
| `day_of_week` | String | no | free-text e.g. `"Monday"` (no enum) |
| `start_time` | Time | no | |
| `end_time` | Time | no | |
| `room` | String | yes | |

- Relationships: `class_`.
- Conflict detection exists in application code (teacher or room overlap on the same weekday). **No DB unique/exclusion constraint**.
- Business meaning: weekly plan. Session engine copies this into dated sessions.

### 4.5 `class_sessions` — `ClassSession`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `id` | Integer | PK | |
| `class_id` | Integer FK → `classes.id` | no | |
| `timetable_id` | Integer FK → `timetables.id` | yes | optional plan link |
| `actual_teacher_id` | Integer FK → `users.id` | no | who actually conducted |
| `date` | Date | no | |
| `start_time` | Time | no | |
| `end_time` | Time | no | |
| `room` | String | yes | |
| `session_type` | Enum `SessionType` | no | `regular`, `cancelled`, `substitute`, `rescheduled`, `compensatory`; default regular |
| `status` | String | no | default `"Scheduled"`; **not** stored as the `ClassSessionStatus` enum column |
| `is_open` | Boolean | no | default `False`; attendance window flag |
| `remarks` | String | yes | |

`ClassSessionStatus` enum exists (`Scheduled`, `Conducted`, `Cancelled`, `Rescheduled`) but the column is a plain `String`. **RISK / ISSUE:** arbitrary status strings can be written via `PUT /session/{id}/status`.

- Relationships: `class_`, `timetable`, `actual_teacher`, `attendance_records`.
- Duplicate generation is skipped in `session_engine` when `(timetable_id, date)` already exists. **No unique constraint** on that pair. Sessions with `timetable_id=NULL` can be duplicated freely.
- `ClassSessionOut` schema **does not include** `status`, `is_open`, or `remarks`.

### 4.6 `attendance` — `Attendance`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `id` | Integer | PK | |
| `student_id` | Integer FK → `students.id` | no | |
| `class_session_id` | Integer FK → `class_sessions.id` | no | |
| `status` | Enum `AttendanceStatus` | no | `present`, `absent`, `late` |
| `marked_at` | DateTime(timezone=True) | yes | `server_default=func.now()` |

- Relationships: `student`, `class_session`.
- **MISSING columns:** `marked_by`, marking method (manual/QR/face), correction flag, audit trail.
- **MISSING unique constraint** on `(student_id, class_session_id)`. Application layer returns HTTP 409 if a row already exists.
- Business meaning: one mark for one student in one **class session** (not class+date).

### 4.7 `academic_events` — `AcademicEvent`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `id` | Integer | PK | |
| `title` | String | no | |
| `description` | String | yes | |
| `event_type` | Enum `EventType` | no | `holiday`, `exam`, `other` |
| `start_date` | Date | no | |
| `end_date` | Date | no | |
| `created_by` | Integer FK → `users.id` | no | |

- Holiday creation cancels overlapping sessions (`cancel_sessions_for_event`).
- This is a calendar of events, **not** an academic year / semester master calendar with working days, term bounds, or department scope.

### 4.8 `notices` — `Notice`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `id` | Integer | PK | |
| `title` | String | no | |
| `message` | String | no | |
| `notice_type` | String | no | default `"Notice"` |
| `is_active` | Boolean | no | default `True` |
| `created_by` | Integer FK → `users.id` | no | |
| `created_at` | DateTime(timezone=True) | yes | server default now |

- Broadcast notice board. **Not** per-user notifications, email/push, or read receipts.

### 4.9 `leave_requests` — `LeaveRequest`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `id` | Integer | PK | |
| `student_id` | Integer FK → `students.id` | no | |
| `leave_type` | Enum `LeaveType` | no | sick/duty/emergency/other |
| `from_date` / `to_date` | Date | no | |
| `reason` | String | no | |
| `status` | Enum `WorkflowStatus` | no | pending/approved/rejected |
| `applied_at` | DateTime(timezone=True) | yes | |
| `approved_by` | Integer FK → `users.id` | yes | |

- Approval does **not** write attendance or block session marking.

### 4.10 `attendance_corrections` — `AttendanceCorrection`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `id` | Integer | PK | |
| `student_id` | Integer FK → `students.id` | no | |
| `class_session_id` | Integer FK → `class_sessions.id` | no | |
| `reason` | String | no | |
| `status` | Enum `WorkflowStatus` | no | |
| `requested_at` | DateTime | yes | |
| `approved_by` | Integer FK → `users.id` | yes | |

- **MISSING:** requested new status, previous status, application of the change to `attendance`.
- Route comment acknowledges that approval should update attendance; the repository only updates workflow status.

### 4.11 Domain questions (answered from code, not inference)

| # | Question | Answer |
| --- | --- | --- |
| 1 | Is attendance linked to Class + Date? | **No.** Linked to `class_session_id`. Date lives on `ClassSession`. |
| 2 | Is there a Class Session model? | **CURRENTLY IMPLEMENTED** (`class_sessions`). |
| 3 | Is there a timetable? | **CURRENTLY IMPLEMENTED** (`timetables` + APIs + conflict checks). |
| 4 | Is there an academic year? | **MISSING** as an entity. Only event dates exist. |
| 5 | Is there a semester? | **PARTIALLY IMPLEMENTED:** integer field on `Student` only. |
| 6 | Is there a department? | **PARTIALLY IMPLEMENTED:** string on `Student` and `Class`. |
| 7 | Is there a section? | **MISSING.** |
| 8 | Is there a subject? | **PARTIALLY IMPLEMENTED:** `Class.name` / `Class.code`. |
| 9 | Is there a teacher entity? | **PARTIALLY IMPLEMENTED:** `User.role = teacher` + `Class.teacher_id` / `ClassSession.actual_teacher_id`. |
| 10 | Is there subject assignment? | **PARTIALLY IMPLEMENTED:** one `teacher_id` per `Class`. No section-scoped many-to-many assignment table. |
| 11 | Is there an academic calendar? | **PARTIALLY IMPLEMENTED:** `AcademicEvent` CRUD + holiday session cancel. |
| 12 | Is there schedule-change support? | **PARTIALLY IMPLEMENTED:** cancel/substitute/status endpoints and `SessionType` values. No `ScheduleChange` entity, no class swap table, no compensatory workflow beyond the enum value. |
| 13 | Is there leave management? | **PARTIALLY IMPLEMENTED:** create + status update. No list endpoint, no attendance effect. |
| 14 | Is there attendance correction? | **PARTIALLY IMPLEMENTED:** request + status update. Does not mutate `attendance`. |
| 15 | Is there audit logging? | **MISSING.** No `AuditLog` model, no change history on attendance. |

### 4.12 Enrollment gap

**MISSING:** student–class or student–section membership. Seed data marks every student in a department on every session of that department’s classes. Live marking can attach **any student ID to any session**.

---

## 5. Current API Endpoints

Authentication key:

- **Public:** no token
- **Any user:** `get_current_user`
- **Teacher+:** `require_teacher` (teacher or admin)
- **Admin:** `require_admin`

Unless noted, “resource-level auth” means **none** beyond role.

### 5.1 Pages (HTML)

| Method | URL | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/` | Public | Login page |
| GET | `/dashboard` | Public HTML | Legacy combined dashboard (login in-page) |
| GET | `/teacher` | Public HTML | Teacher portal |
| GET | `/student` | Public HTML | Student portal |
| GET | `/admin` | Public HTML | Admin portal |

**RISK / ISSUE:** HTML is not gated by role. JS redirects if `sessionStorage.token` is missing, but does not decode JWT role.

### 5.2 Health

| Method | URL | Auth | Purpose | DB | Service/Repo |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/v1/health` | Public | Liveness JSON | none | none |

### 5.3 Auth

| Method | URL | Auth | Request | Response | DB ops | Service |
| --- | --- | --- | --- | --- | --- | --- |
| POST | `/api/v1/auth/register` | **Public** | `UserCreate` (name, email, password, **role**) | `UserOut` | insert user | `auth_service.register_user` |
| POST | `/api/v1/auth/login` | Public | OAuth2 form (`username`=email, `password`) | `Token` | read user | `auth_service.login_user` |

**RISK / ISSUE:** anyone can register with `role=admin`. Password has no complexity rules in schema.

### 5.4 Students

| Method | URL | Auth | Role | Schema | Ops | Layer |
| --- | --- | --- | --- | --- | --- | --- |
| POST | `/api/v1/students/` | Yes | admin | `StudentCreate` → `StudentOut` | insert | `student_repository` |
| GET | `/api/v1/students/` | Yes | any user | `list[StudentOut]` | select all | `student_repository` |

**RISK / ISSUE:** every authenticated user, including students, receives the full student directory (ids, roll numbers, department, semester). The student portal uses this list plus a **hardcoded email→roll map** to find “me”.

### 5.5 Classes

| Method | URL | Auth | Role | Schema | Ops | Layer |
| --- | --- | --- | --- | --- | --- | --- |
| POST | `/api/v1/classes/` | Yes | admin | `ClassCreate` → `ClassOut` | insert | `class_repository` |
| GET | `/api/v1/classes/` | Yes | any user | `list[ClassOut]` | select all | `class_repository` |

No filter by teacher assignment or student enrollment.

### 5.6 Timetable

| Method | URL | Auth | Role | Notes |
| --- | --- | --- | --- | --- |
| POST | `/api/v1/timetable/` | Yes | admin | `TimetableCreate`; conflict check in repository |
| GET | `/api/v1/timetable/` | Yes | any | skip/limit; all entries |
| GET | `/api/v1/timetable/{timetable_id}` | Yes | any | 404 if missing |
| PUT | `/api/v1/timetable/{timetable_id}` | Yes | admin | |
| DELETE | `/api/v1/timetable/{timetable_id}` | Yes | admin | no FK-safe check for existing sessions |
| GET | `/api/v1/timetable/class/{class_id}` | Yes | any | |
| GET | `/api/v1/timetable/teacher/{teacher_id}` | Yes | any | **IDOR:** any user can query any teacher’s timetable |
| GET | `/api/v1/timetable/today` | Yes | any | teachers filtered to own classes; others see all |

**RISK / ISSUE:** `GET /{timetable_id}` is declared **before** `GET /today`. FastAPI will try to parse `"today"` as `int` → **422**, so `/timetable/today` is likely unreachable.

### 5.7 Academic calendar

| Method | URL | Auth | Role | Notes |
| --- | --- | --- | --- | --- |
| POST | `/api/v1/calendar/` | Yes | admin | `AcademicEventCreate`; holidays cancel sessions |
| GET | `/api/v1/calendar/` | Yes | any | all events |
| GET | `/api/v1/calendar/{event_id}` | Yes | any | declared **before** `/range` and `/upcoming` |
| PUT | `/api/v1/calendar/{event_id}` | Yes | admin | mutates fields in the **route**, not a repository update function; overwrites `created_by` |
| DELETE | `/api/v1/calendar/{event_id}` | Yes | admin | |
| GET | `/api/v1/calendar/range` | Yes | any | query `from`/`to` |
| GET | `/api/v1/calendar/upcoming` | Yes | any | `days` query |

**RISK / ISSUE:** `/range` and `/upcoming` are shadowed by `/{event_id}` (path param is `int` → 422 for those paths).

### 5.8 Class sessions

| Method | URL | Auth | Role | Notes |
| --- | --- | --- | --- | --- |
| POST | `/api/v1/session/` | Yes | teacher+ | create any session payload (`ClassSessionCreate`) |
| GET | `/api/v1/session/` | Yes | any | raw query, last 100 by date desc |
| GET | `/api/v1/session/{session_id}` | Yes | any | **before** `/today` |
| GET | `/api/v1/session/class/{class_id}/date/{date}` | Yes | any | |
| GET | `/api/v1/session/date/{target_date}` | Yes | any | all sessions that date |
| GET | `/api/v1/session/today` | Yes | any | likely **422** due to route order |
| POST | `/api/v1/session/generate-daily/{target_date}` | Yes | teacher+ | generates **all** timetable sessions for that weekday |
| PUT | `/api/v1/session/{session_id}/status` | Yes | teacher+ | arbitrary `status: str` query param |
| POST | `/api/v1/session/{session_id}/open` | Yes | teacher+ | sets conducted + `is_open=True` |
| POST | `/api/v1/session/{session_id}/close` | Yes | teacher+ | |
| PUT | `/api/v1/session/{session_id}/cancel` | Yes | teacher+ | any teacher, any session |
| PUT | `/api/v1/session/{session_id}/substitute` | Yes | teacher+ | `new_teacher_id` query; no check that target is a teacher |

`requesting_user` is passed into `substitute_session` and **never used**.

### 5.9 Attendance

| Method | URL | Auth | Role | Request/Response | Ops | Service/Repo |
| --- | --- | --- | --- | --- | --- | --- |
| POST | `/api/v1/attendance/mark` | Yes | teacher+ | `AttendanceCreate` → `AttendanceOut` | insert | `attendance_service.mark_attendance` |
| GET | `/api/v1/attendance/student/{student_id}` | Yes | **any user** | `list[AttendanceOut]` | select | `attendance_repository` |
| GET | `/api/v1/attendance/student/{student_id}/summary` | Yes | **any user** | `AttendanceSummary` | select | `attendance_service` |
| GET | `/api/v1/attendance/session/{class_session_id}` | Yes | teacher+ | list | select | repository |

**IDOR (verified):** a student token can call `/attendance/student/{any_id}` and `/summary` with no ownership check.

Marking does **not** verify: session `is_open`, session not cancelled, teacher assigned to the class/session, or student enrolled.

### 5.10 Reports (legacy)

| Method | URL | Auth | Role | Behavior |
| --- | --- | --- | --- | --- |
| GET | `/api/v1/reports/summary/all` | Yes | **any user** | `analytics_service.get_all_risk_report` — **all students’** risk/percentages |

`templates/dashboard.html` also calls `GET /api/v1/reports/student/{id}/csv`, which **does not exist** on this router. **PARTIALLY IMPLEMENTED** / broken legacy client.

### 5.11 Analytics

| Method | URL | Auth | Role | Notes |
| --- | --- | --- | --- | --- |
| GET | `/api/v1/analytics/risk/all` | Yes | teacher+ | all students |
| GET | `/api/v1/analytics/student/{student_id}` | Yes | **any user** | detailed analytics + student PII fields |
| GET | `/api/v1/analytics/class/{class_id}` | Yes | teacher+ | any class, not only assigned |
| GET | `/api/v1/analytics/student/{student_id}/csv` | Yes | **any user** | CSV of that student’s attendance |

**IDOR (verified):** student/CSV analytics are not scoped to self. CSV columns: Record ID, Student ID, Session ID, Status (no dates/class names).

### 5.12 Workflows

| Method | URL | Auth | Role | Notes |
| --- | --- | --- | --- | --- |
| POST | `/api/v1/workflows/leave` | Yes | any, but 400 if no `current_user.student` | uses linked profile, not URL student_id (good) |
| PUT | `/api/v1/workflows/leave/{leave_id}/status` | Yes | teacher+ | any teacher; no 404 if missing (returns `null`) |
| POST | `/api/v1/workflows/correction` | Yes | student profile required | |
| PUT | `/api/v1/workflows/correction/{correction_id}/status` | Yes | teacher+ | does not update attendance |

**MISSING:** GET list of leaves/corrections for student or approver.

### 5.13 Notices

| Method | URL | Auth | Role |
| --- | --- | --- | --- |
| GET | `/api/v1/notices/` | Yes | any | active notices |
| POST | `/api/v1/notices/` | Yes | admin |
| GET | `/api/v1/notices/{notice_id}` | Yes | any | includes inactive if fetched by id |

### 5.14 Assistant

| Method | URL | Auth | Role | Notes |
| --- | --- | --- | --- | --- |
| GET | `/api/v1/assistant/` | Yes | any | `build_ai_assistant_summary` — **not LLM/RAG**. Computes global `get_all_risk_report` even for a student, then returns a role-flavored text summary. |

### 5.15 Cross-user ID access (authorization question)

**Yes. A logged-in user can access another student’s data by changing IDs** on:

- `GET /api/v1/attendance/student/{student_id}`
- `GET /api/v1/attendance/student/{student_id}/summary`
- `GET /api/v1/analytics/student/{student_id}`
- `GET /api/v1/analytics/student/{student_id}/csv`

A teacher can mark attendance for an arbitrary session/student via `POST /api/v1/attendance/mark` without assignment checks.

This was verified by inspecting route dependencies; it was not exploited in this audit.

---

## 6. Authentication Audit

### 6.1 Password hashing — CURRENTLY IMPLEMENTED

- `passlib.CryptContext(schemes=["bcrypt"])`.
- `hash_password` / `verify_password` used on register/login.
- `bcrypt==4.0.1` in requirements (avoids some passlib/bcrypt 4.1+ breakage).

**RISK / ISSUE:** no password min-length or complexity in `UserCreate`. Seed/demo password is `"password"`. Login page displays demo credentials.

### 6.2 JWT — CURRENTLY IMPLEMENTED (weak configuration)

- Algorithm HS256 via `python-jose`.
- Payload: `sub` = email, `role` = user.role, `exp` = now + **30 minutes**.
- No refresh token, no `jti`, no issuer/audience, no rotation.
- JWT `role` is **not** used for authorization; DB role is used. That is safer than trusting the token role, but unused claims still exist.

### 6.3 Secret key — RISK / ISSUE

```python
secret_key: str = "changethis"
```

If `SECRET_KEY` is unset, tokens are signed with a public default. Render `render.yaml` generates `SECRET_KEY` for that service; local/default Docker does not.

`.env` is gitignored (good). **MISSING:** `.env.example` documenting required variables without values.

### 6.4 OAuth2

- Login uses `OAuth2PasswordRequestForm`; username field is treated as email.
- No OAuth2 providers, no refresh, no scopes.

### 6.5 User lookup / inactive users

- Login: invalid credentials → 401; `is_active` false → 403.
- `get_current_user`: invalid token → 401; missing user → **404** (should typically be 401 to avoid user-existence distinction on a protected route).
- **RISK / ISSUE:** `get_current_user` does **not** check `is_active`. A disabled account’s unexpired token still works.

### 6.6 Registration

- Unauthenticated.
- Client chooses `UserRole` including admin/teacher.
- Duplicate email → 400.

### 6.7 Other auth weaknesses

- No rate limiting / lockout on login.
- No HTTPS enforcement in app code (depends on Render).
- No CORS middleware (same-origin HTML currently; still unspecified for other clients).
- Token in `sessionStorage` (XSS would steal it; no HttpOnly cookie option).
- Login UI redirects by **selected pill**, not by authenticated role (student can open `/admin` HTML with a student token).

---

## 7. Authorization Audit

Authorization today is **role labels**, not resource ownership.

| Actor | Current behavior | Expected (future academic model) | Gap |
| --- | --- | --- | --- |
| Student | Any authenticated student can list all students, all classes, all sessions (capped), all calendar events, any student’s attendance/summary/analytics/CSV (by ID). Leave/correction create uses own profile. | Only own profile, own section timetable, own attendance, own workflows. | **Large.** IDOR on student_id. Directory leak. |
| Teacher | `require_teacher` allows teacher **or** admin. Can mark any student on any session; generate all daily sessions; cancel/substitute/open any session; see all risk reports and any class analytics. | Operate only on assigned `SubjectAssignment` / sessions where they are planned or actual teacher (or approved substitute). | **Large.** No assignment check. `substitute_session` ignores requester. |
| Admin | Admin-only for user-adjacent student/class/calendar/notice create. Still uses same teacher endpoints for attendance. Open registration can create more admins. | Institution-wide academic administration with audit trail; no public self-registration to admin. | Registration + missing audit. |
| Frontend | Token presence only. Role pill chooses portal. Student identity resolved via hardcoded roll map + full student list, not `/me`. | Server-enforced role routes + `/me` profile. | Client-side assumption only. |

**FUTURE REQUIREMENT:** resource-level checks: `current_user.student.id == student_id`; teacher in `{Class.teacher_id, ClassSession.actual_teacher_id}` or admin; enrollment for marking.

Do not implement in this phase.

---

## 8. Attendance Logic Audit

### How attendance is created

`POST /api/v1/attendance/mark` → `attendance_service.mark_attendance`:

1. Student must exist (404).
2. Class session must exist (404).
3. If a row exists for `(student_id, class_session_id)` → **409**.
4. Insert status (`present` / `absent` / `late`).

Does **not** check `is_open`, cancelled type/status, date, teacher, or enrollment.

### Duplicate prevention

| Layer | Present? |
| --- | --- |
| Application | **CURRENTLY IMPLEMENTED** (409) |
| Database unique constraint | **MISSING** |

Race: two concurrent marks can both pass the SELECT and insert two rows.

### Percentage calculation

`attendance_service.get_student_summary` and `analytics_service.get_detailed_student_analytics`:

- Denominator = `len(attendance records)` for that student.
- Numerator = present + **late**.
- Late **counts as present** for percentage.
- If no records: 0%.

**Not used as denominator:** count of conducted sessions, enrolled class sessions, or working days.

### Absents auto-created?

**No.** If a teacher only marks present students, absents never exist and percentage is inflated.

Demo seed **does** create a row per student per generated past session.

### Cancelled / scheduled-not-conducted / future sessions

- Student percentage query does **not** join `ClassSession`. Cancelled or future session rows, if present, **count**.
- `get_class_analytics` excludes `session_type == cancelled` but still includes scheduled/future sessions if they exist; rate is 0% when no marks.
- Holiday generation creates cancelled sessions without attendance rows (good, unless someone later marks them — marking is not blocked).

### Marking method / who marked / correction / audit

| Capability | Status |
| --- | --- |
| Marking method (manual/QR/face) | **MISSING** |
| `marked_by` | **MISSING** |
| Correction mutating attendance | **MISSING** (workflow row only) |
| Attendance audit history | **MISSING** |
| `is_open` window | **PARTIALLY IMPLEMENTED** (open/close APIs exist; mark ignores them) |
| Session types incl. compensatory | Enum **CURRENTLY IMPLEMENTED**; compensatory workflow **MISSING** |

### Weaknesses (attendance)

1. No DB uniqueness.
2. No enrollment.
3. No teacher-session authorization.
4. Mark ignores session lifecycle (`is_open`, cancelled).
5. Percentage ≠ conducted-session policy.
6. Late policy is implicit.
7. Correction/leave disconnected from records.
8. `AttendanceOut` omits `marked_at`.
9. No bulk mark / roster endpoint; UI loads all students then marks one-by-one.

---

## 9. Reporting Audit

### Endpoints

- Legacy: `GET /api/v1/reports/summary/all` (any authenticated user) — same payload as analytics risk-all.
- Analytics: risk-all, per-student, per-class, CSV.
- Assistant summary uses the same risk report internally.

### How summaries are calculated

See §8. Risk bands: `>=85` safe, `>=75` warning, else danger. Recovery/miss buffers use 75% algebra on **record counts**, not remaining timetable.

Student analytics 404 is **not** raised for unknown `student_id`; it returns zeros plus optional empty identity fields.

### Efficiency / N+1 — RISK / ISSUE

- `get_all_risk_report`: 1 query for all students + **1 attendance query per student**.
- `get_class_analytics`: 1 query for sessions + **1 attendance query per session**.
- Teacher/admin dashboards and even the student assistant call `get_all_risk_report`.
- No eager-load of `student.user` except after-the-fact in the analytics route.
- No indexes on `attendance.student_id` or `attendance.class_session_id` beyond PK (SQLite/Postgres may still index FKs on Postgres only if declared; they are **not** declared).

### Authorization of reports/CSV

Insufficient. Any user can export another student’s CSV. `reports/summary/all` is not teacher-gated (unlike `analytics/risk/all`).

### Conducted vs cancelled vs future

Reports are **not** based on conducted sessions. Cancelled sessions are only skipped in class analytics by `session_type`. Future sessions affect class averages if generated. Student totals follow whatever rows exist.

---

## 10. Code Quality Audit

| Area | Finding | Why it matters |
| --- | --- | --- |
| Separation of concerns | Routes mix repository, raw SQLAlchemy, and services. Calendar PUT is inline. Timetable `/today` uses `__import__`. | Harder to test and to add authz consistently. |
| HTTPException in repositories | Timetable, class_session, academic_event, schedule_service | Data layer coupled to FastAPI; reuse/scripts/tests must catch HTTP errors. |
| Transactions | Almost every repository method `commit()`. Session generation commits per created session. Holiday create commits event then cancel. | Partial failure leaves inconsistent data. |
| Type hints | Partial; `current_user` untyped; `role` compared to strings (`"admin"`) which works because `UserRole` is `str` enum. | Fragile if enum type changes. |
| Pydantic | Mix of v1 `class Config: from_attributes` and reasonable schemas. `ClassSessionOut` incomplete vs model. | Clients cannot see `is_open`/`status`. |
| SQLAlchemy | `declarative_base()` (legacy 1.x style). Unlimited `String` lengths. Status as free string. | Weak DB constraints; poor Postgres portability for varchar. |
| Error handling | Missing rows often return `None` (workflow update) instead of 404. | Silent no-ops. |
| Status codes | Register 400, login 401, inactive 403, duplicate attendance 409 — generally sound. User-not-found on auth is 404. | Information leak / inconsistency. |
| DI | `get_db` and user deps used. Services instantiated as modules, not injectable classes. | Fine for size; harder to mock. |
| Logging | **MISSING** in application code (seeds `print`). | Production incidents will be opaque. |
| Config | `pydantic_settings.BaseSettings` with default SQLite and default secret. Field names `database_url` / `secret_key` (Render sets `DATABASE_URL` / `SECRET_KEY`; pydantic-settings is usually case-insensitive). | Misconfig fails closed only if URL is wrong; secret may stay default locally. |
| Duplicate analytics | Summary math copied in attendance_service and analytics_service. | Drift risk (already same late=present rule). |
| Route ordering | `/{id}` before `/today`, `/range`, `/upcoming`. | Dead endpoints. |
| Naming | `class_.py` / `Class` vs academic “course offering”. Settings still say “Smart Attendance Platform”. Health message still “Smart Attendance API”. | Product naming drift. |
| Seed scripts | `seed_data.py` **drops all tables**. `seed_demo_data.py` is additive. | Running the wrong seed destroys production data. |

---

## 11. Database Migration Audit

### What the project uses

| Mechanism | Status |
| --- | --- |
| Alembic | Dependency **pinned** in `requirements.txt` (`alembic==1.18.4`). **No** `alembic.ini`, env.py, or versions. **NOT USED.** |
| Manual SQL migrations | **MISSING** |
| `Base.metadata.create_all()` | **CURRENTLY IMPLEMENTED** in `app/main.py`, `seed_demo_data.py`, tests; `seed_data.py` also `drop_all` |
| Other | **MISSING** |

### Implications of `create_all` in production

- New tables/columns may appear on boot; **existing columns are never altered or dropped**.
- Constraints added in models later will not apply to an already-created SQLite/Postgres database.
- No downgrade path.
- Multiple app instances racing `create_all` is usually OK but is not a migration strategy.
- Impossible to review schema diffs in git as versioned DDL.

**Do not create Alembic revisions in this audit phase.** When introduced later, Alembic must stamp the **current** live schema first, then emit incremental revisions.

### Migrating attendance toward AcademicYear → … → ClassSession

Good news: attendance is **already** `Attendance → ClassSession → (optional Timetable) → Class → teacher User`. That hop does **not** need a data rewrite from class+date.

Remaining structural migration is **around** ClassSession:

- Split `Class` into Subject + Section + SubjectAssignment.
- Add AcademicYear / Semester / Department entities and re-point string fields.
- Add enrollment so historical attendance still points at the same `class_sessions.id` and `students.id`.

**Preserve existing attendance by keeping `attendance.id`, `student_id`, `class_session_id`, `status`, `marked_at` stable.** Add columns as nullable, backfill, then constrain.

Risks:

1. Recreating tables (like `seed_data.drop_all`) **destroys** history.
2. Changing `Class` PK meaning (one class per section) can orphan sessions if codes are reused.
3. Adding a unique `(student_id, class_session_id)` will fail if duplicates already exist — must detect and merge first.
4. SQLite → Postgres type/enum differences (`UserRole`, `AttendanceStatus`, etc.).
5. Render `DATABASE_URL` may be `postgres://...` while the engine branch only special-cases `postgresql` prefix. **RISK / ISSUE:** `postgres://` would take the SQLite `connect_args={"check_same_thread": False}` path.

---

## 12. Testing Audit

### Test files

**CURRENTLY IMPLEMENTED:** `tests/test_phase2.py` only.

`pytest` is **not** listed in `requirements.txt`. CI does not run tests.

### What is tested (in-process SQLite)

- Fixed timetable constant coverage (CSE/ECE, 7 periods).
- Timetable overlap conflict → HTTPException.
- Holiday event cancels matching-date sessions.
- Session open/close flags.
- Notice create + admin assistant summary text.
- Student assistant uses attendance risk math (50% / danger / recover 4).

### What is not tested

- HTTP API (TestClient) / auth login-register-JWT
- Authorization / IDOR
- Attendance mark, 409 duplicate, concurrent duplicate
- DB unique constraints (none exist)
- Percentage edge cases (empty, late-only, cancelled rows)
- Reports/CSV auth
- `is_open` ignored by mark
- Workflows (leave/correction no side effects)
- Route shadowing (`/today`, `/upcoming`)
- Registration of admin role
- Inactive user token
- Session generate-daily / substitute
- Postgres-specific behavior
- Frontend

### Highest-value missing tests (do not write yet)

1. Authn: login, bad password, inactive user, expired token, `get_current_user` after disable.
2. Authz: student A cannot read student B attendance/analytics/CSV; teacher cannot mark unassigned session.
3. Attendance: 409 duplicate; unique constraint once added; mark rejected when session closed/cancelled.
4. Percentage: late vs present; cancelled exclusion; no-row vs absent-row.
5. Reports: `summary/all` role gate; N+1 regression optional later.
6. Route order: `/session/today`, `/calendar/upcoming` return 200 not 422.

---

## 13. Deployment Audit

### Dockerfile — CURRENTLY IMPLEMENTED

- `python:3.10-slim`, copies `requirements.txt`, `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- **MISSING:** non-root user, healthcheck, multi-stage build, `PYTHONUNBUFFERED`, gunicorn/workers, `--proxy-headers`.

### docker-compose

**MISSING.**

### Render — CURRENTLY IMPLEMENTED (`render.yaml`)

- Web service `smart-attendance`, Docker runtime, **free** plan.
- Env: generated `SECRET_KEY`, `DATABASE_URL` from Postgres `smart-attendance-db` (free), `DEBUG=false`.
- **MISSING:** explicit health check path, disk for SQLite (Postgres is intended), log drains, staging vs prod split, Alembic release command.

### Environment variables (code)

| Settings field | Default | Notes |
| --- | --- | --- |
| `app_name` | Smart Attendance Platform | Naming drift |
| `debug` | False | |
| `database_url` | `sqlite:///./attendance.db` | |
| `secret_key` | `changethis` | |

### Production risks

1. Default secret if env not injected.
2. `create_all` as schema manager.
3. `seed_data.py` drop_all if someone runs it against prod.
4. Demo passwords in shipped HTML.
5. Free Render Postgres/web: spin-down, no HA.
6. No structured logging / APM.
7. No CI/CD beyond “Docker on Render”.
8. Health endpoint does not check DB.
9. Possible `postgres://` vs `postgresql://` engine mismatch.
10. Alembic unused but installed (dead dependency, not a runtime risk by itself).

---

## 14. Frontend Audit

### Pages

| Page | Role intent | Notes |
| --- | --- | --- |
| `templates/login.html` | All | Role pills prefill demo emails; password `password`; token + email in `sessionStorage`; redirect by **selected Role**, not JWT. Responsive `@media` at 768px. |
| `templates/admin.html` | Admin | Users (via public register), classes, calendar, attendance roster, analytics/CSV. |
| `templates/teacher.html` | Teacher | Generate daily sessions, mark attendance, cancel, risk table, CSV, calendar. **No `@media` queries.** |
| `templates/student.html` | Student | Overview, history, timetable, leave, calendar, notices, assistant. Identity via **hardcoded** `demoStudentRollByEmail`. **No `@media` queries.** |
| `templates/dashboard.html` | Legacy mixed | In-page login; hardcoded `loadTimetable(1)`; CSV hits **nonexistent** reports path. Token in a JS variable, not sessionStorage. |
| `static/portal.css` | Shared institutional styles | Present; templates still duplicate large inline CSS. |

### Login / token

- Login: `POST /api/v1/auth/login` as `application/x-www-form-urlencoded`.
- Token: `sessionStorage.token` (portals) or in-memory (legacy dashboard).
- No JWT decode, no expiry handling beyond API 401 (portals do not globally refresh).
- Logout: `sessionStorage.clear()` on admin/teacher; student page has analogous UI (not fully re-audited line-by-line for logout, but token gate is present).

### Dashboard architecture

Multi-page MPA. Each portal re-fetches lists. Teacher/admin generate sessions then load `/session/date/{date}`. Student timetable loads **all** timetable rows (`limit=100`) plus all classes, then filters in the browser.

### API / role handling

Frontend assumes APIs succeed for the page’s role. No consistent error component. Failed student profile match shows “attendance unavailable” rather than 403.

### Authorization assumptions

Unsafe: student portal will display whatever `/analytics/student/{id}` returns after client-side roll match. A modified `myStudentId` in memory would call another student’s APIs, and the APIs would allow it.

### Responsiveness

Login page has a mobile breakpoint. Teacher, student, and admin portals: **no `@media` in those templates**. `portal.css` has layout utilities but portals rely on fixed sidebars (~230–258px). **PARTIALLY IMPLEMENTED** responsiveness.

### Code organization

Large inline `<script>` and `<style>` per template. Duplicated API helpers (`h()`, `API` constant). No shared JS module.

---

## 15. Security Issues

Prioritized **RISK / ISSUE** list (verified):

1. **IDOR** on student attendance, summary, analytics, CSV.
2. **Open registration with choosable admin role.**
3. Default JWT **secret** `"changethis"`.
4. **Teacher-any-session** mark/cancel/open/generate-daily.
5. **Full student directory** to every authenticated user.
6. `reports/summary/all` leaks all-student risk to any role.
7. Inactive users remain valid until token expiry.
8. Demo credentials hardcoded in production HTML.
9. No rate limiting on login/register.
10. Workflow approval by any teacher; missing 404; correction does not apply.
11. HTML admin/teacher/student routes public.
12. SQLite foreign keys not enabled; no `ondelete` policy.
13. JWT in `sessionStorage` (XSS).
14. Health is unauthenticated (acceptable) but no DB check.
15. `seed_data.py` destructive drop.

This phase does not fix these.

---

## 16. Data Integrity Issues

1. No unique `(student_id, class_session_id)`.
2. No unique `(timetable_id, date)` for sessions.
3. No FK `ondelete` / ORM cascade documentation; deletes can fail or orphan depending on backend.
4. `ClassSession.status` is unconstrained string vs enum.
5. `day_of_week` free string (`monday` vs `Monday` would miss generation).
6. No enrollment → marks not limited to class members.
7. Leave/correction status can be set without applying domain effects.
8. Timetable delete does not prevent orphaning or blocking sessions.
9. Calendar update rewrites `created_by`.
10. Holiday cancel is global (all sessions in date range), not department-scoped.
11. `create_all` will not add uniqueness later without a real migration + data cleanup.

---

## 17. Performance Issues

1. N+1 analytics (`get_all_risk_report`, `get_class_analytics`).
2. Assistant computes **all-student** risk for every role including students.
3. Unbounded `GET` lists (students, classes, events, sessions limit 100 only on one endpoint).
4. Missing indexes on attendance FKs and `(student_id, class_session_id)`.
5. Per-row `commit` in session generation.
6. Student UI downloads global timetable to render one department.
7. No query for “sessions for this teacher today” on the API (filter is incomplete and `/today` may 422).

---

## 18. Missing Academic Domain Components

Compare to target:

```
AcademicYear → Semester → Department → Section → Student
Subject + Teacher + Section → SubjectAssignment → Timetable → ClassSession → Attendance
```

Supporting: AcademicEvent, ScheduleChange, LeaveRequest, AttendanceCorrection, Notification, AuditLog.

| Component | Status | 1. Why needed | 2. Problem it solves | 3. What existing code it affects | 4. Migration risk | 5. Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| **AcademicYear** | MISSING | Bound attendance and calendars to a year | Mixing 2025/2026 data; no archival | `AcademicEvent`, `Student.semester`, sessions | Low if added as new table + FKs nullable first | None |
| **Semester (entity)** | PARTIAL (int on student) | Shared term for all students in a program | Semester=5 on student does not match class/timetable term | `Student`, future enrollment, events | Medium: cannot infer term of old sessions without dates | AcademicYear |
| **Department (entity)** | PARTIAL (string) | Referential integrity, permissions, reports | Typos (`CSE` vs `Cse`); no HOD model | `Student.department`, `Class.department`, seeds, UI filters | Medium: string backfill/normalize | Optional AcademicYear |
| **Section** | MISSING | Real student grouping | Classes are course codes without A/B sections; seed treats department as cohort | `Class` comment vs model; enrollment; timetable | **High** if `Class` is split; keep `classes.id` until offering table exists | Department, Semester |
| **Student membership / enrollment** | MISSING | Who belongs in a session roster | Any student can be marked anywhere; percentage has no expected session set | `Attendance` marking, analytics denominator, teacher UI roster | Medium: backfill from historical attendance pairs | Section or Class-as-offering |
| **Subject** | PARTIAL (`Class` name/code) | Catalog vs offering | Unique `code` prevents same subject in two sections/years | `Class`, timetable, sessions | **High** if PK split | Department |
| **Teacher entity** | PARTIAL (`User` role) | Staff metadata, load, substitution eligibility | Substitute accepts any `users.id` | `Class.teacher_id`, `actual_teacher_id`, authz | Low as extension table keyed by `user_id` | User |
| **SubjectAssignment** | PARTIAL (one teacher_id) | Multi-teacher, section, term assignment | Cannot model lab vs lecture teachers or co-teaching | `Class.teacher_id`, timetable conflict (uses class.teacher_id), generate-daily | Medium: backfill one assignment per class | Subject, Teacher, Section, Semester |
| **Timetable** | CURRENTLY IMPLEMENTED | Plan of record | Already solves weekly slots | Session engine | Low for keep; medium if keys change to assignment_id | SubjectAssignment |
| **ClassSession** | CURRENTLY IMPLEMENTED | Reality of a meeting | Already the attendance parent | Attendance, analytics, workflows | **Preserve IDs** | Timetable |
| **Attendance** | CURRENTLY IMPLEMENTED | Marks | Already session-scoped | All reports | Add constraints/columns; don’t retarget parent | ClassSession, Student |
| **AcademicEvent** | PARTIAL | Holidays/exams | No year/scope/working-day calendar | session_engine, calendar routes | Low to add FKs | AcademicYear |
| **ScheduleChange** | PARTIAL (session_type + endpoints) | Audit of why reality ≠ plan | Cancel/substitute overwrite the session in place | `schedule_service`, class_session routes | Medium if history required | ClassSession, Teacher |
| **Class swap / reschedule / compensatory workflows** | MISSING (enum values only) | Formal ops | Enum can be set without paired session/date | `SessionType`, status PUT | Medium | ScheduleChange, Timetable |
| **LeaveRequest** | PARTIAL | Student absence process | No list API; no attendance effect | workflows | Low | Student, Attendance policy |
| **AttendanceCorrection** | PARTIAL | Dispute process | Approval no-op on marks | workflows, attendance | Low if we add target status + apply | Attendance, AuditLog |
| **Notification (per-user)** | MISSING (`Notice` is broadcast) | Inform students/teachers | Notices are global | `Notice`, portals | Low as new table | User |
| **AuditLog** | MISSING | Accountability | Cannot see who marked or changed attendance | attendance mark, workflows, admin CRUD | Low as append-only table | Auth users |
| **QR attendance** | MISSING | Alternate mark method | — | mark endpoint, session `is_open` | Low after authz + method column | ClassSession, Attendance |
| **Face attendance** | MISSING | Alternate mark method | — | same | Higher (privacy, models) | Attendance method, infra |
| **Analytics / ML risk** | PARTIAL (rule-based 75%) | Shortage prediction | Not ML; uses record counts | `analytics_service` | Low to keep; high if retraining on wrong denominator | Enrollment, conducted sessions |
| **AI/RAG assistant** | PARTIAL (templated summary) | Academic Q&A | No retrieval, no LLM | `assistant_service` | Low as additive | Authz so students don’t ingest all-student risk |
| **Production monitoring / CI/CD** | PARTIAL (Render only) | Safe releases | No tests in pipeline | Dockerfile, render.yaml | Low | Alembic, tests |

---

## 19. Migration Risks

1. **Attendance parent is already ClassSession.** Do not invent a second attendance table. Extend in place.
2. **`create_all` cannot add unique constraints safely** if duplicate rows exist — detect first.
3. **Splitting `Class` into Subject + Section offerings** is the highest ORM risk; sessions and timetable point at `classes.id`.
4. **String department/semester** must be mapped before FKs become required.
5. **SQLite local vs Postgres Render** enum/FK/check differences.
6. **`seed_data.py` drop_all** vs production.
7. **Downtime:** adding non-null columns without defaults.
8. **Frontend hardcoded roll map** will break when real students register.
9. **Concurrent marks** before unique index.
10. **Route/API clients** (`/today`, `/upcoming`, legacy CSV) already disagree with server; schema changes will amplify client breakage if unversioned.

---

## 20. Recommended Implementation Order

Do **not** start this automatically. After human approval:

1. **Safety net:** introduce Alembic against the *current* schema (stamp), logging, forbid `drop_all` in any deployed path, document env vars. No domain change yet.
2. **Authn harden:** disable public admin self-registration (or restrict role), check `is_active` on every request, secret required in non-debug, password policy.
3. **Authz harden:** `/me` student profile; IDOR fixes on attendance/analytics/CSV; teacher assignment checks on mark/open/cancel; gate `reports/summary/all`.
4. **Integrity:** unique `(student_id, class_session_id)`; unique `(timetable_id, date)` where timetable_id is not null; enable SQLite FKs; `ondelete` policy; fix route ordering.
5. **Attendance policy:** honor `is_open` and cancelled; decide denominator (conducted sessions); optional auto-absent on close; `marked_by`.
6. **Wire workflows:** correction applies status with audit row; leave policy decision (excused vs still absent).
7. **Academic structure (additive):** AcademicYear → Semester → Department entities; keep strings until backfilled.
8. **Section + enrollment** (or Class-as-offering + roster) **before** changing `Class` PK meaning.
9. **SubjectAssignment** replacing sole `Class.teacher_id` (backfill).
10. **ScheduleChange / compensatory / swap** as records, not only enum overwrites.
11. **Notifications + AuditLog.**
12. **Tests + CI** for authz and attendance duplicates.
13. **Deployment:** health including DB, compose, Render healthcheck, `postgresql` URL normalize.
14. **Frontend:** JWT role routing, `/me`, responsive portals; then QR/face/RAG.

---

## 21. Files Likely to Be Modified in Future Phases

Planned only; not modified now.

- `app/main.py` — stop relying on `create_all` after Alembic; middleware/logging
- `app/config.py`, `app/core/database.py`, `app/core/security.py`, `app/core/dependencies.py`
- `app/models/*.py` — new entities, uniques, FKs
- `app/schemas/*.py` — `/me`, session out fields, correction target status
- `app/api/v1/routes/*.py` — especially `auth`, `attendance`, `analytics`, `reports`, `class_session`, `students`, `calendar`, `timetable`, `workflows`
- `app/services/attendance_service.py`, `analytics_service.py`, `auth_service.py`, `schedule_service.py`, `session_engine.py`, `assistant_service.py`
- `app/repositories/*.py`
- `templates/*.html` — role routing, remove hardcoded rolls/demo secrets
- `requirements.txt` — pytest, pin Alembic usage
- `Dockerfile`, `render.yaml`
- `tests/` — expand
- New: `alembic.ini`, `alembic/versions/`
- `seed_data.py` / `seed_demo_data.py` — must not destroy prod; align with new entities

---

## 22. Questions / Ambiguities Requiring Human Decision

1. **Attendance denominator:** count of marked rows (current), conducted sessions for enrolled students, or timetable-planned sessions excluding cancelled?
2. **Should closing a session auto-create `absent` for unmarked enrolled students?**
3. **Does `late` remain equivalent to present for the 75% rule?**
4. **Is `Class` a catalog subject or a section offering?** The unique `code` field conflicts with multi-section teaching of CS301.
5. **Enrollment source of truth:** department-wide (current seed) vs explicit section roster?
6. **Who may register users?** Admin-only vs invite vs student self-register without role choice?
7. **Teacher vs admin on substitution/cancel:** any teacher (current) vs assigned only vs admin-only for substitute?
8. **Leave approved:** excused (exclude from denominator), present, or still absent with a note?
9. **Correction:** what status is requested? The model has no target status field.
10. **Production database today:** SQLite file vs Render Postgres? Any real attendance that must be preserved before unique indexes?
11. **Keep `/dashboard` legacy page** or retire in favor of role portals?
12. **Assistant:** stay rule-based, or is LLM/RAG in scope for a later phase only?
13. **Demo credentials in login HTML:** acceptable for the academic demo, or must be removed before any public URL?
14. **Semester integer vs named terms** (Odd/Even, university calendar PDF alignment)?
15. **Timezone:** `datetime.utcnow` / local `date.today()` vs institution timezone for “today” sessions?

---

## Appendix A — Dependencies (`requirements.txt`)

Pinned notable packages: FastAPI 0.136.1, Starlette 1.0.0, Uvicorn 0.46.0, SQLAlchemy 2.0.49, Pydantic 2.13.3, pydantic-settings 2.14.0, python-jose 3.5.0, passlib 1.7.4, bcrypt 4.0.1, psycopg2-binary 2.9.12, python-multipart, email-validator, Alembic 1.18.4 (unused).

**MISSING from requirements:** `pytest` (tests exist anyway).

## Appendix B — Git snapshot at audit time

- Branch: `development/securetrack-v2`
- Untracked: `.claude/` only (not application code)
- Recent commits include portals, Phase 1–4 features, Dockerfile/Render, reports/CSV
- `.gitignore` excludes `venv/`, `__pycache__/`, `.env`, `*.db`, `*.sqlite3`

No commit was created for this audit phase.

## Appendix C — Files inspected

Application: `app/main.py`, `app/config.py`, `app/core/*`, all `app/models/*`, all `app/schemas/*`, all `app/repositories/*`, all `app/services/*`, all `app/api/v1/routes/*`.

Ops: `requirements.txt`, `Dockerfile`, `render.yaml`, `.gitignore`.

Frontend: `templates/login.html`, `admin.html`, `teacher.html`, `student.html`, `dashboard.html`, `static/portal.css`.

Data/tests: `seed_data.py`, `seed_demo_data.py`, `tests/test_phase2.py`.

Also confirmed absent via search: Alembic config, GitHub Actions, docker-compose, README, pyproject, `.env.example`.
