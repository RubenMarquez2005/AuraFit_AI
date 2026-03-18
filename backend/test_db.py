#!/usr/bin/env python3
"""
Database Connection & Models Test Script
Tests the database configuration and all models
"""

import sys
from app.config.settings import settings
from app.db import SessionLocal, verify_database_connection, engine, Base
from app.models import Rol, Usuario, PerfilSalud, RegistroDiario
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


async def test_database():
    """Run all database tests"""
    
    print_header("AuraFit AI - Database Configuration Test")
    
    # 1. Test Settings
    print("📋 Configuration:")
    print(f"   App Name: {settings.APP_NAME}")
    print(f"   Debug Mode: {settings.DEBUG}")
    print(f"   DB Host: {settings.DB_HOST}")
    print(f"   DB Port: {settings.DB_PORT}")
    print(f"   DB Name: {settings.DB_NAME}")
    print(f"   Database URL: {settings.DATABASE_URL}")
    
    # 2. Test Connection
    print("\n🔌 Testing Database Connection...")
    is_connected = await verify_database_connection()
    if not is_connected:
        print("   ✗ Connection failed!")
        return False
    print("   ✓ Connection successful!")
    
    # 3. Create Tables
    print("\n🗂️  Creating Tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("   ✓ Tables created/verified")
    except Exception as e:
        print(f"   ✗ Error creating tables: {e}")
        return False
    
    # 4. Test Models
    print("\n📦 Testing Models:")
    models = [
        ("Rol", Rol),
        ("Usuario", Usuario),
        ("PerfilSalud", PerfilSalud),
        ("RegistroDiario", RegistroDiario),
    ]
    
    for name, model in models:
        print(f"   ✓ {name}: {model.__tablename__}")
    
    # 5. Test Session
    print("\n🗄️  Testing Database Session...")
    db = SessionLocal()
    try:
        db.execute("SELECT 1")
        print("   ✓ Session query successful")
    except Exception as e:
        print(f"   ✗ Session error: {e}")
        return False
    finally:
        db.close()
    
    # 6. Summary
    print_header("✅ All Tests Passed!")
    print("Your AuraFit AI backend is ready to use.\n")
    print("📚 Next Steps:")
    print("   1. Run: python3 run.py")
    print("   2. Visit: http://localhost:8000/docs")
    print("   3. Check: http://localhost:8000/health/db\n")
    
    return True


if __name__ == "__main__":
    import asyncio
    
    print("\n")
    try:
        success = asyncio.run(test_database())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
