"""
EduTrack — Grading Service
Auto-grading engine for all 16 question types.
"""

import math
import re
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment_attempt import AssessmentAttempt
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.student_answer import StudentAnswer


class QuestionResult:
    def __init__(self, score: float, max_score: float, auto_graded: bool = True, feedback: str = ""):
        self.score = score
        self.max_score = max_score
        self.auto_graded = auto_graded
        self.feedback = feedback


class GradingService:

    async def grade_attempt(self, db: AsyncSession, attempt: AssessmentAttempt) -> dict:
        """
        Grade all answers in an attempt. Returns summary.
        """
        # Load answers with questions
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

            qr = self._auto_grade(question, answer)
            answer.score_awarded = qr.score
            answer.auto_graded = qr.auto_graded

            if qr.feedback:
                answer.teacher_feedback = qr.feedback

            if not qr.auto_graded:
                needs_manual_review = True

            earned_points += qr.score

        # Update attempt scores
        attempt.score_raw = earned_points
        attempt.score_percent = (earned_points / total_points * 100) if total_points > 0 else 0
        attempt.grade = self._compute_grade(attempt.score_percent or 0)

        if needs_manual_review:
            attempt.status = "grading"
        else:
            attempt.status = "graded"

        await db.flush()

        return {
            "total_points": total_points,
            "earned_points": earned_points,
            "score_percent": attempt.score_percent,
            "grade": attempt.grade,
            "needs_manual_review": needs_manual_review,
        }

    def _auto_grade(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        """Route to the appropriate grader based on question type."""
        graders = {
            "true_false": self._grade_true_false,
            "yes_no": self._grade_true_false,         # Same logic
            "mcq_single": self._grade_mcq_single,
            "mcq_multi": self._grade_mcq_multi,
            "image_mcq": self._grade_mcq_single,      # Same as MCQ single
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

    # ── Individual Graders ──

    def _grade_true_false(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        """TYPE-01/02: True/False, Yes/No"""
        if not answer.selected_option_ids:
            return QuestionResult(0, question.points)

        correct_ids = {str(opt.id) for opt in question.options if opt.is_correct}
        selected = {str(oid) for oid in answer.selected_option_ids}

        if selected == correct_ids:
            return QuestionResult(question.points, question.points, feedback="Correct!")
        else:
            penalty = question.negative_marking if question.negative_marking else 0
            return QuestionResult(-penalty, question.points, feedback="Incorrect.")

    def _grade_mcq_single(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        """TYPE-03/05: Single-answer MCQ"""
        if not answer.selected_option_ids:
            return QuestionResult(0, question.points)

        correct_ids = {str(opt.id) for opt in question.options if opt.is_correct}
        selected = {str(oid) for oid in answer.selected_option_ids}

        if selected == correct_ids:
            return QuestionResult(question.points, question.points, feedback="Correct!")
        else:
            penalty = question.negative_marking if question.negative_marking else 0
            return QuestionResult(-penalty, question.points, feedback="Incorrect.")

    def _grade_mcq_multi(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        """TYPE-04: Multiple-answer MCQ with partial scoring."""
        if not answer.selected_option_ids:
            return QuestionResult(0, question.points)

        correct_ids = {str(opt.id) for opt in question.options if opt.is_correct}
        selected = {str(oid) for oid in answer.selected_option_ids}
        total_correct = len(correct_ids)

        if total_correct == 0:
            return QuestionResult(0, question.points)

        correct_selected = len(selected & correct_ids)
        incorrect_selected = len(selected - correct_ids)

        if question.partial_scoring:
            # Partial: (correct_selected - incorrect_selected) / total_correct, floor 0
            raw = (correct_selected - incorrect_selected) / total_correct
            score = max(0, raw) * question.points
            return QuestionResult(score, question.points)
        else:
            # Strict: full marks only if exact match
            if selected == correct_ids:
                return QuestionResult(question.points, question.points, feedback="Correct!")
            else:
                return QuestionResult(0, question.points, feedback="Incorrect.")

    def _grade_short_answer(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        """TYPE-06: Short answer with accepted answers list."""
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
                if case_sensitive:
                    if student_answer == accepted.strip():
                        return QuestionResult(question.points, question.points, feedback="Correct!")
                else:
                    if student_answer.lower() == accepted.strip().lower():
                        return QuestionResult(question.points, question.points, feedback="Correct!")

        # Near-match: flag for teacher review
        return QuestionResult(0, question.points, auto_graded=False, feedback="Needs manual review.")

    def _grade_essay(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        """TYPE-07: Essay — always manual grading."""
        return QuestionResult(0, question.points, auto_graded=False, feedback="Pending teacher review.")

    def _grade_fill_blank(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        """TYPE-08: Fill-in-the-blank (cloze). Multiple blanks, each graded independently."""
        config = question.config or {}
        blanks = config.get("blanks", [])

        if not blanks or not answer.answer_text:
            return QuestionResult(0, question.points)

        # answer_text is JSON: ["answer1", "answer2", ...]
        import json
        try:
            student_answers = json.loads(answer.answer_text)
        except (json.JSONDecodeError, TypeError):
            student_answers = [answer.answer_text]

        points_per_blank = question.points / len(blanks) if blanks else 0
        earned = 0.0

        for i, blank in enumerate(blanks):
            if i >= len(student_answers):
                continue
            student_ans = student_answers[i].strip() if student_answers[i] else ""
            accepted = blank.get("accepted_answers", [])
            case_sensitive = blank.get("case_sensitive", False)

            for acc in accepted:
                if case_sensitive:
                    if student_ans == acc.strip():
                        earned += points_per_blank
                        break
                else:
                    if student_ans.lower() == acc.strip().lower():
                        earned += points_per_blank
                        break

        return QuestionResult(earned, question.points)

    def _grade_numeric(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        """TYPE-09: Numeric with tolerance."""
        if answer.numeric_answer is None:
            return QuestionResult(0, question.points)

        config = question.config or {}
        correct_value = config.get("correct_value")
        tolerance = config.get("tolerance", 0)

        if correct_value is None:
            return QuestionResult(0, question.points, auto_graded=False)

        if abs(answer.numeric_answer - correct_value) <= tolerance:
            return QuestionResult(question.points, question.points, feedback="Correct!")
        else:
            return QuestionResult(0, question.points, feedback=f"Incorrect. Expected: {correct_value}")

    def _grade_matching(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        """TYPE-10: Matching pairs. Partial scoring per correct pair."""
        if not answer.matched_pairs:
            return QuestionResult(0, question.points)

        # Build correct pairs from options
        correct_pairs = {}
        for opt in question.options:
            if opt.match_key:
                correct_pairs[str(opt.id)] = opt.match_key

        total_pairs = len(correct_pairs) if correct_pairs else 1
        points_per_pair = question.points / total_pairs
        earned = 0.0

        for premise_id, response_key in answer.matched_pairs.items():
            if correct_pairs.get(premise_id) == response_key:
                earned += points_per_pair

        return QuestionResult(earned, question.points)

    def _grade_ordering(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        """TYPE-11: Ordering/Sequence. Positional scoring."""
        if not answer.ordered_ids:
            return QuestionResult(0, question.points)

        # Correct order from options
        correct_order = sorted(
            [opt for opt in question.options if opt.order_position is not None],
            key=lambda o: o.order_position or 0,
        )
        correct_ids = [str(opt.id) for opt in correct_order]
        student_ids = [str(oid) for oid in answer.ordered_ids]

        if not correct_ids:
            return QuestionResult(0, question.points, auto_graded=False)

        total_positions = len(correct_ids)
        points_per_position = question.points / total_positions
        earned = 0.0

        for i, sid in enumerate(student_ids):
            if i < len(correct_ids) and sid == correct_ids[i]:
                earned += points_per_position

        return QuestionResult(earned, question.points)

    def _grade_categorization(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        """TYPE-12: Categorization/Sorting into buckets."""
        if not answer.categorized:
            return QuestionResult(0, question.points)

        # Build correct categorization from options
        correct_categories = {}
        for opt in question.options:
            if opt.category_key:
                correct_categories.setdefault(opt.category_key, set()).add(str(opt.id))

        total_items = sum(len(v) for v in correct_categories.values())
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
        """TYPE-13: Hotspot/Image annotation. Check if click is within zone."""
        if not answer.hotspot_coords:
            return QuestionResult(0, question.points)

        config = question.config or {}
        zones = config.get("zones", [])
        if not zones:
            return QuestionResult(0, question.points, auto_graded=False)

        coords = answer.hotspot_coords
        if isinstance(coords, dict):
            coords = [coords]

        # Check if any click falls within any zone
        for click in coords:
            cx, cy = click.get("x", 0), click.get("y", 0)
            for zone in zones:
                if zone.get("type") == "circle":
                    dist = math.sqrt((cx - zone["cx"])**2 + (cy - zone["cy"])**2)
                    if dist <= zone.get("r", 0):
                        return QuestionResult(question.points, question.points, feedback="Correct!")
                elif zone.get("type") == "rect":
                    if (zone["x"] <= cx <= zone["x"] + zone["w"] and
                            zone["y"] <= cy <= zone["y"] + zone["h"]):
                        return QuestionResult(question.points, question.points, feedback="Correct!")

        return QuestionResult(0, question.points, feedback="Incorrect region.")

    def _grade_code(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        """TYPE-14: Code submission — placeholder for sandbox execution."""
        # In production, this would invoke a sandboxed Docker execution
        # For now, flag for manual review
        if not answer.code_submission:
            return QuestionResult(0, question.points)
        return QuestionResult(0, question.points, auto_graded=False, feedback="Code submission pending evaluation.")

    def _grade_likert(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        """TYPE-16: Likert scale — not graded."""
        return QuestionResult(0, 0, auto_graded=True, feedback="Survey response recorded.")

    def _grade_manual(self, question: Question, answer: StudentAnswer) -> QuestionResult:
        """Fallback: requires manual grading."""
        return QuestionResult(0, question.points, auto_graded=False, feedback="Pending manual review.")

    @staticmethod
    def _compute_grade(score_percent: float) -> str:
        """Simple letter grade computation."""
        if score_percent >= 90:
            return "A"
        elif score_percent >= 80:
            return "B"
        elif score_percent >= 70:
            return "C"
        elif score_percent >= 60:
            return "D"
        else:
            return "F"
