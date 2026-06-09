# USER MANUAL

# Attendance Tracker

## 1. Introduction

Attendance Tracker is a simple application designed to help administrators, teachers, and trainers efficiently manage student attendance records. The system allows users to add students, record attendance, and generate attendance reports.

---

## 2. System Requirements

### Hardware Requirements

* Computer or Laptop
* Minimum 4 GB RAM
* Internet connection (optional)

### Software Requirements

* Python 3.8 or above
* Required Python libraries
* Web browser (Chrome, Firefox, Edge)

---

## 3. Installation Guide

### Step 1: Clone the Repository

```bash
git clone <repository-url>
```

### Step 2: Navigate to the Project Directory

```bash
cd attendance-tracker
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Run the Application

```bash
python app.py
```

---

## 4. Application Features

### Student Management

* Add student records
* Edit student information
* Delete student records
* Search students

### Attendance Management

* Mark attendance
* Update attendance records
* View attendance history

### Reporting

* Generate attendance reports
* Calculate attendance percentages
* View attendance summaries

---

## 5. How to Use

### Adding a Student

1. Open the application.
2. Navigate to the **Students** section.
3. Click **Add Student**.
4. Enter student details.
5. Click **Save**.

### Marking Attendance

1. Navigate to the **Attendance** section.
2. Select the date.
3. Choose the student.
4. Mark as:

   * Present
   * Absent
5. Save the attendance record.

### Viewing Attendance Records

1. Open the **Reports** section.
2. Select a student.
3. View attendance history and percentage.

### Generating Reports

1. Navigate to **Reports**.
2. Select the desired date range.
3. Click **Generate Report**.
4. View or download the report.

---

## 6. User Roles

### Administrator

* Manage student records
* Access all attendance data
* Generate reports

### Teacher/Trainer

* Mark attendance
* View attendance records
* Generate attendance summaries

---

## 7. Troubleshooting

### Application Not Starting

* Verify Python is installed.
* Check all dependencies are installed.
* Run:

```bash
pip install -r requirements.txt
```

### Attendance Not Saving

* Verify database connectivity.
* Refresh the application.
* Check input fields for errors.

### Missing Student Records

* Confirm records were saved successfully.
* Verify database files are available.

---

## 8. Frequently Asked Questions

### Can attendance be edited?

Yes. Authorized users can update attendance records.

### Can reports be generated?

Yes. Attendance reports can be generated at any time.

### Is student data stored securely?

Yes. Data is stored within the configured database.

---

## 9. Future Enhancements

* QR Code Attendance
* Face Recognition Attendance
* Mobile Application
* Email Notifications
* Analytics Dashboard

---

## 10. Support

For technical support, bug reports, or feature requests, contact the project team or create an issue in the project repository.

---

**Version:** 1.0

**Project:** Attendance Tracker

**Prepared For:** Internship / Hackathon Project Documentation
