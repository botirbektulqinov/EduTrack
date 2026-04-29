"""
EduTrack — Analytics Service
Dashboard computations and performance metrics.
"""

import statistics
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.curriculum_module import CurriculumModule
from app.models.group import Group
from app.models.group_enrollment import GroupEnrollment
from app.models.question import Question
from app.models.student_answer import StudentAnswer
from app.models.topic import Topic
from app.models.user import User
from app.models.violation import Violation
from app.models.performance_snapshot import PerformanceSnapshot
from app.services.curriculum_service import CurriculumService


class AnalyticsService:

    # ── Student Analytics ──

    @staticmethod
    async def get_student_dashboard(db: AsyncSession, student_id: UUID) -> dict:
        """Compute student performance dashboard data."""
        # All graded attempts
        result = await db.execute(
            select(AssessmentAttempt)
            .options(selectinload(AssessmentAttempt.assessment))
            .where(
                AssessmentAttempt.student_id == student_id,
                AssessmentAttempt.status.in_(["submitted", "graded"]),
            )
            .order_by(AssessmentAttempt.submitted_at)
        )
        attempts = result.scalars().all()

        scores = [a.score_percent for a in attempts if a.score_percent is not None]
        passing_attempts = [
            attempt
            for attempt in attempts
            if attempt.score_percent is not None
            and attempt.score_percent >= float(attempt.assessment.passing_score or 50)
        ]

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
        for attempt in reversed(attempts):
            score = attempt.score_percent
            passing_score = float(attempt.assessment.passing_score or 50)
            if score is not None and score >= passing_score:
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
            "pass_rate": round(len(passing_attempts) / len(scores) * 100, 2) if scores else None,
            "assessments_taken": len(attempts),
            "assessments_passed": len(passing_attempts),
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
            group = (
                await db.execute(
                    select(Group)
                    .options(selectinload(Group.curriculum_subject))
                    .where(Group.id == group_id)
                )
            ).scalar_one_or_none()
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
                    "subject": CurriculumService.group_subject_name(group) or group.name,
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
                "subject": CurriculumService.group_subject_name(group) or group.name,
                "assessments_taken": len(scores),
                "average_score": round(sum(scores) / len(scores), 2) if scores else None,
                "pass_rate": round(len(passing) / len(scores) * 100, 2) if scores else None,
            })

        return breakdown

    @staticmethod
    def _average(scores: list[float]) -> float | None:
        return round(sum(scores) / len(scores), 2) if scores else None

    @staticmethod
    def _score_delta(student_average: float | None, peer_average: float | None) -> float | None:
        if student_average is None or peer_average is None:
            return None
        return round(student_average - peer_average, 2)

    @staticmethod
    def _percentile(student_average: float | None, peer_scores: list[float]) -> float | None:
        if student_average is None or not peer_scores:
            return None
        return round(
            sum(1 for peer_score in peer_scores if peer_score <= student_average) / len(peer_scores) * 100,
            1,
        )

    @staticmethod
    def _build_comparison_item(
        key: str,
        label: str,
        description: str,
        student_average: float | None,
        peer_scores: list[float],
        peer_student_ids: set[UUID],
    ) -> dict:
        peer_average = AnalyticsService._average(peer_scores)
        return {
            "key": key,
            "label": label,
            "description": description,
            "peer_average": peer_average,
            "delta_vs_peer": AnalyticsService._score_delta(student_average, peer_average),
            "percentile_estimate": AnalyticsService._percentile(student_average, peer_scores),
            "peer_attempts": len(peer_scores),
            "peer_students": len(peer_student_ids),
        }

    @staticmethod
    async def get_student_review(
        db: AsyncSession,
        student_id: UUID,
        period: str = "semester",
        academic_year: Optional[str] = None,
        semester: Optional[str] = None,
    ) -> dict:
        student = (await db.execute(select(User).where(User.id == student_id))).scalar_one_or_none()

        enrolled_group_ids = (
            await db.execute(
                select(GroupEnrollment.group_id).where(GroupEnrollment.student_id == student_id)
            )
        ).scalars().all()

        if not enrolled_group_ids:
            return AnalyticsService._empty_student_review(
                student_name=student.full_name if student else None,
                period=period,
                academic_year=academic_year,
                semester=semester,
            )

        student_groups = (
            await db.execute(
                select(Group)
                .options(selectinload(Group.curriculum_subject))
                .where(Group.id.in_(enrolled_group_ids))
            )
        ).scalars().all()

        if not student_groups:
            return AnalyticsService._empty_student_review(
                student_name=student.full_name if student else None,
                period=period,
                academic_year=academic_year,
                semester=semester,
            )

        available_academic_years = sorted(
            {group.academic_year for group in student_groups if group.academic_year},
            reverse=True,
        )
        if not academic_year and available_academic_years:
            academic_year = available_academic_years[0]

        year_groups = [group for group in student_groups if group.academic_year == academic_year]
        available_semesters = sorted(
            {group.semester for group in year_groups if group.semester},
            reverse=True,
        )
        if period != "year" and not semester and available_semesters:
            semester = available_semesters[0]

        if period == "year":
            scope_groups = year_groups
        else:
            scope_groups = [group for group in year_groups if group.semester == semester]

        if not scope_groups:
            return AnalyticsService._empty_student_review(
                student_name=student.full_name if student else None,
                period=period,
                academic_year=academic_year,
                semester=semester,
                available_academic_years=available_academic_years,
                available_semesters=available_semesters,
            )

        period_groups_query = select(Group).options(selectinload(Group.curriculum_subject)).where(
            Group.academic_year == academic_year,
            Group.is_archived == False,
        )
        if period != "year" and semester:
            period_groups_query = period_groups_query.where(Group.semester == semester)
        period_groups = (await db.execute(period_groups_query)).scalars().all()

        if not period_groups:
            return AnalyticsService._empty_student_review(
                student_name=student.full_name if student else None,
                period=period,
                academic_year=academic_year,
                semester=semester,
                available_academic_years=available_academic_years,
                available_semesters=available_semesters,
            )

        period_group_ids = [group.id for group in period_groups]
        scope_group_ids = {group.id for group in scope_groups}
        scope_teacher_ids = {group.teacher_id for group in scope_groups if group.teacher_id}
        scope_subject_ids = {group.subject_id for group in scope_groups if group.subject_id}

        assessments = (
            await db.execute(
                select(Assessment)
                .options(
                    selectinload(Assessment.curriculum_subject),
                    selectinload(Assessment.group).selectinload(Group.curriculum_subject),
                )
                .where(Assessment.group_id.in_(period_group_ids))
            )
        ).scalars().all()

        if not assessments:
            return AnalyticsService._empty_student_review(
                student_name=student.full_name if student else None,
                period=period,
                academic_year=academic_year,
                semester=semester,
                available_academic_years=available_academic_years,
                available_semesters=available_semesters,
            )

        assessment_map = {assessment.id: assessment for assessment in assessments}
        period_assessment_ids = [assessment.id for assessment in assessments]
        scope_assessment_ids = {
            assessment.id for assessment in assessments if assessment.group_id in scope_group_ids
        }

        attempts = (
            await db.execute(
                select(AssessmentAttempt)
                .where(
                    AssessmentAttempt.assessment_id.in_(period_assessment_ids),
                    AssessmentAttempt.status.in_(["submitted", "graded"]),
                    AssessmentAttempt.score_percent.isnot(None),
                )
                .order_by(AssessmentAttempt.submitted_at)
            )
        ).scalars().all()

        student_attempts = [
            attempt
            for attempt in attempts
            if attempt.student_id == student_id and attempt.assessment_id in scope_assessment_ids
        ]
        student_scores = [attempt.score_percent for attempt in student_attempts if attempt.score_percent is not None]
        overall_score_avg = AnalyticsService._average(student_scores)
        passing_attempts = []
        score_trend = []

        for attempt in student_attempts:
            assessment = assessment_map.get(attempt.assessment_id)
            if not assessment or attempt.score_percent is None:
                continue
            if attempt.score_percent >= assessment.passing_score:
                passing_attempts.append(attempt)
            score_trend.append({
                "date": attempt.submitted_at.isoformat() if attempt.submitted_at else attempt.created_at.isoformat(),
                "score": attempt.score_percent,
                "assessment_id": str(attempt.assessment_id),
                "assessment_title": assessment.title,
                "group_name": assessment.group.name if assessment.group else None,
                "subject": CurriculumService.assessment_subject_name(assessment),
                "passed": attempt.score_percent >= assessment.passing_score,
            })

        violation_count = (
            await db.execute(
                select(func.count(Violation.id)).where(
                    Violation.student_id == student_id,
                    Violation.assessment_id.in_(scope_assessment_ids),
                )
            )
        ).scalar() or 0

        streak = 0
        for score in reversed(student_scores):
            if score >= 50:
                streak += 1
            else:
                break

        improvement_rate = None
        if len(student_scores) >= 2:
            n = len(student_scores)
            x_mean = (n - 1) / 2
            y_mean = sum(student_scores) / n
            numerator = sum((index - x_mean) * (score - y_mean) for index, score in enumerate(student_scores))
            denominator = sum((index - x_mean) ** 2 for index in range(n))
            if denominator > 0:
                improvement_rate = round(numerator / denominator, 3)

        comparison_sets: dict[str, list[AssessmentAttempt]] = {
            "group_students": [],
            "same_subject_groups": [],
            "same_teacher_groups": [],
            "university": [],
        }

        for attempt in attempts:
            if attempt.student_id == student_id or attempt.score_percent is None:
                continue

            assessment = assessment_map.get(attempt.assessment_id)
            if not assessment:
                continue
            group = assessment.group

            if attempt.assessment_id in scope_assessment_ids:
                comparison_sets["group_students"].append(attempt)

            assessment_subject_id = CurriculumService.assessment_subject_id(assessment)
            if assessment_subject_id and assessment_subject_id in scope_subject_ids:
                comparison_sets["same_subject_groups"].append(attempt)

            if group and group.teacher_id in scope_teacher_ids:
                comparison_sets["same_teacher_groups"].append(attempt)

            comparison_sets["university"].append(attempt)

        comparison_matrix = [
            AnalyticsService._build_comparison_item(
                "group_students",
                "Group students",
                "Other graded attempts from the same groups in the selected scope.",
                overall_score_avg,
                [attempt.score_percent for attempt in comparison_sets["group_students"] if attempt.score_percent is not None],
                {attempt.student_id for attempt in comparison_sets["group_students"]},
            ),
            AnalyticsService._build_comparison_item(
                "same_subject_groups",
                "Same subject groups",
                "Students in other groups taking assessments mapped to the same subjects.",
                overall_score_avg,
                [attempt.score_percent for attempt in comparison_sets["same_subject_groups"] if attempt.score_percent is not None],
                {attempt.student_id for attempt in comparison_sets["same_subject_groups"]},
            ),
            AnalyticsService._build_comparison_item(
                "same_teacher_groups",
                "Same teacher groups",
                "Other students taught by the same teacher cohort in this scope.",
                overall_score_avg,
                [attempt.score_percent for attempt in comparison_sets["same_teacher_groups"] if attempt.score_percent is not None],
                {attempt.student_id for attempt in comparison_sets["same_teacher_groups"]},
            ),
            AnalyticsService._build_comparison_item(
                "university",
                "University",
                "All graded attempts across the university in the selected scope.",
                overall_score_avg,
                [attempt.score_percent for attempt in comparison_sets["university"] if attempt.score_percent is not None],
                {attempt.student_id for attempt in comparison_sets["university"]},
            ),
        ]

        comparison_summary = comparison_matrix[0] if comparison_matrix else None

        subject_stats: dict[str, dict[str, object]] = {}
        for attempt in student_attempts:
            if attempt.score_percent is None:
                continue
            assessment = assessment_map.get(attempt.assessment_id)
            if not assessment:
                continue
            subject_id = str(CurriculumService.assessment_subject_id(assessment) or assessment.group_id or assessment.id)
            subject_name = CurriculumService.assessment_subject_name(assessment) or "Unassigned subject"
            stats = subject_stats.setdefault(
                subject_id,
                {
                    "subject_id": subject_id,
                    "subject_name": subject_name,
                    "scores": [],
                    "peer_scores": [],
                    "assessment_titles": set(),
                },
            )
            stats["scores"].append(attempt.score_percent)
            stats["assessment_titles"].add(assessment.title)

        for attempt in comparison_sets["same_subject_groups"]:
            if attempt.score_percent is None:
                continue
            assessment = assessment_map.get(attempt.assessment_id)
            if not assessment:
                continue
            subject_id = str(CurriculumService.assessment_subject_id(assessment) or assessment.group_id or assessment.id)
            stats = subject_stats.setdefault(
                subject_id,
                {
                    "subject_id": subject_id,
                    "subject_name": CurriculumService.assessment_subject_name(assessment) or "Unassigned subject",
                    "scores": [],
                    "peer_scores": [],
                    "assessment_titles": set(),
                },
            )
            stats["peer_scores"].append(attempt.score_percent)

        subject_scores = []
        for stats in subject_stats.values():
            scores = stats["scores"]
            peer_scores = stats["peer_scores"]
            average_score = AnalyticsService._average(scores)
            peer_average = AnalyticsService._average(peer_scores)
            pass_rate = round(sum(1 for score in scores if score >= 50) / len(scores) * 100, 2) if scores else None
            subject_scores.append({
                "subject_id": stats["subject_id"],
                "subject_name": stats["subject_name"],
                "assessments_taken": len(scores),
                "assessment_titles": sorted(stats["assessment_titles"]),
                "average_score": average_score,
                "peer_average": peer_average,
                "delta_vs_peer": AnalyticsService._score_delta(average_score, peer_average),
                "pass_rate": pass_rate,
            })
        subject_scores.sort(key=lambda item: item["average_score"] if item["average_score"] is not None else -1, reverse=True)

        topic_rows = (
            await db.execute(
                select(StudentAnswer, Question, Topic)
                .join(Question, StudentAnswer.question_id == Question.id)
                .outerjoin(Topic, Question.topic_id == Topic.id)
                .where(
                    StudentAnswer.attempt_id.in_([attempt.id for attempt in student_attempts]),
                    (Question.topic_tag.isnot(None) | Question.topic_id.isnot(None)),
                )
            )
        ).all()

        topic_stats: dict[str, dict[str, float]] = {}
        for answer, question, topic in topic_rows:
            topic_name = topic.name.strip() if topic and topic.name else (question.topic_tag or "").strip()
            if not topic_name or question.points <= 0:
                continue
            earned = answer.score_awarded if answer.score_awarded is not None else 0.0
            ratio = max(0.0, min(earned / question.points, 1.0))
            if topic_name not in topic_stats:
                topic_stats[topic_name] = {"ratio_sum": 0.0, "count": 0.0}
            topic_stats[topic_name]["ratio_sum"] += ratio
            topic_stats[topic_name]["count"] += 1

        topic_performance = []
        for topic_name, stats in sorted(topic_stats.items(), key=lambda item: item[1]["ratio_sum"] / item[1]["count"]):
            attempts_count = int(stats["count"])
            average_score = round((stats["ratio_sum"] / stats["count"]) * 100, 2)
            topic_performance.append({
                "topic": topic_name,
                "average_score": average_score,
                "attempts": attempts_count,
                "needs_attention": attempts_count >= 2 and average_score < 60,
            })

        weak_topics = [item["topic"] for item in topic_performance if item["needs_attention"]][:5]
        if not weak_topics:
            weak_topics = [item["topic"] for item in topic_performance[:3] if item["average_score"] < 70]

        period_breakdown = []
        if period == "year":
            semester_labels = sorted({group.semester for group in scope_groups if group.semester})
            for semester_label in semester_labels:
                semester_scores = []
                for attempt in student_attempts:
                    assessment = assessment_map.get(attempt.assessment_id)
                    if not assessment or not assessment.group or assessment.group.semester != semester_label:
                        continue
                    if attempt.score_percent is not None:
                        semester_scores.append(attempt.score_percent)
                period_breakdown.append({
                    "label": semester_label,
                    "average_score": AnalyticsService._average(semester_scores),
                    "pass_rate": round(sum(1 for score in semester_scores if score >= 50) / len(semester_scores) * 100, 2) if semester_scores else None,
                    "assessments_taken": len(semester_scores),
                })

        strongest_subject = subject_scores[0]["subject_name"] if subject_scores else None
        weakest_subject = subject_scores[-1]["subject_name"] if subject_scores else None

        insights = []
        if overall_score_avg is None:
            insights.append("No graded assessments are available in this scope yet.")
        else:
            group_delta = comparison_summary["delta_vs_peer"] if comparison_summary else None
            if group_delta is not None:
                if group_delta >= 5:
                    insights.append(f"You are performing {group_delta:.1f} points above your group cohort.")
                elif group_delta <= -5:
                    insights.append(f"You are performing {abs(group_delta):.1f} points below your group cohort.")

            university_delta = next(
                (item["delta_vs_peer"] for item in comparison_matrix if item["key"] == "university"),
                None,
            )
            if university_delta is not None:
                if university_delta >= 5:
                    insights.append(f"You are ahead of the university benchmark by {university_delta:.1f} points.")
                elif university_delta <= -5:
                    insights.append(f"You are trailing the university benchmark by {abs(university_delta):.1f} points.")

            if improvement_rate is not None:
                if improvement_rate >= 2:
                    insights.append("Your scores are trending upward across recent graded attempts.")
                elif improvement_rate <= -2:
                    insights.append("Your scores are trending downward and may need intervention.")

            if strongest_subject and weakest_subject and strongest_subject != weakest_subject:
                insights.append(f"Strongest subject: {strongest_subject}. Weakest subject: {weakest_subject}.")

            if weak_topics:
                insights.append(f"Focus revision on: {', '.join(weak_topics[:3])}.")

            if violation_count >= 3:
                insights.append("Repeated proctoring violations are appearing in this scope.")

        recent_results = list(reversed(score_trend[-8:]))
        pass_rate = round(len(passing_attempts) / len(student_scores) * 100, 2) if student_scores else None

        return {
            "student_name": student.full_name if student else None,
            "period": period,
            "selected_academic_year": academic_year,
            "selected_semester": semester if period != "year" else None,
            "available_academic_years": available_academic_years,
            "available_semesters": available_semesters,
            "overall_score_avg": overall_score_avg,
            "pass_rate": pass_rate,
            "assessments_taken": len(student_attempts),
            "assessments_passed": len(passing_attempts),
            "streak_count": streak,
            "improvement_rate": improvement_rate,
            "violation_count_total": violation_count,
            "score_trend": score_trend,
            "subject_scores": subject_scores,
            "weak_topics": weak_topics,
            "topic_performance": topic_performance,
            "comparison_summary": comparison_summary,
            "comparison_matrix": comparison_matrix,
            "period_breakdown": period_breakdown,
            "insights": insights,
            "recent_results": recent_results,
        }

    @staticmethod
    async def get_student_semester_performance(db: AsyncSession, student_id: UUID, teacher_id: UUID, semester: Optional[str] = None) -> dict:
        """Dashboard data for a student, filtered by semester, accessible only if taught by teacher."""
        student = (await db.execute(select(User).where(User.id == student_id))).scalar_one_or_none()

        # 1. Get all enrollments for the student
        enrollments = (await db.execute(
            select(GroupEnrollment.group_id).where(GroupEnrollment.student_id == student_id)
        )).scalars().all()

        if not enrollments:
            return AnalyticsService._empty_student_dashboard()

        # 2. Get the groups
        groups_result = await db.execute(
            select(Group)
            .options(selectinload(Group.curriculum_subject))
            .where(Group.id.in_(enrollments))
        )
        groups = groups_result.scalars().all()

        if not groups:
            return AnalyticsService._empty_student_dashboard()

        groups_in_scope = groups
        if teacher_id:
            groups_in_scope = [g for g in groups if g.teacher_id == teacher_id]
            if not groups_in_scope:
                return AnalyticsService._empty_student_dashboard()

        available_semesters = sorted({g.semester for g in groups_in_scope if g.semester}, reverse=True)

        if not semester:
            if not available_semesters:
                return AnalyticsService._empty_student_dashboard()
            semester = available_semesters[0]

        # Filter groups by the chosen semester
        semester_groups = [g for g in groups_in_scope if g.semester == semester]
        if not semester_groups:
            return AnalyticsService._empty_student_dashboard()

        # 4. Filter strictly for assessments linked to `semester_groups`
        semester_group_ids = [g.id for g in semester_groups]
        semester_assessments = (await db.execute(
            select(Assessment).where(Assessment.group_id.in_(semester_group_ids))
        )).scalars().all()
        assessment_ids = [assessment.id for assessment in semester_assessments]

        if not assessment_ids:
            return AnalyticsService._empty_student_dashboard()

        assessment_map = {assessment.id: assessment for assessment in semester_assessments}
        group_map = {group.id: group for group in semester_groups}

        # 5. Fetch attempts
        result = await db.execute(
            select(AssessmentAttempt)
            .where(
                AssessmentAttempt.student_id == student_id,
                AssessmentAttempt.assessment_id.in_(assessment_ids),
                AssessmentAttempt.status.in_(["submitted", "graded"])
            )
            .order_by(AssessmentAttempt.submitted_at)
        )
        attempts = result.scalars().all()

        scores = [a.score_percent for a in attempts if a.score_percent is not None]
        passing = [s for s in scores if s >= 50]

        # Violation count
        violation_count = (await db.execute(
            select(func.count(Violation.id)).where(
                Violation.student_id == student_id,
                Violation.assessment_id.in_(assessment_ids)
            )
        )).scalar() or 0

        # Score trend
        score_trend = []
        for a in attempts:
            if a.score_percent is not None and a.submitted_at:
                assessment = assessment_map.get(a.assessment_id)
                group = group_map.get(assessment.group_id) if assessment and assessment.group_id else None
                score_trend.append({
                    "date": a.submitted_at.isoformat(),
                    "score": a.score_percent,
                    "assessment_id": str(a.assessment_id),
                    "assessment_title": assessment.title if assessment else str(a.assessment_id),
                    "group_name": group.name if group else None,
                    "subject": CurriculumService.group_subject_name(group) if group else None,
                    "passed": a.score_percent >= (assessment.passing_score if assessment else 50),
                })

        # Streak
        streak = 0
        for s in reversed(scores):
            if s >= 50:
                streak += 1
            else:
                break

        # Improvement rate
        improvement_rate = None
        if len(scores) >= 2:
            n = len(scores)
            x_mean = (n - 1) / 2
            y_mean = sum(scores) / n
            numerator = sum((i - x_mean) * (s - y_mean) for i, s in enumerate(scores))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            if denominator > 0:
                improvement_rate = round(numerator / denominator, 3)

        peer_result = await db.execute(
            select(
                AssessmentAttempt.assessment_id,
                AssessmentAttempt.student_id,
                AssessmentAttempt.score_percent,
            )
            .where(
                AssessmentAttempt.assessment_id.in_(assessment_ids),
                AssessmentAttempt.status.in_(["submitted", "graded"]),
                AssessmentAttempt.score_percent.isnot(None),
            )
        )
        peer_attempt_rows = peer_result.all()
        peer_scores = [row.score_percent for row in peer_attempt_rows if row.student_id != student_id]

        # Subject scores
        subject_scores = []
        for g in semester_groups:
            group_assessment_ids = [assessment.id for assessment in semester_assessments if assessment.group_id == g.id]
            if not group_assessment_ids:
                continue
            group_scores = [a.score_percent for a in attempts if a.assessment_id in group_assessment_ids and a.score_percent is not None]
            group_passing = [s for s in group_scores if s >= 50]
            group_peer_scores = [
                row.score_percent
                for row in peer_attempt_rows
                if row.assessment_id in group_assessment_ids and row.student_id != student_id
            ]
            if group_scores:
                average_score = round(sum(group_scores) / len(group_scores), 2)
                group_average = round(sum(group_peer_scores) / len(group_peer_scores), 2) if group_peer_scores else None
                subject_scores.append({
                    "group_id": str(g.id),
                    "group_name": g.name,
                    "subject": CurriculumService.group_subject_name(g) or g.name,
                    "assessments_taken": len(group_scores),
                    "average_score": average_score,
                    "pass_rate": round(len(group_passing) / len(group_scores) * 100, 2),
                    "group_average": group_average,
                    "delta_from_group_avg": round(average_score - group_average, 2) if group_average is not None else None,
                })

        topic_rows = (await db.execute(
            select(StudentAnswer, Question, Topic)
            .join(Question, StudentAnswer.question_id == Question.id)
            .outerjoin(Topic, Question.topic_id == Topic.id)
            .where(
                StudentAnswer.attempt_id.in_([attempt.id for attempt in attempts]),
                (Question.topic_tag.isnot(None) | Question.topic_id.isnot(None)),
            )
        )).all()

        topic_stats: dict[str, dict[str, float]] = {}
        for answer, question, topic in topic_rows:
            topic_name = (
                topic.name.strip()
                if topic and topic.name
                else (question.topic_tag or "").strip()
            )
            if not topic_name or question.points <= 0:
                continue

            earned = answer.score_awarded if answer.score_awarded is not None else 0.0
            ratio = max(0.0, min(earned / question.points, 1.0))

            if topic_name not in topic_stats:
                topic_stats[topic_name] = {"ratio_sum": 0.0, "count": 0.0}

            topic_stats[topic_name]["ratio_sum"] += ratio
            topic_stats[topic_name]["count"] += 1

        topic_performance = []
        for topic, stats in sorted(topic_stats.items(), key=lambda item: item[1]["ratio_sum"] / item[1]["count"]):
            attempts_count = int(stats["count"])
            average_score = round((stats["ratio_sum"] / stats["count"]) * 100, 2)
            needs_attention = attempts_count >= 2 and average_score < 60
            topic_performance.append({
                "topic": topic,
                "average_score": average_score,
                "attempts": attempts_count,
                "needs_attention": needs_attention,
            })

        weak_topics = [item["topic"] for item in topic_performance if item["needs_attention"]][:5]
        if not weak_topics:
            weak_topics = [item["topic"] for item in topic_performance[:3] if item["average_score"] < 70]

        overall_score_avg = round(sum(scores) / len(scores), 2) if scores else None
        pass_rate = round(len(passing) / len(scores) * 100, 2) if scores else None
        peer_average = round(sum(peer_scores) / len(peer_scores), 2) if peer_scores else None
        percentile_estimate = None
        if overall_score_avg is not None and peer_scores:
            percentile_estimate = round(
                sum(1 for peer_score in peer_scores if peer_score <= overall_score_avg) / len(peer_scores) * 100,
                1,
            )

        strongest_subject = None
        weakest_subject = None
        if subject_scores:
            strongest_subject = max(
                subject_scores,
                key=lambda item: item["average_score"] if item["average_score"] is not None else -1,
            )["subject"]
            weakest_subject = min(
                subject_scores,
                key=lambda item: item["average_score"] if item["average_score"] is not None else 101,
            )["subject"]

        insights = []
        if overall_score_avg is None:
            insights.append("No graded assessments are available for this semester yet.")
        else:
            if peer_average is not None:
                delta_vs_peer = round(overall_score_avg - peer_average, 2)
                if delta_vs_peer >= 5:
                    insights.append(f"Overall average is {delta_vs_peer:.1f} points above the peer average.")
                elif delta_vs_peer <= -5:
                    insights.append(f"Overall average is {abs(delta_vs_peer):.1f} points below the peer average.")

            if improvement_rate is not None:
                if improvement_rate >= 2:
                    insights.append("Scores are trending upward through the semester.")
                elif improvement_rate <= -2:
                    insights.append("Scores are trending downward through the semester.")

            if weak_topics:
                insights.append(f"Needs reinforcement in: {', '.join(weak_topics[:3])}.")

            if strongest_subject and weakest_subject and strongest_subject != weakest_subject:
                insights.append(f"Strongest subject is {strongest_subject}; weakest is {weakest_subject}.")

            if violation_count >= 3:
                insights.append("Repeated proctoring violations may be affecting outcomes.")

        recent_results = list(reversed(score_trend[-8:]))

        return {
            "student_name": student.full_name if student else None,
            "selected_semester": semester,
            "available_semesters": available_semesters,
            "overall_score_avg": overall_score_avg,
            "pass_rate": pass_rate,
            "assessments_taken": len(attempts),
            "assessments_passed": len(passing),
            "streak_count": streak,
            "improvement_rate": improvement_rate,
            "violation_count_total": violation_count,
            "score_trend": score_trend,
            "subject_scores": subject_scores,
            "weak_topics": weak_topics,
            "topic_performance": topic_performance,
            "comparison_summary": {
                "student_average": overall_score_avg,
                "peer_average": peer_average,
                "delta_vs_peer": round(overall_score_avg - peer_average, 2) if overall_score_avg is not None and peer_average is not None else None,
                "percentile_estimate": percentile_estimate,
            },
            "insights": insights,
            "recent_results": recent_results,
        }

    @staticmethod
    def _empty_student_dashboard() -> dict:
        return {
            "student_name": None,
            "selected_semester": None,
            "available_semesters": [],
            "overall_score_avg": None,
            "pass_rate": None,
            "assessments_taken": 0,
            "assessments_passed": 0,
            "streak_count": 0,
            "improvement_rate": None,
            "violation_count_total": 0,
            "score_trend": [],
            "subject_scores": [],
            "weak_topics": [],
            "topic_performance": [],
            "comparison_summary": {
                "student_average": None,
                "peer_average": None,
                "delta_vs_peer": None,
                "percentile_estimate": None,
            },
            "insights": [],
            "recent_results": [],
        }

    @staticmethod
    def _empty_student_review(
        *,
        student_name: Optional[str] = None,
        period: str = "semester",
        academic_year: Optional[str] = None,
        semester: Optional[str] = None,
        available_academic_years: Optional[list[str]] = None,
        available_semesters: Optional[list[str]] = None,
    ) -> dict:
        return {
            "student_name": student_name,
            "period": period,
            "selected_academic_year": academic_year,
            "selected_semester": semester if period != "year" else None,
            "available_academic_years": available_academic_years or [],
            "available_semesters": available_semesters or [],
            "overall_score_avg": None,
            "pass_rate": None,
            "assessments_taken": 0,
            "assessments_passed": 0,
            "streak_count": 0,
            "improvement_rate": None,
            "violation_count_total": 0,
            "score_trend": [],
            "subject_scores": [],
            "weak_topics": [],
            "topic_performance": [],
            "comparison_summary": None,
            "comparison_matrix": [],
            "period_breakdown": [],
            "insights": [],
            "recent_results": [],
        }

    # ── Teacher Analytics ──

    @staticmethod
    async def get_group_analytics(db: AsyncSession, group_id: UUID, teacher_id: UUID | None = None) -> dict:
        """Aggregate analytics for all assessments within a group."""
        # Get group info
        group = (
            await db.execute(
                select(Group)
                .options(selectinload(Group.curriculum_subject))
                .where(Group.id == group_id)
            )
        ).scalar_one_or_none()
        if not group:
            return {}
        if teacher_id and group.teacher_id != teacher_id:
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

        score_rows = (
            await db.execute(
                select(
                    AssessmentAttempt.assessment_id,
                    AssessmentAttempt.score_percent,
                ).where(
                    AssessmentAttempt.assessment_id.in_(assessment_ids),
                    AssessmentAttempt.status.in_(["submitted", "graded"]),
                    AssessmentAttempt.score_percent.isnot(None),
                )
            )
        ).all()
        scores_by_assessment: dict[UUID, list[float]] = {}
        for row in score_rows:
            scores_by_assessment.setdefault(row.assessment_id, []).append(row.score_percent)
        all_scores = [score for scores in scores_by_assessment.values() for score in scores]
        passing = [score for score in all_scores if score >= 50]

        summaries = []
        for a in assessments:
            assessment_scores = scores_by_assessment.get(a.id, [])
            if assessment_scores:
                passing_scores = [score for score in assessment_scores if score >= 50]
                mean_score = round(statistics.mean(assessment_scores), 2)
                pass_rate = round(len(passing_scores) / len(assessment_scores) * 100, 2)
            else:
                mean_score = None
                pass_rate = None
            summaries.append({
                "assessment_id": str(a.id),
                "title": a.title,
                "attempts_count": len(assessment_scores),
                "mean_score": mean_score,
                "pass_rate": pass_rate,
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
