# 🏫 School Management System (LMS)

A powerful, full-stack Django-based Learning Management System (LMS) designed for schools to manage academic activities with ease.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Django](https://img.shields.io/badge/Django-5.0-green?logo=django)
![License](https://img.shields.io/badge/License-MIT-blue.svg)

---

## 🚀 Features

- 🎓 **Student & Staff Dashboards**
- 📚 **Subjects, Classes, Departments**
- 📝 **Timetables + Dynamic Calendars (FullCalendar)**
- 📥 **Assignment Upload & Submission**
- ✅ **Staff Grading + In-app Notifications**
- 🧪 **Auto-Graded Quiz System with Timer**
- 📅 **Academic Event Calendar (Exams, Holidays, Results)**
- 🔔 **Real-time Notifications using Django Signals**
- 📱 **Mobile-ready Frontend (responsive layout)**

---

## 📂 Tech Stack

| Tech | Purpose |
|------|---------|
| 🐍 Python 3.11 | Backend language |
| 🌿 Django 5.x | Web framework |
| 🧩 Django REST Framework | API layer |
| 🗃️ SQLite / PostgreSQL | Database |
| 📊 FullCalendar JS | Dynamic schedules |
| 📱 Bootstrap 5 | Frontend styling |
| 🔔 Django-Notifications | In-app alerts |

---

## 🏗️ Project Structure

school-management-lms/
│
├── schoolapp/ # Main Django app
│ ├── views/ # All views (student, staff, admin)
│ ├── models.py # Data models
│ ├── urls.py
│ ├── templates/
│
├── static/ # CSS, JS, images
├── media/ # Uploaded files
├── api/ # Optional API (DRF)
│
├── manage.py
└── requirements.txt
