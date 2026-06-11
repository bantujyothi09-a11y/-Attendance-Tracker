import importlib
import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app


class AttendanceTrackerCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = app.DB_PATH
        app.DB_PATH = Path(self.temp_dir.name) / "attendance.db"
        app.init_db()

    def tearDown(self):
        app.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def test_seeded_admin_login_uses_hashed_password(self):
        user = app.get_user_by_credentials("admin", "admin123")
        self.assertIsNotNone(user)
        self.assertEqual(user.role, "Admin")

        row = app.fetch_one("SELECT password_hash FROM users WHERE username = ?", ("admin",))
        self.assertNotEqual(row["password_hash"], "admin123")
        self.assertIn("$", row["password_hash"])

    def test_old_naive_session_timestamp_is_normalized(self):
        old_value = app.datetime(2026, 6, 11, 12, 0, 0)
        normalized = app.normalize_last_seen(old_value)
        self.assertIsNotNone(normalized)
        self.assertIs(normalized.tzinfo, app.UTC)

    def test_missing_user_does_not_clear_login_widget_state(self):
        from unittest.mock import patch

        fake_state = {"Username": "admin"}
        with patch.object(app.st, "session_state", fake_state):
            self.assertIsNone(app.current_user())
        self.assertEqual(fake_state["Username"], "admin")

    def test_duplicate_attendance_is_prevented_by_unique_constraint(self):
        with app.closing(app.connect()) as conn:
            student_id = conn.execute("SELECT id FROM students LIMIT 1").fetchone()["id"]
            user_id = conn.execute("SELECT id FROM users WHERE username = 'teacher'").fetchone()["id"]
            stamp = app.now_text()
            values = (student_id, "2026-06-11", "Present", user_id, "", stamp, stamp)
            conn.execute(
                """
                INSERT INTO attendance
                    (student_id, attendance_date, status, marked_by, remarks, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            with self.assertRaises(app.sqlite3.IntegrityError):
                conn.execute(
                    """
                    INSERT INTO attendance
                        (student_id, attendance_date, status, marked_by, remarks, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )

    def test_report_percentage_excludes_excused_from_denominator(self):
        row = {
            "roll_number": "AT-001",
            "student": "Aarav Sharma",
            "class_name": "10",
            "section": "A",
            "present": 3,
            "absent": 1,
            "excused": 5,
            "total_records": 9,
        }
        result = app.row_with_percentage(row)
        self.assertEqual(result["attendance_percentage"], 75.0)

    def test_face_hash_matches_identical_reference(self):
        image_bytes = BytesIO()
        Image.new("RGB", (80, 80), color=(120, 170, 210)).save(image_bytes, format="PNG")
        image_bytes.seek(0)
        image_hash = app.image_to_hash(image_bytes)

        with app.closing(app.connect()) as conn:
            student_id = conn.execute("SELECT id FROM students LIMIT 1").fetchone()["id"]
            stamp = app.now_text()
            conn.execute(
                """
                INSERT INTO face_profiles (student_id, image_hash, image_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (student_id, image_hash, "face_data/test.png", stamp, stamp),
            )
            conn.commit()

        match, confidence, distance = app.find_face_match(image_hash)
        self.assertIsNotNone(match)
        self.assertEqual(distance, 0)
        self.assertEqual(confidence, 100.0)


if __name__ == "__main__":
    unittest.main()
