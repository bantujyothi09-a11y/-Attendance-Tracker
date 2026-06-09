# Attendance Tracker Database Specification

## Entity Definitions
- Students: Stores student demographics and academic details.
- Attendance: Stores daily attendance records and status.
- Users: Stores credentials and role information for Admin and Teacher accounts.

## Relationships
- A Student can have many Attendance records.
- A User can mark many Attendance records.
- Attendance belongs to a single Student and is associated with the User who recorded it.

## Database Schema
### Students Table
| Column | Type | Description |
| --- | --- | --- |
| id | integer / UUID | Primary key |
| first_name | string | Student first name |
| last_name | string | Student last name |
| roll_number | string | Unique identifier |
| class | string | Academic class or grade |
| section | string | Section or group |
| enrollment_date | date | Student enrollment date |
| contact_number | string | Phone number |
| email | string | Optional contact email |
| status | string | Active / archived |
| created_at | datetime | Created timestamp |
| updated_at | datetime | Last updated timestamp |

### Attendance Table
| Column | Type | Description |
| --- | --- | --- |
| id | integer / UUID | Primary key |
| student_id | integer / UUID | Foreign key to Students.id |
| attendance_date | date | Date of attendance |
| status | string | Present / Absent / Excused |
| marked_by | integer / UUID | Foreign key to Users.id |
| remarks | text | Optional notes |
| created_at | datetime | Created timestamp |
| updated_at | datetime | Last updated timestamp |

### Users Table
| Column | Type | Description |
| --- | --- | --- |
| id | integer / UUID | Primary key |
| username | string | Unique login name |
| password_hash | string | Hashed password |
| full_name | string | User full name |
| role | string | Admin / Teacher |
| email | string | Contact email |
| phone | string | Optional phone number |
| created_at | datetime | Created timestamp |
| updated_at | datetime | Last updated timestamp |
| last_login | datetime | Most recent login timestamp |

## ER Diagram Description
The ER diagram contains three core entities:
- `Students` connects to `Attendance` through a one-to-many relationship.
- `Users` connects to `Attendance` through a one-to-many relationship for recorded entries.
- `Attendance` is the junction entity containing attendance status and metadata.

This schema supports auditability, percentage calculation, and role-aware attendance operations.
