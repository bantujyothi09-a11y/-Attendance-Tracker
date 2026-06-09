# Attendance Tracker Requirements

## Functional Requirements
- FR-1: Admin users can add new students with personal and academic details.
- FR-2: Admin users can edit student profiles and update contact information.
- FR-3: Admin users can archive or remove student records.
- FR-4: Teachers can mark student attendance for selected dates.
- FR-5: The system must support attendance statuses: Present, Absent, Excused.
- FR-6: Teachers can update attendance records after submission.
- FR-7: The system prevents duplicate attendance entries for the same student and date.
- FR-8: Admin and Teacher users can search for students by name, roll number, class, or section.
- FR-9: The system can generate attendance reports filtered by date range, student, and class.
- FR-10: The system calculates attendance percentages automatically.
- FR-11: Admin users can manage teacher user accounts.
- FR-12: Users must authenticate with username and password.
- FR-13: The application must support secure logout and session expiration.

## Non-Functional Requirements
- NFR-1: The application must load pages within 2 seconds under normal usage.
- NFR-2: Attendance submission latency should remain under 1 second for typical use.
- NFR-3: Report queries must return within 3 seconds for average data sets.
- NFR-4: The application must use secure password storage with hashing.
- NFR-5: All production traffic must use HTTPS.
- NFR-6: The UI should be responsive and work on desktops, tablets, and laptops.
- NFR-7: The system must log errors and significant user actions.
- NFR-8: The system should remain available 99% during business hours.

## Business Rules
- BR-1: Only Admin users may create or delete student and user records.
- BR-2: Teachers may only mark attendance for students assigned to their class or section.
- BR-3: Attendance records are unique per student and date.
- BR-4: Attendance percentages are based on recorded Present and Absent statuses.
- BR-5: Archived student records are excluded from active attendance entry lists.
- BR-6: Reports display data only for the current school session or selected range.

## Constraints
- C-1: The MVP must be completed within the internship or hackathon time frame.
- C-2: The application must use a relational database.
- C-3: No external Single Sign-On (SSO) provider is required for phase 1.
- C-4: The system must operate on standard web browsers without plugins.
- C-5: Data export may be limited to CSV and printable formats for the first release.
