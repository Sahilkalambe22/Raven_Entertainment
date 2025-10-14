# 🎭 Raven Entertainment - Event & Theatre Management Web App

![Django](https://img.shields.io/badge/Django-5.0+-green?style=for-the-badge&logo=django)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5-purple?style=for-the-badge&logo=bootstrap)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-informational?style=for-the-badge&logo=postgresql)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

---

## 📌 Project Overview
**Raven Entertainment** is a Django-based web application designed for **theatre and event management**.  
It offers a **user interface** for browsing events, viewing details, and seat booking,  
and an **admin interface** for event management, ticket QR analysis, finances, and sponsor details.

---

## ✨ Features

### 🎟 User Side
- Browse theatre events with detailed descriptions.
- View available and booked seats in real-time.
- Seat booking system (similar to BookMyShow, but for single-show at a time).
- Access portfolio and services of the company.

### 🛠 Admin Side
- Manage events (CRUD operations).
- Media & storage management for each event.
- Finance management and sponsor details.
- QR code-based ticket scanning & analysis.
- Event statistics & data visualization.

---

## 📂 Tech Stack
- **Backend:** Django 5.0+, Python 3.10
- **Frontend:** HTML5, CSS3, Bootstrap 5, JavaScript
- **Database:** PostgreSQL / SQLite (dev mode)
- **Others:** QRCode, WeasyPrint for PDF generation

---

## 📸 Screenshots

> Replace these placeholders with your actual project screenshots from the `/screenshots` folder.

**User Interface**
![User Interface](screenshots/user-ui.png)

**Admin Dashboard**
![Admin Interface](screenshots/admin-ui.png)

**Seat Booking System**
![Seat Booking](screenshots/seat-booking.png)

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/raven-entertainment.git
cd raven-entertainment


### 2️⃣ Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate   # On Mac/Linux
venv\Scripts\activate      # On Windows



python manage.py migrate
python manage.py runserver




## 👨‍💻 Authors
- **Your Name** - *Full Stack Development* - [GitHub](https://github.com/YOUR_USERNAME)
