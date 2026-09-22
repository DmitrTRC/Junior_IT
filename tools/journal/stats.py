from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import date

from journal import store
from journal.model import LessonRecord, Student

SUBMITTED_STALE_DAYS = 3


@dataclass
class StudentStats:
    id: str
    name: str
    lessons_total: int = 0
    present: int = 0
    late: int = 0
    recording: int = 0
    absent: int = 0
    hw_issued: int = 0
    hw_submitted: int = 0
    hw_accepted: int = 0
    hw_rework: int = 0
    points_total: float = 0.0
    points_period: float = 0.0
    last_lesson: date | None = None
    tails: list[str] = field(default_factory=list)


@dataclass
class GroupStats:
    lessons_total: int
    students: list[StudentStats]
    missing_journals: list[date]


def student_stats(student: Student, lessons: list[LessonRecord], plans: dict,
                  today: date, since: date | None = None) -> StudentStats:
    s = StudentStats(id=student.id, name=student.name, lessons_total=len(lessons))
    for rec in lessons:
        status = rec.attendance.get(student.id)
        if status is not None:
            setattr(s, status, getattr(s, status) + 1)
            if s.last_lesson is None or rec.date > s.last_lesson:
                s.last_lesson = rec.date
        plan = plans.get(rec.date)
        due = store.hw_due_from_plan(plan) if plan else None
        for hw_id, marks in rec.homework.items():
            mark = marks.get(student.id)
            if mark is None:
                continue
            s.hw_issued += 1
            if mark.status == "submitted":
                s.hw_submitted += 1
            elif mark.status == "accepted":
                s.hw_accepted += 1
            elif mark.status == "rework":
                s.hw_rework += 1
            if mark.status in ("issued", "rework") and due and due < today:
                s.tails.append(f"{hw_id}: просрочена с {due.isoformat()}")
            if mark.status == "submitted" and mark.at and (today - mark.at).days > SUBMITTED_STALE_DAYS:
                s.tails.append(f"{hw_id}: сдана {mark.at.isoformat()}, ждёт решения")
        for p in rec.points:
            if p.who != student.id:
                continue
            s.points_total += p.amount
            if since is None or rec.date >= since:
                s.points_period += p.amount
    return s


def group_stats(roster: list[Student], lessons: list[LessonRecord], plans: dict,
                today: date, since: date | None = None) -> GroupStats:
    active = [st for st in roster if st.status == "active"]
    students = sorted((student_stats(st, lessons, plans, today, since) for st in active),
                      key=lambda x: -x.points_total)
    journaled = {rec.date for rec in lessons}
    missing = sorted(d for d in plans if d < today and d not in journaled)
    return GroupStats(lessons_total=len(lessons), students=students, missing_journals=missing)


def load_plans(repo_root=None) -> dict:
    return {d: store.load_plan(d, repo_root) for d in store.plan_dates(repo_root)}


def collect(root=None, repo_root=None, today: date | None = None, since: date | None = None) -> GroupStats:
    roster = store.load_roster(root)
    lessons = store.load_lessons(root, roster)
    return group_stats(roster, lessons, load_plans(repo_root), today or date.today(), since)


def to_json_dict(g: GroupStats) -> dict:
    def conv(value):
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, dict):
            return {k: conv(v) for k, v in value.items()}
        if isinstance(value, list):
            return [conv(v) for v in value]
        return value
    return conv(asdict(g))
