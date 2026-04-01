#!/usr/bin/env python
"""
Database migration script for Azure PostgreSQL
Creates tables and seeds initial data
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.db.models import *

def migrate():
    # Use psycopg (sync) driver
    db_url = 'postgresql://pgadmin:SecurePass123@secureai-pg.postgres.database.azure.com:5432/secure_audit'
    
    print("🔄 Connecting to Azure PostgreSQL...")
    engine = create_engine(db_url, echo=False)
    
    print("🔄 Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created!")
    
    print("🌱 Seeding database...")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        from app.scripts.seed import seed_db
        seed_db(session)
        session.commit()
        print("✅ Database seeded!")
    except Exception as e:
        session.rollback()
        print(f"⚠️ Seed warning: {e}")
    finally:
        session.close()
    
    print("✅ Migration complete!")

if __name__ == "__main__":
    migrate()
