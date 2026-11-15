# ClinicQ: User stories

A user story says **who** wants **what** and **why**. The acceptance criteria say how we know it works. Each story links to a requirement in `requirements.md`.

Format: *As a [role], I want [action], so that [benefit].*
Criteria: *Given [situation], when [action], then [result].*

---

## Epic A: Clinic setup (Admin)

**US-1: Staff login** (FR-1)
As a staff member, I want to log in with my email and password, so that only authorized people can manage the clinic.
- Given a correct email and password, when I log in, then I see the page for my role.
- Given a wrong password, when I log in, then I see an error and no access.
- Given 5 failed attempts in a row, when I try again, then I must wait before trying again.

**US-2: Set up services and providers** (FR-2)
As an admin, I want to create services, providers, working hours and slot length, so that patients can only book real times.
- Given I am an admin, when I add a provider with working hours, then free slots appear for those hours.
- Given a receptionist is logged in, when they try to open the setup page, then access is denied.

**US-3: Manage staff accounts** (FR-3)
As an admin, I want to create and disable staff accounts, so that former staff can no longer log in.
- Given I disable an account, when that person tries to log in, then they are refused.

---

## Epic B: Booking (Patient)

**US-4: See free slots** (FR-4)
As a patient, I want to see free slots by service, provider and date, so that I can choose a time that suits me.
- Given a provider works Monday 9:00 to 12:00 with 20-minute slots, when I open Monday, then I see 9 slots.
- Given a slot is already booked, when I look at the list, then that slot is not shown as free.

**US-5: Book a slot** (FR-5, FR-6, FR-8)
As a patient, I want to book a slot with my name and phone number, so that I do not have to queue to get an appointment.
- Given a free slot, when I submit my name and phone, then I get a booking code.
- Given two people choose the same slot at the same moment, when both submit, then one succeeds and the other sees "slot no longer available".
- Given a time in the past, when I try to book it, then it is refused.

**US-6: Cancel a booking** (FR-7)
As a patient, I want to cancel my booking with my booking code and phone number, so that the slot is free for someone else.
- Given a correct code and phone, when I cancel, then the slot becomes free.
- Given a wrong phone number, when I try to cancel, then it is refused.

---

## Epic C: Reception

**US-7: Today's list** (FR-9)
As a receptionist, I want to see today's bookings, so that I know who is expected.
- Given bookings exist today, when I open the dashboard, then I see them ordered by time, with their status.

**US-8: Check in** (FR-10)
As a receptionist, I want to check in a patient who arrives, so that they enter the queue.
- Given a booking with status `booked`, when I check the patient in, then the status becomes `checked_in`.

**US-9: Mark no-show** (FR-10)
As a receptionist, I want to mark a patient as a no-show, so that the schedule stays accurate.
- Given a patient has not arrived 15 minutes after the slot start, when I mark no-show, then the status becomes `no_show`.

**US-10: Add a walk-in** (FR-11)
As a receptionist, I want to add a patient who has no booking, so that they join the queue.
- Given a provider is working today, when I add a walk-in, then they appear in that provider's queue after patients already checked in.

---

## Epic D: Queue

**US-11: Follow my place in the queue** (FR-13)
As a patient, I want to enter my booking code and see my position and estimated wait, so that I can wait outside and come back when it is my turn.
- Given I am third in the queue, when I open my page, then it shows position 3 and an estimate.
- Given the queue moves, when I stay on the page, then it updates without me reloading.

**US-12: Call the next patient** (FR-12)
As a provider, I want to see and call the next waiting patient, so that the day runs smoothly.
- Given patients are checked in, when I press "Next", then the first one becomes `in_progress`.
- Given I finish with a patient, when I press "Done", then the status becomes `done`.

---

## Epic E: Reminders and language

**US-13: Reminder email** (FR-15)
As a patient, I want an email reminder the day before, so that I do not forget my visit.
- Given I gave an email, when it is 24 hours before my slot, then I receive a reminder.
- Given I cancelled, when the reminder time comes, then no reminder is sent.

**US-14: Choose my language** (FR-16)
As a patient, I want to use the app in French, Arabic or English, so that I understand every screen.
- Given I choose Arabic, when the page loads, then text is in Arabic and the layout reads right to left.

---

## Epic F: Accountability

**US-15: Activity log** (FR-14)
As an admin, I want to see who changed what and when, so that mistakes and misuse can be traced.
- Given a receptionist cancels a booking, when I open the log, then I see their name, the action and the time.
