#!/usr/bin/env python3
"""
Example usage of AuraFit AI models and schemas
Demonstrates how to work with the database layer
"""

from sqlalchemy.orm import Session
from app.db import SessionLocal, engine, Base
from app.models import Rol, Usuario, PerfilSalud, RegistroDiario
from app.schemas import (
    RolCreate, UsuarioCreate, PerfilSaludCreate, RegistroDiarioCreate
)
from datetime import datetime, date, time


def setup_database():
    """Create all tables"""
    print("📦 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tables ready\n")


def create_sample_data():
    """Create sample data for testing"""
    db = SessionLocal()
    
    try:
        print("📝 Creating sample data...\n")
        
        # 1. Create Roles
        print("1️⃣  Creating roles...")
        roles_data = [
            Rol(nombre="administrador"),
            Rol(nombre="cliente"),
            Rol(nombre="nutricionista"),
            Rol(nombre="psicologo"),
            Rol(nombre="coach"),
        ]
        
        # Check if roles already exist
        existing_roles = db.query(Rol).count()
        if existing_roles == 0:
            db.add_all(roles_data)
            db.commit()
            print("   ✓ Roles created\n")
        else:
            print(f"   ℹ️  Roles already exist ({existing_roles} roles)\n")
        
        # Get the "cliente" role
        cliente_role = db.query(Rol).filter(Rol.nombre == "cliente").first()
        
        # 2. Create a Sample User
        print("2️⃣  Creating sample user...")
        # from werkzeug.security import generate_password_hash  # Optional: pip install werkzeug for real hashing
        
        sample_user = Usuario(
            nombre="Juan Pérez",
            email="juan.perez@example.com",
            password_hash="hashed_password_securely_stored",  # In production, hash with werkzeug
            rol_id=cliente_role.id if cliente_role else None,
            fecha_registro=datetime.utcnow()
        )
        
        # Check if user already exists
        existing_user = db.query(Usuario).filter(
            Usuario.email == "juan.perez@example.com"
        ).first()
        
        if not existing_user:
            db.add(sample_user)
            db.commit()
            print(f"   ✓ User created (ID: {sample_user.id})\n")
            user = sample_user
        else:
            print(f"   ℹ️  User already exists (ID: {existing_user.id})\n")
            user = existing_user
        
        # 3. Create Health Profile
        print("3️⃣  Creating health profile...")
        health_profile = db.query(PerfilSalud).filter(
            PerfilSalud.usuario_id == user.id
        ).first()
        
        if not health_profile:
            health_profile = PerfilSalud(
                usuario_id=user.id,
                peso_actual=75.5,
                altura=175,
                imc_actual=24.6,
                frecuencia_gym="4+ dias",
                hora_desayuno=time(7, 30),
                hora_comida=time(13, 0),
                hora_cena=time(20, 0),
                momento_critico_picoteo="tarde",
                percepcion_corporal="Me siento bien con mi cuerpo, pero quiero mejorar mi resistencia cardiovascular"
            )
            db.add(health_profile)
            db.commit()
            print(f"   ✓ Health profile created (ID: {health_profile.id})\n")
        else:
            print(f"   ℹ️  Health profile already exists (ID: {health_profile.id})\n")
        
        # 4. Create Daily Record
        print("4️⃣  Creating daily record...")
        daily_record = RegistroDiario(
            usuario_id=user.id,
            fecha=date.today(),
            foto_comida_url="https://example.com/food-photo-001.jpg",
            analisis_nutricional_ia="Comida balanceada. Alto en proteínas (30g), carbohidratos complejos y grasas saludables.",
            estado_animo_puntuacion=8,
            sentimiento_detectado_ia="felicidad",
            notas_diario="Tuve un excelente día. Ejercicio matutino completado, alimentación balanceada."
        )
        db.add(daily_record)
        db.commit()
        print(f"   ✓ Daily record created (ID: {daily_record.id})\n")
        
        # 5. Display Summary
        print("=" * 60)
        print("📊 DATA SUMMARY")
        print("=" * 60)
        print(f"\n👤 User: {user.nombre}")
        print(f"   Email: {user.email}")
        print(f"   Role: {user.rol.nombre if user.rol else 'N/A'}")
        print(f"   Registered: {user.fecha_registro}\n")
        
        print(f"❤️  Health Profile:")
        print(f"   Weight: {health_profile.peso_actual} kg")
        print(f"   Height: {health_profile.altura} cm")
        print(f"   BMI: {health_profile.imc_actual}")
        print(f"   Gym frequency: {health_profile.frecuencia_gym}\n")
        
        print(f"📝 Daily Record (Today):")
        print(f"   Mood: {daily_record.estado_animo_puntuacion}/10")
        print(f"   Sentiment: {daily_record.sentimiento_detectado_ia}")
        print(f"   Notes: {daily_record.notas_diario}\n")
        
        print("=" * 60)
        print("✅ Sample data created successfully!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def query_examples():
    """Show query examples"""
    db = SessionLocal()
    
    print("\n" + "=" * 60)
    print("🔍 QUERY EXAMPLES")
    print("=" * 60 + "\n")
    
    # Query all users
    print("1️⃣  All users:")
    users = db.query(Usuario).all()
    for user in users:
        print(f"   - {user.nombre} ({user.email})")
    
    # Query user with relationships
    print("\n2️⃣  User with relationships:")
    user = db.query(Usuario).first()
    if user:
        print(f"   User: {user.nombre}")
        print(f"   Role: {user.rol.nombre}")
        if user.perfil_salud:
            print(f"   BMI: {user.perfil_salud.imc_actual}")
        print(f"   Daily records: {len(user.registros_diarios)}")
    
    # Query by role
    print("\n3️⃣  Clients only:")
    clients = db.query(Usuario).join(Rol).filter(Rol.nombre == "cliente").all()
    print(f"   Found: {len(clients)} client(s)")
    
    db.close()
    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("\n🚀 AuraFit AI - Database Example\n")
    
    try:
        setup_database()
        create_sample_data()
        query_examples()
        print("✅ All examples completed!\n")
    except Exception as e:
        print(f"\n❌ Failed: {e}\n")
