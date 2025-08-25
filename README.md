# 🎓 LMS School Management System

A modern **Learning Management System (LMS)** built with Django, designed for schools to manage students, staff, classes, sessions, quizzes, and communication in one unified platform.  
Clean UI, real-time messaging, and AI-powered quiz grading make this system stand out from traditional LMS platforms.

---

## ✨ Features

### 🔑 Authentication & Profiles
- Role-based login system (**Admin, Staff, Student**).
- Each role has its own **custom dashboard**.
- User profile pages with profile pictures.

### 💬 Real-Time Feedback & Communication
- **Student → Admin** feedback messaging with notifications system (chat-bubble UI).
- **Staff → Admin** feedback messaging with notifications system (chat-bubble UI).
- **Admin → Staff/Students** threaded conversations.
- Sidebar shows scrollable list of users with:
  - Latest activity
  - Add Sessions (Here you add students, staffs, Session Year, Time Table, and more...)
  - manage Sessions (Here you manage students, staffs, Session Year, Time Table, and more...)
  - Feedback Real-Time Messaging
  - Message count indicators
- Smooth **AJAX-powered chat** (no page reload).

### 📚 Exams & Assessments
- Staff create Exams for their subjects.
- Two question types supported:
  - ✅ Multiple Choice (MCQs) – Options A–D
  - ✅ Short Answer – Students type answers
- Exam options:
  - Title, Instructions, Subject, Class, Department, Session
  - Deadline, Duration, Start/End time
  - Status: **Draft / Published**
- **Automatic Grading**:
  - MCQs graded instantly
  - **AI-powered grading** for open-ended answers (OpenAI GPT integration)
- Staff can **add/edit/delete** questions.
- Admin can view **all staff Exams** with teacher info, subject, deadlines, status.
- Direct links to send **feedback messages** to staff about their quizzes.

### 🏫 Admin Management
- Full CRUD for **Students, Staff, Classes, Departments, Sessions**.
- Read-only access to quiz details.
- Direct communication with staff/students.

### ⚡ Extra Features / Upcoming
- Sidebar notifications with unread counts.
- WhatsApp-style chat bubble interface.
- Section switching for staff/students.
- SaaS-ready for multi-school hosting.

---

## 🖼️ Screenshots

> _(Add your project screenshots here for max impact)_

- **Login Page**
- **Admin Dashboard**
- **Staff Quiz Creation**
- **Student Quiz Attempt**
- **Chat System with Notifications**

---

## 🚀 Tech Stack

- **Backend**: Django, Django ORM  
- **Frontend**: HTML5, CSS3, Bootstrap, JavaScript (AJAX)  
- **Database**: PostgreSQL / MySQL  
- **AI Grading**: OpenAI GPT API  
- **Hosting Ready**: Heroku, DigitalOcean, AWS, or Render  

---

