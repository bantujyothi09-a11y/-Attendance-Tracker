from __future__ import annotations

import csv
import hashlib
import hmac
import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Iterable

import streamlit as st
from PIL import Image, ImageOps


APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "database" / "attendance.db"
FACE_DIR = APP_DIR / "face_data"
STYLE_PATH = APP_DIR / "static" / "style.css"
SESSION_TIMEOUT_MINUTES = 45
ATTENDANCE_STATUSES = ("Present", "Absent", "Excused")


@dataclass(frozen=True)
class User:
    id: int
    username: str
    full_name: str
    role: str


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def now_text() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, expected = stored_hash.split("$", 1)
    except ValueError:
        return False
    actual = hash_password(password, salt).split("$", 1)[1]
    return hmac.compare_digest(actual, expected)


def init_db() -> None:
    with closing(connect()) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('Admin', 'Teacher')),
                email TEXT,
                phone TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login TEXT
            );

            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                roll_number TEXT NOT NULL UNIQUE,
                class_name TEXT NOT NULL,
                section TEXT NOT NULL,
                enrollment_date TEXT NOT NULL,
                contact_number TEXT,
                email TEXT,
                status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active', 'Archived')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                attendance_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('Present', 'Absent', 'Excused')),
                marked_by INTEGER NOT NULL,
                remarks TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(student_id, attendance_date),
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY(marked_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS face_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL UNIQUE,
                image_hash TEXT NOT NULL,
                image_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_students_search
                ON students(first_name, last_name, roll_number, class_name, section);
            CREATE INDEX IF NOT EXISTS idx_attendance_date
                ON attendance(attendance_date);
            """
        )
        seed_defaults(conn)
        conn.commit()


def seed_defaults(conn: sqlite3.Connection) -> None:
    created = now_text()
    users = [
        ("admin", "admin123", "System Admin", "Admin", "admin@example.com", "9000000000"),
        ("teacher", "teacher123", "Demo Teacher", "Teacher", "teacher@example.com", "9000000001"),
    ]
    for username, password, full_name, role, email, phone in users:
        conn.execute(
            """
            INSERT OR IGNORE INTO users
                (username, password_hash, full_name, role, email, phone, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (username, hash_password(password), full_name, role, email, phone, created, created),
        )

    existing_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    if existing_students:
        return

    students = [
        ("Aarav", "Sharma", "AT-001", "10", "A", "2026-04-01", "9876500011", "aarav@example.com"),
        ("Diya", "Patel", "AT-002", "10", "A", "2026-04-01", "9876500012", "diya@example.com"),
        ("Kabir", "Rao", "AT-003", "10", "B", "2026-04-01", "9876500013", "kabir@example.com"),
        ("Meera", "Iyer", "AT-004", "11", "A", "2026-04-01", "9876500014", "meera@example.com"),
        ("Vivaan", "Khan", "AT-005", "11", "B", "2026-04-01", "9876500015", "vivaan@example.com"),
    ]
    for row in students:
        conn.execute(
            """
            INSERT INTO students
                (first_name, last_name, roll_number, class_name, section, enrollment_date,
                 contact_number, email, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*row, created, created),
        )


def load_css() -> None:
    if STYLE_PATH.exists():
        st.markdown(f"<style>{STYLE_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def page_header(kicker: str, title: str, copy: str, chips: Iterable[str] = ()) -> None:
    chip_html = "".join(f'<span class="status-chip">{chip}</span>' for chip in chips)
    st.markdown(
        f"""
        <section class="hero-panel">
          <div class="hero-kicker">{kicker}</div>
          <h1 class="hero-title">{title}</h1>
          <div class="hero-copy">{copy}</div>
          <div class="status-strip">{chip_html}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def image_to_hash(uploaded_image) -> str:
    image = Image.open(uploaded_image).convert("L")
    image = ImageOps.fit(image, (32, 32), method=Image.Resampling.LANCZOS)
    pixel_source = image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()
    pixels = list(pixel_source)
    average = sum(pixels) / len(pixels)
    return "".join("1" if pixel >= average else "0" for pixel in pixels)


def hamming_distance(left: str, right: str) -> int:
    return sum(1 for a, b in zip(left, right) if a != b) + abs(len(left) - len(right))


def face_match_confidence(distance: int, hash_size: int = 1024) -> float:
    return max(0.0, round((1 - distance / hash_size) * 100, 2))


def save_face_reference(student_id: int, uploaded_image) -> str:
    FACE_DIR.mkdir(parents=True, exist_ok=True)
    uploaded_image.seek(0)
    image = Image.open(uploaded_image).convert("RGB")
    path = FACE_DIR / f"student-{student_id}.jpg"
    image.save(path, format="JPEG", quality=88)
    uploaded_image.seek(0)
    return str(path.relative_to(APP_DIR))


def find_face_match(image_hash: str, threshold: int = 330) -> tuple[sqlite3.Row | None, float, int]:
    profiles = fetch_all(
        """
        SELECT fp.student_id, fp.image_hash, s.roll_number,
               s.first_name || ' ' || s.last_name AS student,
               s.class_name, s.section
        FROM face_profiles fp
        JOIN students s ON s.id = fp.student_id
        WHERE s.status = 'Active'
        """
    )
    if not profiles:
        return None, 0.0, 0

    best = min(profiles, key=lambda row: hamming_distance(image_hash, row["image_hash"]))
    distance = hamming_distance(image_hash, best["image_hash"])
    confidence = face_match_confidence(distance)
    if distance > threshold:
        return None, confidence, distance
    return best, confidence, distance


def get_user_by_credentials(username: str, password: str) -> User | None:
    with closing(connect()) as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()
        if not row or not verify_password(password, row["password_hash"]):
            return None
        conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (now_text(), row["id"]))
        conn.commit()
        return User(row["id"], row["username"], row["full_name"], row["role"])


def normalize_last_seen(value) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
            return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed
        except ValueError:
            return None
    return None


def current_user() -> User | None:
    user_data = st.session_state.get("user")
    last_seen = normalize_last_seen(st.session_state.get("last_seen"))
    if not user_data:
        return None
    if not last_seen:
        st.session_state.pop("user", None)
        st.session_state.pop("last_seen", None)
        return None
    if datetime.now(UTC) - last_seen > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
        st.session_state.clear()
        st.warning("Session expired. Please sign in again.")
        return None
    st.session_state.last_seen = datetime.now(UTC)
    return User(**user_data)


def login_screen() -> None:
    st.markdown('<div class="app-shell">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Neural Attendance Console</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="app-title">Attendance <strong>Tracker</strong></h1>', unsafe_allow_html=True)
    st.markdown(
        '<div class="app-subtitle">A futuristic control room for student records, live attendance capture, secure sessions, and report intelligence.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="status-strip">
          <span class="status-chip">SQLite core online</span>
          <span class="status-chip">Role access enabled</span>
          <span class="status-chip">Reports ready</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", value="admin")
        password = st.text_input("Password", type="password", value="admin123")
        submitted = st.form_submit_button("Sign in", use_container_width=True)

    st.markdown(
        '<div class="notice">Demo accounts: admin / admin123 and teacher / teacher123.</div>',
        unsafe_allow_html=True,
    )

    if submitted:
        user = get_user_by_credentials(username, password)
        if user:
            st.session_state.user = user.__dict__
            st.session_state.last_seen = datetime.now(UTC)
            st.rerun()
        st.error("Invalid username or password.")
    st.markdown("</div>", unsafe_allow_html=True)


def fetch_all(query: str, params: Iterable = ()) -> list[sqlite3.Row]:
    with closing(connect()) as conn:
        return list(conn.execute(query, tuple(params)).fetchall())


def fetch_one(query: str, params: Iterable = ()) -> sqlite3.Row | None:
    with closing(connect()) as conn:
        return conn.execute(query, tuple(params)).fetchone()


def dashboard() -> None:
    totals = fetch_one(
        """
        SELECT
            (SELECT COUNT(*) FROM students WHERE status = 'Active') AS active_students,
            (SELECT COUNT(*) FROM users) AS users,
            (SELECT COUNT(*) FROM attendance WHERE attendance_date = ?) AS today_records,
            (SELECT COUNT(*) FROM attendance) AS all_records
        """,
        (date.today().isoformat(),),
    )
    present_absent = fetch_one(
        """
        SELECT
            SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS present_count,
            SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) AS absent_count
        FROM attendance
        """
    )
    present = present_absent["present_count"] or 0
    absent = present_absent["absent_count"] or 0
    rate = round((present / (present + absent)) * 100, 1) if present + absent else 0

    page_header(
        "Mission Control",
        "Attendance <strong>Dashboard</strong>",
        "Monitor daily attendance signals, active student load, user access, and live reporting health from one command surface.",
        ("Live SQLite telemetry", "Session protected", "CSV export armed"),
    )
    st.markdown(
        f"""
        <div class="metric-row">
          <div class="metric-tile"><strong>{totals['active_students']}</strong><span>Active students</span></div>
          <div class="metric-tile"><strong>{totals['today_records']}</strong><span>Marked today</span></div>
          <div class="metric-tile"><strong>{rate}%</strong><span>Overall attendance</span></div>
          <div class="metric-tile"><strong>{totals['users']}</strong><span>System users</span></div>
        </div>
        <div class="signal-grid">
          <div class="signal-card">
            <div class="signal-title">Attendance signal strength</div>
            <div class="signal-bar"><div class="signal-fill" style="width: {max(4, min(rate, 100))}%;"></div></div>
          </div>
          <div class="signal-card">
            <div class="signal-title">System mode</div>
            <strong>Operational</strong><br><span style="color: var(--muted);">All core agents are responding.</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    recent = fetch_all(
        """
        SELECT s.roll_number, s.first_name || ' ' || s.last_name AS student,
               s.class_name || '-' || s.section AS class, a.attendance_date, a.status, u.full_name AS marked_by
        FROM attendance a
        JOIN students s ON s.id = a.student_id
        JOIN users u ON u.id = a.marked_by
        ORDER BY a.attendance_date DESC, a.updated_at DESC
        LIMIT 15
        """
    )
    st.subheader("Recent Attendance")
    st.dataframe([dict(row) for row in recent], use_container_width=True, hide_index=True)


def student_options(active_only: bool = True) -> list[sqlite3.Row]:
    status_filter = "WHERE status = 'Active'" if active_only else ""
    return fetch_all(
        f"""
        SELECT id, first_name, last_name, roll_number, class_name, section, status
        FROM students
        {status_filter}
        ORDER BY class_name, section, roll_number
        """
    )


def student_management(user: User) -> None:
    page_header(
        "Student Matrix",
        "Student <strong>Records</strong>",
        "Search, create, update, and archive student profiles with role-aware controls and persistent storage.",
        ("Admin write access" if user.role == "Admin" else "Teacher read-only", "Indexed search", "Active archive flow"),
    )

    if user.role != "Admin":
        st.info("Teacher access is read-only for student records.")

    search = st.text_input("Search by name, roll number, class, or section")
    params: list[str] = []
    where = ""
    if search.strip():
        like = f"%{search.strip()}%"
        where = """
            WHERE first_name LIKE ? OR last_name LIKE ? OR roll_number LIKE ?
               OR class_name LIKE ? OR section LIKE ?
        """
        params = [like] * 5

    rows = fetch_all(
        f"""
        SELECT id, first_name, last_name, roll_number, class_name, section,
               enrollment_date, contact_number, email, status
        FROM students
        {where}
        ORDER BY status, class_name, section, roll_number
        """,
        params,
    )
    st.dataframe([dict(row) for row in rows], use_container_width=True, hide_index=True)

    if user.role != "Admin":
        return

    tab_add, tab_edit = st.tabs(["Add Student", "Edit or Archive"])
    with tab_add:
        with st.form("add_student"):
            cols = st.columns(2)
            first_name = cols[0].text_input("First name")
            last_name = cols[1].text_input("Last name")
            roll_number = cols[0].text_input("Roll number")
            class_name = cols[1].text_input("Class")
            section = cols[0].text_input("Section")
            enrollment_date = cols[1].date_input("Enrollment date", value=date.today())
            contact_number = cols[0].text_input("Contact number")
            email = cols[1].text_input("Email")
            if st.form_submit_button("Create student", use_container_width=True):
                if not all([first_name.strip(), last_name.strip(), roll_number.strip(), class_name.strip(), section.strip()]):
                    st.error("First name, last name, roll number, class, and section are required.")
                else:
                    try:
                        with closing(connect()) as conn:
                            stamp = now_text()
                            conn.execute(
                                """
                                INSERT INTO students
                                    (first_name, last_name, roll_number, class_name, section,
                                     enrollment_date, contact_number, email, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    first_name.strip(),
                                    last_name.strip(),
                                    roll_number.strip(),
                                    class_name.strip(),
                                    section.strip(),
                                    enrollment_date.isoformat(),
                                    contact_number.strip(),
                                    email.strip(),
                                    stamp,
                                    stamp,
                                ),
                            )
                            conn.commit()
                        st.success("Student created.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Roll number already exists.")

    with tab_edit:
        all_students = student_options(active_only=False)
        if not all_students:
            st.info("No students available.")
            return
        selected = st.selectbox(
            "Select student",
            all_students,
            format_func=lambda r: f"{r['roll_number']} - {r['first_name']} {r['last_name']} ({r['status']})",
        )
        detail = fetch_one("SELECT * FROM students WHERE id = ?", (selected["id"],))
        if not detail:
            st.warning("Selected student was not found.")
            return

        with st.form("edit_student"):
            cols = st.columns(2)
            first_name = cols[0].text_input("First name", value=detail["first_name"])
            last_name = cols[1].text_input("Last name", value=detail["last_name"])
            roll_number = cols[0].text_input("Roll number", value=detail["roll_number"])
            class_name = cols[1].text_input("Class", value=detail["class_name"])
            section = cols[0].text_input("Section", value=detail["section"])
            enrollment_date = cols[1].date_input("Enrollment date", value=date.fromisoformat(detail["enrollment_date"]))
            contact_number = cols[0].text_input("Contact number", value=detail["contact_number"] or "")
            email = cols[1].text_input("Email", value=detail["email"] or "")
            status = st.selectbox("Status", ("Active", "Archived"), index=0 if detail["status"] == "Active" else 1)
            if st.form_submit_button("Save changes", use_container_width=True):
                try:
                    with closing(connect()) as conn:
                        conn.execute(
                            """
                            UPDATE students
                            SET first_name = ?, last_name = ?, roll_number = ?, class_name = ?, section = ?,
                                enrollment_date = ?, contact_number = ?, email = ?, status = ?, updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                first_name.strip(),
                                last_name.strip(),
                                roll_number.strip(),
                                class_name.strip(),
                                section.strip(),
                                enrollment_date.isoformat(),
                                contact_number.strip(),
                                email.strip(),
                                status,
                                now_text(),
                                detail["id"],
                            ),
                        )
                        conn.commit()
                    st.success("Student updated.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Roll number already exists.")


def attendance_page(user: User) -> None:
    page_header(
        "Capture Grid",
        "Mark <strong>Attendance</strong>",
        "Select a class, lock onto a date, and submit attendance with duplicate-safe upsert behavior.",
        ("Present", "Absent", "Excused"),
    )

    classes = fetch_all(
        "SELECT DISTINCT class_name, section FROM students WHERE status = 'Active' ORDER BY class_name, section"
    )
    if not classes:
        st.info("Add active students before marking attendance.")
        return

    class_choice = st.selectbox("Class and section", classes, format_func=lambda r: f"{r['class_name']} - {r['section']}")
    selected_date = st.date_input("Attendance date", value=date.today())

    students = fetch_all(
        """
        SELECT s.*, a.status AS existing_status, a.remarks AS existing_remarks
        FROM students s
        LEFT JOIN attendance a ON a.student_id = s.id AND a.attendance_date = ?
        WHERE s.status = 'Active' AND s.class_name = ? AND s.section = ?
        ORDER BY s.roll_number
        """,
        (selected_date.isoformat(), class_choice["class_name"], class_choice["section"]),
    )

    with st.form("attendance_form"):
        entries = []
        for student in students:
            cols = st.columns([2, 2, 3])
            cols[0].write(f"**{student['roll_number']}**")
            cols[0].caption(f"{student['first_name']} {student['last_name']}")
            current_status = student["existing_status"] or "Present"
            status = cols[1].selectbox(
                "Status",
                ATTENDANCE_STATUSES,
                index=ATTENDANCE_STATUSES.index(current_status),
                key=f"status_{student['id']}",
                label_visibility="collapsed",
            )
            remarks = cols[2].text_input(
                "Remarks",
                value=student["existing_remarks"] or "",
                key=f"remarks_{student['id']}",
                label_visibility="collapsed",
                placeholder="Optional remarks",
            )
            entries.append((student["id"], status, remarks))

        submitted = st.form_submit_button("Save attendance", use_container_width=True)

    if submitted:
        with closing(connect()) as conn:
            stamp = now_text()
            for student_id, status, remarks in entries:
                conn.execute(
                    """
                    INSERT INTO attendance
                        (student_id, attendance_date, status, marked_by, remarks, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(student_id, attendance_date)
                    DO UPDATE SET status = excluded.status,
                                  marked_by = excluded.marked_by,
                                  remarks = excluded.remarks,
                                  updated_at = excluded.updated_at
                    """,
                    (student_id, selected_date.isoformat(), status, user.id, remarks.strip(), stamp, stamp),
                )
            conn.commit()
        st.success("Attendance saved. Existing entries were updated safely when present.")
        st.rerun()

    summary = fetch_all(
        """
        SELECT status, COUNT(*) AS total
        FROM attendance
        WHERE attendance_date = ?
        GROUP BY status
        ORDER BY status
        """,
        (selected_date.isoformat(),),
    )
    if summary:
        st.subheader("Daily Summary")
        st.dataframe([dict(row) for row in summary], use_container_width=True, hide_index=True)


def face_attendance_page(user: User) -> None:
    page_header(
        "Vision Gate",
        "Face <strong>Attendance</strong>",
        "Enroll student face references, then capture or upload a face image to mark attendance automatically.",
        ("Camera capture", "Face profile registry", "Auto present marking"),
    )

    registered = fetch_one("SELECT COUNT(*) AS total FROM face_profiles")
    active_students = fetch_one("SELECT COUNT(*) AS total FROM students WHERE status = 'Active'")
    st.markdown(
        f"""
        <div class="metric-row">
          <div class="metric-tile"><strong>{registered['total']}</strong><span>Face profiles</span></div>
          <div class="metric-tile"><strong>{active_students['total']}</strong><span>Active students</span></div>
          <div class="metric-tile"><strong>Present</strong><span>Recognition result</span></div>
          <div class="metric-tile"><strong>Secure</strong><span>Stored as image fingerprint</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    enroll_tab, scan_tab = st.tabs(["Register Face", "Scan Attendance"])

    with enroll_tab:
        if user.role != "Admin":
            st.info("Only Admin users can register or update student face profiles.")
        students = student_options(active_only=True)
        if not students:
            st.warning("Add active students before registering faces.")
        else:
            selected = st.selectbox(
                "Student",
                students,
                format_func=lambda r: f"{r['roll_number']} - {r['first_name']} {r['last_name']} ({r['class_name']}-{r['section']})",
                key="face_register_student",
            )
            source = st.radio("Reference image source", ("Camera", "Upload"), horizontal=True, key="face_register_source")
            image_file = (
                st.camera_input("Capture student face", key="face_register_camera")
                if source == "Camera"
                else st.file_uploader("Upload student face image", type=("jpg", "jpeg", "png"), key="face_register_upload")
            )

            if st.button("Save face profile", disabled=user.role != "Admin" or image_file is None, use_container_width=True):
                try:
                    image_hash = image_to_hash(image_file)
                    image_path = save_face_reference(selected["id"], image_file)
                    with closing(connect()) as conn:
                        stamp = now_text()
                        conn.execute(
                            """
                            INSERT INTO face_profiles (student_id, image_hash, image_path, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT(student_id)
                            DO UPDATE SET image_hash = excluded.image_hash,
                                          image_path = excluded.image_path,
                                          updated_at = excluded.updated_at
                            """,
                            (selected["id"], image_hash, image_path, stamp, stamp),
                        )
                        conn.commit()
                    st.success("Face profile saved for attendance recognition.")
                    st.rerun()
                except Exception as exc:
                    st.error("Could not save that face image. Try a clearer front-facing photo.")
                    st.caption(str(exc))

    with scan_tab:
        selected_date = st.date_input("Attendance date", value=date.today(), key="face_scan_date")
        source = st.radio("Scan image source", ("Camera", "Upload"), horizontal=True, key="face_scan_source")
        scan_file = (
            st.camera_input("Capture face for attendance", key="face_scan_camera")
            if source == "Camera"
            else st.file_uploader("Upload face image for attendance", type=("jpg", "jpeg", "png"), key="face_scan_upload")
        )

        if st.button("Recognize and mark present", disabled=scan_file is None, use_container_width=True):
            try:
                scan_hash = image_to_hash(scan_file)
                match, confidence, distance = find_face_match(scan_hash)
                if not match:
                    st.error(f"No confident face match found. Closest confidence: {confidence}%.")
                    st.caption(f"Distance score: {distance}. Register a clearer face profile or try a brighter image.")
                    return

                with closing(connect()) as conn:
                    stamp = now_text()
                    conn.execute(
                        """
                        INSERT INTO attendance
                            (student_id, attendance_date, status, marked_by, remarks, created_at, updated_at)
                        VALUES (?, ?, 'Present', ?, ?, ?, ?)
                        ON CONFLICT(student_id, attendance_date)
                        DO UPDATE SET status = 'Present',
                                      marked_by = excluded.marked_by,
                                      remarks = excluded.remarks,
                                      updated_at = excluded.updated_at
                        """,
                        (
                            match["student_id"],
                            selected_date.isoformat(),
                            user.id,
                            f"Marked by face recognition with {confidence}% confidence",
                            stamp,
                            stamp,
                        ),
                    )
                    conn.commit()

                st.success(
                    f"Attendance marked Present for {match['student']} "
                    f"({match['roll_number']}) with {confidence}% confidence."
                )
            except Exception as exc:
                st.error("Could not process that face image. Try a clearer front-facing photo.")
                st.caption(str(exc))


def build_report_rows(start_date: date, end_date: date, class_filter: str, student_id: int | None) -> list[sqlite3.Row]:
    filters = ["a.attendance_date BETWEEN ? AND ?"]
    params: list[object] = [start_date.isoformat(), end_date.isoformat()]
    if class_filter != "All":
        filters.append("s.class_name = ?")
        params.append(class_filter)
    if student_id:
        filters.append("s.id = ?")
        params.append(student_id)
    where = " AND ".join(filters)
    return fetch_all(
        f"""
        SELECT s.roll_number, s.first_name || ' ' || s.last_name AS student,
               s.class_name, s.section,
               SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present,
               SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent,
               SUM(CASE WHEN a.status = 'Excused' THEN 1 ELSE 0 END) AS excused,
               COUNT(a.id) AS total_records
        FROM attendance a
        JOIN students s ON s.id = a.student_id
        WHERE {where}
        GROUP BY s.id
        ORDER BY s.class_name, s.section, s.roll_number
        """,
        params,
    )


def row_with_percentage(row: sqlite3.Row) -> dict:
    present = row["present"] or 0
    absent = row["absent"] or 0
    denominator = present + absent
    percentage = round((present / denominator) * 100, 2) if denominator else 0
    data = dict(row)
    data["attendance_percentage"] = percentage
    return data


def to_csv(rows: list[dict]) -> str:
    output = StringIO()
    if not rows:
        return ""
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def reports_page() -> None:
    page_header(
        "Analytics Core",
        "Attendance <strong>Reports</strong>",
        "Filter attendance intelligence by date range, class, or student, then export clean CSV summaries.",
        ("Percentage engine", "Range filters", "CSV export"),
    )

    cols = st.columns(4)
    start_date = cols[0].date_input("Start date", value=date.today() - timedelta(days=30))
    end_date = cols[1].date_input("End date", value=date.today())
    classes = ["All"] + [row["class_name"] for row in fetch_all("SELECT DISTINCT class_name FROM students ORDER BY class_name")]
    class_filter = cols[2].selectbox("Class", classes)
    students = student_options(active_only=False)
    student_labels = {0: "All students"} | {
        row["id"]: f"{row['roll_number']} - {row['first_name']} {row['last_name']}" for row in students
    }
    student_id = cols[3].selectbox("Student", list(student_labels.keys()), format_func=student_labels.get)

    if start_date > end_date:
        st.error("Start date must be before or equal to end date.")
        return

    rows = [row_with_percentage(row) for row in build_report_rows(start_date, end_date, class_filter, student_id or None)]
    total_present = sum(row["present"] or 0 for row in rows)
    total_absent = sum(row["absent"] or 0 for row in rows)
    total_excused = sum(row["excused"] or 0 for row in rows)
    rate = round(total_present / (total_present + total_absent) * 100, 1) if total_present + total_absent else 0

    st.markdown(
        f"""
        <div class="metric-row">
          <div class="metric-tile"><strong>{total_present}</strong><span>Total present</span></div>
          <div class="metric-tile"><strong>{total_absent}</strong><span>Total absent</span></div>
          <div class="metric-tile"><strong>{total_excused}</strong><span>Total excused</span></div>
          <div class="metric-tile"><strong>{rate}%</strong><span>Attendance rate</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.dataframe(rows, use_container_width=True, hide_index=True)
    csv_data = to_csv(rows)
    st.download_button(
        "Download CSV",
        data=csv_data,
        file_name=f"attendance-report-{start_date.isoformat()}-{end_date.isoformat()}.csv",
        mime="text/csv",
        disabled=not bool(rows),
        use_container_width=True,
    )


def users_page(user: User) -> None:
    page_header(
        "Admin Control",
        "User <strong>Access</strong>",
        "Manage teacher and admin identities with hashed passwords and role-separated workflows.",
        ("Password hashing", "Role gates", "Session timeout"),
    )
    if user.role != "Admin":
        st.error("Only Admin users can manage system users.")
        return

    rows = fetch_all("SELECT id, username, full_name, role, email, phone, last_login FROM users ORDER BY role, username")
    st.dataframe([dict(row) for row in rows], use_container_width=True, hide_index=True)

    with st.form("create_user"):
        cols = st.columns(2)
        username = cols[0].text_input("Username")
        full_name = cols[1].text_input("Full name")
        password = cols[0].text_input("Temporary password", type="password")
        role = cols[1].selectbox("Role", ("Teacher", "Admin"))
        email = cols[0].text_input("Email")
        phone = cols[1].text_input("Phone")
        if st.form_submit_button("Create user", use_container_width=True):
            if len(password) < 6:
                st.error("Password must contain at least 6 characters.")
                return
            if not username.strip() or not full_name.strip():
                st.error("Username and full name are required.")
                return
            try:
                with closing(connect()) as conn:
                    stamp = now_text()
                    conn.execute(
                        """
                        INSERT INTO users
                            (username, password_hash, full_name, role, email, phone, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            username.strip(),
                            hash_password(password),
                            full_name.strip(),
                            role,
                            email.strip(),
                            phone.strip(),
                            stamp,
                            stamp,
                        ),
                    )
                    conn.commit()
                st.success("User created.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Username already exists.")


def sidebar(user: User) -> str:
    st.sidebar.title("AT Command")
    st.sidebar.caption(f"{user.full_name} / {user.role}")
    pages = ["Dashboard", "Students", "Attendance", "Face Attendance", "Reports", "Users"]
    page = st.sidebar.radio("Navigation", pages, label_visibility="collapsed")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    return page


def app() -> None:
    st.set_page_config(page_title="Attendance Tracker", page_icon="AT", layout="wide")
    load_css()
    init_db()
    user = current_user()
    if not user:
        login_screen()
        return

    page = sidebar(user)
    if page == "Dashboard":
        dashboard()
    elif page == "Students":
        student_management(user)
    elif page == "Attendance":
        attendance_page(user)
    elif page == "Face Attendance":
        face_attendance_page(user)
    elif page == "Reports":
        reports_page()
    elif page == "Users":
        users_page(user)


def main() -> None:
    try:
        app()
    except Exception as exc:
        st.error("The application could not complete that action. Please check your data and try again.")
        with st.expander("Technical details"):
            st.code(str(exc))


if __name__ == "__main__":
    main()
