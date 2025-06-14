﻿# Hospital Management System

## Overview
The **Hospital Management System** is a comprehensive solution for managing hospital operations, including patient registration, appointment booking, OPD and IPD management, billing, and more. This software is designed to streamline workflows, improve patient care, and ensure efficient hospital administration.

## Features
- **Patient Management:**
  - Registration with unique patient code generation
  - Profile management
  - Emergency case handling

- **Appointment & OPD Management:**
  - Online appointment booking with token system
  - Automatic OPD assignment for confirmed appointments
  - Admit patients from OPD to IPD

- **IPD Management:**
  - Multiple beds per room with different pricing
  - Total cost calculation based on stay duration
  - Prescription and regular checkups management
  - NICU daily monitoring chart (day-wise record keeping)

- **Billing System:**
  - Expense tracking for each patient
  - Invoice generation and printing

- **Additional Modules:**
  - License Updates and Renewal Management
  - Hospital Asset & Machine Substore Management
  - Maintenance Management

## Installation
### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Django & required dependencies
- PostgreSQL or MySQL database

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/hospital-management.git
   cd hospital-management
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure `.env` file with database credentials.
5. Apply migrations:
   ```bash
   1. python manage.py makemigrations
   2. python manage.py migrate
   ```
6. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```
7. Run the development server:
   ```bash
   python manage.py runserver
   ```
8. (Optional) Run using Docker:
   ```bash
   docker-compose up --build
   ```

## Usage
1. Login as an admin at `http://127.0.0.1:8000/admin/`
2. Register patients, book appointments, and manage hospital operations.
3. Use the billing system to generate and print invoices.

## Technologies Used
- **Backend:** Django, Django REST Framework
- **Frontend:** HTML, CSS, JavaScript (or React if applicable)
- **Database:** PostgreSQL/MySQL
- **Containerization:** Docker, Gunicorn

## Contributing
Contributions are welcome! Follow these steps:
1. Fork the repository.
2. Create a feature branch.
3. Commit changes and push to your fork.
4. Create a pull request.

## License
This project is licensed under the MIT License.

## Contact
For any queries, contact us at `support@yourhospital.com`.

