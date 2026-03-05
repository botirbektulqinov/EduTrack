# EduTrack — University Assessment & Performance Management System

### Complete Technical Documentation · v1.0.0

---

> **Document Status:** Final  
> **Audience:** Backend Engineers, Frontend Engineers, DevOps, QA, University Administrators  
> **Last Revised:** 2026  
> **Classification:** Internal / University Confidential

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Overview & Architecture](#2-system-overview--architecture)
3. [User Roles & Permissions](#3-user-roles--permissions)
4. [Feature Catalog](#4-feature-catalog)
5. [Assessment Types — Full Reference](#5-assessment-types--full-reference)
6. [Anti-Cheat & Proctoring Engine](#6-anti-cheat--proctoring-engine)
7. [Assessment Lifecycle](#7-assessment-lifecycle)
8. [Performance Analytics & Dashboard](#8-performance-analytics--dashboard)
9. [Database Schema](#9-database-schema)
10. [API Reference](#10-api-reference)
11. [Frontend Architecture](#11-frontend-architecture)
12. [Backend Architecture](#12-backend-architecture)
13. [Security & Authentication](#13-security--authentication)
14. [Notifications & Communication](#14-notifications--communication)
15. [Accessibility & Internationalization](#15-accessibility--internationalization)
16. [Deployment & DevOps](#16-deployment--devops)
17. [Database Migrations — Alembic](#17-database-migrations--alembic)
18. [Testing Strategy](#18-testing-strategy)
19. [Error Handling & Logging](#19-error-handling--logging)
20. [Future Roadmap](#20-future-roadmap)
21. [Glossary](#21-glossary)

---

## 1. Executive Summary

**EduTrack** is a comprehensive, web-based university assessment and student performance management platform. It digitizes the entire lifecycle of academic evaluation — from test creation and assignment through proctored delivery, automated grading, analytics, and long-term performance tracking.

### Core Value Proposition

| Stakeholder          | Value Delivered                                                                |
| -------------------- | ------------------------------------------------------------------------------ |
| **University Admin** | Centralized control over all academic actors and results                       |
| **Teachers**         | Rich assessment authoring, automated grading, per-student insight              |
| **Students**         | Transparent results, self-performance visibility, structured learning feedback |
| **Institution**      | Longitudinal academic analytics, accreditation-ready reporting                 |

### Key Technical Characteristics

- **Full-stack web application** — accessible from any modern browser on any device
- **Proctored assessment delivery** — enforced fullscreen, tab-lock, violation logging
- **Role-based access control** — Admin → Teacher → Student hierarchy
- **Real-time analytics** — live dashboards with semester, year, and cumulative views
- **Secure link-based access** — time-bounded, one-time-use or limited access tokens
- **AI-ready performance analysis** — per-student weak-point detection and recommendations

---

## 2. System Overview & Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│   Browser (React SPA)  ←→  WebSocket  ←→  REST API              │
└────────────────────────────────┬────────────────────────────────┘
                                 │ HTTPS / WSS
┌────────────────────────────────▼────────────────────────────────┐
│                        API GATEWAY                              │
│              Nginx Reverse Proxy + Rate Limiter                 │
└────────────────────────────────┬────────────────────────────────┘
                                 │
        ┌────────────────────────┼────────────────────┐
        │                        │                    │
┌───────▼──────┐    ┌────────────▼──────┐    ┌────────▼──────────┐
│  Auth Service│    │  Core API Service │    │  Analytics Engine │
│  (FastAPI)   │    │    (FastAPI)      │    │   (FastAPI)       │
└───────┬──────┘    └────────────┬──────┘    └────────┬──────────┘
        │                        │                    │
┌───────▼────────────────────────▼────────────────────▼───────────┐
│                     DATA LAYER                                  │
│   PostgreSQL (Primary)   │   Redis (Cache/Session)              │
│   Alembic (Migrations)   │   Celery (Background Tasks)          │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack

#### Backend

| Component        | Technology            | Version  |
| ---------------- | --------------------- | -------- |
| Web Framework    | FastAPI               | ≥ 0.110  |
| ORM              | SQLAlchemy            | ≥ 2.0    |
| DB Migrations    | Alembic               | ≥ 1.13   |
| Database         | PostgreSQL            | ≥ 15     |
| Cache / Session  | Redis                 | ≥ 7      |
| Task Queue       | Celery + Redis Broker | ≥ 5.3    |
| Authentication   | JWT (RS256) + OAuth2  | —        |
| Password Hashing | bcrypt (via passlib)  | —        |
| Validation       | Pydantic v2           | ≥ 2.5    |
| Email            | FastAPI-Mail          | —        |
| File Storage     | MinIO (S3-compatible) | —        |
| WebSockets       | FastAPI WebSocket     | built-in |

#### Frontend

| Component        | Technology                     |
| ---------------- | ------------------------------ |
| Framework        | React 19 + TypeScript          |
| State Management | Zustand + React Query          |
| UI Components    | shadcn/ui + Tailwind CSS       |
| Charts           | Recharts + D3.js               |
| Rich Text / Math | Quill.js + KaTeX               |
| Form Management  | React Hook Form + Zod          |
| Routing          | React Router latest version    |
| Real-time        | Socket.io-client               |
| Anti-cheat       | Custom Proctoring SDK (see §6) |

#### DevOps

| Component        | Technology              |
| ---------------- | ----------------------- |
| Containerization | Docker + Docker Compose |
| Orchestration    | Kubernetes (production) |
| CI/CD            | GitHub Actions          |
| Monitoring       | Prometheus + Grafana    |
| Log Aggregation  | ELK Stack               |
| SSL              | Let's Encrypt (Certbot) |

---

## 3. User Roles & Permissions

### 3.1 Role Hierarchy

```
ADMIN
  └── TEACHER  (scoped to own groups)
        └── STUDENT  (scoped to own results)
```

### 3.2 Permission Matrix

| Action                               | Admin |     Teacher     | Student  |
| ------------------------------------ | :---: | :-------------: | :------: |
| Create / edit / delete Teachers      |  ✅   |       ❌        |    ❌    |
| Create / edit / delete Groups        |  ✅   |       ❌        |    ❌    |
| Assign Teachers to Groups            |  ✅   |       ❌        |    ❌    |
| Enroll Students into Groups          |  ✅   |       ❌        |    ❌    |
| Create / edit / delete Assessments   |  ✅   |    ✅ (own)     |    ❌    |
| Publish Assessment & generate link   |  ✅   |    ✅ (own)     |    ❌    |
| Set Assessment time window           |  ✅   |    ✅ (own)     |    ❌    |
| Assign Assessment to Group           |  ✅   |    ✅ (own)     |    ❌    |
| Take Assessment                      |  ❌   |       ❌        |    ✅    |
| View own results                     |  ✅   |       ✅        |    ✅    |
| View results of own group's students |  ✅   | ✅ (own groups) |    ❌    |
| View results of ALL students         |  ✅   |       ❌        |    ❌    |
| View violation logs                  |  ✅   | ✅ (own groups) |    ❌    |
| Manage system settings               |  ✅   |       ❌        |    ❌    |
| Export reports                       |  ✅   | ✅ (own groups) | ✅ (own) |
| View analytics dashboard             |  ✅   | ✅ (own groups) | ✅ (own) |

### 3.3 Admin Capabilities — Detail

- **User Management:** Create, activate, deactivate, reset password for any Teacher or Student account
- **Group Management:** Create academic groups (e.g., CS-101-A), assign a Teacher as the primary instructor, enroll Students
- **System Oversight:** View all assessments, all results, all violation logs across the university
- **Reports:** Export any data slice as CSV, PDF, or Excel
- **Configuration:** Set global policies (max violation count, default time penalties, allowed question types, grading scales)

### 3.4 Teacher Capabilities — Detail

- Manage assessments only within groups they are assigned to
- Cannot see students or results outside their groups
- Can create question banks, reuse questions across assessments
- Can view per-student violation logs for their assessments
- Can manually override or review flagged open-answer submissions
- Can set re-attempt policies per assessment

### 3.5 Student Capabilities — Detail

- Access assessments only via valid, non-expired link
- See only their own submissions and results
- View their own performance dashboard (semester, year, cumulative)
- Cannot see other students' names, scores, or data at any point

---

## 4. Feature Catalog

### 4.1 Assessment Management

#### F-001 — Create Assessment

- Teacher selects assessment type (Test or Quiz)
- Sets title, description, subject, associated group
- Configures time limit (minutes), availability window (start/end datetime), max attempts
- Selects question types from the bank
- Shuffles questions and/or answer options per-student (anti-plagiarism)
- Sets passing score threshold
- Enables proctoring settings (fullscreen enforcement, violation limits)

#### F-002 — Question Bank

- Centralized per-teacher repository of questions
- Questions tagged by topic, difficulty (Easy / Medium / Hard), bloom's level
- Import questions from CSV, JSON, or GIFT format (Moodle-compatible)
- Export question bank for backup or sharing

#### F-003 — Publish & Link Generation

- Teacher publishes the assessment to generate a unique access link
- Link format: `https://edutrack.university.edu/take/{uuid-token}`
- Link is valid only within the configured time window
- Teacher can copy link, send via the platform's notification system, or share manually
- Teacher can deactivate a link at any time (immediately invalidates ongoing sessions)
- Optional: password-protected links for additional access control

#### F-004 — Attempt Management

- System tracks attempts per student per assessment
- Configurable: 1 attempt (default), unlimited, or N attempts
- If multiple attempts: best score, last score, or average score recorded (configurable)
- Attempt state machine: `NOT_STARTED → IN_PROGRESS → SUBMITTED | TERMINATED`

#### F-005 — Automated Grading

- All closed-answer types graded instantly upon submission
- Open-ended / essay types flagged for manual teacher review
- Partial scoring available for matching, ordering, and multi-select types
- Results released: immediately, after teacher review, or after window closes (configurable)

#### F-006 — Manual Grading Interface

- Teacher sees student's open-answer submission with rubric panel
- Assign score, add inline feedback comments
- Batch-grade view for efficiency
- AI-assist suggestions for open-answer scoring (optional, flagged as AI)

#### F-007 — Result Release & Feedback

- Configurable result visibility: score only, score + correct answers, score + full feedback
- Students receive notification when results are released
- Per-question feedback can be added by teacher
- Results cannot be altered after release unless teacher explicitly unlocks

### 4.2 Assessment Delivery

#### F-010 — Fullscreen Enforcement

- On assessment start, browser enters fullscreen API (`document.documentElement.requestFullscreen()`)
- User presented with consent and instruction screen before entering fullscreen
- If fullscreen is exited by any means, a warning overlay is triggered
- See §6 (Anti-Cheat Engine) for complete behavior specification

#### F-011 — Timer System

- Countdown timer displayed prominently (top-right, always visible)
- Timer continues running if student loses focus (no pause on tab switch)
- Configurable penalty: each violation deducts N minutes from remaining time (default: 2 minutes)
- Visual warnings at 10 min, 5 min, 1 min remaining
- Auto-submit when timer reaches zero
- Server-side timer validation (client clock manipulation not accepted)

#### F-012 — Auto-Save

- Answers auto-saved to server every 30 seconds via WebSocket
- Student can see "Last saved: X seconds ago" indicator
- If connection drops, answers cached locally (IndexedDB) and synced on reconnect
- Prevents loss of work on accidental disconnect

#### F-013 — Navigation Controls

- Students can navigate between questions freely (unless teacher restricts to linear mode)
- "Flag for review" button per question
- Question palette showing: answered (green), flagged (yellow), unanswered (grey)
- "Submit Assessment" button with confirmation dialog showing unanswered count

#### F-014 — Accessibility Mode

- High-contrast mode toggle
- Font size adjustment (Small / Medium / Large / Extra Large)
- Screen reader compatibility (ARIA labels on all interactive elements)
- Extended time accommodation flag (set by Admin per student, multiplies time limit)

### 4.3 Performance Analytics

#### F-020 — Student Dashboard

- Overall GPA/score trend over time (line chart)
- Per-subject performance breakdown (radar/spider chart)
- Recent assessments list with score and percentile rank
- Performance vs. class average comparison
- Weak topic identification ("You consistently score below 60% in Recursion")
- Streak tracking (consecutive passing assessments)

#### F-021 — Teacher Dashboard

- Class performance distribution (histogram)
- Per-assessment statistics: mean, median, standard deviation, pass rate
- Per-question difficulty analysis (% of students who answered correctly)
- Item discrimination index (how well each question differentiates high/low performers)
- Student-level performance table with sort/filter
- At-risk student alerts (students below threshold for N consecutive assessments)

#### F-022 — Admin Dashboard

- University-wide pass/fail rates by department, subject, group
- Teacher effectiveness overview (average class performance per teacher)
- Assessment completion rates
- Violation and integrity incident summary
- Longitudinal trends: semester-over-semester, year-over-year
- Exportable: all charts and tables to PDF, Excel

#### F-023 — Performance Period Filters

All dashboards support filtering by:

- Current semester
- Academic year
- Custom date range
- Since enrollment (lifetime)

### 4.4 User & Group Management

#### F-030 — Admin: Manage Teachers

- Create teacher account (name, email, department, employee ID)
- Assign teacher to one or more groups
- Activate / deactivate accounts
- Reset passwords, send invitation emails
- View teacher's assessment activity

#### F-031 — Admin: Manage Groups

- Create academic group (group name, academic year, semester, subject)
- Assign primary teacher
- Enroll students (bulk upload via CSV)
- Remove students from group
- Archive groups at end of semester (data retained, no new activity)

#### F-032 — Admin: Manage Students

- Create student accounts individually or bulk import (CSV: name, email, student ID, group)
- View student's full history across all groups and teachers
- Apply special accommodations (extended time, etc.)
- Generate student progress reports

---

## 5. Assessment Types — Full Reference

EduTrack supports **14 question/assessment types**, grouped into categories:

### 5.1 Binary / Forced-Choice

#### TYPE-01 — True / False

- Statement presented; student selects True or False
- Optional: "True / False / Cannot be determined" (three-option variant)
- Supports image or code snippet in the statement
- Auto-graded; 1 point for correct

**Example:**

> _"Python is a statically typed language."_
> ○ True ● False

---

#### TYPE-02 — Yes / No

- Variant of True/False using Yes/No framing
- Useful for opinion-based or procedural questions
- Grading: exact match

---

### 5.2 Multiple Choice

#### TYPE-03 — Single-Answer Multiple Choice (MCQ)

- 2–8 answer options; exactly one correct
- Options can be text, image, code, math (LaTeX)
- Shuffle options per student (anti-cheat)
- Negative marking option (configurable: −0.25, −0.5 per wrong answer)
- Auto-graded

---

#### TYPE-04 — Multiple-Answer Multiple Choice (MAQ)

- 2–8 options; one or more correct
- Student selects all that apply
- Partial scoring: score = (correct selected − incorrect selected) / total correct, floor 0
- Or strict scoring: full marks only if all correct and none wrong selected

---

#### TYPE-05 — Image-Based MCQ

- Question stem is an image or diagram
- Student selects from text or image options
- Supports hotspot variant (student clicks region on image as answer)

---

### 5.3 Open / Constructed Response

#### TYPE-06 — Short Answer (Open-Ended Closed)

- Student types a brief response (1–5 words / a number)
- Teacher defines accepted answers (case-insensitive, trim whitespace)
- Optional: regex pattern matching for flexible acceptance
- Near-match suggestion: flag for teacher review if answer is close but not exact
- Auto-graded if exact match; otherwise flagged

---

#### TYPE-07 — Long Answer / Essay

- Rich text editor (formatting, lists, code blocks)
- Optional word limit (min / max)
- File attachment support (PDF, image — for diagrams)
- Manual grading only; rubric displayed to teacher during review
- AI-assist scoring: suggested score with reasoning (teacher must confirm)

---

#### TYPE-08 — Fill in the Blank (Cloze)

- Sentence with one or more blanks (`___`)
- Student types into blank fields inline within the text
- Multiple blanks supported per question
- Each blank graded independently
- Accepted answers list per blank; case sensitivity configurable

**Example:**

> _"The process by which plants convert sunlight into energy is called ***. The by-product of this process is ***."_

---

#### TYPE-09 — Numeric / Calculated

- Student enters a numerical answer
- Teacher defines exact value or acceptable range (`answer ± tolerance`)
- Unit specification optional (e.g., answer must include "m/s")
- Supports scientific notation input
- Auto-graded

---

### 5.4 Ordering & Matching

#### TYPE-10 — Matching (Headings / Pairs)

- Two columns: premises and responses
- Student drags/drops or selects from dropdowns to pair items
- Options: 1:1 matching, or responses can be reused (many-to-one)
- Partial scoring: 1 point per correct pair
- Shuffle both columns per student

**Example:**

> _Match the data structure to its primary use case:_
> Stack → LIFO operations  
> Queue → BFS traversal  
> Heap → Priority scheduling

---

#### TYPE-11 — Ordering / Sequence

- List of items presented in shuffled order
- Student drags to arrange in correct sequence
- Partial scoring: adjacent-pair scoring or positional scoring (configurable)
- Useful for: algorithm steps, historical events, procedural tasks

---

#### TYPE-12 — Categorization / Sorting

- Items must be sorted into 2–6 labeled buckets/categories
- Drag-and-drop interface
- Items may belong to only one category (strict) or multiple (flexible)
- Partial scoring per item

---

### 5.5 Advanced / Specialized

#### TYPE-13 — Hotspot / Image Annotation

- Student clicks one or more regions on an image to mark correct location(s)
- Teacher defines correct zone(s) as polygons or circles during authoring
- Useful for: anatomy, geography, circuit diagrams, architecture plans
- Tolerance radius configurable

---

#### TYPE-14 — Code Submission

- Student writes code in an embedded editor (Monaco Editor / CodeMirror)
- Supported languages: Python, JavaScript, Java, C++, C#, SQL, and more
- Auto-evaluation: code executed against hidden test cases in a sandboxed environment (Docker container per submission)
- Results: pass/fail per test case, partial scoring
- Time limit and memory limit per execution
- Teacher can view student's code; manual override possible

---

#### TYPE-15 — Audio / Video Response _(Optional Module)_

- Student records a response via webcam/microphone
- Stored securely; teacher reviews and grades manually
- Useful for language assessments, oral presentations

---

#### TYPE-16 — Likert Scale / Survey

- Not graded; used for course feedback and self-assessment
- 1–5 or 1–7 scale per item
- Results visible to teacher in aggregate (anonymous by default)
- Can be embedded at start or end of a test

---

### 5.6 Assessment Format Types

Beyond question types, EduTrack supports different **assessment formats**:

| Format                     | Description                                                    |
| -------------------------- | -------------------------------------------------------------- |
| **Timed Test**             | Fixed duration; auto-submits at end                            |
| **Untimed Quiz**           | No timer; submit when ready                                    |
| **Adaptive Assessment**    | Difficulty adjusts based on ongoing performance                |
| **Sectioned Exam**         | Multiple sections, each with own time limit and question types |
| **Practice Mode**          | Immediate feedback per question; not recorded in performance   |
| **Diagnostic Assessment**  | Maps student knowledge to competency matrix                    |
| **Survey / Feedback Form** | Ungraded; anonymous or identified                              |

---

## 6. Anti-Cheat & Proctoring Engine

> This section defines the complete specification of EduTrack's browser-level proctoring system. All behaviors are client-enforced AND server-validated.

### 6.1 Proctoring Philosophy

EduTrack implements a **non-intrusive but firm** proctoring approach:

- No webcam or microphone access required by default (optional module)
- No screen recording
- Behavioral signals are monitored and logged
- Violations are transparent to the student — they are warned at each event
- The system is a deterrent, not a surveillance tool

### 6.2 Fullscreen Enforcement

#### Activation

```
On assessment start:
1. Display consent modal explaining fullscreen requirement
2. Call document.documentElement.requestFullscreen() on student confirmation
3. If browser rejects (older browser): show warning and block assessment start
4. Lock body scroll; hide browser chrome via CSS pointer-events
5. Emit WebSocket event: { type: "ASSESSMENT_STARTED", fullscreen: true }
```

#### Fullscreen Exit Detection

```javascript
document.addEventListener("fullscreenchange", handleFullscreenChange);
document.addEventListener("webkitfullscreenchange", handleFullscreenChange); // Safari
document.addEventListener("mozfullscreenchange", handleFullscreenChange); // Firefox

function handleFullscreenChange() {
  if (!document.fullscreenElement) {
    triggerViolation("FULLSCREEN_EXIT");
  }
}
```

#### Exit via F11

- F11 is intercepted and suppressed during active assessment session
- `keydown` event with `key === 'F11'` → `e.preventDefault()` + `triggerViolation('F11_PRESSED')`
- Note: OS-level F11 cannot be fully suppressed in all browsers; fullscreenchange event catches the result regardless

#### Exit via Escape Key

- ESC key is intercepted during active assessment
- `key === 'Escape'` → `e.preventDefault()` (prevents fullscreen exit where API allows)
- If fullscreen still exits (browser default): `triggerViolation('ESCAPE_PRESSED')`

### 6.3 Developer Tools Detection

The following keyboard shortcuts are intercepted and blocked:

| Shortcut       | Description                                |
| -------------- | ------------------------------------------ |
| `F12`          | Open DevTools                              |
| `Ctrl+Shift+I` | Open DevTools (Inspect)                    |
| `Ctrl+Shift+J` | Open Console                               |
| `Ctrl+Shift+C` | Open Element Inspector                     |
| `Ctrl+U`       | View Page Source                           |
| `Ctrl+S`       | Save Page                                  |
| `Ctrl+P`       | Print page                                 |
| `Ctrl+Shift+P` | Chrome Command Palette                     |
| `Ctrl+A`       | Select All (blocked in non-input contexts) |
| `Ctrl+C`       | Copy (blocked outside input fields)        |
| `Ctrl+V`       | Paste (blocked outside input fields)       |
| `Ctrl+X`       | Cut (blocked outside input fields)         |
| `Ctrl+Shift+K` | Firefox DevTools Console                   |
| `Cmd+Option+I` | macOS DevTools (Safari/Chrome)             |
| `Cmd+Option+J` | macOS DevTools Console                     |
| `Cmd+Option+C` | macOS Element Inspector                    |
| `Cmd+P`        | macOS Print                                |

```javascript
document.addEventListener(
  "keydown",
  (e) => {
    const blocked = isBlockedShortcut(e);
    if (blocked) {
      e.preventDefault();
      e.stopPropagation();
      logViolationAttempt(blocked.reason);
    }
  },
  true,
); // useCapture = true to intercept before other handlers
```

#### DevTools Open Detection (Runtime)

```javascript
// Method 1: Window size differential
const devToolsOpen = () => {
  return (
    window.outerWidth - window.innerWidth > 160 ||
    window.outerHeight - window.innerHeight > 160
  );
};

// Method 2: debugger timing attack
function devToolsTimingCheck() {
  const start = performance.now();
  debugger; // pauses when DevTools is open
  const elapsed = performance.now() - start;
  if (elapsed > 100) triggerViolation("DEVTOOLS_DETECTED");
}

// Method 3: console object override detection
const detector = /./;
detector.toString = () => {
  triggerViolation("DEVTOOLS_DETECTED");
  return "";
};
console.log(detector);
```

### 6.4 Tab & Window Focus Detection

#### Tab Switch Detection

```javascript
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden") {
    triggerViolation("TAB_SWITCH");
  }
});
```

#### Window Focus Loss

```javascript
window.addEventListener("blur", () => {
  triggerViolation("WINDOW_FOCUS_LOST");
});
```

#### Alt+Tab / Cmd+Tab Detection

- Detected via `window.blur` event (fires when any OS window switcher is used)
- Logged as `ALT_TAB` violation

#### New Tab / Window Opening

```javascript
window.addEventListener("beforeunload", (e) => {
  if (assessmentInProgress) {
    e.preventDefault();
    triggerViolation("PAGE_UNLOAD_ATTEMPT");
    return (e.returnValue = "");
  }
});
```

#### Right-Click Context Menu

```javascript
document.addEventListener("contextmenu", (e) => {
  e.preventDefault();
  // Optionally log as minor violation
});
```

### 6.5 Virtual Desktop / Application Switching

- `window.blur` reliably fires when switching to another application or virtual desktop on all major OS
- Each `blur` event during active assessment triggers a `WINDOW_FOCUS_LOST` violation log entry
- Students are shown a warning overlay on focus return

### 6.6 Violation System — State Machine

```
Violation Event Received
         │
         ▼
Log violation to server (POST /api/violations)
         │
         ▼
Increment violation_count for this attempt
         │
         ▼
Deduct N minutes from remaining time (configurable, default: 2 min)
         │
         ├── violation_count == 1 → Warning Overlay: "Warning 1/3: Return to fullscreen"
         │
         ├── violation_count == 2 → Warning Overlay: "Warning 2/3: Next violation = TERMINATION"
         │
         └── violation_count >= 3 → TERMINATE ASSESSMENT
                                       Score = 0 | Grade = FAIL
                                       Lock attempt; no retry on same token
                                       Notify teacher via WebSocket
```

### 6.7 Violation Log Entry Schema

```json
{
  "violation_id": "uuid",
  "attempt_id": "uuid",
  "student_id": "uuid",
  "assessment_id": "uuid",
  "timestamp": "2026-03-15T10:23:45Z",
  "violation_type": "FULLSCREEN_EXIT | TAB_SWITCH | DEVTOOLS_DETECTED | F11_PRESSED | ...",
  "time_remaining_at_event_seconds": 1820,
  "time_deducted_seconds": 120,
  "violation_count_after": 2,
  "browser_user_agent": "Mozilla/5.0...",
  "client_ip": "192.168.1.x",
  "resolved": false
}
```

### 6.8 Configurable Proctoring Settings (Per Assessment)

| Setting                           | Default | Options                    |
| --------------------------------- | ------- | -------------------------- |
| Enforce fullscreen                | ✅ ON   | ON / OFF                   |
| Max violations before termination | 3       | 1–10                       |
| Time penalty per violation        | 2 min   | 0–10 min                   |
| Block keyboard shortcuts          | ✅ ON   | ON / OFF                   |
| Tab switch detection              | ✅ ON   | ON / OFF                   |
| DevTools detection                | ✅ ON   | ON / OFF                   |
| Right-click block                 | ✅ ON   | ON / OFF                   |
| Copy-paste block                  | ✅ ON   | ON / OFF                   |
| Randomize question order          | ✅ ON   | ON / OFF                   |
| Randomize answer order            | ✅ ON   | ON / OFF                   |
| Webcam proctoring                 | ❌ OFF  | ON / OFF (requires module) |

### 6.9 Browser Extension / Plugin Detection

- Content Security Policy (CSP) headers prevent injection from most extensions
- `window.length` and DOM mutation observer used to detect injected iframes
- `navigator.plugins` scanned for suspicious plugin signatures
- DOM MutationObserver detects injected script nodes:

```javascript
const observer = new MutationObserver((mutations) => {
  for (const mutation of mutations) {
    for (const node of mutation.addedNodes) {
      if (node.nodeName === "SCRIPT" || node.nodeName === "IFRAME") {
        triggerViolation("INJECTED_ELEMENT_DETECTED");
      }
    }
  }
});
observer.observe(document.documentElement, { childList: true, subtree: true });
```

### 6.10 Network Proctoring (Optional)

- All API calls during assessment validated server-side against expected sequence
- Unusual API call patterns (e.g., calling grade endpoints directly) flagged as `API_MANIPULATION`
- Rate limiting on answer submission endpoints prevents scripted submission attacks

---

## 7. Assessment Lifecycle

### 7.1 Complete State Diagram

```
DRAFT ──(publish)──► PUBLISHED
                          │
              ┌───────────┴───────────┐
              │ (within time window)  │ (outside time window)
              ▼                       ▼
           ACTIVE                  EXPIRED
              │
   ┌──────────┴──────────┐
   │                     │
   ▼                     ▼
ATTEMPT_IN_PROGRESS   ATTEMPT_STARTED
   │                     │
   ├── (submitted) ──► SUBMITTED
   │                     │
   └── (terminated) ──► TERMINATED (score: 0, grade: FAIL)
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
         AUTO_GRADED          PENDING_REVIEW
              │                     │
              └──────────┬──────────┘
                         ▼
                   RESULTS_RELEASED
                         │
                         ▼
                      ARCHIVED
```

### 7.2 Access Link Lifecycle

```
Teacher creates assessment
         │
         ▼
Teacher publishes → UUID token generated → Secure link created
         │
         ▼
Teacher shares link with students (copy / notification)
         │
         ▼
Student clicks link
         │
         ├── Token valid + within time window + student in group → ALLOW
         │
         ├── Token expired → "This assessment is no longer available"
         │
         ├── Token not yet active → "This assessment opens on [date/time]"
         │
         ├── Student not in group → "You are not authorized for this assessment"
         │
         ├── Max attempts reached → "You have used all available attempts"
         │
         └── Token deactivated by teacher → "This assessment has been closed"
```

### 7.3 Student Session Flow

```
1. Student opens link
2. Identity verification (logged-in session required; redirect to login if not)
3. Pre-assessment screen:
   - Assessment title, subject, group
   - Duration, number of questions, question types
   - Proctoring rules and consent
   - "Begin Assessment" button
4. Fullscreen activation
5. Assessment interface loads (questions pre-fetched, shuffled server-side)
6. Timer starts (server-side clock, synced to client every 60s)
7. Student answers questions; auto-save every 30s
8. Student submits OR timer expires OR 3rd violation → submission
9. Thank-you / confirmation screen
10. Results displayed (if immediate release) or "Results pending"
```

---

## 8. Performance Analytics & Dashboard

### 8.1 Metrics Computed Per Student

| Metric                       | Definition                                       |
| ---------------------------- | ------------------------------------------------ |
| `overall_score_avg`          | Mean score across all assessments in period      |
| `subject_score_avg`          | Mean score per subject                           |
| `pass_rate`                  | % of assessments with score ≥ passing threshold  |
| `improvement_rate`           | Score trend slope (linear regression over time)  |
| `percentile_rank`            | Student rank within their group per assessment   |
| `weak_topics`                | Topics where student score < 60% consistently    |
| `streak_count`               | Consecutive assessments above passing threshold  |
| `violation_count_total`      | Total proctoring violations across all attempts  |
| `avg_time_used`              | Average % of allowed time used before submission |
| `assessment_completion_rate` | % of assigned assessments started and submitted  |

### 8.2 Dashboard Chart Types

| Chart                          | Applicable Roles | Description                                            |
| ------------------------------ | ---------------- | ------------------------------------------------------ |
| Score Trend Line               | All              | Score over time with moving average                    |
| Radar / Spider                 | Student, Teacher | Per-subject or per-topic breakdown                     |
| Bar Chart — Score Distribution | Teacher, Admin   | Histogram of class scores per assessment               |
| Heatmap — Activity Calendar    | Admin, Teacher   | Assessment completion activity                         |
| Box Plot                       | Teacher, Admin   | Score spread per assessment (min, Q1, median, Q3, max) |
| Scatter Plot                   | Teacher          | Score vs. time spent — effort correlation              |
| Donut Chart                    | All              | Pass/Fail ratio                                        |
| Stacked Bar — Violation Types  | Teacher, Admin   | Violation breakdown by type                            |
| Table — Student Ranking        | Teacher          | Sortable/filterable rank table                         |
| Gauge Chart                    | Student          | Current GPA gauge vs. target                           |

### 8.3 At-Risk Detection

The system automatically flags students as "At Risk" when:

- Score drops below group average for 2+ consecutive assessments
- Score in any subject is below passing threshold for 3+ consecutive attempts
- Assessment completion rate falls below 70%
- Excessive violations in a period

At-risk students appear highlighted (amber / red) in the Teacher and Admin dashboards with a summary reason. Teachers receive an email/notification when a student in their group is flagged.

### 8.4 Item Analysis (Question-Level Analytics)

For each question in a graded assessment, EduTrack computes:

| Metric                         | Formula                                        |
| ------------------------------ | ---------------------------------------------- |
| **Difficulty Index (p)**       | p = (# correct) / (# total attempts)           |
| **Discrimination Index (D)**   | D = p_upper_27% − p_lower_27%                  |
| **Distractor Analysis**        | % of students who chose each wrong option      |
| **Point-Biserial Correlation** | Correlation between item score and total score |

Questions flagged as: Easy (p > 0.80), Medium, Hard (p < 0.20), or Flawed (D < 0.20 — poor discriminator).

### 8.5 Export Formats

| Export                       | Formats Available  |
| ---------------------------- | ------------------ |
| Student results (individual) | PDF, CSV           |
| Class results (all students) | Excel (.xlsx), CSV |
| Performance dashboard        | PDF (snapshot)     |
| Question analysis report     | PDF, CSV           |
| Violation log                | CSV, PDF           |
| Full course report           | PDF (multi-page)   |

---

## 9. Database Schema

### 9.1 Entity Relationship Overview

```
universities ──< departments ──< groups ──< group_enrollments >── users
                                    │
                                    └──< assessments ──< questions
                                              │               │
                                              │           question_options
                                              │
                                        assessment_attempts
                                              │
                                        ┌────┴────┐
                                   violations   answers
                                                  │
                                             graded_answers
```

### 9.2 Core Tables

```sql
-- users
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('admin','teacher','student')),
    student_id      VARCHAR(50),               -- for students only
    employee_id     VARCHAR(50),               -- for teachers only
    department_id   UUID REFERENCES departments(id),
    is_active       BOOLEAN DEFAULT TRUE,
    extra_time_factor FLOAT DEFAULT 1.0,       -- accommodation multiplier
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- groups
CREATE TABLE groups (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    subject         VARCHAR(200),
    academic_year   VARCHAR(20),
    semester        VARCHAR(20),
    teacher_id      UUID REFERENCES users(id),
    is_archived     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- group_enrollments
CREATE TABLE group_enrollments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id        UUID REFERENCES groups(id) ON DELETE CASCADE,
    student_id      UUID REFERENCES users(id) ON DELETE CASCADE,
    enrolled_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(group_id, student_id)
);

-- assessments
CREATE TABLE assessments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    assessment_type VARCHAR(20) NOT NULL CHECK (assessment_type IN ('test','quiz','survey','practice')),
    group_id        UUID REFERENCES groups(id),
    teacher_id      UUID REFERENCES users(id),
    time_limit_minutes INT,
    available_from  TIMESTAMPTZ,
    available_until TIMESTAMPTZ,
    max_attempts    INT DEFAULT 1,
    passing_score   FLOAT DEFAULT 50.0,
    score_release_policy VARCHAR(30) DEFAULT 'immediate',
    shuffle_questions BOOLEAN DEFAULT TRUE,
    shuffle_options  BOOLEAN DEFAULT TRUE,
    max_violations  INT DEFAULT 3,
    time_penalty_minutes INT DEFAULT 2,
    enforce_fullscreen BOOLEAN DEFAULT TRUE,
    access_token    UUID UNIQUE DEFAULT gen_random_uuid(),
    is_published    BOOLEAN DEFAULT FALSE,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- questions
CREATE TABLE questions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id   UUID REFERENCES assessments(id) ON DELETE CASCADE,
    question_bank_id UUID REFERENCES question_banks(id),
    question_type   VARCHAR(30) NOT NULL,
    -- Types: true_false, yes_no, mcq_single, mcq_multi, image_mcq,
    --        short_answer, essay, fill_blank, numeric, matching,
    --        ordering, categorization, hotspot, code, audio_video, likert
    content         TEXT NOT NULL,             -- HTML / Markdown / LaTeX
    image_url       VARCHAR(500),
    points          FLOAT DEFAULT 1.0,
    partial_scoring BOOLEAN DEFAULT FALSE,
    negative_marking FLOAT DEFAULT 0.0,
    order_index     INT,
    topic_tag       VARCHAR(100),
    difficulty      VARCHAR(10) CHECK (difficulty IN ('easy','medium','hard')),
    blooms_level    VARCHAR(20),
    time_suggestion_seconds INT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- question_options (for MCQ, matching, ordering, categorization)
CREATE TABLE question_options (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id     UUID REFERENCES questions(id) ON DELETE CASCADE,
    content         TEXT NOT NULL,
    is_correct      BOOLEAN DEFAULT FALSE,
    match_key       VARCHAR(100),              -- for matching type
    category_key    VARCHAR(100),              -- for categorization
    order_position  INT,                       -- correct position for ordering
    image_url       VARCHAR(500)
);

-- assessment_attempts
CREATE TABLE assessment_attempts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id   UUID REFERENCES assessments(id),
    student_id      UUID REFERENCES users(id),
    status          VARCHAR(20) DEFAULT 'in_progress'
                    CHECK (status IN ('not_started','in_progress','submitted','terminated','grading','graded')),
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    submitted_at    TIMESTAMPTZ,
    time_limit_seconds INT,                    -- actual limit incl. accommodations
    time_remaining_seconds INT,
    score_raw       FLOAT,
    score_percent   FLOAT,
    grade           VARCHAR(10),
    violation_count INT DEFAULT 0,
    termination_reason VARCHAR(100),
    server_token    UUID UNIQUE DEFAULT gen_random_uuid(),
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- student_answers
CREATE TABLE student_answers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id      UUID REFERENCES assessment_attempts(id) ON DELETE CASCADE,
    question_id     UUID REFERENCES questions(id),
    answer_text     TEXT,                      -- for open types
    selected_option_ids UUID[],               -- for MCQ types
    matched_pairs   JSONB,                     -- for matching
    ordered_ids     UUID[],                    -- for ordering
    categorized     JSONB,                     -- for categorization
    hotspot_coords  JSONB,                     -- {x, y, width, height}
    code_submission TEXT,                      -- for code type
    is_flagged      BOOLEAN DEFAULT FALSE,
    time_spent_seconds INT,
    saved_at        TIMESTAMPTZ DEFAULT NOW(),
    score_awarded   FLOAT,
    auto_graded     BOOLEAN DEFAULT FALSE,
    teacher_feedback TEXT
);

-- violations
CREATE TABLE violations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id      UUID REFERENCES assessment_attempts(id),
    student_id      UUID REFERENCES users(id),
    assessment_id   UUID REFERENCES assessments(id),
    violation_type  VARCHAR(50) NOT NULL,
    occurred_at     TIMESTAMPTZ DEFAULT NOW(),
    time_remaining_at_event INT,
    time_deducted_seconds INT,
    violation_count_after INT,
    browser_info    JSONB,
    ip_address      INET,
    resolved        BOOLEAN DEFAULT FALSE,
    notes           TEXT
);

-- performance_snapshots (materialized, updated by Celery)
CREATE TABLE performance_snapshots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id      UUID REFERENCES users(id),
    group_id        UUID REFERENCES groups(id),
    period_type     VARCHAR(20),              -- 'semester','year','all_time'
    period_label    VARCHAR(50),
    assessments_taken INT DEFAULT 0,
    assessments_passed INT DEFAULT 0,
    avg_score       FLOAT,
    best_score      FLOAT,
    worst_score     FLOAT,
    improvement_rate FLOAT,                   -- regression slope
    violation_total INT DEFAULT 0,
    at_risk         BOOLEAN DEFAULT FALSE,
    computed_at     TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 10. API Reference

### 10.1 Authentication Endpoints

```
POST   /api/v1/auth/login              Login; returns access + refresh JWT
POST   /api/v1/auth/refresh            Refresh access token
POST   /api/v1/auth/logout             Invalidate refresh token
POST   /api/v1/auth/forgot-password    Send reset email
POST   /api/v1/auth/reset-password     Reset with token
GET    /api/v1/auth/me                 Current user profile
```

### 10.2 Admin Endpoints

```
# Users
GET    /api/v1/admin/users             List all users (paginated, filterable)
POST   /api/v1/admin/users             Create user
GET    /api/v1/admin/users/{id}        Get user
PATCH  /api/v1/admin/users/{id}        Update user
DELETE /api/v1/admin/users/{id}        Deactivate user
POST   /api/v1/admin/users/bulk-import Import users from CSV

# Groups
GET    /api/v1/admin/groups            List groups
POST   /api/v1/admin/groups            Create group
PATCH  /api/v1/admin/groups/{id}       Update group
POST   /api/v1/admin/groups/{id}/enroll  Enroll students
DELETE /api/v1/admin/groups/{id}/students/{sid}  Remove student

# Reports
GET    /api/v1/admin/analytics/overview    University dashboard data
GET    /api/v1/admin/analytics/violations  Violation summary
GET    /api/v1/admin/reports/export        Export report (query: format, period)
```

### 10.3 Teacher Endpoints

```
# Assessments
GET    /api/v1/teacher/assessments          List own assessments
POST   /api/v1/teacher/assessments          Create assessment
GET    /api/v1/teacher/assessments/{id}     Get assessment detail
PATCH  /api/v1/teacher/assessments/{id}     Update assessment
DELETE /api/v1/teacher/assessments/{id}     Delete draft assessment
POST   /api/v1/teacher/assessments/{id}/publish   Publish assessment
POST   /api/v1/teacher/assessments/{id}/unpublish  Unpublish assessment
POST   /api/v1/teacher/assessments/{id}/deactivate Deactivate link

# Questions
POST   /api/v1/teacher/assessments/{id}/questions        Add question
PATCH  /api/v1/teacher/questions/{qid}                   Update question
DELETE /api/v1/teacher/questions/{qid}                   Delete question
POST   /api/v1/teacher/questions/bulk-import             Import from JSON/CSV

# Results & Grading
GET    /api/v1/teacher/assessments/{id}/attempts         List attempts
GET    /api/v1/teacher/attempts/{aid}                    Get attempt detail
PATCH  /api/v1/teacher/attempts/{aid}/grade              Manual grade submission
GET    /api/v1/teacher/groups/{gid}/analytics            Group analytics
GET    /api/v1/teacher/assessments/{id}/item-analysis    Question-level analysis

# Violations
GET    /api/v1/teacher/assessments/{id}/violations       Violations list
```

### 10.4 Student Endpoints

```
# Assessment Access
GET    /api/v1/student/take/{token}          Validate token; get assessment metadata
POST   /api/v1/student/take/{token}/start    Start attempt; receive shuffled questions
POST   /api/v1/student/attempts/{aid}/save   Auto-save answers (partial)
POST   /api/v1/student/attempts/{aid}/submit Final submission
GET    /api/v1/student/attempts/{aid}/result Get result (if released)

# Results History
GET    /api/v1/student/results               All my results
GET    /api/v1/student/results/{aid}         Specific result detail
GET    /api/v1/student/analytics/dashboard   My performance dashboard data
GET    /api/v1/student/analytics/subjects    Per-subject breakdown
```

### 10.5 Proctoring / WebSocket

```
WS     /ws/attempt/{attempt_id}?token={server_token}

Client → Server events:
  { type: "HEARTBEAT", time_remaining: 1820 }
  { type: "ANSWER_SAVE", question_id: "...", data: {...} }
  { type: "VIOLATION", violation_type: "FULLSCREEN_EXIT", time_remaining: 1820 }

Server → Client events:
  { type: "TIME_UPDATE", time_remaining: 1818 }
  { type: "TIME_PENALTY", deducted: 120, new_remaining: 1700 }
  { type: "WARNING", count: 2, message: "2nd violation: 1 warning remaining" }
  { type: "TERMINATE", reason: "MAX_VIOLATIONS", score: 0 }
  { type: "FORCE_SUBMIT", reason: "TIME_EXPIRED" }
  { type: "ASSESSMENT_DEACTIVATED", message: "Teacher closed this assessment" }
```

### 10.6 API Response Standards

```json
// Success
{
  "success": true,
  "data": { ... },
  "meta": { "page": 1, "total": 42, "per_page": 20 }
}

// Error
{
  "success": false,
  "error": {
    "code": "ASSESSMENT_NOT_FOUND",
    "message": "The requested assessment does not exist.",
    "details": {}
  }
}
```

### 10.7 Rate Limiting

| Endpoint Group          | Limit                   |
| ----------------------- | ----------------------- |
| Auth (login/reset)      | 10 req / min per IP     |
| Assessment start        | 5 req / min per student |
| Answer save (WebSocket) | 2 req / 30s per attempt |
| General API             | 200 req / min per user  |
| Export endpoints        | 5 req / min per user    |

---

## 11. Frontend Architecture

### 11.1 Application Structure

```
src/
├── app/
│   ├── router.tsx               # React Router config
│   ├── store.ts                 # Zustand global store
│   └── queryClient.ts           # React Query client config
│
├── modules/
│   ├── auth/                    # Login, reset password
│   ├── admin/
│   │   ├── users/               # User management pages
│   │   ├── groups/              # Group management
│   │   ├── analytics/           # Admin dashboard
│   │   └── reports/             # Export UI
│   ├── teacher/
│   │   ├── assessments/         # Assessment builder
│   │   ├── questions/           # Question editor, bank
│   │   ├── results/             # Grading interface
│   │   └── analytics/           # Teacher dashboard
│   └── student/
│       ├── take/                # Assessment taking UI
│       │   ├── ProctoredWrapper.tsx   # Anti-cheat HOC
│       │   ├── AssessmentShell.tsx    # Timer, nav, submit
│       │   └── questions/       # Question renderers per type
│       ├── results/             # Results view
│       └── dashboard/           # Student performance dashboard
│
├── components/
│   ├── ui/                      # shadcn/ui base components
│   ├── charts/                  # Chart components (Recharts wrappers)
│   ├── question-types/          # Reusable question display/input components
│   └── shared/                  # Navbar, Sidebar, etc.
│
├── hooks/
│   ├── useProctoring.ts         # Anti-cheat hook
│   ├── useTimer.ts              # Assessment timer
│   ├── useWebSocket.ts          # WS connection management
│   └── useAutoSave.ts           # Auto-save logic
│
├── lib/
│   ├── api.ts                   # Axios instance with interceptors
│   ├── proctoring-sdk.ts        # Violation detection engine
│   └── utils.ts
│
└── types/                       # TypeScript interfaces
```

### 11.2 Proctoring SDK — Frontend Module

```typescript
// lib/proctoring-sdk.ts

export class ProctoringSDK {
  private violationCount = 0;
  private onViolation: (v: ViolationEvent) => void;
  private onTerminate: () => void;
  private maxViolations: number;
  private listeners: Array<[string, EventListener]> = [];

  constructor(config: ProctoringConfig) {
    this.maxViolations = config.maxViolations;
    this.onViolation = config.onViolation;
    this.onTerminate = config.onTerminate;
  }

  init() {
    this.attachFullscreenListener();
    this.attachKeydownBlocker();
    this.attachVisibilityListener();
    this.attachBlurListener();
    this.attachContextMenuBlocker();
    this.attachBeforeUnloadGuard();
    this.attachDevToolsDetector();
    this.attachMutationObserver();
    this.enterFullscreen();
  }

  private triggerViolation(type: ViolationType) {
    this.violationCount++;
    const event: ViolationEvent = {
      type,
      count: this.violationCount,
      timestamp: new Date().toISOString(),
    };
    this.onViolation(event);
    if (this.violationCount >= this.maxViolations) {
      this.onTerminate();
    }
  }

  destroy() {
    this.listeners.forEach(([event, handler]) => {
      document.removeEventListener(event, handler, true);
      window.removeEventListener(event, handler, true);
    });
  }

  // ... individual attachment methods
}
```

### 11.3 Question Renderer Components

Each question type has a dedicated renderer:

```
QuestionRenderer (factory component)
   ├── TrueFalseQuestion
   ├── MCQSingleQuestion
   ├── MCQMultiQuestion
   ├── ShortAnswerQuestion
   ├── EssayQuestion (with RichTextEditor)
   ├── FillBlankQuestion (inline input fields)
   ├── NumericQuestion
   ├── MatchingQuestion (drag-and-drop pairs)
   ├── OrderingQuestion (drag-and-drop list)
   ├── CategorizationQuestion (drag into buckets)
   ├── HotspotQuestion (clickable image canvas)
   ├── CodeQuestion (Monaco Editor + result panel)
   └── LikertQuestion (scale selector)
```

---

## 12. Backend Architecture

### 12.1 FastAPI Application Structure

```
app/
├── main.py                      # App factory; mount routers
├── core/
│   ├── config.py                # Settings (pydantic-settings)
│   ├── security.py              # JWT, password hashing
│   ├── database.py              # SQLAlchemy engine + session
│   └── redis.py                 # Redis connection
│
├── api/
│   ├── deps.py                  # Dependency injection (current_user, db)
│   ├── v1/
│   │   ├── auth.py
│   │   ├── admin/
│   │   │   ├── users.py
│   │   │   ├── groups.py
│   │   │   └── analytics.py
│   │   ├── teacher/
│   │   │   ├── assessments.py
│   │   │   ├── questions.py
│   │   │   ├── results.py
│   │   │   └── analytics.py
│   │   └── student/
│   │       ├── take.py          # Assessment delivery
│   │       ├── results.py
│   │       └── analytics.py
│   └── websocket/
│       └── proctoring.py        # WS endpoint for attempt monitoring
│
├── models/                      # SQLAlchemy ORM models
├── schemas/                     # Pydantic request/response schemas
├── services/
│   ├── assessment_service.py    # Assessment business logic
│   ├── grading_service.py       # Auto-grading engine
│   ├── analytics_service.py     # Dashboard computations
│   ├── proctoring_service.py    # Violation handling
│   ├── link_service.py          # Token validation
│   └── notification_service.py  # Email / push
│
├── workers/                     # Celery tasks
│   ├── analytics_worker.py      # Periodic snapshot computation
│   ├── notification_worker.py   # Async email sending
│   └── report_worker.py         # PDF/Excel generation
│
└── alembic/                     # Database migrations
    ├── env.py
    ├── script.py.mako
    └── versions/
        ├── 0001_initial_schema.py
        ├── 0002_add_violations.py
        └── ...
```

### 12.2 Grading Service Logic

```python
# services/grading_service.py

class GradingService:
    def grade_attempt(self, attempt: AssessmentAttempt) -> GradingResult:
        total_points = 0.0
        earned_points = 0.0
        pending_manual = []

        for question in attempt.assessment.questions:
            answer = self._get_student_answer(attempt.id, question.id)

            if question.question_type in AUTO_GRADEABLE_TYPES:
                result = self._auto_grade(question, answer)
                earned_points += result.points_awarded
                total_points += question.points
            else:
                pending_manual.append(question.id)
                total_points += question.points

        score_percent = (earned_points / total_points * 100) if total_points > 0 else 0
        passed = score_percent >= attempt.assessment.passing_score

        return GradingResult(
            score_raw=earned_points,
            score_percent=score_percent,
            total_points=total_points,
            passed=passed,
            grade=self._compute_grade(score_percent),
            pending_manual_grading=len(pending_manual) > 0,
        )

    def _auto_grade(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        grader = GRADER_MAP[question.question_type]
        return grader.grade(question, answer)
```

### 12.3 Background Workers (Celery)

```python
# workers/analytics_worker.py

@celery.task(name="compute_performance_snapshots")
def compute_performance_snapshots():
    """
    Runs every hour. Recomputes performance_snapshots for
    all students who had activity in the last 2 hours.
    """

@celery.task(name="flag_at_risk_students")
def flag_at_risk_students():
    """
    Runs daily at midnight. Flags students who meet at-risk criteria.
    Sends alerts to teachers.
    """

@celery.task(name="expire_assessments")
def expire_assessments():
    """
    Runs every 5 minutes. Terminates any in-progress attempt
    whose assessment window has passed.
    """

@celery.task(name="generate_report")
def generate_report(report_config: dict, user_id: str):
    """
    Async report generation triggered by export API.
    Result stored in Redis/S3; user notified when ready.
    """
```

---

## 13. Security & Authentication

### 13.1 Authentication Flow

```
1. POST /auth/login { email, password }
2. Server: verify bcrypt hash
3. Server: issue Access Token (JWT RS256, exp: 15 min) + Refresh Token (exp: 7 days)
4. Client: store access token in memory (not localStorage)
5. Client: store refresh token in httpOnly cookie (Secure, SameSite=Strict)
6. Every request: Authorization: Bearer {access_token}
7. On 401: auto-refresh using cookie refresh token
8. On logout: server blacklists refresh token in Redis
```

### 13.2 Assessment Session Security

- `server_token` (UUID) generated on attempt start; required in WebSocket header
- All attempt-modifying API calls validated against `server_token` + `student_id` match
- Server-side timer is authoritative; client timer is display only
- Shuffled question order is generated and stored server-side on attempt start; cannot be re-fetched in different order
- Submitted answers are locked server-side; no PUT after submit

### 13.3 Link Security

- Access token is a UUIDv4 — unpredictable, single-use namespace
- Token validated against: exists, not expired, student in group, attempts not exhausted
- Tokens are not sequential or guessable
- Optional: token + student email verification step before granting access

### 13.4 Data Security

- All data in transit: TLS 1.3
- Database: encrypted at rest (PostgreSQL with pgcrypto)
- Student PII: GDPR-aware design — exportable, deletable on request
- Passwords: bcrypt with cost factor 12
- Uploaded files (essay attachments): scanned for malware (ClamAV)
- CSP headers prevent XSS and injection attacks
- SQL injection: prevented by SQLAlchemy parameterized queries (ORM only; no raw strings)
- CORS: whitelist of allowed frontend origins only

### 13.5 Audit Log

All sensitive actions are logged to an immutable `audit_log` table:

```sql
CREATE TABLE audit_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id    UUID REFERENCES users(id),
    actor_role  VARCHAR(20),
    action      VARCHAR(100),     -- e.g., 'ASSESSMENT_PUBLISHED', 'USER_DEACTIVATED'
    target_type VARCHAR(50),      -- e.g., 'Assessment', 'User'
    target_id   UUID,
    metadata    JSONB,
    ip_address  INET,
    occurred_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 14. Notifications & Communication

### 14.1 Notification Types

| Trigger                             | Recipients                   | Channel            |
| ----------------------------------- | ---------------------------- | ------------------ |
| New assessment published            | Students in group            | In-app + Email     |
| Assessment starting soon (1 hour)   | Students                     | In-app             |
| Assessment window closing (30 min)  | Students who haven't started | In-app             |
| Results released                    | Students who attempted       | In-app + Email     |
| At-risk alert                       | Teacher                      | In-app + Email     |
| Violation threshold warning         | Teacher (real-time)          | In-app (WebSocket) |
| Assessment terminated by violations | Student + Teacher            | In-app + Email     |
| Manual grading complete             | Student                      | In-app + Email     |
| Account created (welcome)           | All new users                | Email              |
| Password reset                      | User                         | Email              |

### 14.2 In-App Notification Center

- Bell icon with badge count in navbar
- Notification panel: title, body, timestamp, read status, action link
- Mark all as read
- Notification preferences: per-type opt-out for email

---

## 15. Accessibility & Internationalization

### 15.1 Accessibility (WCAG 2.1 AA)

- All interactive elements have ARIA labels
- Keyboard navigation for all features (Tab, Enter, Space, Arrow keys)
- Focus trapping in modals and assessment shell
- Color contrast ratios ≥ 4.5:1 throughout
- Screen reader announcements for timer updates and warnings
- Assessment questions support alt text on all images

### 15.2 Internationalization (i18n)

- i18next integration; all UI strings externalized
- RTL layout support (Arabic, Hebrew) via CSS logical properties
- Date/time displayed in user's local timezone
- Locale-aware number formatting for scores and analytics
- Initial languages: English (en), Russian (ru), Uzbek (uz)

---

## 16. Deployment & DevOps

### 16.1 Docker Compose (Development)

```yaml
version: "3.9"
services:
  api:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
    depends_on: [postgres, redis]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]

  postgres:
    image: postgres:15
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine

  celery_worker:
    build: ./backend
    command: celery -A app.workers worker -l info

  celery_beat:
    build: ./backend
    command: celery -A app.workers beat -l info
```

### 16.2 Environment Variables

```env
# App
SECRET_KEY=...
ENVIRONMENT=production
DEBUG=false
FRONTEND_URL=https://edutrack.university.edu

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/edutrack

# Redis
REDIS_URL=redis://:password@redis-host:6379/0

# JWT
JWT_PRIVATE_KEY=...   # RS256 private key
JWT_PUBLIC_KEY=...    # RS256 public key

# Email
SMTP_HOST=smtp.university.edu
SMTP_PORT=587
SMTP_USER=noreply@university.edu
SMTP_PASSWORD=...

# Storage (MinIO / S3)
S3_ENDPOINT=https://minio.university.edu
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_BUCKET=edutrack-media

# Code Execution Sandbox
SANDBOX_DOCKER_HOST=...
```

### 16.3 CI/CD Pipeline (GitHub Actions)

```yaml
on: [push, pull_request]
jobs:
  test:
    steps:
      - run: pytest --cov=app tests/
      - run: npm run test --prefix frontend

  lint:
    steps:
      - run: ruff check app/
      - run: npm run lint --prefix frontend

  build:
    needs: [test, lint]
    steps:
      - uses: docker/build-push-action@v5

  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: azure/k8s-deploy@v4 # or equivalent
```

---

## 17. Database Migrations — Alembic

### 17.1 Setup

```python
# alembic/env.py
from app.core.config import settings
from app.models import Base  # Import ALL models here

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
target_metadata = Base.metadata
```

### 17.2 Common Commands

```bash
# Initialize (first time)
alembic init alembic

# Create new migration (auto-detect model changes)
alembic revision --autogenerate -m "add_violations_table"

# Apply all pending migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# Rollback to specific revision
alembic downgrade 0001

# Show current revision
alembic current

# Show migration history
alembic history --verbose
```

### 17.3 Migration Best Practices

- Never edit a migration file after it has been applied to any environment
- All migrations must have both `upgrade()` and `downgrade()` functions
- Data migrations (backfills) are separate from schema migrations
- Run migrations on deployment before starting the API server
- Test downgrade path in staging before production deployment
- Migrations are transactional; a failed migration rolls back automatically

### 17.4 Example Migration

```python
# alembic/versions/0002_add_violations_table.py

def upgrade() -> None:
    op.create_table(
        'violations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('attempt_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('assessment_attempts.id'), nullable=False),
        sa.Column('violation_type', sa.String(50), nullable=False),
        sa.Column('occurred_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text('NOW()')),
        sa.Column('time_deducted_seconds', sa.Integer()),
        sa.Column('violation_count_after', sa.Integer()),
        sa.Column('browser_info', postgresql.JSONB()),
        sa.Column('ip_address', postgresql.INET()),
    )
    op.create_index('ix_violations_attempt_id', 'violations', ['attempt_id'])
    op.create_index('ix_violations_occurred_at', 'violations', ['occurred_at'])

def downgrade() -> None:
    op.drop_table('violations')
```

---

## 18. Testing Strategy

### 18.1 Test Pyramid

```
         ┌──────────────┐
         │   E2E Tests  │  Playwright — 20 critical user journeys
         ├──────────────┤
         │ Integration  │  API endpoint tests — all routes, auth, edge cases
         ├──────────────┤
         │  Unit Tests  │  Services, grading logic, utilities
         └──────────────┘
```

### 18.2 Key Test Scenarios

#### Grading Engine Tests

- True/False: correct, incorrect, unsubmitted
- MCQ-Multi: all correct, partial, none, all wrong with negative marking
- Numeric: exact match, within tolerance, outside tolerance
- Fill-blank: exact match, near match, case-insensitive

#### Proctoring Tests

- Violation count increment per event type
- Time deduction per violation
- Termination at max violations (default 3)
- Score = 0 after termination
- Lock attempt after termination (no further saves accepted)

#### Access Control Tests

- Student cannot access another student's results
- Teacher cannot access another teacher's group's data
- Expired token returns 403
- Token for wrong group returns 403

#### Concurrency Tests

- Two simultaneous submissions for same attempt (only first accepted)
- Server timer vs. client timer drift handling

### 18.3 Test Coverage Requirements

| Module                  | Minimum Coverage |
| ----------------------- | ---------------- |
| Grading service         | 95%              |
| Proctoring service      | 90%              |
| Auth & access control   | 95%              |
| Assessment delivery API | 85%              |
| Analytics service       | 80%              |
| Overall backend         | 80%              |

---

## 19. Error Handling & Logging

### 19.1 Error Codes

| Code                            | HTTP | Description                                |
| ------------------------------- | ---- | ------------------------------------------ |
| `AUTH_INVALID_CREDENTIALS`      | 401  | Wrong email or password                    |
| `AUTH_TOKEN_EXPIRED`            | 401  | JWT expired; refresh needed                |
| `AUTH_INSUFFICIENT_PERMISSIONS` | 403  | Role does not allow this action            |
| `ASSESSMENT_NOT_FOUND`          | 404  | Assessment does not exist                  |
| `ASSESSMENT_TOKEN_INVALID`      | 403  | Access token invalid or expired            |
| `ASSESSMENT_NOT_IN_WINDOW`      | 403  | Outside of availability window             |
| `ASSESSMENT_MAX_ATTEMPTS`       | 403  | No remaining attempts                      |
| `ATTEMPT_ALREADY_SUBMITTED`     | 409  | Cannot save to a submitted attempt         |
| `ATTEMPT_TERMINATED`            | 403  | Attempt was terminated by violations       |
| `STUDENT_NOT_IN_GROUP`          | 403  | Student not enrolled in assessment's group |
| `VALIDATION_ERROR`              | 422  | Request body failed validation             |
| `INTERNAL_ERROR`                | 500  | Unexpected server error                    |

### 19.2 Structured Logging

```python
import structlog
log = structlog.get_logger()

log.info("attempt.started",
    attempt_id=str(attempt.id),
    student_id=str(student.id),
    assessment_id=str(assessment.id),
    ip=request.client.host)

log.warning("violation.recorded",
    violation_type="FULLSCREEN_EXIT",
    attempt_id=str(attempt.id),
    count=violation.violation_count_after)

log.error("grading.failed",
    attempt_id=str(attempt.id),
    error=str(e),
    exc_info=True)
```

---

## 20. Future Roadmap

### Phase 2 (Next Semester)

- **Webcam Proctoring Module** — Optional face detection (TensorFlow.js) to verify student presence
- **AI Essay Grading** — LLM-based rubric scoring with confidence scores for teacher review
- **Adaptive Testing** — IRT-based dynamic question selection
- **LMS Integration** — Moodle, Canvas, Blackboard via LTI 1.3 protocol
- **Mobile App** — React Native iOS/Android client (non-proctored quizzes only)

### Phase 3 (Next Year)

- **Plagiarism Detection** — Cross-student open-answer similarity analysis (cosine similarity + MOSS for code)
- **Live Proctor Dashboard** — Real-time view of all ongoing attempts with violation feeds
- **Question Recommendation Engine** — ML-based suggestions for teachers based on student weak areas
- **Parent Portal** — Read-only access for parents/guardians of undergraduate students
- **API Webhooks** — Allow university SIS integrations (auto-enroll from LDAP/Active Directory)
- **Multi-Tenancy** — Support multiple universities on a single EduTrack instance

---

## 21. Glossary

| Term                          | Definition                                                                                             |
| ----------------------------- | ------------------------------------------------------------------------------------------------------ |
| **Assessment**                | Umbrella term for any graded or ungraded evaluation (test, quiz, survey)                               |
| **Test**                      | A formal, timed, proctored assessment counted toward academic grade                                    |
| **Quiz**                      | A shorter, typically informal assessment; may be untimed                                               |
| **Attempt**                   | A single student session taking an assessment                                                          |
| **Access Token (Link Token)** | UUID embedded in the URL that validates and scopes an assessment session                               |
| **Server Token**              | A secondary UUID issued on attempt start; used to authorize WebSocket and API calls during the session |
| **Violation**                 | A detected proctoring event (e.g., leaving fullscreen, switching tabs)                                 |
| **Termination**               | Forced end of an attempt due to exceeding max violations or time; score set to 0 / FAIL                |
| **Question Bank**             | Teacher's personal reusable repository of questions                                                    |
| **Group**                     | An academic cohort (class), assigned to one teacher, containing enrolled students                      |
| **At-Risk**                   | A system-generated flag indicating a student may be struggling, based on performance criteria          |
| **Item Analysis**             | Statistical analysis of individual question quality and difficulty                                     |
| **Discrimination Index**      | Measures how well a question differentiates high-performing from low-performing students               |
| **Partial Scoring**           | Awarding fractional points for partially correct answers                                               |
| **Score Release Policy**      | Configures when results become visible to students                                                     |
| **Alembic**                   | Python database migration tool used with SQLAlchemy                                                    |
| **Celery**                    | Python distributed task queue used for background processing                                           |
| **CSP**                       | Content Security Policy — HTTP header restricting resource loading                                     |
| **IRT**                       | Item Response Theory — statistical model for adaptive testing                                          |
| **LTI**                       | Learning Tools Interoperability — standard for integrating with LMS platforms                          |

---

_EduTrack Technical Documentation — Prepared for University Engineering Team_  
_Version 1.0.0 — This document is the authoritative technical reference for the EduTrack system._

---
