"""Prueba manual: save → get → save (versión) → conflicto optimista. Limpia al final."""
import asyncio
from datetime import date, time

from sqlalchemy import delete

import src.infrastructure.database.registry  # noqa: F401  (registra TODOS los modelos)
from src.infrastructure.database.session import SessionFactory, engine
from src.prescription.adapters.persistence.models import PrescriptionModel
from src.prescription.adapters.persistence.repository import SqlPrescriptionRepository
from src.prescription.domain.aggregates import Prescription
from src.prescription.domain.events import PrescriptionActivated
from src.prescription.domain.value_objects import (
    Dosage, DosageForm, DoseSchedule, Medication, PatientId, PrescriptionStatus,
    TreatmentPeriod, Weekday,
)
from src.shared_kernel.domain import ConcurrencyConflict


def ok(msg: str) -> None:
    print(f"  ✅ {msg}")


async def main() -> None:
    patient = PatientId.new()
    rx = Prescription.draft(patient, TreatmentPeriod(date(2026, 1, 1)))
    rx.add_item(
        Medication("Metformina", "Metformina HCl", "850 mg"),
        Dosage(1, DosageForm.TABLET),
        DoseSchedule((time(8), time(20)), frozenset({Weekday.MON, Weekday.WED}), "America/Guayaquil"),
        "Con comida",
    )
    rx_id = rx.id

    try:
        # ── 1. SAVE inicial (INSERT) ─────────────────────────────────────
        print("1) save inicial")
        async with SessionFactory() as s:
            await SqlPrescriptionRepository(s).save(rx)
            await s.commit()
        assert rx.version == 1, f"versión esperada 1, obtenida {rx.version}"
        ok(f"insertada, version={rx.version}")

        # ── 2. GET en sesión nueva + comparación de datos ────────────────
        print("2) get (sesión nueva)")
        async with SessionFactory() as s:
            loaded = await SqlPrescriptionRepository(s).get(rx_id)
        assert loaded is not None, "get devolvió None"
        assert loaded.status is PrescriptionStatus.DRAFT
        assert len(loaded.items) == 1
        it = loaded.items[0]
        assert it.medication.name == "Metformina" and it.medication.concentration == "850 mg"
        assert it.schedule.times_of_day == (time(8), time(20))
        assert it.schedule.days_of_week == frozenset({Weekday.MON, Weekday.WED})
        assert loaded.version == 1
        ok("agregado rehidratado idéntico (VOs, horarios, ítems)")

        # ── 3. SEGUNDO SAVE (UPDATE) → version debe subir ────────────────
        print("3) segundo save (activate)")
        loaded.activate()
        async with SessionFactory() as s:
            await SqlPrescriptionRepository(s).save(loaded)
            await s.commit()
        assert loaded.version == 2, f"versión esperada 2, obtenida {loaded.version}"
        assert isinstance(loaded.pull_events()[0], PrescriptionActivated)
        ok(f"UPDATE aplicado, version={loaded.version}, evento PrescriptionActivated emitido")

        async with SessionFactory() as s:
            repo = SqlPrescriptionRepository(s)
            again = await repo.get(rx_id)
            listed = await repo.list_by_patient(patient)
        assert again.status is PrescriptionStatus.ACTIVE and again.version == 2
        assert len(listed) == 1
        ok("persistido: ACTIVE v2; list_by_patient devuelve 1")

        # ── 4. CONFLICTO OPTIMISTA (dos "usuarios" a la vez) ─────────────
        print("4) bloqueo optimista")
        async with SessionFactory() as sa, SessionFactory() as sb:
            repo_a, repo_b = SqlPrescriptionRepository(sa), SqlPrescriptionRepository(sb)
            rx_a = await repo_a.get(rx_id)   # ambos leen la v2
            rx_b = await repo_b.get(rx_id)
            rx_a.suspend()
            await repo_a.save(rx_a)
            await sa.commit()                # A gana → v3
            rx_b.complete()
            try:
                await repo_b.save(rx_b)      # B trabaja con datos viejos
                raise AssertionError("B debió fallar con ConcurrencyConflict")
            except ConcurrencyConflict:
                await sb.rollback()
                ok("B rechazado con ConcurrencyConflict (v3 de A intacta)")

        async with SessionFactory() as s:
            final = await SqlPrescriptionRepository(s).get(rx_id)
        assert final.status is PrescriptionStatus.SUSPENDED and final.version == 3
        ok("estado final SUSPENDED v3")

        print("\n🎉 RONDA COMPLETA: repositorio, mappers y bloqueo optimista funcionan.")

    finally:
        # ── Limpieza (los ítems caen por ON DELETE CASCADE) ──────────────
        async with SessionFactory() as s:
            await s.execute(delete(PrescriptionModel).where(PrescriptionModel.id == rx_id.value))
            await s.commit()
        print("🧹 datos de prueba eliminados")
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())