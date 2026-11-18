from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
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