"""
EduTrack — Analytics Service
Dashboard computations and performance metrics.
"""

import statistics
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.group import Group
from app.models.group_enrollment import GroupEnrollment
from app.models.question import Question
from app.models.student_answer import StudentAnswer
from app.models.user import User
from app.models.violation import Violation
from app.models.performance_snapshot import PerformanceSnapshot


class AnalyticsService:

    # ── Student Analytics ──

    @staticmethod
    async def get_student_dashboard(db: AsyncSession, student_id: UUID) -> dict:
        """Compute student performance dashboard data."""
        # All graded attempts
        result = await db.execute(
            select(AssessmentAttempt)
            .where(
                AssessmentAttempt.student_id == student_id,
                AssessmentAttempt.status.in_(["submitted", "graded"]),
            )
            .order_by(AssessmentAttempt.submitted_at)
        )
        attempts = result.scalars().all()

        scores = [a.score_percent for a in attempts if a.score_percent is not None]
        passing = [s for s in scores if s >= 50]  # TODO: use assessment-specific passing score

        # Load violation count
        violation_count = (await db.execute(
            select(func.count(Violation.id)).where(Violation.student_id == student_id)
        )).scalar() or 0

        # Score trend
        score_trend = []
        for a in attempts:
            if a.score_percent is not None and a.submitted_at:
                score_trend.append({
                    "date": a.submitted_at.isoformat(),
                    "score": a.score_percent,
                    "assessment_id": str(a.assessment_id),
                })

        # Compute streak
        streak = 0
        for s in reversed(scores):
            if s >= 50:
                streak += 1
            else:
                break

        # Improvement rate (simple slope)
        improvement_rate = None
        if len(scores) >= 2:
            n = len(scores)
            x_mean = (n - 1) / 2
            y_mean = sum(scores) / n
            numerator = sum((i - x_mean) * (s - y_mean) for i, s in enumerate(scores))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            if denominator > 0:
                improvement_rate = round(numerator / denominator, 3)

        return {
            "overall_score_avg": round(sum(scores) / len(scores), 2) if scores else None,
            "pass_rate": round(len(passing) / len(scores) * 100, 2) if scores else None,
            "assessments_taken": len(attempts),
            "assessments_passed": len(passing),
            "streak_count": streak,
            "improvement_rate": improvement_rate,
            "violation_count_total": violation_count,
            "score_trend": score_trend,
            "subject_scores": [],  # Requires joining with assessments/groups
            "weak_topics": [],     # Requires per-question topic analysis
            "recent_results": score_trend[-10:] if score_trend else [],
        }

    @staticmethod
    async def get_subject_breakdown(db: AsyncSession, student_id: UUID) -> list[dict]:
        """Per-subject (group) performance breakdown for a student."""
        # Get all groups the student is enrolled in
        enrollments = (await db.execute(
            select(GroupEnrollment.group_id).where(GroupEnrollment.student_id == student_id)
        )).scalars().all()

        if not enrollments:
            return []

        breakdown = []
        for group_id in enrollments:
            group = (await db.execute(select(Group).where(Group.id == group_id))).scalar_one_or_none()
            if not group:
                continue

            # Get all assessments for this group
            assessment_ids = (await db.execute(
                select(Assessment.id).where(Assessment.group_id == group_id)
            )).scalars().all()

            if not assessment_ids:
                breakdown.append({
                    "group_id": str(group_id),
                    "group_name": group.name,
                    "subject": group.subject or group.name,
                    "assessments_taken": 0,
                    "average_score": None,
                    "pass_rate": None,
                })
                continue

            # Get student's attempts for these assessments
            result = await db.execute(
                select(AssessmentAttempt.score_percent)
                .where(
                    AssessmentAttempt.student_id == student_id,
                    AssessmentAttempt.assessment_id.in_(assessment_ids),
                    AssessmentAttempt.status.in_(["submitted", "graded"]),
                    AssessmentAttempt.score_percent.isnot(None),
                )
            )
            scores = [row[0] for row in result]
            passing = [s for s in scores if s >= 50]

            breakdown.append({
                "group_id": str(group_id),
                "group_name": group.name,
                "subject": group.subject or group.name,
                "assessments_taken": len(scores),
                "average_score": round(sum(scores) / len(scores), 2) if scores else None,
                "pass_rate": round(len(passing) / len(scores) * 100, 2) if scores else None,
            })

        return breakdown

    # ── Teacher Analytics ──

    @staticmethod
    async def get_group_analytics(db: AsyncSession, group_id: UUID, teacher_id: UUID | None = None) -> dict:
        """Aggregate analytics for all assessments within a group."""
        # Get group info
        group = (await db.execute(select(Group).where(Group.id == group_id))).scalar_one_or_none()
        if not group:
            return {}

        # Get assessments for this group
        q = select(Assessment).where(Assessment.group_id == group_id)
        if teacher_id:
            q = q.where(Assessment.teacher_id == teacher_id)
        assessments = (await db.execute(q)).scalars().all()
        assessment_ids = [a.id for a in assessments]

        if not assessment_ids:
            return {
                "group_id": str(group_id),
                "group_name": group.name,
                "total_assessments": 0,
                "total_students_enrolled": 0,
                "overall_pass_rate": None,
                "average_score": None,
                "assessment_summaries": [],
            }

        # Get enrolled student count
        enrolled_count = (await db.execute(
            select(func.count(GroupEnrollment.id)).where(GroupEnrollment.group_id == group_id)
        )).scalar() or 0

        # All graded attempts for these assessments
        result = await db.execute(
            select(AssessmentAttempt.score_percent)
            .where(
                AssessmentAttempt.assessment_id.in_(assessment_ids),
                AssessmentAttempt.status.in_(["submitted", "graded"]),
                AssessmentAttempt.score_percent.isnot(None),
            )
        )
        all_scores = [row[0] for row in result]
        passing = [s for s in all_scores if s >= 50]

        # Per-assessment summary
        summaries = []
        for a in assessments:
            stats = await AnalyticsService.get_assessment_stats(db, a.id)
            summaries.append({
                "assessment_id": str(a.id),
                "title": a.title,
                "attempts_count": stats["attempts_count"],
                "mean_score": stats["mean_score"],
                "pass_rate": stats["pass_rate"],
            })

        return {
            "group_id": str(group_id),
            "group_name": group.name,
            "total_assessments": len(assessments),
            "total_students_enrolled": enrolled_count,
            "overall_pass_rate": round(len(passing) / len(all_scores) * 100, 2) if all_scores else None,
            "average_score": round(sum(all_scores) / len(all_scores), 2) if all_scores else None,
            "assessment_summaries": summaries,
        }

    @staticmethod
    async def get_assessment_stats(db: AsyncSession, assessment_id: UUID) -> dict:
        """Per-assessment statistics: mean, median, std dev, pass rate."""
        result = await db.execute(
            select(AssessmentAttempt.score_percent)
            .where(
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.status.in_(["submitted", "graded"]),
                AssessmentAttempt.score_percent.isnot(None),
            )
        )
        scores = [row[0] for row in result]

        if not scores:
            return {
                "attempts_count": 0,
                "mean_score": None,
                "median_score": None,
                "std_deviation": None,
                "pass_rate": None,
                "min_score": None,
                "max_score": None,
            }

        passing = [s for s in scores if s >= 50]

        return {
            "attempts_count": len(scores),
            "mean_score": round(statistics.mean(scores), 2),
            "median_score": round(statistics.median(scores), 2),
            "std_deviation": round(statistics.stdev(scores), 2) if len(scores) > 1 else 0,
            "pass_rate": round(len(passing) / len(scores) * 100, 2),
            "min_score": round(min(scores), 2),
            "max_score": round(max(scores), 2),
        }

    @staticmethod
    async def get_item_analysis(db: AsyncSession, assessment_id: UUID) -> List[dict]:
        """Per-question difficulty and discrimination analysis."""
        # Get all questions
        questions_result = await db.execute(
            select(Question).where(Question.assessment_id == assessment_id)
        )
        questions = questions_result.scalars().all()

        # Get all attempts for this assessment (graded)
        attempts_result = await db.execute(
            select(AssessmentAttempt)
            .where(
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.status.in_(["submitted", "graded"]),
            )
        )
        attempts = attempts_result.scalars().all()

        if not attempts:
            return []

        attempt_ids = [a.id for a in attempts]

        analysis = []
        for question in questions:
            # Get all answers to this question
            answers_result = await db.execute(
                select(StudentAnswer).where(
                    StudentAnswer.question_id == question.id,
                    StudentAnswer.attempt_id.in_(attempt_ids),
                )
            )
            answers = answers_result.scalars().all()

            total = len(answers)
            if total == 0:
                analysis.append({
                    "question_id": str(question.id),
                    "question_type": question.question_type,
                    "content": question.content[:100],
                    "difficulty_index": None,
                    "discrimination_index": None,
                    "point_biserial": None,
                    "distractor_analysis": None,
                    "classification": "unknown",
                })
                continue

            correct = sum(1 for a in answers if a.score_awarded and a.score_awarded >= question.points)
            p = correct / total  # difficulty index

            # Classification
            if p > 0.80:
                classification = "easy"
            elif p < 0.20:
                classification = "hard"
            else:
                classification = "medium"

            analysis.append({
                "question_id": str(question.id),
                "question_type": question.question_type,
                "content": question.content[:100],
                "difficulty_index": round(p, 3),
                "discrimination_index": None,  # Requires upper/lower 27% computation
                "point_biserial": None,
                "distractor_analysis": None,
                "classification": classification,
            })

        return analysis

    # ── Admin Analytics ──

    @staticmethod
    async def get_admin_overview(db: AsyncSession) -> dict:
        """University-wide overview stats."""
        total_students = (await db.execute(
            select(func.count(User.id)).where(User.role == "student", User.is_active == True)
        )).scalar() or 0

        total_teachers = (await db.execute(
            select(func.count(User.id)).where(User.role == "teacher", User.is_active == True)
        )).scalar() or 0

        total_groups = (await db.execute(
            select(func.count(Group.id)).where(Group.is_archived == False)
        )).scalar() or 0

        total_assessments = (await db.execute(
            select(func.count(Assessment.id))
        )).scalar() or 0

        # University pass rate
        result = await db.execute(
            select(AssessmentAttempt.score_percent)
            .where(
                AssessmentAttempt.status.in_(["submitted", "graded"]),
                AssessmentAttempt.score_percent.isnot(None),
            )
        )
        all_scores = [row[0] for row in result]
        passing = [s for s in all_scores if s >= 50]
        pass_rate = round(len(passing) / len(all_scores) * 100, 2) if all_scores else None

        # Violation summary
        violation_result = await db.execute(
            select(
                Violation.violation_type,
                func.count(Violation.id).label("count"),
            ).group_by(Violation.violation_type)
        )
        violation_summary = {row.violation_type: row.count for row in violation_result}

        return {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_groups": total_groups,
            "total_assessments": total_assessments,
            "university_pass_rate": pass_rate,
            "department_stats": [],
            "violation_summary": violation_summary,
            "completion_rate": None,
            "semester_trends": [],
        }
