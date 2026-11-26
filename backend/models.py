from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ScholarshipScheme(Base):
    __tablename__ = "scholarship_schemes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)


class Scholarship(Base):
    __tablename__ = "scholarships"

    __table_args__ = (
        CheckConstraint(
            "funding_category IN "
            "('full', 'tuition_only', 'partial', 'unknown')",
            name="ck_scholarships_funding",
        ),
        CheckConstraint(
            "call_status IN ('open', 'upcoming', 'closed', 'unknown')",
            name="ck_scholarships_call_status",
        ),
        CheckConstraint(
            "review_state IN "
            "('draft', 'needs_review', 'published', 'archived')",
            name="ck_scholarships_review_state",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scheme_id: Mapped[int] = mapped_column(
        ForeignKey("scholarship_schemes.id", ondelete="RESTRICT"),
        index=True,
    )

    source_key: Mapped[str | None] = mapped_column(
        String(200),
        unique=True,
        nullable=True,
    )

    title: Mapped[str] = mapped_column(String(250))
    cycle: Mapped[str | None] = mapped_column(String(100))
    intake_year: Mapped[int | None]
    description: Mapped[str | None] = mapped_column(Text)

    # Country codes such as GB, US and FI. None means unknown.
    countries: Mapped[list[str] | None] = mapped_column(ARRAY(String(2)))
    degree_levels: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(40))
    )
    fields_of_study: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(100))
    )

    funding_category: Mapped[str] = mapped_column(
        String(20), server_default="unknown"
    )
    funding_notes: Mapped[str | None] = mapped_column(Text)
    call_status: Mapped[str] = mapped_column(
        String(20), server_default="unknown"
    )
    review_state: Mapped[str] = mapped_column(
        String(20), server_default="draft"
    )

    official_url: Mapped[str | None] = mapped_column(Text)
    last_checked: Mapped[date | None] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
class Application(Base):
    __tablename__ = 'applications'
    __table_args__ = (CheckConstraint("status IN ('researching','preparing','submitted','result_received','withdrawn')", name='ck_application_status'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(250))
    provider: Mapped[str | None] = mapped_column(String(250))
    source_url: Mapped[str | None] = mapped_column(Text)
    cycle: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), server_default='researching')
    notes: Mapped[str | None] = mapped_column(Text)
    next_action: Mapped[str | None] = mapped_column(Text)
    archived: Mapped[bool] = mapped_column(server_default='false')
    submission_date: Mapped[date | None] = mapped_column(Date)
    interview_date: Mapped[date | None] = mapped_column(Date)
    outcome: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApplicationDeadline(Base):
    __tablename__ = 'application_deadlines'
    __table_args__ = (CheckConstraint("kind IN ('official','personal')", name='ck_deadline_kind'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey('applications.id', ondelete='CASCADE'), index=True)
    label: Mapped[str] = mapped_column(String(250))
    kind: Mapped[str] = mapped_column(String(20))
    due_date: Mapped[date | None] = mapped_column(Date)
    due_time: Mapped[str | None] = mapped_column(String(20))
    timezone: Mapped[str | None] = mapped_column(String(100))


class ApplicationTask(Base):
    __tablename__ = 'application_tasks'
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey('applications.id', ondelete='CASCADE'), index=True)
    title: Mapped[str] = mapped_column(String(250))
    due_date: Mapped[date | None] = mapped_column(Date)
    completed: Mapped[bool] = mapped_column(server_default='false')


class TrackedScholarship(Base):
    __tablename__ = 'tracked_scholarships'
    __table_args__ = (CheckConstraint("status IN ('saved','preparing','submitted','accepted','rejected')", name='ck_tracked_status'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    url_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str | None] = mapped_column(String(250))
    provider: Mapped[str | None] = mapped_column(String(250))
    intake: Mapped[str | None] = mapped_column(String(250))
    deadline: Mapped[date | None] = mapped_column(Date)
    funding: Mapped[str | None] = mapped_column(Text)
    eligibility: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), server_default='saved')
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ChecklistItem(Base):
    __tablename__ = 'tracked_checklist'
    __table_args__ = (UniqueConstraint('scholarship_id', 'proposal_key', name='uq_checklist_proposal'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    scholarship_id: Mapped[int] = mapped_column(ForeignKey('tracked_scholarships.id', ondelete='CASCADE'), index=True)
    label: Mapped[str] = mapped_column(String(250), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    proposal_key: Mapped[str | None] = mapped_column(String(64))
    completed: Mapped[bool] = mapped_column(server_default='false')


class TrackedSourcePage(Base):
    __tablename__ = 'tracked_source_pages'
    __table_args__ = (
        CheckConstraint("source_url LIKE 'https://%'", name='ck_tracked_source_https'),
        UniqueConstraint('scholarship_id', 'url_key', name='uq_tracked_source_page_url'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    scholarship_id: Mapped[int] = mapped_column(ForeignKey('tracked_scholarships.id', ondelete='CASCADE'), index=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    url_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExtractionAttempt(Base):
    __tablename__ = 'extraction_attempts'
    id: Mapped[int] = mapped_column(primary_key=True)
    scholarship_id: Mapped[int] = mapped_column(ForeignKey('tracked_scholarships.id', ondelete='CASCADE'), index=True)
    input_kind: Mapped[str] = mapped_column(String(10), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    suggestions_json: Mapped[str] = mapped_column(Text, nullable=False, server_default='{}')
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudentProfile(Base):
    __tablename__ = 'student_profile'
    id: Mapped[int] = mapped_column(primary_key=True)
    nationality: Mapped[str | None] = mapped_column(String(120))
    prior_degree: Mapped[str | None] = mapped_column(String(120))
    field: Mapped[str | None] = mapped_column(String(120))
    target_intake: Mapped[str | None] = mapped_column(String(120))
    language_status: Mapped[str | None] = mapped_column(String(120))


class ReviewedRequirement(Base):
    __tablename__ = 'reviewed_requirements'
    id: Mapped[int] = mapped_column(primary_key=True)
    scholarship_id: Mapped[int] = mapped_column(ForeignKey('tracked_scholarships.id', ondelete='CASCADE'), index=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    expected: Mapped[str] = mapped_column(String(120), nullable=False)
