# Attendance Tracker Acceptance Criteria

## Student Management
- AC-1: Admin can create a student record with first name, last name, roll number, class, and contact information.
- AC-2: Admin can edit student details and save changes.
- AC-3: Admin can archive students to remove them from active attendance workflows.
- AC-4: Search returns student results matching name, roll number, class, or section.

## Attendance Management
- AC-5: Teacher can mark attendance for each student in the selected class and date.
- AC-6: Duplicate attendance for the same student and date is blocked.
- AC-7: Teacher can edit existing attendance entries and save revisions.
- AC-8: Attendance history displays correct status values for selected students.

## Report Generation
- AC-9: The system generates reports for a chosen date range and student/class filter.
- AC-10: Attendance percentage is calculated accurately based on Present and Absent counts.
- AC-11: Reports include summaries of total present, total absent, and attendance rate.
- AC-12: Admin and Teacher roles have access only to authorized report data.

## Authentication and Security
- AC-13: Users must authenticate with a valid username and password.
- AC-14: Admin-only endpoints and views are inaccessible to Teachers.
- AC-15: Passwords are stored hashed and not exposed in responses.
- AC-16: Sessions expire after a defined inactivity period.

## User Interface and Validation
- AC-17: The UI is responsive on desktop and tablet devices.
- AC-18: Input forms display validation errors clearly.
- AC-19: Successful actions show confirmation feedback.
- AC-20: Failed actions return meaningful error messages.

## Success Conditions
- SC-1: Core workflows complete without system errors.
- SC-2: Reports are generated in a timely manner.
- SC-3: Users can perform role-specific tasks without unauthorized access.
- SC-4: Data persists reliably across workflows.
