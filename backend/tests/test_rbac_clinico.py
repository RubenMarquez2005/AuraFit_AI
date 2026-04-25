"""Tests RBAC para endpoints clínicos hospitalarios y nutricionales."""

import json
import unittest
from typing import Callable

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, joinedload, sessionmaker
from sqlalchemy.pool import StaticPool

import main as backend_main
from app.models import (
    Rol,
    Usuario,
    PlanNutricionalClinico,
    ProtocoloHospitalario,
)


class RbacClinicoTestCase(unittest.TestCase):
    """Verifica lectura vs edición por rol en endpoints clínicos."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

        backend_main.Base.metadata.create_all(bind=cls.engine)

        # Evita tocar la startup de MySQL durante tests unitarios.
        backend_main.app.router.on_startup.clear()
        backend_main.app.router.on_shutdown.clear()

        def override_get_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        backend_main.app.dependency_overrides[backend_main.get_db] = override_get_db
        cls.client = TestClient(backend_main.app)

    @classmethod
    def tearDownClass(cls) -> None:
        backend_main.app.dependency_overrides.clear()
        backend_main.Base.metadata.drop_all(bind=cls.engine)

    def setUp(self) -> None:
        self._reset_db()
        self.ids = self._seed_datos_base()

    def _reset_db(self) -> None:
        backend_main.Base.metadata.drop_all(bind=self.engine)
        backend_main.Base.metadata.create_all(bind=self.engine)

    def _seed_datos_base(self) -> dict:
        with self.SessionLocal() as db:
            roles = {}
            for nombre in ["administrador", "cliente", "nutricionista", "psicologo", "coach", "medico"]:
                rol = Rol(nombre=nombre)
                db.add(rol)
                db.flush()
                roles[nombre] = rol.id

            paciente = Usuario(
                nombre="Paciente Test",
                email="paciente@test.local",
                password_hash="x",
                rol_id=roles["cliente"],
            )
            coach = Usuario(
                nombre="Coach Test",
                email="coach@test.local",
                password_hash="x",
                rol_id=roles["coach"],
            )
            nutri = Usuario(
                nombre="Nutri Test",
                email="nutri@test.local",
                password_hash="x",
                rol_id=roles["nutricionista"],
            )
            medico = Usuario(
                nombre="Medico Test",
                email="medico@test.local",
                password_hash="x",
                rol_id=roles["medico"],
            )

            db.add_all([paciente, coach, nutri, medico])
            db.flush()

            db.add(
                PlanNutricionalClinico(
                    paciente_id=paciente.id,
                    profesional_id=nutri.id,
                    calorias_objetivo=2200,
                    proteinas_g=140,
                    carbohidratos_g=250,
                    grasas_g=70,
                    objetivo_clinico="mantenimiento",
                    riesgo_metabolico="bajo",
                    observaciones="Plan inicial",
                    activo=True,
                )
            )
            db.add(
                ProtocoloHospitalario(
                    trastorno="tca",
                    severidad="leve",
                    especialidad="nutricionista",
                    titulo="TCA leve",
                    checklist_json=json.dumps(["item 1", "item 2"]),
                    ruta_escalado="Derivar si empeora",
                    activo=True,
                )
            )
            db.commit()

            return {
                "paciente": paciente.id,
                "coach": coach.id,
                "nutri": nutri.id,
                "medico": medico.id,
            }

    def _override_usuario_actual(self, usuario_id: int) -> None:
        def _resolver_usuario_actual() -> Usuario:
            with self.SessionLocal() as db:
                user = (
                    db.query(Usuario)
                    .options(joinedload(Usuario.rol))
                    .filter(Usuario.id == usuario_id)
                    .first()
                )
                if user is None:
                    raise RuntimeError("Usuario de test no encontrado")
                db.expunge(user)
                return user

        backend_main.app.dependency_overrides[backend_main.obtener_usuario_actual] = _resolver_usuario_actual

    def _request_put_plan(self) -> int:
        response = self.client.put(
            f"/profesionales/pacientes/{self.ids['paciente']}/plan-nutricional",
            json={
                "calorias_objetivo": 2200,
                "proteinas_g": 140,
                "carbohidratos_g": 250,
                "grasas_g": 70,
                "objetivo_clinico": "mantenimiento",
                "riesgo_metabolico": "bajo",
                "observaciones": "Ajuste",
            },
        )
        return response.status_code

    def test_plan_nutricional_lectura_permitida_para_coach(self) -> None:
        self._override_usuario_actual(self.ids["coach"])
        response = self.client.get(
            f"/profesionales/pacientes/{self.ids['paciente']}/plan-nutricional"
        )
        self.assertEqual(response.status_code, 200)

    def test_plan_nutricional_edicion_denegada_para_coach(self) -> None:
        self._override_usuario_actual(self.ids["coach"])
        self.assertEqual(self._request_put_plan(), 403)

    def test_plan_nutricional_edicion_permitida_para_nutricionista(self) -> None:
        self._override_usuario_actual(self.ids["nutri"])
        self.assertEqual(self._request_put_plan(), 200)

    def test_protocolos_hospitalarios_lectura_permitida_para_coach(self) -> None:
        self._override_usuario_actual(self.ids["coach"])
        response = self.client.get(
            "/profesionales/protocolos-hospitalarios?trastorno=tca&severidad=leve"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data) >= 1)

    def test_protocolos_hospitalarios_edicion_denegada_para_coach(self) -> None:
        self._override_usuario_actual(self.ids["coach"])
        response = self.client.put(
            "/profesionales/protocolos-hospitalarios",
            json={
                "trastorno": "ansiedad",
                "severidad": "moderado",
                "especialidad": "psicologo",
                "titulo": "Ansiedad moderada",
                "checklist": ["item a", "item b"],
                "ruta_escalado": "Escalar a medicina ante deterioro funcional",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_protocolos_hospitalarios_edicion_permitida_para_medico(self) -> None:
        self._override_usuario_actual(self.ids["medico"])
        response = self.client.put(
            "/profesionales/protocolos-hospitalarios",
            json={
                "trastorno": "ansiedad",
                "severidad": "moderado",
                "especialidad": "psicologo",
                "titulo": "Ansiedad moderada",
                "checklist": ["item a", "item b"],
                "ruta_escalado": "Escalar a medicina ante deterioro funcional",
            },
        )
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
