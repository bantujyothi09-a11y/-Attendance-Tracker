# Attendance Tracker User Stories

## Administrator User Stories
- As an Administrator, I want to add new student records so that attendance can be tracked accurately.
- As an Administrator, I want to edit student profiles so that student information remains current.
- As an Administrator, I want to archive or remove students so that inactive students do not clutter active lists.
- As an Administrator, I want to manage teacher accounts so that only authorized staff can access the system.
- As an Administrator, I want to generate attendance reports so that I can review institutional attendance trends.

### Acceptance Criteria (Admin)
- Students can be created with required profile fields.
- Student edits are persisted and visible immediately.
- Archived students are excluded from active attendance lists.
- Teacher accounts can be created, updated, and disabled.
- Reports return correct attendance totals and percentages.

## Teacher User Stories
- As a Teacher, I want to mark attendance for my class so that daily records are maintained.
- As a Teacher, I want to update attendance entries to correct mistakes.
- As a Teacher, I want to view attendance history for each student so I can assess performance.
- As a Teacher, I want to search students by roll number or name so I can find records quickly.
- As a Teacher, I want to export attendance data so I can share it with administrators.

### Acceptance Criteria (Teacher)
- Attendance can be marked for the selected date and student list.
- Duplicate attendance entries for the same student and date are prevented.
- History views show student attendance status and totals.
- Search returns matching students by name, roll number, or class.
- Exported reports contain accurate attendance figures.
