# FitnessZone - Gym Management System

FitnessZone is a template-driven Django gym management application built around two core experiences:

- a member-facing portal for registration, profile management, workout and diet access, exercise browsing, and membership payment submission
- an admin-facing management area for member onboarding, attendance tracking, exercise management, and manual payment verification

The project uses Django's built-in authentication system, stores data in SQLite by default, and combines a custom admin portal (`/admin_portal`) with the standard Django admin site (`/admin/`).

## Live Demo

🔗 [View Live Project](https://akashpal.pythonanywhere.com/)


## Project Description

This project is a complete gym management system implemented with pure Django server-side rendering. There is no REST API layer in this repository. Instead, the application is organized around Django apps, models, forms, views, templates, and static assets.

Main capabilities include:

- member registration and login
- role-based admin login
- profile dashboard with BMI and attendance summary
- exercise library with muscle-group filtering
- diet and workout plan pages
- manual UPI membership payment flow with screenshot and UTR upload
- custom admin payment approval/rejection workflow
- attendance management
- contact form with email notification

## Features

- Role-based authentication for members and staff
- Transaction-safe member registration using `auth.User` + `Gym_user`
- Custom member profile with physical details, image upload, and attendance count
- Exercise catalog with grouping, filtering, and admin CRUD support
- Membership plans for Monthly, Quarterly, and Yearly durations
- Manual UPI payment submission with QR/deep link generation
- Payment proof validation and admin verification
- Automatic membership activation, rejection handling, and expiry updates
- Contact form persistence with email notification support
- Django admin customization for memberships, payment proofs, contacts, attendance, and exercises
- Test coverage for member access, contact flow, payment approval, and custom admin portal behavior

## Admin Panel Functionalities

### Custom Admin Portal (`/admin_portal`)

- Dashboard cards for adding members, viewing members, taking attendance, changing password, and adding exercises
- Quick stats for:
  - total members
  - members present/absent today
  - monthly registrations
  - monthly growth rate
  - active members with attendance
  - total admin accounts
  - pending/approved/rejected payments
  - active memberships
- Membership payment review queue with screenshot preview, UTR display, admin note, and approve/reject actions
- Recent payment activity table

### Member Management

- Register new members from the same registration form used by public users
- View all members
- Search members by first name, last name, member ID, username, or date of birth
- Open member detail page with BMI, attendance total, member since date, and last login display
- Delete member accounts

### Attendance Management

- Mark members as `present` or `absent` for the current day
- Save or update daily attendance records
- Use quick actions such as "Mark All Present" from the attendance UI

### Exercise Management

- Add new exercises
- Edit existing exercises
- Upload exercise images or provide external image URLs
- Preview exercise images before saving

### Django Admin (`/admin/`)

- Manage `Gym_user`, `Contact`, `Attendance`, `Membership`, `PaymentProof`, and exercise records
- Bulk approve or reject payment proofs
- Use custom approve/reject buttons on the `PaymentProof` change form
- Filter and search memberships and payment proofs by status, plan, user, and date
- Auto-refresh overdue membership states when opening membership-related admin screens

## User Functionalities

- Register a new member account
- Log in and log out
- Auto-login immediately after successful public registration
- View a personalized profile dashboard
- Upload a profile picture using AJAX
- View BMI score and BMI category
- Track total attendance days
- Browse membership status and payment history
- Choose a membership plan and submit manual payment proof
- View workout plan and diet plan pages
- View today's workout recommendation based on gym split and joining date
- Browse the exercise library by muscle group
- Change password
- Submit contact form messages
- Delete own account/profile

## Technologies Used

| Category | Stack |
| --- | --- |
| Backend | Python, Django 4.2.6 |
| Database | SQLite3 |
| Authentication | Django `auth.User`, sessions, password validators |
| Frontend | Django Templates, HTML, CSS, JavaScript |
| UI Libraries | Bootstrap 5.3.2, Font Awesome, AOS |
| Media Handling | Pillow |
| QR Support | `qrcode[pil]` on the server, `qrcode.js` fallback in the template |
| Email | Django email backend (console backend by default in development) |

## System Architecture

```text
Browser
  -> fitness_zone/urls.py
     -> workouts app
        - public homepage
        - exercise library
     -> Gym app
        - registration/login
        - member profile
        - membership/payment flow
        - attendance
        - custom admin portal
        - contact form
        - password management
  -> Django Forms
     - input validation
  -> Django Models
     - business rules
     - membership activation/rejection/expiry
  -> SQLite database
  -> Templates + static files + uploaded media
```

Architecture notes:

- `fitness_zone/` is the Django project configuration package.
- `Gym/` contains most business logic for members, staff workflows, authentication, attendance, and membership payments.
- `workouts/` contains the public homepage exercise preview and the exercise library domain model.
- Templates are app-level templates with `APP_DIRS=True`.
- Uploaded files are stored under `media/`, including profile images, exercise uploads, and payment screenshots.

## Database Models

### Relationship Types Used

- `ForeignKey`: many child records can point to one parent record. This is used for `Gym_user -> Address/Gender/Gym_split/Muscle_strength`, `Attendance -> Gym_user`, `Membership -> User`, and `PaymentProof -> User`.
- `OneToOneField`: exactly one child record maps to one parent record. This is used for `Gym_user -> User` and `PaymentProof -> Membership`.

### Lookup / Reference Models

| Model | Fields | Purpose |
| --- | --- | --- |
| `Gym_split` | `split_name` | Stores workout split choices such as `5 Day Split` and `3 Day Split (PPL)`. |
| `Gender` | `gender` | Stores selectable gender values for member registration. |
| `Muscle_strength` | `type` | Stores member training level values such as `Beginner`, `Intermediate`, and `Advanced`. |
| `Address` | `area` | Stores supported city/area choices for registration. |

### `Gym_user`

Purpose: member profile model that extends Django's built-in `auth.User` with gym-specific details.

| Field | Type | Notes |
| --- | --- | --- |
| `user` | `OneToOneField(User)` | Optional link to the Django authentication user; used for login-enabled members. |
| `first_name` | `CharField` | Member first name. |
| `last_name` | `CharField` | Member last name. |
| `no_of_days` | `IntegerField` | Attendance counter shown on profile/dashboard screens. |
| `dob` | `DateField` | Member date of birth. |
| `phone_number` | `IntegerField` | Member phone number. |
| `image` | `ImageField` | Profile image upload with default placeholder. |
| `weight` | `IntegerField` | Stored in kilograms for BMI calculation. |
| `height` | `IntegerField` | Stored in centimeters for BMI calculation. |
| `date_of_joining` | `DateTimeField` | Auto-set on profile creation. |
| `email` | `EmailField` | Member email, synchronized from linked `User` when available. |
| `username` | `CharField(unique=True)` | Member username, also synchronized from linked `User`. |
| `password` | `CharField` | Legacy non-editable field kept blank; real authentication uses Django's `User` password hashing. |
| `address` | `ForeignKey(Address)` | Selected city/area. |
| `gender` | `ForeignKey(Gender)` | Selected gender. |
| `gym_split` | `ForeignKey(Gym_split)` | Selected workout split. |
| `muscle_strength` | `ForeignKey(Muscle_strength)` | Selected training level. |

Behavior:

- `save()` keeps `username`, `email`, `first_name`, and `last_name` aligned with the linked `auth.User`.
- Search helper methods support admin-side search by first name, last name, username, ID, and date of birth.

### `Contact`

Purpose: stores contact form submissions from the public site.

| Field | Type | Notes |
| --- | --- | --- |
| `name` | `CharField` | Sender name. |
| `email` | `EmailField` | Sender email address. |
| `subject` | `CharField` | Message subject. |
| `message` | `TextField` | Contact message body. |
| `created_at` | `DateTimeField` | Auto-set submission timestamp. |

### `Attendance`

Purpose: stores a member's attendance status for a specific day.

| Field | Type | Notes |
| --- | --- | --- |
| `member` | `ForeignKey(Gym_user)` | Member whose attendance is being tracked. |
| `date` | `DateField` | Defaults to the current day. |
| `status` | `CharField(choices)` | `present` or `absent`. |
| `updated_at` | `DateTimeField` | Auto-updated timestamp for edits. |

Important constraints:

- `unique_together = ('member', 'date')` prevents duplicate attendance rows for the same member on the same date.
- Indexed by `(date, member)` and `(member, date)` for faster lookups.

### `Membership`

Purpose: represents a selected membership plan and its payment/membership lifecycle for a user.

| Field | Type | Notes |
| --- | --- | --- |
| `user` | `ForeignKey(User)` | Django account that owns the membership submission. |
| `plan_name` | `CharField` | Stores plan name such as `Monthly`, `Quarterly`, or `Yearly`. |
| `amount` | `DecimalField` | Plan amount at the time of submission. |
| `duration` | `PositiveIntegerField` | Membership duration in days; must be at least 1. |
| `start_date` | `DateField` | Filled when payment is approved. |
| `expiry_date` | `DateField` | Calculated from `start_date + duration`. |
| `payment_status` | `CharField(choices)` | `pending`, `approved`, or `rejected`. |
| `membership_status` | `CharField(choices)` | `pending`, `active`, `inactive`, or `expired`. |
| `created_at` | `DateTimeField` | Auto-set submission timestamp. |

Business methods:

- `activate()` approves payment, sets start date, computes expiry date, and marks the membership active.
- `mark_rejected()` clears dates and marks the membership inactive.
- `expire_if_needed()` and `expire_overdue_memberships()` automatically mark overdue active memberships as expired.

### `PaymentProof`

Purpose: stores the uploaded proof for a membership payment submission.

| Field | Type | Notes |
| --- | --- | --- |
| `user` | `ForeignKey(User)` | User who submitted the payment proof. |
| `membership` | `OneToOneField(Membership)` | Exactly one proof record per membership submission. |
| `screenshot` | `ImageField` | Payment screenshot upload. |
| `utr_number` | `CharField(unique=True)` | Unique UTR / transaction ID. |
| `payment_method` | `CharField(choices)` | Currently supports `upi` (`Manual UPI`). |
| `payment_status` | `CharField(choices)` | `pending`, `approved`, or `rejected`. |
| `uploaded_at` | `DateTimeField` | Auto-set upload timestamp. |
| `admin_note` | `TextField` | Optional note/reason added during verification. |

Business rules:

- Upload path includes user ID, membership ID, timestamp, and UUID.
- File extensions are limited to `jpg`, `jpeg`, `png`, and `webp`.
- File size is limited to 5 MB.
- `clean()` ensures the screenshot exists, the UTR exists, and the proof belongs to the same user as the membership.
- `save()` triggers membership activation or rejection when the payment status changes.
- `approve()` and `reject()` centralize admin workflow behavior.

### `Exercise`

Purpose: stores exercise library entries used on the homepage preview, public exercise library, and admin exercise management screens.

| Field | Type | Notes |
| --- | --- | --- |
| `name` | `CharField(unique=True)` | Exercise name. |
| `muscle_group` | `CharField(choices)` | One of `chest`, `back`, `shoulders`, `biceps`, `triceps`, `forearms`, or `legs`. |
| `instructions` | `TextField` | How-to text shown in the UI. |
| `image_url` | `URLField` | Optional external image URL. |
| `image` | `ImageField` | Optional uploaded image. |

Behavior:

- `fallback_static_image` returns a default local image based on muscle group.
- `library_context()` prepares grouped exercise data and counts for the public exercise filter UI.

## URL Routes

### Project-Level Routes

| Route | Source | Purpose |
| --- | --- | --- |
| `/admin/` | `fitness_zone/urls.py` | Standard Django admin site. |
| `/` | `workouts.urls` then `Gym.urls` | Root URL space shared by both apps. |

### Public and Member Routes

| Route | View | Access | Purpose |
| --- | --- | --- | --- |
| `/` | `workouts.views.home` | Public | Homepage with featured exercise preview. |
| `/exercises/` | `workouts.views.exercises` | Public | Exercise library grouped and filtered by muscle group. |
| `/membership` | `Gym.views.membership` | Public | Membership plan listing page. |
| `/membership/join/<plan_slug>` | `Gym.views.join_membership` | Public -> redirects | Sends logged-in members to payment or anonymous users to login with `next`. |
| `/payment/<plan_slug>` | `Gym.views.payment_page` | Member | Manual UPI payment page for the selected plan. |
| `/contact` | `Gym.views.contact_view` | Public | Contact form submission page. |
| `/register` | `Gym.views.register_view` | Public | Member registration endpoint alias. |
| `/new_registration` | `Gym.views.register_view` | Public or Admin | Public signup page and admin add-member page. |
| `/login` | `Gym.views.login_view` | Public | Member login page. |
| `/logout` | `Gym.views.logout_view` | Authenticated user | Logs out current session and redirects home. |
| `/profile_page` | `Gym.views.profilePage` | Member or Admin with query string | Member profile dashboard; admins can inspect a member via `?u_id=`. |
| `/diet_plan` | `Gym.views.diet_plan` | Member or Admin with query string | Diet plan page for the current or selected member. |
| `/workout_plan` | `Gym.views.workout_plan` | Member or Admin with query string | Workout plan page for the current or selected member. |
| `/workout` | `Gym.views.workout` | Member or Admin with query string | Daily workout category based on split and days since joining. |
| `/change_user_password` | `Gym.views.change_user_password` | Member | Member password change page. |
| `/delete_user` | `Gym.views.delete_profbyuser` | Member or Admin | Deletes the current member profile/account or lets admin remove it. |

### Admin and Utility Routes

| Route | View | Access | Purpose |
| --- | --- | --- | --- |
| `/admin_login` | `Gym.views.admin_login_view` | Public | Staff-only login page for the custom admin portal. |
| `/admin_logout` | `Gym.views.admin_logout_view` | Staff | Logs out admin and redirects to admin login. |
| `/admin_portal` | `Gym.views.admin_portal` | Staff | Custom admin dashboard and payment review screen. |
| `/add_exercise` | `Gym.views.add_exercise` | Staff | Create a new exercise record. |
| `/add_exercise/<int:exercise_id>` | `Gym.views.add_exercise` | Staff | Edit an existing exercise record. |
| `/all_members` | `Gym.views.all_members` | Staff | List all member profiles. |
| `/attendance` | `Gym.views.attendance` | Staff | Mark and save attendance for the day. |
| `/userdetails` | `Gym.views.userdetails` | Staff | Open a single member detail page via `?u_id=`. |
| `/searchPage` | `Gym.views.searchPage` | Staff | Search result page for member lookup. |
| `/upload_profile_image/` | `Gym.views.upload_profile_image` | Member self or Staff, POST only | AJAX endpoint for profile image upload. |
| `/change_admin_password` | `Gym.views.change_admin_password` | Staff | Admin password change page. |
| `/delete` | `Gym.views.delete_user` | Staff | Deletes a member account via `?u_id=`. |

## Authentication Flow

1. Public registration is handled by `MemberRegistrationForm`, which creates a Django `User` and then creates a linked `Gym_user` profile inside a database transaction.
2. Public users must accept the Terms & Conditions checkbox; staff users adding members from `/new_registration` do not need to.
3. After successful public registration, the new member is authenticated immediately and redirected to `next` or `/profile_page`.
4. Member login uses `StyledAuthenticationForm`.
5. Admin login uses `StaffAuthenticationForm`, which explicitly blocks non-staff accounts.
6. Redirect targets are sanitized with `url_has_allowed_host_and_scheme()` before use.
7. Member-only pages use `member_login_required`, while admin-only pages use `_admin_session_required`.
8. Password changes use Django's `PasswordChangeForm` via `StyledPasswordChangeForm`, and the session is preserved with `update_session_auth_hash()`.
9. A custom `csrf_failure_view` stores a friendly session message and redirects back to a safe page if a stale CSRF token is submitted.

## Form Validation Highlights

| Form | Validation / Behavior |
| --- | --- |
| `StyledAuthenticationForm` | Styled member login form using Django auth validation. |
| `StaffAuthenticationForm` | Extends member login validation and rejects users without `is_staff=True`. |
| `MemberRegistrationForm` | Validates names, phone number length, age range (13-100), unique email, unique username, height (100-250 cm), weight (30-200 kg), and terms acceptance for public signups. |
| `StyledPasswordChangeForm` | Uses Django password validation rules with custom widgets and preserved session after success. |
| `ContactForm` | Validates full name, email, subject length, message length, hidden honeypot field, and excessive links in message content. |
| `PaymentProofForm` | Requires screenshot and UTR, validates UTR format and uniqueness, restricts file types, and verifies the uploaded file is a real image. |
| `ExerciseForm` | Trims whitespace in exercise names and instructions before saving. |

### Registration Validation Details

- First and last names must contain only alphabets/spaces and be at least 2 characters long.
- Phone numbers are normalized to digits only and must be 10 to 15 digits.
- Date of birth must produce an age between 13 and 100 years.
- Email and username must be unique.
- Registration reference options are auto-created for city, gender, fitness level, and split choices.

### Payment Validation Details

- UTR / transaction ID must match `^[A-Za-z0-9-]{8,50}$`.
- UTRs are normalized to uppercase and must be unique.
- Screenshot is required and must be a valid JPG, PNG, or WebP image.
- Payment screenshot size is limited to 5 MB.
- Model validation ensures the payment proof belongs to the same user as the membership record.

## Membership & Payment Workflow

### Membership Plans Defined in Code

| Plan | Slug | Amount | Duration |
| --- | --- | --- | --- |
| Monthly | `monthly` | Rs 999 | 30 days |
| Quarterly | `quarterly` | Rs 2,499 | 90 days |
| Yearly | `yearly` | Rs 8,999 | 365 days |

### Workflow

1. A user opens `/membership` and selects a plan.
2. `/membership/join/<plan_slug>` checks authentication state.
3. Anonymous users are redirected to `/login?next=/payment/<plan_slug>`.
4. Logged-in members open `/payment/<plan_slug>`.
5. The payment page generates:
   - a UPI deep link using `UPI_PAYMENT_ID` and `UPI_PAYEE_NAME`
   - a server-side QR code if `qrcode` is available
   - a client-side QR fallback if needed
6. On form submission, the system creates a `Membership` and `PaymentProof` record inside a transaction.
7. Duplicate pending submissions for the same plan are blocked.
8. The new membership starts as:
   - `payment_status = pending`
   - `membership_status = pending`
9. Admins approve or reject the proof from either:
   - the custom admin portal
   - the Django admin `PaymentProof` screen
10. Approval triggers:
    - `PaymentProof.payment_status = approved`
    - `Membership.payment_status = approved`
    - `Membership.membership_status = active`
    - `Membership.start_date = today`
    - `Membership.expiry_date = today + duration`
11. Rejection triggers:
    - `PaymentProof.payment_status = rejected`
    - `Membership.payment_status = rejected`
    - `Membership.membership_status = inactive`
    - `start_date` and `expiry_date` are cleared
12. Overdue active memberships are auto-marked as `expired` by model logic used in profile/admin contexts.

## Attendance Management

- Attendance is stored in the `Attendance` model with one row per member per date.
- The attendance screen defaults unsaved members to `absent` in the UI.
- Admins can mark `present` or `absent` and submit all updates together.
- `update_or_create()` is used so the same day can be edited without creating duplicate records.
- Member profile pages display `no_of_days` as the attendance count.
- Admin portal statistics use today's attendance data to show present/absent totals.

## Installation Guide

### Prerequisites

- Python 3
- `pip`
- Virtual environment support

### Setup

```bash
git clone <your-repository-url>
cd fitness_zone

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

python manage.py migrate
python manage.py seed_exercises
python manage.py createsuperuser
python manage.py runserver
```

### Optional Environment Variables

The project reads several values from environment variables in `settings.py`:

| Variable | Purpose | Default |
| --- | --- | --- |
| `SECRET_KEY` | Django secret key | bundled development key |
| `EMAIL_BACKEND` | Django email backend | `django.core.mail.backends.console.EmailBackend` |
| `DEFAULT_FROM_EMAIL` | Sender email for contact notifications | `noreply@fitnesspro.com` |
| `ADMIN_EMAIL` | Admin fallback email | `admin@gym.com` |
| `CONTACT_NOTIFICATION_EMAIL` | Contact form recipient | falls back to admin/staff email |
| `UPI_PAYMENT_ID` | UPI ID shown on the payment page | `gymowner@upi` |
| `UPI_PAYEE_NAME` | UPI payee name shown on the payment page | `fitnessZone` |

### Run the Test Suite

```bash
python manage.py test
```

The current repository test suite covers member route access, contact flow, payment approval logic, Django admin payment actions, and the custom admin portal payment workflow.

## Project Structure

```text
fitness_zone/
|-- manage.py
|-- db.sqlite3
|-- requirements.txt
|-- README.md
|-- screenshots/
|   |-- admin.png
|   |-- homepage.png
|   `-- user.png
|-- media/
|   |-- exercises/
|   |-- payment_proofs/
|   `-- users_profile_images/
|-- fitness_zone/
|   |-- __init__.py
|   |-- asgi.py
|   |-- settings.py
|   |-- settings_production.py
|   |-- urls.py
|   `-- wsgi.py
|-- Gym/
|   |-- __init__.py
|   |-- admin.py
|   |-- apps.py
|   |-- forms.py
|   |-- models.py
|   |-- tests.py
|   |-- urls.py
|   |-- views.py
|   |-- migrations/
|   |-- static/
|   |   |-- exercises/
|   |   |-- images/
|   |   `-- js/profile_upload.js
|   `-- templates/
|       |-- add_exercise.html
|       |-- admin_base.html
|       |-- admin_login.html
|       |-- admin_portal.html
|       |-- all_members.html
|       |-- attendance.html
|       |-- change_admin_password.html
|       |-- change_user_password.html
|       |-- contact.html
|       |-- diet_plan.html
|       |-- home.html
|       |-- login_page.html
|       |-- membership.html
|       |-- new_registration.html
|       |-- parent.html
|       |-- payment.html
|       |-- profile_page.html
|       |-- searchPage.html
|       |-- userdetails.html
|       |-- workout.html
|       |-- workout_plan.html
|       `-- admin/Gym/paymentproof/change_form.html
`-- workouts/
    |-- __init__.py
    |-- admin.py
    |-- apps.py
    |-- forms.py
    |-- models.py
    |-- urls.py
    |-- views.py
    |-- migrations/
    |-- management/
    |   `-- commands/seed_exercises.py
    `-- templates/workouts/exercises.html
```

## Database Schema Summary

### Core Relationships

| Relationship | Type | Description |
| --- | --- | --- |
| `User -> Gym_user` | One-to-one | One Django auth account can have one gym member profile. |
| `Address -> Gym_user` | One-to-many | Many members can share the same area/city option. |
| `Gender -> Gym_user` | One-to-many | Many members can share the same gender option. |
| `Gym_split -> Gym_user` | One-to-many | Many members can share the same workout split. |
| `Muscle_strength -> Gym_user` | One-to-many | Many members can share the same training level. |
| `Gym_user -> Attendance` | One-to-many | A member can have many attendance records across dates. |
| `User -> Membership` | One-to-many | A user can create multiple membership submissions over time. |
| `Membership -> PaymentProof` | One-to-one | Each membership submission has at most one payment proof. |
| `User -> PaymentProof` | One-to-many | A user can upload payment proofs for multiple membership submissions. |

### Important Constraints and Indexes

- `Gym_user.username` is unique.
- `PaymentProof.utr_number` is unique.
- `Attendance(member, date)` is unique.
- `Membership` is indexed by:
  - `(user, created_at)`
  - `(payment_status, membership_status)`
- `PaymentProof` is indexed by:
  - `(payment_status, uploaded_at)`
  - `(user, uploaded_at)`

## Security Features

- Django authentication and password hashing via `auth.User`
- Django password validators enabled in settings
- Separate member and staff login flows
- Staff-only gate for the custom admin login form
- Safe redirect handling for `next` URLs
- CSRF middleware enabled
- Custom CSRF failure recovery with user-friendly message
- `@require_POST` for profile image upload endpoint
- Server-side file type and size checks for uploads
- Image integrity verification for payment proof uploads
- Unique constraints to reduce duplicate usernames, UTRs, and attendance rows

## Future Enhancements

- Replace manual UPI proof review with a direct payment gateway integration
- Add scheduled reminders for pending verification and membership expiry
- Export attendance and membership reports to CSV/PDF
- Add richer admin analytics dashboards and charts
- Extend exercise management with categories such as warm-up, cardio, and mobility
- Move production secrets and host settings fully to environment-based deployment configuration

## Author

Author: Suraj Pal
