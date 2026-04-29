import uuid

import pytest

from app.models.assessment_attempt import AssessmentAttempt
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.student_answer import StudentAnswer
from app.services.grading_service import GradingService


def option(*, is_correct: bool = False) -> QuestionOption:
    return QuestionOption(id=uuid.uuid4(), content="option", is_correct=is_correct)


def question(
    question_type: str,
    *,
    points: float = 10,
    options: list[QuestionOption] | None = None,
    config: dict | None = None,
    partial_scoring: bool = False,
    negative_marking: float = 0,
) -> Question:
    q = Question(
        id=uuid.uuid4(),
        question_type=question_type,
        content="Question?",
        points=points,
        config=config,
        partial_scoring=partial_scoring,
        negative_marking=negative_marking,
    )
    q.options = options or []
    return q


def answer(q: Question, **kwargs) -> StudentAnswer:
    a = StudentAnswer(id=uuid.uuid4(), attempt_id=uuid.uuid4(), question_id=q.id, **kwargs)
    a.question = q
    return a


def grade(q: Question, a: StudentAnswer):
    return GradingService()._auto_grade(q, a)


def test_mcq_single_correct_and_incorrect_with_negative_marking():
    correct = option(is_correct=True)
    wrong = option()
    q = question("mcq_single", options=[correct, wrong], negative_marking=2)

    assert grade(q, answer(q, selected_option_ids=[correct.id])).score == 10
    assert grade(q, answer(q, selected_option_ids=[wrong.id])).score == -2


def test_mcq_multi_full_partial_and_wrong():
    correct_a = option(is_correct=True)
    correct_b = option(is_correct=True)
    wrong = option()
    q = question(
        "mcq_multi",
        options=[correct_a, correct_b, wrong],
        partial_scoring=True,
    )

    assert grade(q, answer(q, selected_option_ids=[correct_a.id, correct_b.id])).score == 10
    assert grade(q, answer(q, selected_option_ids=[correct_a.id])).score == 5
    assert grade(q, answer(q, selected_option_ids=[wrong.id])).score == 0


def test_numeric_exact_within_tolerance_and_outside_tolerance():
    q = question("numeric", config={"correct_value": 3.14, "tolerance": 0.01})

    assert grade(q, answer(q, numeric_answer=3.14)).score == 10
    assert grade(q, answer(q, numeric_answer=3.149)).score == 10
    assert grade(q, answer(q, numeric_answer=3.2)).score == 0


def test_fill_blank_exact_case_insensitive_and_incorrect():
    q = question(
        "fill_blank",
        config={"blanks": [{"accepted_answers": ["FastAPI"], "case_sensitive": False}]},
    )

    assert grade(q, answer(q, answer_text='["FastAPI"]')).score == 10
    assert grade(q, answer(q, answer_text='["fastapi"]')).score == 10
    assert grade(q, answer(q, answer_text='["Django"]')).score == 0


def test_text_and_essay_require_manual_review():
    short = question("short_answer", config={"accepted_answers": ["expected"]})
    essay = question("essay")

    short_result = grade(short, answer(short, answer_text="needs context"))
    essay_result = grade(essay, answer(essay, answer_text="long response"))

    assert short_result.auto_graded is False
    assert essay_result.auto_graded is False
    assert essay_result.feedback == "Pending teacher review."


def test_code_preview_timeout_returns_safe_error():
    q = question(
        "code",
        config={
            "language": "python",
            "execution_mode": "stdin_stdout",
            "time_limit_seconds": 1,
            "visible_test_cases": [{"input": "", "output": "done"}],
        },
    )

    result = GradingService().run_code_preview(q, "while True:\n    pass")

    assert result["passed_cases"] == 0
    assert result["cases"][0]["passed"] is False
    assert "timed out" in result["cases"][0]["error"].lower()


def test_code_preview_invalid_code_returns_safe_error():
    q = question(
        "code",
        config={
            "language": "python",
            "execution_mode": "stdin_stdout",
            "visible_test_cases": [{"input": "", "output": "ok"}],
        },
    )

    result = GradingService().run_code_preview(q, "print(")

    assert result["passed_cases"] == 0
    assert result["cases"][0]["passed"] is False
    assert result["cases"][0]["error"]


class FakeScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class FakeDb:
    def __init__(self, answers):
        self.answers = answers
        self.flushed = False

    async def execute(self, _statement):
        return FakeScalarResult(self.answers)

    async def flush(self):
        self.flushed = True


@pytest.mark.asyncio
async def test_grade_attempt_zero_total_points_is_safe():
    q = question("likert", points=0)
    attempt = AssessmentAttempt(id=uuid.uuid4(), assessment_id=uuid.uuid4(), student_id=uuid.uuid4())
    db = FakeDb([answer(q, likert_value=4)])

    result = await GradingService().grade_attempt(db, attempt)

    assert result["total_points"] == 0
    assert result["score_percent"] == 0
    assert attempt.status == "graded"
    assert db.flushed is True
