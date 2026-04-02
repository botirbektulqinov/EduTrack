"""
EduTrack — Seed Script
Creates users, groups, enrollments, assessments with diverse question types.

Usage:
    py seed.py
"""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import select

from app.core.database import Base, async_session_factory, engine
from app.models import User
from app.models.group import Group
from app.models.group_enrollment import GroupEnrollment
from app.models.assessment import Assessment
from app.models.question import Question
from app.models.question_option import QuestionOption

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

NOW = datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


# ──────────────────────────── Users ────────────────────────────

SEED_USERS = [
    {
        "email": "admin@edutrack.edu",
        "password": "Admin123!",
        "full_name": "System Administrator",
        "role": "admin",
    },
    {
        "email": "teacher@edutrack.edu",
        "password": "Teacher123!",
        "full_name": "Sarah Johnson",
        "role": "teacher",
        "employee_id": "EMP-001",
    },
    {
        "email": "student@edutrack.edu",
        "password": "Student123!",
        "full_name": "Alex Chen",
        "role": "student",
        "student_id_number": "STU-001",
    },
    {
        "email": "student2@edutrack.edu",
        "password": "Student123!",
        "full_name": "Maria Garcia",
        "role": "student",
        "student_id_number": "STU-002",
    },
    {
        "email": "student3@edutrack.edu",
        "password": "Student123!",
        "full_name": "James Wilson",
        "role": "student",
        "student_id_number": "STU-003",
    },
]


# ──────────────────────── Helper builders ──────────────────────


def make_option(question_id, content, is_correct=False, *, match_key=None, category_key=None, order_position=None):
    return QuestionOption(
        id=uuid.uuid4(),
        question_id=question_id,
        content=content,
        is_correct=is_correct,
        match_key=match_key,
        category_key=category_key,
        order_position=order_position,
    )


def make_question(assessment_id, qtype, content, points=1.0, *, order=0, difficulty="medium",
                  topic_tag=None, config=None, partial_scoring=False, explanation=None,
                  time_suggestion_seconds=None):
    return Question(
        id=uuid.uuid4(),
        assessment_id=assessment_id,
        question_type=qtype,
        content=content,
        points=points,
        order_index=order,
        difficulty=difficulty,
        topic_tag=topic_tag,
        config=config,
        partial_scoring=partial_scoring,
        explanation=explanation,
        time_suggestion_seconds=time_suggestion_seconds,
        created_at=NOW,
        updated_at=NOW,
    )


# ──────────────────── Assessment & Questions ───────────────────


def build_assessments(teacher_id: uuid.UUID, group_ids: dict[str, uuid.UUID]):
    """Return (assessments, questions, options) lists."""
    assessments = []
    questions = []
    options = []

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Assessment 1 — General Knowledge Quiz (MCQ + True/False)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    a1_id = uuid.uuid4()
    assessments.append(Assessment(
        id=a1_id, title="General Knowledge Quiz", description="Test your general knowledge across various topics.",
        assessment_type="quiz", group_id=group_ids["cs101"], teacher_id=teacher_id,
        time_limit_minutes=15, max_attempts=3, passing_score=60.0, total_points=10.0,
        shuffle_questions=True, shuffle_options=True,
        enforce_fullscreen=False, max_violations=5, time_penalty_minutes=1,
        is_published=True, is_active=True,
        available_from=NOW - timedelta(days=1), available_until=NOW + timedelta(days=30),
        created_at=NOW, updated_at=NOW,
    ))

    # Q1 — True/False
    q = make_question(a1_id, "true_false", "The Python programming language was named after Monty Python.", 1.0,
                      order=1, difficulty="easy", topic_tag="Python", explanation="Guido van Rossum named it after Monty Python's Flying Circus.")
    questions.append(q)
    options.extend([make_option(q.id, "True", True), make_option(q.id, "False", False)])

    # Q2 — True/False
    q = make_question(a1_id, "true_false", "HTTP stands for HyperText Transfer Protocol.", 1.0,
                      order=2, difficulty="easy", topic_tag="Web")
    questions.append(q)
    options.extend([make_option(q.id, "True", True), make_option(q.id, "False", False)])

    # Q3 — MCQ Single
    q = make_question(a1_id, "mcq_single", "Which data structure uses LIFO (Last In, First Out)?", 1.0,
                      order=3, difficulty="easy", topic_tag="Data Structures")
    questions.append(q)
    options.extend([
        make_option(q.id, "Queue", False),
        make_option(q.id, "Stack", True),
        make_option(q.id, "Linked List", False),
        make_option(q.id, "Tree", False),
    ])

    # Q4 — MCQ Single
    q = make_question(a1_id, "mcq_single", "What is the time complexity of binary search?", 1.0,
                      order=4, difficulty="medium", topic_tag="Algorithms")
    questions.append(q)
    options.extend([
        make_option(q.id, "O(n)", False),
        make_option(q.id, "O(log n)", True),
        make_option(q.id, "O(n²)", False),
        make_option(q.id, "O(1)", False),
    ])

    # Q5 — MCQ Multi
    q = make_question(a1_id, "mcq_multi", "Which of the following are valid Python data types? (Select all that apply)", 2.0,
                      order=5, difficulty="easy", topic_tag="Python", partial_scoring=True)
    questions.append(q)
    options.extend([
        make_option(q.id, "int", True),
        make_option(q.id, "float", True),
        make_option(q.id, "varchar", False),
        make_option(q.id, "list", True),
        make_option(q.id, "dictionary", True),
    ])

    # Q6 — Yes/No
    q = make_question(a1_id, "yes_no", "Can JavaScript run on the server side?", 1.0,
                      order=6, difficulty="easy", topic_tag="JavaScript")
    questions.append(q)
    options.extend([make_option(q.id, "Yes", True), make_option(q.id, "No", False)])

    # Q7 — MCQ Single
    q = make_question(a1_id, "mcq_single", "Which SQL keyword is used to retrieve data from a database?", 1.0,
                      order=7, difficulty="easy", topic_tag="SQL")
    questions.append(q)
    options.extend([
        make_option(q.id, "GET", False),
        make_option(q.id, "SELECT", True),
        make_option(q.id, "FETCH", False),
        make_option(q.id, "RETRIEVE", False),
    ])

    # Q8 — True/False
    q = make_question(a1_id, "true_false", "An array and a linked list have the same time complexity for insertion at the beginning.", 1.0,
                      order=8, difficulty="medium", topic_tag="Data Structures",
                      explanation="Array insertion at index 0 is O(n) while linked list is O(1).")
    questions.append(q)
    options.extend([make_option(q.id, "True", False), make_option(q.id, "False", True)])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Assessment 2 — Programming Fundamentals Exam (Short Answer, Fill-in, Numeric, Code)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    a2_id = uuid.uuid4()
    assessments.append(Assessment(
        id=a2_id, title="Programming Fundamentals Exam", description="Comprehensive exam covering programming basics, algorithms, and problem solving.",
        assessment_type="exam", group_id=group_ids["cs101"], teacher_id=teacher_id,
        time_limit_minutes=45, max_attempts=1, passing_score=50.0, total_points=30.0,
        shuffle_questions=False, shuffle_options=False,
        enforce_fullscreen=True, max_violations=3, time_penalty_minutes=2,
        block_keyboard_shortcuts=True, copy_paste_block=True,
        is_published=True, is_active=True,
        available_from=NOW - timedelta(days=1), available_until=NOW + timedelta(days=14),
        created_at=NOW, updated_at=NOW,
    ))

    # Q1 — Short Answer
    q = make_question(a2_id, "short_answer", "What keyword is used in Python to define a function?", 2.0,
                      order=1, difficulty="easy", topic_tag="Python Basics",
                      config={"accepted_answers": ["def"]},
                      explanation="The 'def' keyword is used to define functions in Python.")
    questions.append(q)

    # Q2 — Short Answer
    q = make_question(a2_id, "short_answer", "What does 'OOP' stand for?", 2.0,
                      order=2, difficulty="easy", topic_tag="OOP",
                      config={"accepted_answers": ["Object Oriented Programming", "Object-Oriented Programming"]})
    questions.append(q)

    # Q3 — Numeric
    q = make_question(a2_id, "numeric", "What is the output of: 2 ** 10?", 2.0,
                      order=3, difficulty="easy", topic_tag="Python Basics",
                      config={"correct_value": 1024, "tolerance": 0, "unit": ""})
    questions.append(q)

    # Q4 — Numeric
    q = make_question(a2_id, "numeric", "How many bits are in 1 byte?", 1.0,
                      order=4, difficulty="easy", topic_tag="Computer Architecture",
                      config={"correct_value": 8, "tolerance": 0})
    questions.append(q)

    # Q5 — Fill in the Blank
    q = make_question(a2_id, "fill_blank", "In Python, use the ___ statement to handle exceptions.", 2.0,
                      order=5, difficulty="medium", topic_tag="Error Handling",
                      config={"blanks": [{"accepted_answers": ["try", "try/except", "try-except"]}]})
    questions.append(q)

    # Q6 — Fill in the Blank
    q = make_question(a2_id, "fill_blank", "The ___ method adds an element to the end of a Python list.", 2.0,
                      order=6, difficulty="easy", topic_tag="Python Basics",
                      config={"blanks": [{"accepted_answers": ["append", ".append()", "append()"]}]})
    questions.append(q)

    # Q7 — Code
    q = make_question(a2_id, "code",
                      "Write a Python function called `factorial` that takes a positive integer n and returns n! (n factorial). Use recursion.",
                      5.0, order=7, difficulty="medium", topic_tag="Recursion",
                      config={"language": "python", "starter_code": "def factorial(n):\n    # Your code here\n    pass",
                              "test_cases": [
                                  {"input": "factorial(0)", "expected": "1"},
                                  {"input": "factorial(5)", "expected": "120"},
                                  {"input": "factorial(10)", "expected": "3628800"},
                              ]},
                      time_suggestion_seconds=300)
    questions.append(q)

    # Q8 — Code
    q = make_question(a2_id, "code",
                      "Write a Python function `is_palindrome(s)` that checks if a string is a palindrome (reads the same forwards and backwards). Ignore case.",
                      5.0, order=8, difficulty="medium", topic_tag="Strings",
                      config={"language": "python", "starter_code": "def is_palindrome(s):\n    # Your code here\n    pass",
                              "test_cases": [
                                  {"input": "is_palindrome('racecar')", "expected": "True"},
                                  {"input": "is_palindrome('Hello')", "expected": "False"},
                                  {"input": "is_palindrome('Madam')", "expected": "True"},
                              ]},
                      time_suggestion_seconds=240)
    questions.append(q)

    # Q9 — Essay
    q = make_question(a2_id, "essay",
                      "Explain the difference between a stack and a queue. Provide real-world examples for each and discuss their time complexities for common operations.",
                      5.0, order=9, difficulty="medium", topic_tag="Data Structures",
                      config={"min_words": 100, "max_words": 500},
                      time_suggestion_seconds=600)
    questions.append(q)

    # Q10 — MCQ Single
    q = make_question(a2_id, "mcq_single", "Which sorting algorithm has the best average-case time complexity?", 2.0,
                      order=10, difficulty="hard", topic_tag="Algorithms")
    questions.append(q)
    options.extend([
        make_option(q.id, "Bubble Sort — O(n²)", False),
        make_option(q.id, "Merge Sort — O(n log n)", True),
        make_option(q.id, "Selection Sort — O(n²)", False),
        make_option(q.id, "Insertion Sort — O(n²)", False),
    ])

    # Q11 — MCQ Multi
    q = make_question(a2_id, "mcq_multi", "Which of these are principles of OOP? (Select all that apply)", 2.0,
                      order=11, difficulty="medium", topic_tag="OOP", partial_scoring=True)
    questions.append(q)
    options.extend([
        make_option(q.id, "Encapsulation", True),
        make_option(q.id, "Compilation", False),
        make_option(q.id, "Inheritance", True),
        make_option(q.id, "Polymorphism", True),
        make_option(q.id, "Abstraction", True),
        make_option(q.id, "Serialization", False),
    ])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Assessment 3 — Database Concepts (Matching, Ordering, Categorization)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    a3_id = uuid.uuid4()
    assessments.append(Assessment(
        id=a3_id, title="Database Concepts Assessment", description="Test your understanding of database concepts, SQL, and data modeling.",
        assessment_type="quiz", group_id=group_ids["db201"], teacher_id=teacher_id,
        time_limit_minutes=25, max_attempts=2, passing_score=60.0, total_points=20.0,
        shuffle_questions=False, shuffle_options=False,
        enforce_fullscreen=True, max_violations=3, time_penalty_minutes=1,
        is_published=True, is_active=True,
        available_from=NOW - timedelta(days=1), available_until=NOW + timedelta(days=30),
        created_at=NOW, updated_at=NOW,
    ))

    # Q1 — Matching (SQL commands ↔ descriptions)
    q = make_question(a3_id, "matching", "Match each SQL command with its purpose:", 3.0,
                      order=1, difficulty="medium", topic_tag="SQL",
                      config={"pairs": [
                          {"left": "SELECT", "right": "Retrieve data"},
                          {"left": "INSERT", "right": "Add new records"},
                          {"left": "UPDATE", "right": "Modify existing records"},
                          {"left": "DELETE", "right": "Remove records"},
                      ]},
                      partial_scoring=True)
    questions.append(q)
    # Options represent the matchable items
    options.extend([
        make_option(q.id, "SELECT", False, match_key="Retrieve data"),
        make_option(q.id, "INSERT", False, match_key="Add new records"),
        make_option(q.id, "UPDATE", False, match_key="Modify existing records"),
        make_option(q.id, "DELETE", False, match_key="Remove records"),
    ])

    # Q2 — Ordering (Normal forms)
    q = make_question(a3_id, "ordering", "Arrange the database normal forms in order from least to most normalized:", 3.0,
                      order=2, difficulty="medium", topic_tag="Normalization")
    questions.append(q)
    options.extend([
        make_option(q.id, "1NF (First Normal Form)", False, order_position=1),
        make_option(q.id, "2NF (Second Normal Form)", False, order_position=2),
        make_option(q.id, "3NF (Third Normal Form)", False, order_position=3),
        make_option(q.id, "BCNF (Boyce-Codd Normal Form)", False, order_position=4),
    ])

    # Q3 — Categorization (SQL vs NoSQL features)
    q = make_question(a3_id, "categorization",
                      "Categorize each feature as belonging to SQL or NoSQL databases:", 3.0,
                      order=3, difficulty="medium", topic_tag="Databases",
                      config={"categories": ["SQL", "NoSQL"]},
                      partial_scoring=True)
    questions.append(q)
    options.extend([
        make_option(q.id, "Fixed schema", False, category_key="SQL"),
        make_option(q.id, "ACID transactions", False, category_key="SQL"),
        make_option(q.id, "Flexible schema", False, category_key="NoSQL"),
        make_option(q.id, "Horizontal scaling", False, category_key="NoSQL"),
        make_option(q.id, "JOINs between tables", False, category_key="SQL"),
        make_option(q.id, "Document-based storage", False, category_key="NoSQL"),
    ])

    # Q4 — MCQ Single
    q = make_question(a3_id, "mcq_single", "Which type of JOIN returns all records from both tables?", 2.0,
                      order=4, difficulty="medium", topic_tag="SQL")
    questions.append(q)
    options.extend([
        make_option(q.id, "INNER JOIN", False),
        make_option(q.id, "LEFT JOIN", False),
        make_option(q.id, "RIGHT JOIN", False),
        make_option(q.id, "FULL OUTER JOIN", True),
    ])

    # Q5 — Short Answer
    q = make_question(a3_id, "short_answer", "What SQL clause is used to filter groups of rows after aggregation?", 2.0,
                      order=5, difficulty="medium", topic_tag="SQL",
                      config={"accepted_answers": ["HAVING", "having"]})
    questions.append(q)

    # Q6 — True/False
    q = make_question(a3_id, "true_false", "A primary key can contain NULL values.", 1.0,
                      order=6, difficulty="easy", topic_tag="Constraints",
                      explanation="Primary keys must be NOT NULL and UNIQUE.")
    questions.append(q)
    options.extend([make_option(q.id, "True", False), make_option(q.id, "False", True)])

    # Q7 — Numeric
    q = make_question(a3_id, "numeric", "If a table has 1000 rows and you use LIMIT 10 OFFSET 50, how many rows are returned?", 2.0,
                      order=7, difficulty="easy", topic_tag="SQL",
                      config={"correct_value": 10, "tolerance": 0})
    questions.append(q)

    # Q8 — Essay
    q = make_question(a3_id, "essay",
                      "Explain the ACID properties of database transactions and why they are important for data integrity.",
                      4.0, order=8, difficulty="hard", topic_tag="Transactions",
                      config={"min_words": 80, "max_words": 400},
                      time_suggestion_seconds=480)
    questions.append(q)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Assessment 4 — Web Development Practical (Code-heavy + Likert survey)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    a4_id = uuid.uuid4()
    assessments.append(Assessment(
        id=a4_id, title="Web Development Practical", description="Hands-on web development assessment — write HTML, CSS, and JavaScript.",
        assessment_type="exam", group_id=group_ids["web301"], teacher_id=teacher_id,
        time_limit_minutes=60, max_attempts=1, passing_score=50.0, total_points=25.0,
        shuffle_questions=False,
        enforce_fullscreen=True, max_violations=3, time_penalty_minutes=3,
        block_keyboard_shortcuts=True, copy_paste_block=False,
        is_published=True, is_active=True,
        available_from=NOW - timedelta(hours=12), available_until=NOW + timedelta(days=7),
        created_at=NOW, updated_at=NOW,
    ))

    # Q1 — Code (HTML)
    q = make_question(a4_id, "code",
                      "Write an HTML form with fields for name (text), email (email), and a submit button. Use semantic HTML5 elements.",
                      4.0, order=1, difficulty="easy", topic_tag="HTML",
                      config={"language": "html",
                              "starter_code": "<!-- Write your HTML form here -->"},
                      time_suggestion_seconds=300)
    questions.append(q)

    # Q2 — Code (CSS)
    q = make_question(a4_id, "code",
                      "Write CSS to create a centered card component: max-width 400px, white background, rounded corners (8px), a subtle shadow, and 24px padding.",
                      4.0, order=2, difficulty="medium", topic_tag="CSS",
                      config={"language": "css",
                              "starter_code": ".card {\n  /* Your styles here */\n}"},
                      time_suggestion_seconds=240)
    questions.append(q)

    # Q3 — Code (JavaScript)
    q = make_question(a4_id, "code",
                      "Write a JavaScript function `debounce(fn, delay)` that returns a debounced version of the given function.",
                      5.0, order=3, difficulty="hard", topic_tag="JavaScript",
                      config={"language": "javascript",
                              "starter_code": "function debounce(fn, delay) {\n  // Your code here\n}"},
                      time_suggestion_seconds=360)
    questions.append(q)

    # Q4 — MCQ Single
    q = make_question(a4_id, "mcq_single", "Which HTTP method is idempotent AND safe?", 2.0,
                      order=4, difficulty="medium", topic_tag="HTTP")
    questions.append(q)
    options.extend([
        make_option(q.id, "POST", False),
        make_option(q.id, "PUT", False),
        make_option(q.id, "GET", True),
        make_option(q.id, "DELETE", False),
    ])

    # Q5 — MCQ Multi
    q = make_question(a4_id, "mcq_multi", "Which are valid CSS position values? (Select all)", 2.0,
                      order=5, difficulty="easy", topic_tag="CSS", partial_scoring=True)
    questions.append(q)
    options.extend([
        make_option(q.id, "static", True),
        make_option(q.id, "relative", True),
        make_option(q.id, "absolute", True),
        make_option(q.id, "floating", False),
        make_option(q.id, "fixed", True),
        make_option(q.id, "sticky", True),
    ])

    # Q6 — Ordering (CSS specificity)
    q = make_question(a4_id, "ordering", "Order CSS selectors from LOWEST to HIGHEST specificity:", 3.0,
                      order=6, difficulty="hard", topic_tag="CSS")
    questions.append(q)
    options.extend([
        make_option(q.id, "* (universal)", False, order_position=1),
        make_option(q.id, "div (element)", False, order_position=2),
        make_option(q.id, ".class (class)", False, order_position=3),
        make_option(q.id, "#id (ID)", False, order_position=4),
        make_option(q.id, "style=\"\" (inline)", False, order_position=5),
    ])

    # Q7 — Short Answer
    q = make_question(a4_id, "short_answer", "What does the 'async' keyword do in JavaScript?", 2.0,
                      order=7, difficulty="medium", topic_tag="JavaScript",
                      config={"accepted_answers": [
                          "makes a function return a promise",
                          "returns a promise",
                          "makes function asynchronous",
                      ]})
    questions.append(q)

    # Q8 — Likert (course survey at the end)
    q = make_question(a4_id, "likert",
                      "I feel confident in my ability to build a responsive web page.", 1.0,
                      order=8, difficulty="easy", topic_tag="Self-Assessment",
                      config={"scale": 5, "labels": ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]})
    questions.append(q)

    # Q9 — Likert
    q = make_question(a4_id, "likert",
                      "The course material was well-structured and easy to follow.", 1.0,
                      order=9, difficulty="easy", topic_tag="Self-Assessment",
                      config={"scale": 5, "labels": ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]})
    questions.append(q)

    # Q10 — Likert
    q = make_question(a4_id, "likert",
                      "I would like more hands-on coding exercises in future assessments.", 1.0,
                      order=10, difficulty="easy", topic_tag="Self-Assessment",
                      config={"scale": 5, "labels": ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]})
    questions.append(q)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Assessment 5 — Quick Math Drill (Numeric-only, fast)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    a5_id = uuid.uuid4()
    assessments.append(Assessment(
        id=a5_id, title="Quick Math Drill", description="Speed drill — answer simple math questions as fast as you can.",
        assessment_type="quiz", group_id=group_ids["cs101"], teacher_id=teacher_id,
        time_limit_minutes=5, max_attempts=5, passing_score=70.0, total_points=10.0,
        shuffle_questions=True,
        enforce_fullscreen=False, max_violations=10, time_penalty_minutes=0,
        is_published=True, is_active=True,
        available_from=NOW - timedelta(days=1), available_until=NOW + timedelta(days=60),
        created_at=NOW, updated_at=NOW,
    ))

    math_problems = [
        ("What is 15 × 13?", 195),
        ("What is 256 ÷ 16?", 16),
        ("What is 2^8?", 256),
        ("What is √144?", 12),
        ("What is 17 + 28 + 55?", 100),
        ("What is 1000 - 387?", 613),
        ("What is 7! / 5! ?", 42),
        ("How many degrees in a triangle?", 180),
        ("What is the 10th Fibonacci number?", 55),
        ("What is 0.1 + 0.2 rounded to 1 decimal?", 0.3),
    ]
    for i, (text, answer) in enumerate(math_problems, 1):
        tolerance = 0.05 if isinstance(answer, float) else 0
        q = make_question(a5_id, "numeric", text, 1.0, order=i, difficulty="easy",
                          topic_tag="Math", config={"correct_value": answer, "tolerance": tolerance})
        questions.append(q)

    return assessments, questions, options


# ──────────────────────────── Main ─────────────────────────────


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        # ── 1. Users ──
        user_map = {}  # email → User
        for user_data in SEED_USERS:
            ud = dict(user_data)
            password = ud.pop("password")
            result = await session.execute(select(User).where(User.email == ud["email"]))
            existing = result.scalar_one_or_none()
            if existing:
                user_map[ud["email"]] = existing
                print(f"  ✓ {ud['email']} already exists — skipped")
                continue
            user = User(
                id=uuid.uuid4(), password_hash=hash_password(password),
                is_active=True, extra_time_factor=1.0,
                created_at=NOW, updated_at=NOW, **ud,
            )
            session.add(user)
            await session.flush()
            user_map[ud["email"]] = user
            print(f"  + Created {ud['role']:>8}  {ud['email']}  /  {password}")

        teacher = user_map["teacher@edutrack.edu"]
        students = [user_map[e] for e in ("student@edutrack.edu", "student2@edutrack.edu", "student3@edutrack.edu")]

        # ── 2. Groups ──
        group_defs = [
            {"key": "cs101", "name": "CS 101", "subject": "Computer Science", "academic_year": "2025-2026", "semester": "Spring"},
            {"key": "db201", "name": "DB 201", "subject": "Database Systems", "academic_year": "2025-2026", "semester": "Spring"},
            {"key": "web301", "name": "WEB 301", "subject": "Web Development", "academic_year": "2025-2026", "semester": "Spring"},
        ]
        group_ids: dict[str, uuid.UUID] = {}
        for gd in group_defs:
            key = gd.pop("key")
            result = await session.execute(select(Group).where(Group.name == gd["name"], Group.teacher_id == teacher.id))
            existing = result.scalar_one_or_none()
            if existing:
                group_ids[key] = existing.id
                print(f"  ✓ Group '{gd['name']}' already exists — skipped")
                continue
            group = Group(id=uuid.uuid4(), teacher_id=teacher.id, created_at=NOW, updated_at=NOW, **gd)
            session.add(group)
            await session.flush()
            group_ids[key] = group.id
            print(f"  + Created group '{gd['name']}'")

        # ── 3. Enrollments ──
        for student in students:
            for gid in group_ids.values():
                result = await session.execute(
                    select(GroupEnrollment).where(GroupEnrollment.group_id == gid, GroupEnrollment.student_id == student.id)
                )
                if result.scalar_one_or_none():
                    continue
                session.add(GroupEnrollment(id=uuid.uuid4(), group_id=gid, student_id=student.id, enrolled_at=NOW))
        print(f"  + Enrolled {len(students)} students in {len(group_ids)} groups")

        # ── 4. Assessments ──
        # Check if any already seeded
        result = await session.execute(select(Assessment).where(Assessment.teacher_id == teacher.id).limit(1))
        if result.scalar_one_or_none():
            print("  ✓ Assessments already exist — skipping assessment seed")
        else:
            assessments, all_questions, all_options = build_assessments(teacher.id, group_ids)
            session.add_all(assessments)
            await session.flush()
            session.add_all(all_questions)
            await session.flush()
            session.add_all(all_options)
            print(f"  + Created {len(assessments)} assessments with {len(all_questions)} questions and {len(all_options)} options")

        await session.commit()

    print("\nSeed complete.")
    print("\nCredentials:")
    for u in SEED_USERS:
        print(f"  {u['role']:>8}  {u['email']}  /  {u['password']}")


if __name__ == "__main__":
    print("Seeding EduTrack database...\n")
    asyncio.run(seed())
