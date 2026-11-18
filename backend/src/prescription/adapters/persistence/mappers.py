from src.prescription.adapters.persistence.models import PrescriptionItemModel, PrescriptionModel
from src.prescription.domain.aggregates import Prescription, PrescriptionItem
from src.prescription.domain.value_objects import (
    Dosage, DosageForm, DoseSchedule, Medication, PatientId, PrescriptionId, PrescriptionItemId,
    PrescriptionStatus, TreatmentPeriod, Weekday,
)


def to_domain(m: PrescriptionModel) -> Prescription:
    items = [
        PrescriptionItem(
            id=PrescriptionItemId(i.id),
            medication=Medication(i.medication_name, i.active_ingredient, i.concentration),
            dosage=Dosage(i.units_per_intake, DosageForm(i.dosage_form)),
            schedule=DoseSchedule(
                times_of_day=tuple(i.times_of_day),
                days_of_week=frozenset(Weekday(d) for d in i.days_of_week),
                timezone=i.timezone,
            ),
            instructions=i.instructions,
        )
        for i in m.items
    ]
    return Prescription(
        id=PrescriptionId(m.id), patient_id=PatientId(m.patient_id),
        validity=TreatmentPeriod(m.validity_start, m.validity_end),
        status=PrescriptionStatus(m.status), items=items, version=m.version,
    )


def apply_to_model(p: Prescription, m: PrescriptionModel) -> None:
    m.patient_id = p.patient_id.value
    m.status = p.status.value
    m.validity_start = p.validity.start_date
    m.validity_end = p.validity.end_date

    existing = {i.id: i for i in m.items}
    synced: list[PrescriptionItemModel] = []
    for it in p.items:
        im = existing.get(it.id.value) or PrescriptionItemModel(id=it.id.value)
        im.medication_name = it.medication.name
        im.active_ingredient = it.medication.active_ingredient
        im.concentration = it.medication.concentration
        im.units_per_intake = it.dosage.units_per_intake
        im.dosage_form = it.dosage.form.value
        im.times_of_day = list(it.schedule.times_of_day)
        im.days_of_week = sorted(int(d) for d in it.schedule.days_of_week)
        im.timezone = it.schedule.timezone
        im.instructions = it.instructions
        synced.append(im)
    m.items = synced  # delete-orphan elimina los ítems quitados del agregado