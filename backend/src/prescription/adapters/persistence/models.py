import uuid
from datetime import date, time

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, SmallInteger, String, Text, Time
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base, TimestampMixin


class PrescriptionModel(Base, TimestampMixin):
    __tablename__ = "prescriptions"
    __table_args__ = (
        CheckConstraint("status IN ('DRAFT','ACTIVE','SUSPENDED','COMPLETED')", name="status"),
        CheckConstraint("validity_end IS NULL OR validity_end >= validity_start", name="validity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    # Referencia por ID, SIN FK física a patients (ver decisión D1)
    patient_id: Mapped[uuid.UUID] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(String(16))
    validity_start: Mapped[date] = mapped_column(Date)
    validity_end: Mapped[date | None] = mapped_column(Date)
    version: Mapped[int] = mapped_column(Integer, default=1)  # bloqueo optimista del agregado

    items: Mapped[list["PrescriptionItemModel"]] = relationship(
        back_populates="prescription", cascade="all, delete-orphan", lazy="selectin"
    )

    __mapper_args__ = {"version_id_col": version}


class PrescriptionItemModel(Base):
    __tablename__ = "prescription_items"
    __table_args__ = (
        CheckConstraint("units_per_intake > 0", name="units_positive"),
        CheckConstraint("cardinality(times_of_day) >= 1", name="has_times"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    prescription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prescriptions.id", ondelete="CASCADE"), index=True
    )
    # Medication (VO)
    medication_name: Mapped[str] = mapped_column(String(200))
    active_ingredient: Mapped[str | None] = mapped_column(String(200))
    concentration: Mapped[str | None] = mapped_column(String(64))
    # Dosage (VO)
    units_per_intake: Mapped[int] = mapped_column(SmallInteger)
    dosage_form: Mapped[str] = mapped_column(String(32))
    # DoseSchedule (VO) aplanado
    times_of_day: Mapped[list[time]] = mapped_column(ARRAY(Time))
    days_of_week: Mapped[list[int]] = mapped_column(ARRAY(SmallInteger))  # ISO 1=Lun..7=Dom
    timezone: Mapped[str] = mapped_column(String(64))
    instructions: Mapped[str | None] = mapped_column(Text)

    prescription: Mapped[PrescriptionModel] = relationship(back_populates="items")