from datetime import date, datetime, time, timezone
from uuid import uuid4

import pytest

from src.dispenser_iot.domain.aggregates import DispenserIoT
from src.dispenser_iot.domain.events import DoseDispensed, StockLow
from src.dispenser_iot.domain.value_objects import (
    DispenseOrigin, DispenseOutcome, PatientId, PrescriptionItemId, SerialNumber, SlotNumber,
)
from src.prescription.domain.aggregates import Prescription
from src.prescription.domain.events import PrescriptionActivated
from src.prescription.domain.value_objects import (
    Dosage, DosageForm, DoseSchedule, Medication, TreatmentPeriod, Weekday,
)
from src.shared_kernel.domain import InvariantViolation


def _item():
    return dict(
        medication=Medication("Metformina"), dosage=Dosage(1, DosageForm.TABLET),
        schedule=DoseSchedule((time(8),), frozenset({Weekday.MON}), "America/Guayaquil"),
    )


def _rx():
    return Prescription.draft(PatientId.new(), TreatmentPeriod(date(2026, 1, 1)))


def test_cannot_activate_empty():
    with pytest.raises(InvariantViolation):
        _rx().activate()


def test_activate_emits_event():
    p = _rx(); p.add_item(**_item()); p.activate()
    assert isinstance(p.pull_events()[0], PrescriptionActivated)


def test_overlapping_schedule_rejected():
    p = _rx(); p.add_item(**_item())
    with pytest.raises(InvariantViolation):
        p.add_item(**_item())


def test_dispense_is_idempotent_and_flags_low_stock():
    d = DispenserIoT.register(owner_id=PatientId.new(), serial_number=SerialNumber("RC-000001"), slot_count=7)
    d.load_compartment(SlotNumber(1), PrescriptionItemId.new(), stock=4, low_threshold=3)
    now = datetime.now(timezone.utc)
    kw = dict(event_id=uuid4(), slot=SlotNumber(1), scheduled_at=now, dispensed_at=now,
              outcome=DispenseOutcome.DISPENSED, origin=DispenseOrigin.OFFLINE_SYNCED)
    assert d.confirm_dispense(**kw) is True
    assert d.confirm_dispense(**kw) is False
    assert [type(e) for e in d.pull_events()] == [DoseDispensed, StockLow]