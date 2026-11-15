# ClinicQ: Requirements

Version 0.1. Stack: React, Django (Django REST Framework), PostgreSQL.

## 1. Purpose

ClinicQ lets people book an appointment and follow their place in the queue from their phone, and lets a clinic's staff manage the day.

**Problem (to be confirmed with real people, see `discovery.md`):**
- People wait a long time in physical queues and do not know when it is their turn.
- Clinics lose time when people book and do not come.
- Paper registers make it hard to know who is next.

ClinicQ is built for any organization that works with appointments (clinic, office, university service). A clinic is the first example.

## 2. Users and roles

| Role | Who | Main goal |
|------|-----|-----------|
| Patient | A visitor, no account needed | Book a visit and see when it is their turn |
| Receptionist | Staff at the front desk | Manage today's list and the queue |
| Provider | Doctor or other service giver | See who is next |
| Admin | Clinic owner or manager | Set up services, providers and hours, and manage staff |

## 3. Scope

**In version 1:** staff login with roles, setup of services and providers, online booking, cancellation, reception dashboard, walk-ins, live queue page, activity log, reminder emails, French / Arabic / English.

**Not in version 1:** online payment, medical records, SMS or WhatsApp messages, video consultation, mobile apps (the web app should work well on a phone).

## 4. Functional requirements

Priority: **M** = must have, **S** = should have, **C** = could have.

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Staff log in with email and password. Each staff member has one role (receptionist, provider, admin). | M |
| FR-2 | An admin creates services, providers, working hours and slot length. | M |
| FR-3 | An admin creates and disables staff accounts. | M |
| FR-4 | A patient sees free slots by service, provider and date. | M |
| FR-5 | A patient books a slot with name and phone number and receives a booking code. | M |
| FR-6 | The system never allows two bookings for the same provider at the same time, even when two people book at the same moment. | M |
| FR-7 | A patient cancels a booking using the booking code and phone number. | M |
| FR-8 | The system rejects bookings in the past or too far ahead (default maximum 30 days, set by the admin). | M |
| FR-9 | A receptionist sees today's list of bookings. | M |
| FR-10 | A receptionist checks in a patient and marks no-shows. | M |
| FR-11 | A receptionist adds a walk-in patient to the queue. | M |
| FR-12 | A provider sees the next waiting patient and calls them. | M |
| FR-13 | A patient opens a page with their booking code and sees their position, status and estimated wait. The page refreshes by itself. | M |
| FR-14 | The system records who changed what and when (activity log). Admins can read it. | M |
| FR-15 | The system sends a reminder email 24 hours before the visit, if the patient gave an email. | S |
| FR-16 | The interface is available in French, Arabic (right to left) and English. | S |
| FR-17 | The app can be installed on a phone and shows a clear message when the internet is down. | C |

## 5. Business rules

- Slot length is between 10 and 60 minutes, set per service.
- A patient who has not arrived 15 minutes after the slot start can be marked as a no-show (the grace time can be changed by the admin).
- Walk-ins join the queue after the patients who are already checked in for the same provider.
- A booking has exactly one status: `booked`, `checked_in`, `in_progress`, `done`, `cancelled`, `no_show`.

## 6. Non-functional requirements

- **Security:** passwords are hashed, all traffic uses HTTPS, staff actions need the right role, and login attempts are rate limited.
- **Privacy:** store only what is needed (name, phone, optional email). Do not store medical information in version 1.
- **Reliability:** booking uses a database transaction and a database constraint, not only application code.
- **Performance:** key pages load in under 3 seconds on a slow phone connection.
- **Usability:** works on small phone screens. Text can be read in all three languages.
- **Quality:** automated tests for every feature, and the main branch must always pass them.
- **Operations:** the whole system starts with one command, is deployed automatically from GitHub, and has database backups.

## 7. Assumptions and risks

- The problems in section 1 are assumptions. We confirm them by talking to at least 5 people (`discovery.md`).
- Messages by SMS or WhatsApp may cost money. Version 1 uses email only.
- Health-related data may be regulated. We avoid medical data to reduce risk.

## 8. Milestones

1. Discovery and documents
2. Project setup and database design
3. Booking core (FR-4 to FR-8)
4. Staff login, reception and queue (FR-1, FR-9 to FR-14)
5. Reminders and languages (FR-15, FR-16)
6. Installable app (FR-17)
7. Security, tests, Docker and live deployment
8. Pilot with real users

## 9. Definition of done (for every feature)

- It works as described in its user story.
- It has automated tests that pass.
- It is documented in the README if someone needs to know how to use it.
- It is merged through a pull request.
