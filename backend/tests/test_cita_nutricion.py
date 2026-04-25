"""Tests para solicitud de cita nutricional y flujo integrado IMC -> cita."""

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload, sessionmaker
from sqlalchemy.pool import StaticPool

import main as backend_main
from app.models import Derivacion, PerfilSalud, Rol, Usuario


class CitaNutricionTestCase(unittest.TestCase):
    """Valida endpoint de cita nutricional del paciente y su integración clínica básica."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

        backend_main.Base.metadata.create_all(bind=cls.engine)

        # Evita usar startup real (MySQL/seed productivo) en tests unitarios.
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
                nombre="Paciente Cita",
                email="paciente.cita@test.local",
                password_hash="x",
                rol_id=roles["cliente"],
            )
            nutricionista = Usuario(
                nombre="Nutricionista Cita",
                email="nutri.cita@test.local",
                password_hash="x",
                rol_id=roles["nutricionista"],
            )
            admin = Usuario(
                nombre="Admin Cita",
                email="admin.cita@test.local",
                password_hash="x",
                rol_id=roles["administrador"],
            )

            db.add_all([paciente, nutricionista, admin])
            db.commit()

            return {
                "paciente": paciente.id,
                "nutricionista": nutricionista.id,
                "admin": admin.id,
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

    def test_solicitar_cita_nutricion_crea_derivacion(self) -> None:
        self._override_usuario_actual(self.ids["paciente"])

        response = self.client.post(
            "/pacientes/solicitar-cita-nutricion",
            json={"motivo": "Necesito seguimiento nutricional por cambios de peso."},
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["paciente_id"], self.ids["paciente"])
        self.assertEqual(data["especialidad_destino"], "nutricion")
        self.assertEqual(data["estado"], "pendiente")
        self.assertEqual(data["destino_profesional_id"], self.ids["nutricionista"])

        with self.SessionLocal() as db:
            count = (
                db.query(Derivacion)
                .filter(Derivacion.paciente_id == self.ids["paciente"])
                .filter(Derivacion.especialidad_destino == "nutricion")
                .count()
            )
            self.assertEqual(count, 1)

    def test_solicitar_cita_reutiliza_derivacion_abierta(self) -> None:
        self._override_usuario_actual(self.ids["paciente"])

        first = self.client.post(
            "/pacientes/solicitar-cita-nutricion",
            json={"motivo": "Primera solicitud para valoración nutricional."},
        )
        second = self.client.post(
            "/pacientes/solicitar-cita-nutricion",
            json={"motivo": "Segunda solicitud sin cerrar la anterior."},
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.json()["id"], second.json()["id"])

        with self.SessionLocal() as db:
            count = (
                db.query(Derivacion)
                .filter(Derivacion.paciente_id == self.ids["paciente"])
                .filter(Derivacion.especialidad_destino == "nutricion")
                .count()
            )
            self.assertEqual(count, 1)

    def test_integracion_imc_a_cita_y_bandeja_paciente(self) -> None:
        self._override_usuario_actual(self.ids["paciente"])

        # Paso 1: paciente actualiza métricas IMC.
        imc_resp = self.client.patch(
            "/perfil/metricas-imc",
            json={"peso": 81.0, "altura": 172},
        )
        self.assertEqual(imc_resp.status_code, 200)
        imc_data = imc_resp.json()
        self.assertEqual(imc_data["usuario_id"], self.ids["paciente"])
        self.assertIn("imc_calculado", imc_data)

        # Paso 2: con ese contexto clínico solicita cita de nutrición.
        cita_resp = self.client.post(
            "/pacientes/solicitar-cita-nutricion",
            json={"motivo": "Solicito cita tras revisar mi IMC en el panel."},
        )
        self.assertEqual(cita_resp.status_code, 201)

        # Paso 3: valida que aparece en la bandeja de derivaciones del paciente.
        bandeja_resp = self.client.get("/pacientes/derivaciones")
        self.assertEqual(bandeja_resp.status_code, 200)
        derivaciones = bandeja_resp.json()
        self.assertEqual(len(derivaciones), 1)
        self.assertEqual(derivaciones[0]["especialidad_destino"], "nutricion")

        with self.SessionLocal() as db:
            perfil = db.query(PerfilSalud).filter(PerfilSalud.usuario_id == self.ids["paciente"]).first()
            self.assertIsNotNone(perfil)
            self.assertIsNotNone(perfil.imc_actual)


if __name__ == "__main__":
    unittest.main()
