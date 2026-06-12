from __future__ import annotations

import csv
import hashlib
import hmac
import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from io import BytesIO, StringIO
from pathlib import Path
from typing import Iterable

import streamlit as st
from PIL import Image, ImageDraw, ImageOps
from translations import LANGUAGE_OPTIONS, translations


APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "database" / "attendance.db"
FACE_DIR = APP_DIR / "face_data"
STYLE_PATH = APP_DIR / "static" / "style.css"
SESSION_TIMEOUT_MINUTES = 45
ATTENDANCE_STATUSES = ("Present", "Absent", "Excused")
STATUS_KEYS = {"Present": "present", "Absent": "absent", "Excused": "excused"}
STUDENT_STATUS_KEYS = {"Active": "active", "Archived": "archived"}
ROLE_KEYS = {"Admin": "admin", "Teacher": "teacher"}
COLUMN_KEYS = {
    "id": "col_id",
    "first_name": "col_first_name",
    "last_name": "col_last_name",
    "roll_number": "col_roll_number",
    "student": "col_student",
    "class": "col_class",
    "class_name": "col_class_name",
    "section": "col_section",
    "attendance_date": "col_attendance_date",
    "status": "col_status",
    "marked_by": "col_marked_by",
    "enrollment_date": "col_enrollment_date",
    "contact_number": "col_contact_number",
    "email": "col_email",
    "present": "col_present",
    "absent": "col_absent",
    "excused": "col_excused",
    "total": "col_total",
    "total_records": "col_total_records",
    "attendance_percentage": "col_attendance_percentage",
    "username": "col_username",
    "full_name": "col_full_name",
    "role": "col_role",
    "phone": "col_phone",
    "last_login": "col_last_login",
}


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


def init_language() -> None:
    if "language" not in st.session_state:
        st.session_state.language = "en"


def t(key: str) -> str:
    return translations[st.session_state.language][key]


def language_selector(location=st.sidebar) -> None:
    init_language()
    current_label = next(label for label, code in LANGUAGE_OPTIONS.items() if code == st.session_state.language)
    selected_label = location.selectbox(
        t("language_label"),
        list(LANGUAGE_OPTIONS.keys()),
        index=list(LANGUAGE_OPTIONS.keys()).index(current_label),
        format_func=lambda label: translations[LANGUAGE_OPTIONS[label]][
            {"English": "english", "हिन्दी": "hindi", "తెలుగు": "telugu"}[label]
        ],
    )
    st.session_state.language = LANGUAGE_OPTIONS[selected_label]


def clear_session_keep_language() -> None:
    language = st.session_state.get("language", "en")
    st.session_state.clear()
    st.session_state.language = language


def translate_status(status: str) -> str:
    return t(STATUS_KEYS.get(status, status.lower()))


def translate_student_status(status: str) -> str:
    return t(STUDENT_STATUS_KEYS.get(status, status.lower()))


def translate_role(role: str) -> str:
    return t(ROLE_KEYS.get(role, role.lower()))


def localize_row(row: dict) -> dict:
    localized = {}
    for key, value in row.items():
        column = t(COLUMN_KEYS[key]) if key in COLUMN_KEYS else key
        if key == "status" and value in STATUS_KEYS:
            value = translate_status(value)
        elif key == "status" and value in STUDENT_STATUS_KEYS:
            value = translate_student_status(value)
        elif key == "role" and value in ROLE_KEYS:
            value = translate_role(value)
        localized[column] = value
    return localized


def localize_rows(rows: Iterable[dict | sqlite3.Row]) -> list[dict]:
    return [localize_row(dict(row)) for row in rows]


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


def demo_face_image(student: sqlite3.Row | dict) -> BytesIO:
    seed = int(hashlib.sha256(str(student["id"]).encode()).hexdigest()[:8], 16)
    bg = (55 + ((seed >> 16) % 90), 70 + ((seed >> 8) % 80), 80 + (seed % 85))
    accent = (80 + ((seed >> 12) % 120), 90 + ((seed >> 4) % 100), 100 + ((seed >> 20) % 90))
    image = Image.new("RGB", (256, 256), bg)
    draw = ImageDraw.Draw(image)
    draw.ellipse((54, 34, 202, 206), fill=(224, 181, 136), outline=accent, width=7)
    draw.ellipse((88, 96, 108, 116), fill=(30, 35, 45))
    draw.ellipse((148, 96, 168, 116), fill=(30, 35, 45))
    draw.arc((92, 122, 164, 174), 15, 165, fill=(90, 55, 50), width=5)
    draw.rectangle((70, 54, 186, 76), fill=accent)
    initials = f"{student['first_name'][:1]}{student['last_name'][:1]}".upper()
    draw.text((104, 210), initials, fill=(255, 255, 255))
    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return output


def create_demo_face_profiles() -> int:
    students = student_options(active_only=True)
    created = 0
    with closing(connect()) as conn:
        stamp = now_text()
        for student in students:
            image_file = demo_face_image(student)
            image_hash = image_to_hash(image_file)
            image_path = save_face_reference(student["id"], image_file)
            conn.execute(
                """
                INSERT INTO face_profiles (student_id, image_hash, image_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(student_id)
                DO UPDATE SET image_hash = excluded.image_hash,
                              image_path = excluded.image_path,
                              updated_at = excluded.updated_at
                """,
                (student["id"], image_hash, image_path, stamp, stamp),
            )
            created += 1
        conn.commit()
    return created


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
        clear_session_keep_language()
        st.warning(t("session_expired"))
        return None
    st.session_state.last_seen = datetime.now(UTC)
    return User(**user_data)


def login_screen() -> None:
    language_selector()
    st.markdown('<div class="app-shell">', unsafe_allow_html=True)
    st.markdown(f'<div class="section-label">{t("login_kicker")}</div>', unsafe_allow_html=True)
    st.markdown(f'<h1 class="app-title">{t("login_title_html")}</h1>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="app-subtitle">{t("login_subtitle")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="status-strip">
          <span class="status-chip">{t("sqlite_online")}</span>
          <span class="status-chip">{t("role_access_enabled")}</span>
          <span class="status-chip">{t("reports_ready")}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input(t("username"), value="admin")
        password = st.text_input(t("password"), type="password", value="admin123")
        submitted = st.form_submit_button(t("sign_in"), use_container_width=True)

    st.markdown(
        f'<div class="notice">{t("demo_accounts")}</div>',
        unsafe_allow_html=True,
    )

    if submitted:
        user = get_user_by_credentials(username, password)
        if user:
            st.session_state.user = user.__dict__
            st.session_state.last_seen = datetime.now(UTC)
            st.rerun()
        st.error(t("invalid_login"))
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
        t("mission_control"),
        t("dashboard_title_html"),
        t("dashboard_copy"),
        (t("live_sqlite_telemetry"), t("session_protected"), t("csv_export_armed")),
    )
    st.markdown(
        f"""
        <div class="metric-row">
          <div class="metric-tile"><strong>{totals['active_students']}</strong><span>{t("active_students")}</span></div>
          <div class="metric-tile"><strong>{totals['today_records']}</strong><span>{t("marked_today")}</span></div>
          <div class="metric-tile"><strong>{rate}%</strong><span>{t("overall_attendance")}</span></div>
          <div class="metric-tile"><strong>{totals['users']}</strong><span>{t("system_users")}</span></div>
        </div>
        <div class="signal-grid">
          <div class="signal-card">
            <div class="signal-title">{t("attendance_signal_strength")}</div>
            <div class="signal-bar"><div class="signal-fill" style="width: {max(4, min(rate, 100))}%;"></div></div>
          </div>
          <div class="signal-card">
            <div class="signal-title">{t("system_mode")}</div>
            <strong>{t("operational")}</strong><br><span style="color: var(--muted);">{t("core_agents_responding")}</span>
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
    st.subheader(t("recent_attendance"))
    st.dataframe(localize_rows(recent), use_container_width=True, hide_index=True)


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
        t("student_matrix"),
        t("student_records_title_html"),
        t("student_records_copy"),
        (
            t("admin_write_access") if user.role == "Admin" else t("teacher_read_only"),
            t("indexed_search"),
            t("active_archive_flow"),
        ),
    )

    if user.role != "Admin":
        st.info(t("teacher_student_readonly"))

    search = st.text_input(t("search_student"), placeholder=t("search_student_placeholder"))
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
    st.dataframe(localize_rows(rows), use_container_width=True, hide_index=True)

    if user.role != "Admin":
        return

    tab_add, tab_edit = st.tabs([t("add_student"), t("edit_or_archive")])
    with tab_add:
        with st.form("add_student"):
            cols = st.columns(2)
            first_name = cols[0].text_input(t("first_name"))
            last_name = cols[1].text_input(t("last_name"))
            roll_number = cols[0].text_input(t("roll_number"))
            class_name = cols[1].text_input(t("class"))
            section = cols[0].text_input(t("section"))
            enrollment_date = cols[1].date_input(t("enrollment_date"), value=date.today())
            contact_number = cols[0].text_input(t("contact_number"))
            email = cols[1].text_input(t("email"))
            if st.form_submit_button(t("create_student"), use_container_width=True):
                if not all([first_name.strip(), last_name.strip(), roll_number.strip(), class_name.strip(), section.strip()]):
                    st.error(t("required_student_fields"))
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
                        st.success(t("student_created"))
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error(t("roll_number_exists"))

    with tab_edit:
        all_students = student_options(active_only=False)
        if not all_students:
            st.info(t("no_students_available"))
            return
        student_lookup = {row["id"]: row for row in all_students}
        selected = st.selectbox(
            t("select_student"),
            list(student_lookup.keys()),
            format_func=lambda student_id: (
                f"{student_lookup[student_id]['roll_number']} - "
                f"{student_lookup[student_id]['first_name']} {student_lookup[student_id]['last_name']} "
                f"({translate_student_status(student_lookup[student_id]['status'])})"
            ),
        )
        detail = fetch_one("SELECT * FROM students WHERE id = ?", (selected,))
        if not detail:
            st.warning(t("selected_student_not_found"))
            return

        with st.form("edit_student"):
            cols = st.columns(2)
            first_name = cols[0].text_input(t("first_name"), value=detail["first_name"])
            last_name = cols[1].text_input(t("last_name"), value=detail["last_name"])
            roll_number = cols[0].text_input(t("roll_number"), value=detail["roll_number"])
            class_name = cols[1].text_input(t("class"), value=detail["class_name"])
            section = cols[0].text_input(t("section"), value=detail["section"])
            enrollment_date = cols[1].date_input(t("enrollment_date"), value=date.fromisoformat(detail["enrollment_date"]))
            contact_number = cols[0].text_input(t("contact_number"), value=detail["contact_number"] or "")
            email = cols[1].text_input(t("email"), value=detail["email"] or "")
            status = st.selectbox(
                t("status"),
                ("Active", "Archived"),
                index=0 if detail["status"] == "Active" else 1,
                format_func=translate_student_status,
            )
            if st.form_submit_button(t("save_changes"), use_container_width=True):
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
                    st.success(t("student_updated"))
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error(t("roll_number_exists"))


def attendance_page(user: User) -> None:
    page_header(
        t("capture_grid"),
        t("mark_attendance_title_html"),
        t("mark_attendance_copy"),
        (t("present"), t("absent"), t("excused")),
    )

    classes = fetch_all(
        "SELECT DISTINCT class_name, section FROM students WHERE status = 'Active' ORDER BY class_name, section"
    )
    if not classes:
        st.info(t("add_active_students_attendance"))
        return

    class_options = {f"{row['class_name']}|||{row['section']}": row for row in classes}
    class_key = st.selectbox(
        t("class_and_section"),
        list(class_options.keys()),
        format_func=lambda key: f"{class_options[key]['class_name']} - {class_options[key]['section']}",
    )
    class_choice = class_options[class_key]
    selected_date = st.date_input(t("attendance_date"), value=date.today())

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
                t("status"),
                ATTENDANCE_STATUSES,
                index=ATTENDANCE_STATUSES.index(current_status),
                key=f"status_{student['id']}",
                label_visibility="collapsed",
                format_func=translate_status,
            )
            remarks = cols[2].text_input(
                t("remarks"),
                value=student["existing_remarks"] or "",
                key=f"remarks_{student['id']}",
                label_visibility="collapsed",
                placeholder=t("optional_remarks"),
            )
            entries.append((student["id"], status, remarks))

        submitted = st.form_submit_button(t("save_attendance"), use_container_width=True)

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
        st.success(t("attendance_saved"))
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
        st.subheader(t("daily_summary"))
        st.dataframe(localize_rows(summary), use_container_width=True, hide_index=True)


def face_attendance_page(user: User) -> None:
    page_header(
        t("vision_gate"),
        t("face_attendance_title_html"),
        t("face_attendance_copy"),
        (t("camera_capture"), t("face_profile_registry"), t("auto_present_marking")),
    )

    registered = fetch_one("SELECT COUNT(*) AS total FROM face_profiles")
    active_students = fetch_one("SELECT COUNT(*) AS total FROM students WHERE status = 'Active'")
    st.markdown(
        f"""
        <div class="metric-row">
          <div class="metric-tile"><strong>{registered['total']}</strong><span>{t("face_profiles")}</span></div>
          <div class="metric-tile"><strong>{active_students['total']}</strong><span>{t("active_students")}</span></div>
          <div class="metric-tile"><strong>{t("present")}</strong><span>{t("recognition_result")}</span></div>
          <div class="metric-tile"><strong>{t("secure")}</strong><span>{t("stored_as_image_fingerprint")}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    enroll_tab, scan_tab = st.tabs([t("register_face"), t("scan_attendance")])

    with enroll_tab:
        if registered["total"] == 0 and user.role == "Admin":
            st.info(t("demo_profiles_help"))
            if st.button(t("create_demo_face_profiles"), use_container_width=True):
                count = create_demo_face_profiles()
                st.success(t("demo_profiles_created").format(count=count))
                st.rerun()
        if user.role != "Admin":
            st.info(t("admin_face_only"))
        students = student_options(active_only=True)
        if not students:
            st.warning(t("add_active_students_faces"))
        else:
            student_lookup = {row["id"]: row for row in students}
            selected = st.selectbox(
                t("student"),
                list(student_lookup.keys()),
                format_func=lambda student_id: (
                    f"{student_lookup[student_id]['roll_number']} - "
                    f"{student_lookup[student_id]['first_name']} {student_lookup[student_id]['last_name']} "
                    f"({student_lookup[student_id]['class_name']}-{student_lookup[student_id]['section']})"
                ),
                key="face_register_student",
            )
            source = st.radio(
                t("reference_image_source"),
                ("Camera", "Upload"),
                horizontal=True,
                key="face_register_source",
                format_func=lambda value: t("camera") if value == "Camera" else t("upload"),
            )
            image_file = (
                st.camera_input(t("capture_student_face"), key="face_register_camera")
                if source == "Camera"
                else st.file_uploader(t("upload_student_face_image"), type=("jpg", "jpeg", "png"), key="face_register_upload")
            )

            if st.button(t("save_face_profile"), disabled=user.role != "Admin" or image_file is None, use_container_width=True):
                try:
                    image_hash = image_to_hash(image_file)
                    image_path = save_face_reference(selected, image_file)
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
                            (selected, image_hash, image_path, stamp, stamp),
                        )
                        conn.commit()
                    st.success(t("face_profile_saved"))
                    st.rerun()
                except Exception as exc:
                    st.error(t("face_image_save_error"))
                    st.caption(str(exc))

    with scan_tab:
        selected_date = st.date_input(t("attendance_date"), value=date.today(), key="face_scan_date")
        scan_sources = ("Camera", "Upload", "Demo")
        source = st.radio(
            t("scan_image_source"),
            scan_sources,
            horizontal=True,
            key="face_scan_source",
            format_func=lambda value: {"Camera": t("camera"), "Upload": t("upload"), "Demo": t("demo")}[value],
        )
        demo_student = None
        if source == "Camera":
            scan_file = st.camera_input(t("capture_face_attendance"), key="face_scan_camera")
        elif source == "Upload":
            scan_file = st.file_uploader(t("upload_face_attendance"), type=("jpg", "jpeg", "png"), key="face_scan_upload")
        else:
            students = student_options(active_only=True)
            student_lookup = {row["id"]: row for row in students}
            demo_student_id = None
            demo_student = st.selectbox(
                t("demo_face_scan_student"),
                list(student_lookup.keys()),
                format_func=lambda student_id: (
                    f"{student_lookup[student_id]['roll_number']} - "
                    f"{student_lookup[student_id]['first_name']} {student_lookup[student_id]['last_name']}"
                ),
                key="face_demo_student",
            )
            demo_student_id = demo_student
            demo_student = student_lookup[demo_student_id] if demo_student_id else None
            scan_file = demo_face_image(demo_student) if demo_student else None
            if scan_file:
                st.image(scan_file, caption=t("demo_face_preview"), width=180)

        if st.button(t("recognize_mark_present"), disabled=scan_file is None, use_container_width=True):
            try:
                if source == "Demo" and demo_student:
                    scan_file = demo_face_image(demo_student)
                scan_file.seek(0)
                scan_hash = image_to_hash(scan_file)
                match, confidence, distance = find_face_match(scan_hash)
                if not match:
                    st.error(t("no_face_match").format(confidence=confidence))
                    st.caption(t("distance_score_hint").format(distance=distance))
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
                            t("marked_by_face").format(confidence=confidence),
                            stamp,
                            stamp,
                        ),
                    )
                    conn.commit()

                st.success(
                    t("face_marked_success").format(
                        status=t("present"),
                        student=match["student"],
                        roll_number=match["roll_number"],
                        confidence=confidence,
                    )
                )
            except Exception as exc:
                st.error(t("face_process_error"))
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
    return "\ufeff" + output.getvalue()


def reports_page() -> None:
    page_header(
        t("analytics_core"),
        t("reports_title_html"),
        t("reports_copy"),
        (t("percentage_engine"), t("range_filters"), t("csv_export")),
    )

    cols = st.columns(4)
    start_date = cols[0].date_input(t("start_date"), value=date.today() - timedelta(days=30))
    end_date = cols[1].date_input(t("end_date"), value=date.today())
    classes = ["All"] + [row["class_name"] for row in fetch_all("SELECT DISTINCT class_name FROM students ORDER BY class_name")]
    class_filter = cols[2].selectbox(t("class"), classes, format_func=lambda value: t("all") if value == "All" else value)
    students = student_options(active_only=False)
    student_labels = {0: t("all_students")} | {
        row["id"]: f"{row['roll_number']} - {row['first_name']} {row['last_name']}" for row in students
    }
    student_id = cols[3].selectbox(t("student"), list(student_labels.keys()), format_func=student_labels.get)

    if start_date > end_date:
        st.error(t("date_validation"))
        return

    rows = [row_with_percentage(row) for row in build_report_rows(start_date, end_date, class_filter, student_id or None)]
    total_present = sum(row["present"] or 0 for row in rows)
    total_absent = sum(row["absent"] or 0 for row in rows)
    total_excused = sum(row["excused"] or 0 for row in rows)
    rate = round(total_present / (total_present + total_absent) * 100, 1) if total_present + total_absent else 0

    st.markdown(
        f"""
        <div class="metric-row">
          <div class="metric-tile"><strong>{total_present}</strong><span>{t("total_present")}</span></div>
          <div class="metric-tile"><strong>{total_absent}</strong><span>{t("total_absent")}</span></div>
          <div class="metric-tile"><strong>{total_excused}</strong><span>{t("total_excused")}</span></div>
          <div class="metric-tile"><strong>{rate}%</strong><span>{t("attendance_rate")}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    localized_rows = localize_rows(rows)
    st.dataframe(localized_rows, use_container_width=True, hide_index=True)
    csv_data = to_csv(localized_rows)
    st.download_button(
        t("download_csv"),
        data=csv_data,
        file_name=f"attendance-report-{start_date.isoformat()}-{end_date.isoformat()}.csv",
        mime="text/csv",
        disabled=not bool(rows),
        use_container_width=True,
    )


def users_page(user: User) -> None:
    page_header(
        t("admin_control"),
        t("user_access_title_html"),
        t("user_access_copy"),
        (t("password_hashing"), t("role_gates"), t("session_timeout")),
    )
    if user.role != "Admin":
        st.error(t("admin_users_only"))
        return

    rows = fetch_all("SELECT id, username, full_name, role, email, phone, last_login FROM users ORDER BY role, username")
    st.dataframe(localize_rows(rows), use_container_width=True, hide_index=True)

    with st.form("create_user"):
        cols = st.columns(2)
        username = cols[0].text_input(t("username"))
        full_name = cols[1].text_input(t("full_name"))
        password = cols[0].text_input(t("temporary_password"), type="password")
        role = cols[1].selectbox(t("role"), ("Teacher", "Admin"), format_func=translate_role)
        email = cols[0].text_input(t("email"))
        phone = cols[1].text_input(t("phone"))
        if st.form_submit_button(t("create_user"), use_container_width=True):
            if len(password) < 6:
                st.error(t("password_length_validation"))
                return
            if not username.strip() or not full_name.strip():
                st.error(t("user_required_fields"))
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
                st.success(t("user_created"))
                st.rerun()
            except sqlite3.IntegrityError:
                st.error(t("username_exists"))


def sidebar(user: User) -> str:
    language_selector()
    st.sidebar.title(t("sidebar_title"))
    st.sidebar.caption(f"{user.full_name} / {translate_role(user.role)}")
    pages = ["dashboard", "students", "attendance", "face_attendance", "reports", "users"]
    page = st.sidebar.radio(t("navigation"), pages, format_func=t, label_visibility="collapsed")
    if st.sidebar.button(t("logout"), use_container_width=True):
        clear_session_keep_language()
        st.rerun()
    return page


def app() -> None:
    init_language()
    st.set_page_config(page_title=t("app_title"), page_icon="AT", layout="wide")
    load_css()
    init_db()
    user = current_user()
    if not user:
        login_screen()
        return

    page = sidebar(user)
    if page == "dashboard":
        dashboard()
    elif page == "students":
        student_management(user)
    elif page == "attendance":
        attendance_page(user)
    elif page == "face_attendance":
        face_attendance_page(user)
    elif page == "reports":
        reports_page()
    elif page == "users":
        users_page(user)


def main() -> None:
    try:
        app()
    except Exception as exc:
        if "language" not in st.session_state:
            st.session_state.language = "en"
        st.error(t("app_error"))
        with st.expander(t("technical_details")):
            st.code(str(exc))


if __name__ == "__main__":
    main()
