"""
EduTrack - Grading Service
Auto-grading engine for all supported question types.
"""

import json
import math
import re
import subprocess
import sys
import textwrap
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment_attempt import AssessmentAttempt
from app.models.question import Question
from app.models.student_answer import StudentAnswer


PYTHON_CODE_RUNNER = textwrap.dedent(
    """
    import contextlib
    import io
    import json
    import sys
    import traceback

    payload = json.loads(sys.stdin.read())
    namespace = {"__name__": "__main__"}
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    try:
        code = payload.get("code", "")
        execution_mode = payload.get("execution_mode", "stdin_stdout")

        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            if execution_mode == "function":
                exec(code, namespace)
                function_name = payload.get("function_name") or "solve"
                target = namespace.get(function_name)
                if not callable(target):
                    raise RuntimeError(f"Function '{function_name}' was not found.")
                result = target(payload.get("input", ""))
                if result is not None:
                    print(result)
            else:
                original_stdin = sys.stdin
                sys.stdin = io.StringIO(payload.get("input", ""))
                try:
                    exec(code, namespace)
                finally:
                    sys.stdin = original_stdin

        json.dump(
            {
                "ok": True,
                "stdout": stdout_buffer.getvalue(),
                "stderr": stderr_buffer.getvalue(),
            },
            sys.stdout,
        )
    except Exception:
        json.dump(
            {
                "ok": False,
                "stdout": stdout_buffer.getvalue(),
                "stderr": stderr_buffer.getvalue(),
                "error": traceback.format_exc(limit=3),
            },
            sys.stdout,
        )
    """
)


class QuestionResult:
    def __init__(self, score: float, max_score: float, auto_graded: bool = True, feedback: str = ""):
        self.score = score
        self.max_score = max_score
        self.auto_graded = auto_graded
        self.feedback = feedback


class GradingService:
    async def grade_attempt(self, db: AsyncSession, attempt: AssessmentAttempt) -> dict:
        """Grade all answers in an attempt and return a summary."""
        result = await db.execute(
            select(StudentAnswer)
            .options(selectinload(StudentAnswer.question).selectinload(Question.options))
            .where(StudentAnswer.attempt_id == attempt.id)
        )
        answers = result.scalars().all()

        total_points = 0.0
        earned_points = 0.0
        needs_manual_review = False

        for answer in answers:
            question = answer.question
            total_points += question.points

            question_result = self._auto_grade(question, answer)
            answer.score_awarded = question_result.score
            answer.auto_graded = question_result.auto_graded

            if question_result.feedback:
                answer.teacher_feedback = question_result.feedback

            if not question_result.auto_graded:
                needs_manual_review = True

            earned_points += question_result.score

        attempt.score_raw = earned_points
        attempt.score_percent = (earned_points / total_points * 100) if total_points > 0 else 0
        attempt.grade = self._compute_grade(attempt.score_percent or 0)
        attempt.status = "grading" if needs_manual_review else "graded"

        await db.flush()

        return {
            "total_points": total_points,
            "earned_points": earned_points,
            "score_percent": attempt.score_percent,
            "grade": attempt.grade,
            "needs_manual_review": needs_manual_review,
        }

    def run_code_preview(self, question: Question, code_submission: str) -> dict[str, Any]:
        config = question.config or {}
        language = str(config.get("language", "python")).lower().strip()
        execution_mode = str(config.get("execution_mode", "stdin_stdout"))
        function_name = str(config.get("function_name", "solve"))

        if language not in {"python", "py"}:
            raise ValueError("Code preview is currently available only for Python questions.")

        visible_test_cases = [
            test_case
            for test_case in self._get_code_test_cases(config)
            if not bool(test_case.get("is_hidden", False))
        ]
        if not visible_test_cases:
            raise ValueError("No visible test cases are available for this question.")

        timeout_seconds = self._bounded_int(
            config.get("time_limit_seconds"),
            default=2,
            minimum=1,
            maximum=10,
        )
        case_results = []
        passed_cases = 0

        for index, test_case in enumerate(visible_test_cases, start=1):
            run_result = self._run_python_code_submission(
                code=code_submission,
                stdin_data=str(test_case.get("input", "")),
                execution_mode=execution_mode,
                function_name=function_name,
                timeout_seconds=timeout_seconds,
            )
            expected_output = self._normalize_code_output(test_case.get("output", ""))
            actual_output = self._normalize_code_output(run_result.get("stdout", ""))
            passed = bool(run_result.get("ok")) and actual_output == expected_output

            if passed:
                passed_cases += 1

            case_results.append({
                "index": index,
                "input": str(test_case.get("input", "")),
                "expected_output": expected_output,
                "actual_output": actual_output,
                "passed": passed,
                "error": run_result.get("error"),
            })

        return {
            "language": language,
            "execution_mode": execution_mode,
            "passed_cases": passed_cases,
            "total_cases": len(visible_test_cases),
            "feedback": self._build_code_feedback([
                {
                    "index": case["index"],
                    "is_hidden": False,
                    "passed": case["passed"],
                    "expected": case["expected_output"],
                    "actual": case["actual_output"],
                    "error": case["error"],
                }
                for case in case_results
            ]),
            "cases": case_results,
        }

    def _auto_grade(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        graders = {
            "true_false": self._grade_true_false,
            "yes_no": self._grade_true_false,
            "mcq_single": self._grade_mcq_single,
            "mcq_multi": self._grade_mcq_multi,
            "image_mcq": self._grade_mcq_single,
            "short_answer": self._grade_short_answer,
            "essay": self._grade_essay,
            "fill_blank": self._grade_fill_blank,
            "numeric": self._grade_numeric,
            "matching": self._grade_matching,
            "ordering": self._grade_ordering,
            "categorization": self._grade_categorization,
            "hotspot": self._grade_hotspot,
            "code": self._grade_code,
            "audio_video": self._grade_manual,
            "likert": self._grade_likert,
        }

        grader = graders.get(question.question_type, self._grade_manual)
        return grader(question, answer)

    def _grade_true_false(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        if not answer.selected_option_ids:
            return QuestionResult(0, question.points)

        correct_ids = {str(opt.id) for opt in question.options if opt.is_correct}
        selected = {str(option_id) for option_id in answer.selected_option_ids}

        if selected == correct_ids:
            return QuestionResult(question.points, question.points, feedback="Correct!")

        penalty = question.negative_marking if question.negative_marking else 0
        return QuestionResult(-penalty, question.points, feedback="Incorrect.")

    def _grade_mcq_single(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        if not answer.selected_option_ids:
            return QuestionResult(0, question.points)

        correct_ids = {str(opt.id) for opt in question.options if opt.is_correct}
        selected = {str(option_id) for option_id in answer.selected_option_ids}

        if selected == correct_ids:
            return QuestionResult(question.points, question.points, feedback="Correct!")

        penalty = question.negative_marking if question.negative_marking else 0
        return QuestionResult(-penalty, question.points, feedback="Incorrect.")

    def _grade_mcq_multi(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        if not answer.selected_option_ids:
            return QuestionResult(0, question.points)

        correct_ids = {str(opt.id) for opt in question.options if opt.is_correct}
        selected = {str(option_id) for option_id in answer.selected_option_ids}
        total_correct = len(correct_ids)

        if total_correct == 0:
            return QuestionResult(0, question.points)

        correct_selected = len(selected & correct_ids)
        incorrect_selected = len(selected - correct_ids)

        if question.partial_scoring:
            raw = (correct_selected - incorrect_selected) / total_correct
            score = max(0, raw) * question.points
            return QuestionResult(score, question.points)

        if selected == correct_ids:
            return QuestionResult(question.points, question.points, feedback="Correct!")
        return QuestionResult(0, question.points, feedback="Incorrect.")

    def _grade_short_answer(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        if not answer.answer_text:
            return QuestionResult(0, question.points)

        config = question.config or {}
        accepted_answers = config.get("accepted_answers", [])
        case_sensitive = config.get("case_sensitive", False)
        use_regex = config.get("use_regex", False)
        student_answer = answer.answer_text.strip()

        for accepted in accepted_answers:
            if use_regex:
                flags = 0 if case_sensitive else re.IGNORECASE
                if re.fullmatch(accepted, student_answer, flags):
                    return QuestionResult(question.points, question.points, feedback="Correct!")
            else:
                if case_sensitive and student_answer == accepted.strip():
                    return QuestionResult(question.points, question.points, feedback="Correct!")
                if not case_sensitive and student_answer.lower() == accepted.strip().lower():
                    return QuestionResult(question.points, question.points, feedback="Correct!")

        return QuestionResult(0, question.points, auto_graded=False, feedback="Needs manual review.")

    def _grade_essay(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        return QuestionResult(0, question.points, auto_graded=False, feedback="Pending teacher review.")

    def _grade_fill_blank(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        config = question.config or {}
        blanks = config.get("blanks", [])

        if not blanks or not answer.answer_text:
            return QuestionResult(0, question.points)

        try:
            student_answers = json.loads(answer.answer_text)
        except (json.JSONDecodeError, TypeError):
            student_answers = [answer.answer_text]

        points_per_blank = question.points / len(blanks) if blanks else 0
        earned = 0.0

        for index, blank in enumerate(blanks):
            if index >= len(student_answers):
                continue

            student_answer = student_answers[index].strip() if student_answers[index] else ""
            accepted_answers = blank.get("accepted_answers", [])
            case_sensitive = blank.get("case_sensitive", False)

            for accepted in accepted_answers:
                if case_sensitive and student_answer == accepted.strip():
                    earned += points_per_blank
                    break
                if not case_sensitive and student_answer.lower() == accepted.strip().lower():
                    earned += points_per_blank
                    break

        return QuestionResult(earned, question.points)

    def _grade_numeric(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        if answer.numeric_answer is None:
            return QuestionResult(0, question.points)

        config = question.config or {}
        correct_value = config.get("correct_value")
        tolerance = config.get("tolerance", 0)

        if correct_value is None:
            return QuestionResult(0, question.points, auto_graded=False)

        if abs(answer.numeric_answer - correct_value) <= tolerance:
            return QuestionResult(question.points, question.points, feedback="Correct!")
        return QuestionResult(0, question.points, feedback=f"Incorrect. Expected: {correct_value}")

    def _grade_matching(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        if not answer.matched_pairs:
            return QuestionResult(0, question.points)

        correct_pairs = {}
        for option in question.options:
            if option.match_key:
                correct_pairs[str(option.id)] = option.match_key

        total_pairs = len(correct_pairs) if correct_pairs else 1
        points_per_pair = question.points / total_pairs
        earned = 0.0

        for premise_id, response_key in answer.matched_pairs.items():
            if correct_pairs.get(premise_id) == response_key:
                earned += points_per_pair

        return QuestionResult(earned, question.points)

    def _grade_ordering(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        if not answer.ordered_ids:
            return QuestionResult(0, question.points)

        correct_order = sorted(
            [option for option in question.options if option.order_position is not None],
            key=lambda option: option.order_position or 0,
        )
        correct_ids = [str(option.id) for option in correct_order]
        student_ids = [str(option_id) for option_id in answer.ordered_ids]

        if not correct_ids:
            return QuestionResult(0, question.points, auto_graded=False)

        total_positions = len(correct_ids)
        points_per_position = question.points / total_positions
        earned = 0.0

        for index, student_id in enumerate(student_ids):
            if index < len(correct_ids) and student_id == correct_ids[index]:
                earned += points_per_position

        return QuestionResult(earned, question.points)

    def _grade_categorization(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        if not answer.categorized:
            return QuestionResult(0, question.points)

        correct_categories: dict[str, set[str]] = {}
        for option in question.options:
            if option.category_key:
                correct_categories.setdefault(option.category_key, set()).add(str(option.id))

        total_items = sum(len(items) for items in correct_categories.values())
        if total_items == 0:
            return QuestionResult(0, question.points, auto_graded=False)

        points_per_item = question.points / total_items
        earned = 0.0

        for category, item_ids in answer.categorized.items():
            correct_set = correct_categories.get(category, set())
            for item_id in item_ids:
                if item_id in correct_set:
                    earned += points_per_item

        return QuestionResult(earned, question.points)

    def _grade_hotspot(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        if not answer.hotspot_coords:
            return QuestionResult(0, question.points)

        config = question.config or {}
        zones = config.get("zones", [])
        if not zones:
            return QuestionResult(0, question.points, auto_graded=False)

        coords = answer.hotspot_coords
        if isinstance(coords, dict):
            coords = [coords]

        for click in coords:
            cx, cy = click.get("x", 0), click.get("y", 0)
            for zone in zones:
                if zone.get("type") == "circle":
                    distance = math.sqrt((cx - zone["cx"]) ** 2 + (cy - zone["cy"]) ** 2)
                    if distance <= zone.get("r", 0):
                        return QuestionResult(question.points, question.points, feedback="Correct!")
                elif zone.get("type") == "rect":
                    if zone["x"] <= cx <= zone["x"] + zone["w"] and zone["y"] <= cy <= zone["y"] + zone["h"]:
                        return QuestionResult(question.points, question.points, feedback="Correct!")

        return QuestionResult(0, question.points, feedback="Incorrect region.")

    def _grade_code(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        if not answer.code_submission:
            return QuestionResult(0, question.points)

        config = question.config or {}
        language = str(config.get("language", "python")).lower().strip()
        if language not in {"python", "py"}:
            return QuestionResult(
                0,
                question.points,
                auto_graded=False,
                feedback=f"Auto-grading is currently available only for Python submissions. Submitted language: {language}.",
            )

        test_cases = self._get_code_test_cases(config)
        if not test_cases:
            return QuestionResult(
                0,
                question.points,
                auto_graded=False,
                feedback="No test cases configured for this coding question.",
            )

        execution_mode = str(config.get("execution_mode", "stdin_stdout"))
        function_name = str(config.get("function_name", "solve"))
        timeout_seconds = self._bounded_int(config.get("time_limit_seconds"), default=2, minimum=1, maximum=10)

        case_results = []
        passed_cases = 0

        for index, test_case in enumerate(test_cases, start=1):
            run_result = self._run_python_code_submission(
                code=answer.code_submission,
                stdin_data=str(test_case.get("input", "")),
                execution_mode=execution_mode,
                function_name=function_name,
                timeout_seconds=timeout_seconds,
            )

            if run_result.get("internal_error"):
                return QuestionResult(
                    0,
                    question.points,
                    auto_graded=False,
                    feedback=run_result.get("error", "Code execution failed unexpectedly."),
                )

            expected_output = self._normalize_code_output(test_case.get("output", ""))
            actual_output = self._normalize_code_output(run_result.get("stdout", ""))
            passed = bool(run_result.get("ok")) and actual_output == expected_output

            if passed:
                passed_cases += 1

            case_results.append({
                "index": index,
                "is_hidden": bool(test_case.get("is_hidden", False)),
                "passed": passed,
                "expected": expected_output,
                "actual": actual_output,
                "error": run_result.get("error"),
            })

        if question.partial_scoring:
            score = round(question.points * (passed_cases / len(test_cases)), 4)
        else:
            score = question.points if passed_cases == len(test_cases) else 0

        return QuestionResult(
            score,
            question.points,
            auto_graded=True,
            feedback=self._build_code_feedback(case_results),
        )

    def _grade_likert(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        return QuestionResult(0, 0, auto_graded=True, feedback="Survey response recorded.")

    def _grade_manual(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        return QuestionResult(0, question.points, auto_graded=False, feedback="Pending manual review.")

    @staticmethod
    def _get_code_test_cases(config: dict[str, Any]) -> list[dict[str, Any]]:
        if isinstance(config.get("test_cases"), list) and config.get("test_cases"):
            return [
                {
                    "input": str(test_case.get("input", "")),
                    "output": str(test_case.get("output", "")),
                    "is_hidden": bool(test_case.get("is_hidden", False)),
                }
                for test_case in config["test_cases"]
                if isinstance(test_case, dict)
            ]

        combined_cases: list[dict[str, Any]] = []
        for test_case in config.get("visible_test_cases", []):
            if isinstance(test_case, dict):
                combined_cases.append({
                    "input": str(test_case.get("input", "")),
                    "output": str(test_case.get("output", "")),
                    "is_hidden": False,
                })

        for test_case in config.get("hidden_test_cases", []):
            if isinstance(test_case, dict):
                combined_cases.append({
                    "input": str(test_case.get("input", "")),
                    "output": str(test_case.get("output", "")),
                    "is_hidden": True,
                })

        return combined_cases

    @staticmethod
    def _run_python_code_submission(
        *,
        code: str,
        stdin_data: str,
        execution_mode: str,
        function_name: str,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        payload = {
            "code": code,
            "input": stdin_data,
            "execution_mode": execution_mode,
            "function_name": function_name,
        }

        try:
            process = subprocess.run(
                [sys.executable, "-c", PYTHON_CODE_RUNNER],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                timeout=timeout_seconds + 1,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "stdout": "",
                "error": f"Execution timed out after {timeout_seconds}s.",
            }
        except Exception as exc:
            return {
                "ok": False,
                "stdout": "",
                "error": f"Executor failure: {exc}",
                "internal_error": True,
            }

        if not process.stdout:
            return {
                "ok": False,
                "stdout": "",
                "error": process.stderr.strip() or "Executor returned no output.",
                "internal_error": True,
            }

        try:
            return json.loads(process.stdout)
        except json.JSONDecodeError:
            return {
                "ok": False,
                "stdout": "",
                "error": "Executor produced an unreadable response.",
                "internal_error": True,
            }

    @staticmethod
    def _normalize_code_output(value: Any) -> str:
        text = "" if value is None else str(value)
        text = text.replace("\r\n", "\n").strip()
        if not text:
            return ""
        return "\n".join(line.rstrip() for line in text.split("\n")).strip()

    @staticmethod
    def _clip_text(value: str, limit: int = 80) -> str:
        if len(value) <= limit:
            return value
        return f"{value[:limit - 3]}..."

    @classmethod
    def _build_code_feedback(cls, case_results: list[dict[str, Any]]) -> str:
        total_cases = len(case_results)
        passed_cases = sum(1 for case in case_results if case["passed"])
        hidden_failures = sum(1 for case in case_results if not case["passed"] and case["is_hidden"])
        visible_failures = [case for case in case_results if not case["passed"] and not case["is_hidden"]]

        feedback_parts = [f"Passed {passed_cases}/{total_cases} test cases."]

        if visible_failures:
            failure = visible_failures[0]
            if failure.get("error"):
                error_line = str(failure["error"]).strip().splitlines()[-1]
                feedback_parts.append(
                    f"Visible case {failure['index']} failed with an error: {cls._clip_text(error_line)}"
                )
            else:
                expected = cls._clip_text(failure["expected"] or "<empty>")
                actual = cls._clip_text(failure["actual"] or "<empty>")
                feedback_parts.append(
                    f"Visible case {failure['index']} expected '{expected}' but got '{actual}'."
                )

        if hidden_failures:
            feedback_parts.append(f"{hidden_failures} hidden test case(s) failed.")

        if passed_cases == total_cases:
            feedback_parts.append("All configured test cases passed.")

        return " ".join(feedback_parts)

    @staticmethod
    def _bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        return max(minimum, min(parsed, maximum))

    @staticmethod
    def _compute_grade(score_percent: float) -> str:
        if score_percent >= 90:
            return "A"
        if score_percent >= 80:
            return "B"
        if score_percent >= 70:
            return "C"
        if score_percent >= 60:
            return "D"
        return "F"
