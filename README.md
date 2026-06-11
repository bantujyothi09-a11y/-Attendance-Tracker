

## Overview

Attendance Tracker is a simple and efficient application designed to manage student attendance records. It enables administrators, teachers, or trainers to record attendance, monitor participation, and generate attendance reports with ease.

## Features

* Add, edit, and delete student records
* Mark daily attendance
* View attendance history
* Calculate attendance percentages automatically
* Generate attendance reports
* User-friendly interface
* Secure and organized data management

## Problem Statement

Manual attendance management is time-consuming and prone to errors. This project provides a digital solution to efficiently track attendance and maintain accurate records.

## Objectives

* Simplify attendance management
* Reduce manual errors
* Provide quick access to attendance records
* Generate attendance statistics and reports

## Technology Stack

### Frontend

* HTML
* CSS
* JavaScript

### Backend

* Python

### Database

* SQLite / CSV Storage

## Project Structure

attendance-tracker/

├── app.py

├── database/

├── templates/

├── static/

├── reports/

├── requirements.txt

└── README.md

## Installation

### Prerequisites

* Python 3.8 or above
* pip package manager

### Steps

1. Clone the repository

   git clone <repository-url>

2. Navigate to the project folder

   cd attendance-tracker

3. Install dependencies

   pip install -r requirements.txt

4. Run the application

   python app.py

5. Open the application in your browser.

## Streamlit Website Version

This repository now includes a working Streamlit website based on the Spec Kit files.

Run it with:

```bash
python -m streamlit run app.py
```

Then open:

```text
http://localhost:8501
```

Demo login accounts:

| Role | Username | Password |
| --- | --- | --- |
| Admin | admin | admin123 |
| Teacher | teacher | teacher123 |

### Face Attendance

Open `Face Attendance` from the sidebar.

1. Sign in as Admin and use `Register Face` to save a reference face image for a student.
2. Use `Scan Attendance` with camera or upload to recognize the student.
3. A successful match marks that student as `Present` for the selected date.

## Usage

### Adding Students

1. Navigate to the Students section.
2. Click Add Student.
3. Enter student details.
4. Save the information.

### Marking Attendance

1. Open the Attendance page.
2. Select the desired date.
3. Mark students as Present or Absent.
4. Save attendance records.

### Viewing Reports

1. Navigate to Reports.
2. Select a student or class.
3. View attendance summaries and percentages.

## Future Enhancements

* QR Code Attendance
* Face Recognition Attendance
* Mobile Application Support
* Email Notifications
* Cloud Database Integration
* Analytics Dashboard

## Contributors

* Project Team Members
* Internship Participants

## License

This project is developed for educational and internship purposes.
