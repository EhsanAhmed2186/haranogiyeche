# Haranogiyeche

A community-based **Lost & Found** platform built with Django. People join communities (a university, an organization or a neighbourhood), post lost and found items, and claim items through an **ownership-verification process**. Private messaging opens only after the item's owner approves a claim.

Repository: https://github.com/EhsanAhmed2186/haranogiyeche

## Features

**Accounts and communities**
- Registration, login and logout, with a profile page and profile photo upload
- Forgot password: a 6-digit code is emailed, valid for 10 minutes and usable once
- Create a community or join one with its **join code**; roles are admin, moderator and member
- Public pages for guests: welcome page, list of communities, About. Joining needs an account **and** the code
- Light and dark mode

**Lost & found feed**
- Lost and found posts with an optional photo (up to 5 MB)
- Filter by type and status, and search descriptions
- Item status: active, returned or closed
- Comments, and reports of suspicious posts (one report per user per post)

**Verification and contact**
- The post owner sets questions; the expected answers are stored only as **hashes**
- A claimant answers the questions and sends a contact request
- The owner (or a community moderator) reviews the answers and approves or rejects. A matching answer is only a hint, never automatic approval

**Messaging and notifications**
- Private messages, allowed only on an **approved** request and only between its two participants
- Notifications for new requests and decisions, with unread counters in the navbar that update live
- Friendly 403, 404 and 500 pages

## Technology

| Part | Choice |
|---|---|
| Language and framework | Python 3.12 or newer, Django 6.1 |
| Database | SQLite (Django ORM) |
| Frontend | Django templates, Bootstrap 5 (CDN), a little vanilla JavaScript |
| Images | Pillow |
| Live updates | Polling every 8 seconds, no WebSockets |

## Project structure

```text
Haranogiyeche/
├── .gitignore
├── manage.py
├── requirements.txt
├── README.md
│
├── config/                 settings, root URLs, ASGI and WSGI
├── accounts/               users, communities, memberships, password reset
├── newsfeed/               posts, comments, reports
├── verification/           questions, contact requests, answers
├── messaging/              private messages
├── notifications/          notifications and the live-update endpoint
│
├── templates/              HTML templates, one folder per app, plus base.html
├── static/
│   ├── css/site.css
│   └── js/                 theme.js (light/dark), live.js (live badges)
├── media/                  uploaded files (not committed)
└── docs/                   diagrams and project report
```

## Getting started

You need Python 3.12 or newer and Git.

```powershell
git clone https://github.com/EhsanAhmed2186/haranogiyeche.git
cd haranogiyeche

python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/. The admin site is at http://127.0.0.1:8000/admin/.

Do **not** commit `db.sqlite3`, `.env`, `.venv`, `.idea` or uploaded files in `media/`. They are already in `.gitignore`.

## Run the tests

```powershell
python manage.py test
```

To test one app: `python manage.py test newsfeed`.

Never write the password into `settings.py` or commit it.

## Main pages

| Page | Address | Who can open it |
|---|---|---|
| Home / My communities | `/` | Everyone (guests see a welcome page) |
| All communities | `/communities/` | Everyone |
| About | `/about/` | Everyone |
| Register, log in, forgot password | `/accounts/register/`, `/accounts/login/`, `/accounts/password-reset/` | Guests |
| Profile | `/profile/` | Logged-in users |
| Community page | `/accounts/communities/<id>/` | Members only |
| Feed | `/communities/<id>/posts/` | Members only |
| Post | `/posts/<id>/` | Members of its community |
| Request | `/requests/<id>/` | The sender, the owner, or community moderators |
| Conversation | `/conversations/<id>/` | The two participants only, after approval |
| Inbox and notifications | `/inbox/`, `/notifications/` | Logged-in users (own data only) |

## Demo scenario

1. A registers, logs in and creates a community. B registers and joins it with the join code.
2. A posts a found item with a photo and adds a verification question.
3. B finds the post and clicks **This is mine**, then answers the question.
4. A gets a notification, reviews B's answer and approves the request.
5. A and B exchange private messages; each sees live unread counters.
6. A marks the item as **Returned**.
7. A third user, or someone outside the community, opening the conversation or the request gets a **403** page.

## Security design

| Rule | How it is enforced |
|---|---|
| Posts and members are private to a community | Every view checks membership first |
| Knowing a join code does not bypass login | Joining requires an account; the code only identifies the community |
| Expected answers are never readable | Stored only as salted hashes, like passwords |
| Only the right person decides a request | The receiver or a moderator; a sender can never approve their own request |
| Conversations are private | Open only for approved requests and only for the two participants |
| Password reset codes | Hashed, expire in 10 minutes, single use, 5 wrong tries, resend limits, same reply for unknown emails |
| Uploads | Checked as real images, size-limited, saved under random file names |

## Database

12 model classes across 5 apps.

| App | Classes |
|---|---|
| `accounts` | `User`, `Community`, `Membership`, `PasswordResetOTP` |
| `newsfeed` | `Post`, `Comment`, `Report` |
| `verification` | `VerificationQuestion`, `ContactRequest`, `VerificationAnswer` |
| `messaging` | `Message` |
| `notifications` | `Notification` |

- **Foreign keys:** 20, used in every class except `User`.
- **Media fields:** 3 classes: `User.avatar`, `Post.image` and `Community.qr_code` (the QR field is reserved and not used by the pages yet).

## Team

| Member | Share | Apps | Classes |
|---|---|---|---|
| Ehsan Ahmed  | 50% | `accounts`, `verification`, integration of all apps | `User`, `Community`, `Membership`, `PasswordResetOTP`, `VerificationQuestion`, `ContactRequest`, `VerificationAnswer` |
| Farhan | 30% | `newsfeed` | `Post`, `Comment`, `Report` |
| Sathi | 20% | `messaging`, `notifications` | `Message`, `Notification` |



## Git workflow

- `main` holds the stable version. Work happens on `feature/accounts-verification`, `feature/newsfeed` and `feature/messaging-models`.
- Each member commits their own files and opens a pull request into `main`; the team leader reviews and merges.
- After every merge, run `git pull` and `python manage.py migrate`. Only one person creates the migrations for each app.
