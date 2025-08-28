#!/usr/bin/env python3
"""
Seed database with test data for development.
"""

import asyncio
import sys
import json
from pathlib import Path
from uuid import uuid4

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
import logging

# Set environment variables for seeding to avoid validation errors
import os
os.environ.setdefault("SERVICETITAN_CLIENT_ID", "seeding_temp")
os.environ.setdefault("SERVICETITAN_CLIENT_SECRET", "seeding_temp")
os.environ.setdefault("SERVICETITAN_TENANT_ID", "seeding_temp")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://integration_user:integration_pass@localhost:5432/integration_service")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_seed_database_url():
    """Get database URL for seeding."""
    # Allow override for Docker environment
    import os
    migration_url = os.getenv('MIGRATION_DATABASE_URL')
    if migration_url:
        return migration_url
    
    # Default local development URL
    return "postgresql+asyncpg://integration_user:integration_pass@localhost:5432/integration_service"


async def seed_database():
    """Seed database with test data."""
    try:
        # Get database URL
        database_url = get_seed_database_url()
        logger.info(f"Connecting to database: {database_url}")
        
        # Create engine and session factory
        engine = create_async_engine(database_url)
        async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session_factory() as session:
            # Check if data already exists
            existing_companies = await session.execute(
                text("SELECT COUNT(*) FROM companies")
            )
            if existing_companies.scalar() > 0:
                logger.info("Database already has data, skipping seed.")
                return
            
            # Create test companies
            logger.info("Creating test companies...")
            
            # ServiceTitan company - Plumbing & HVAC
            servicetitan_company_id = uuid4()
            await session.execute(
                text("""
                INSERT INTO companies (id, name, provider_type, provider_config, is_active)
                VALUES (:id, :name, :provider_type, :provider_config, :is_active)
                """),
                {
                    "id": servicetitan_company_id,
                    "name": "ABC Plumbing & HVAC Services",
                    "provider_type": "servicetitan",
                    "provider_config": json.dumps({
                        "client_id": "test_client_id",
                        "client_secret": "test_client_secret",
                        "tenant_id": "test_tenant_id",
                        "api_version": "v1",
                        "timeout_seconds": 30
                    }),
                    "is_active": True
                }
            )
            
            # Mock company - General Home Services
            mock_company_id = uuid4()
            await session.execute(
                text("""
                INSERT INTO companies (id, name, provider_type, provider_config, is_active)
                VALUES (:id, :name, :provider_type, :provider_config, :is_active)
                """),
                {
                    "id": mock_company_id,
                    "name": "XYZ Home Solutions",
                    "provider_type": "mock",
                    "provider_config": json.dumps({
                        "mock_delay_ms": 1000,
                        "mock_success_rate": 0.95,
                        "mock_error_types": ["timeout", "rate_limit"]
                    }),
                    "is_active": True
                }
            )
            
            # Housecall Pro company - Electrical & Plumbing
            housecall_company_id = uuid4()
            await session.execute(
                text("""
                INSERT INTO companies (id, name, provider_type, provider_config, is_active)
                VALUES (:id, :name, :provider_type, :provider_config, :is_active)
                """),
                {
                    "id": housecall_company_id,
                    "name": "ElectroFix Electrical & Plumbing",
                    "provider_type": "housecallpro",
                    "provider_config": json.dumps({
                        "api_key": "test_housecall_api_key",
                        "company_id": "test_housecall_company_id",
                        "webhook_url": "https://webhook.site/test",
                        "timeout_seconds": 25
                    }),
                    "is_active": True
                }
            )
            
            # Company that REQUESTS jobs (empresa que SOLICITA trabalhos)
            requesting_company_id = uuid4()
            await session.execute(
                text("""
                INSERT INTO companies (id, name, provider_type, provider_config, is_active)
                VALUES (:id, :name, :provider_type, :provider_config, :is_active)
                """),
                {
                    "id": requesting_company_id,
                    "name": "Home Services Co.",  # Empresa que solicita trabalhos
                    "provider_type": "mock",
                    "provider_config": json.dumps({
                        "mock_delay_ms": 500,
                        "mock_success_rate": 1.0
                    }),
                    "is_active": True
                }
            )
            
            # Create company skills
            logger.info("Creating company skills...")
            
            # ABC Plumbing & HVAC Skills
            await session.execute(
                text("""
                INSERT INTO company_skills (id, company_id, skill_name, skill_level, is_primary)
                VALUES (:id, :company_id, :skill_name, :skill_level, :is_primary)
                """),
                {
                    "id": uuid4(),
                    "company_id": servicetitan_company_id,
                    "skill_name": "plumbing",
                    "skill_level": "expert",
                    "is_primary": True
                }
            )
            
            await session.execute(
                text("""
                INSERT INTO company_skills (id, company_id, skill_name, skill_level, is_primary)
                VALUES (:id, :company_id, :skill_name, :skill_level, :is_primary)
                """),
                {
                    "id": uuid4(),
                    "company_id": servicetitan_company_id,
                    "skill_name": "hvac",
                    "skill_level": "expert",
                    "is_primary": True
                }
            )
            
            await session.execute(
                text("""
                INSERT INTO company_skills (id, company_id, skill_name, skill_level, is_primary)
                VALUES (:id, :company_id, :skill_name, :skill_level, :is_primary)
                """),
                {
                    "id": uuid4(),
                    "company_id": servicetitan_company_id,
                    "skill_name": "water_heater_repair",
                    "skill_level": "expert",
                    "is_primary": True
                }
            )
            
            # XYZ Home Solutions Skills
            await session.execute(
                text("""
                INSERT INTO company_skills (id, company_id, skill_name, skill_level, is_primary)
                VALUES (:id, :company_id, :skill_name, :skill_level, :is_primary)
                """),
                {
                    "id": uuid4(),
                    "company_id": mock_company_id,
                    "skill_name": "general_repairs",
                    "skill_level": "intermediate",
                    "is_primary": True
                }
            )
            
            await session.execute(
                text("""
                INSERT INTO company_skills (id, company_id, skill_name, skill_level, is_primary)
                VALUES (:id, :company_id, :skill_name, :skill_level, :is_primary)
                """),
                {
                    "id": uuid4(),
                    "company_id": mock_company_id,
                    "skill_name": "appliance_repair",
                    "skill_level": "intermediate",
                    "is_primary": True
                }
            )
            
            await session.execute(
                text("""
                INSERT INTO company_skills (id, company_id, skill_name, skill_level, is_primary)
                VALUES (:id, :company_id, :skill_name, :skill_level, :is_primary)
                """),
                {
                    "id": uuid4(),
                    "company_id": mock_company_id,
                    "skill_name": "handyman_services",
                    "skill_level": "basic",
                    "is_primary": True
                }
            )
            
            # ElectroFix Skills
            await session.execute(
                text("""
                INSERT INTO company_skills (id, company_id, skill_name, skill_level, is_primary)
                VALUES (:id, :company_id, :skill_name, :skill_level, :is_primary)
                """),
                {
                    "id": uuid4(),
                    "company_id": housecall_company_id,
                    "skill_name": "electrical",
                    "skill_level": "expert",
                    "is_primary": True
                }
            )
            
            await session.execute(
                text("""
                INSERT INTO company_skills (id, company_id, skill_name, skill_level, is_primary)
                VALUES (:id, :company_id, :skill_name, :skill_level, :is_primary)
                """),
                {
                    "id": uuid4(),
                    "company_id": housecall_company_id,
                    "skill_name": "plumbing",
                    "skill_level": "intermediate",
                    "is_primary": True
                }
            )
            
            # Home Services Co. Skills (Requesting Company)
            await session.execute(
                text("""
                INSERT INTO company_skills (id, company_id, skill_name, skill_level, is_primary)
                VALUES (:id, :company_id, :skill_name, :skill_level, :is_primary)
                """),
                {
                    "id": uuid4(),
                    "company_id": requesting_company_id,
                    "skill_name": "job_coordination",
                    "skill_level": "expert",
                    "is_primary": True
                }
            )
            
            # Create company provider associations
            logger.info("Creating company provider associations...")
            
            # ABC Plumbing & HVAC - ServiceTitan
            await session.execute(
                text("""
                INSERT INTO company_provider_associations (id, company_id, provider_type, provider_config, is_active)
                VALUES (:id, :company_id, :provider_type, :provider_config, :is_active)
                """),
                {
                    "id": uuid4(),
                    "company_id": servicetitan_company_id,
                    "provider_type": "servicetitan",
                    "provider_config": json.dumps({
                        "client_id": "test_client_id",
                        "client_secret": "test_client_secret",
                        "tenant_id": "test_tenant_id",
                        "api_version": "v1",
                        "timeout_seconds": 30
                    }),
                    "is_active": True
                }
            )
            
            # XYZ Home Solutions - Mock Provider
            await session.execute(
                text("""
                INSERT INTO company_provider_associations (id, company_id, provider_type, provider_config, is_active)
                VALUES (:id, :company_id, :provider_type, :provider_config, :is_active)
                """),
                {
                    "id": uuid4(),
                    "company_id": mock_company_id,
                    "provider_type": "mock",
                    "provider_config": json.dumps({
                        "mock_delay_ms": 1000,
                        "mock_success_rate": 0.95,
                        "mock_error_types": ["timeout", "rate_limit"]
                    }),
                    "is_active": True
                }
            )
            
            # ElectroFix - Housecall Pro
            await session.execute(
                text("""
                INSERT INTO company_provider_associations (id, company_id, provider_type, provider_config, is_active)
                VALUES (:id, :company_id, :provider_type, :provider_config, :is_active)
                """),
                {
                    "id": uuid4(),
                    "company_id": housecall_company_id,
                    "provider_type": "housecallpro",
                    "provider_config": json.dumps({
                        "api_key": "test_housecall_api_key",
                        "company_id": "test_housecall_company_id",
                        "webhook_url": "https://webhook.site/test",
                        "timeout_seconds": 25
                    }),
                    "is_active": True
                }
            )
            
            # Home Services Co. - Mock Provider (for requesting)
            await session.execute(
                text("""
                INSERT INTO company_provider_associations (id, company_id, provider_type, provider_config, is_active)
                VALUES (:id, :company_id, :provider_type, :provider_config, :is_active)
                """),
                {
                    "id": uuid4(),
                    "company_id": requesting_company_id,
                    "provider_type": "mock",
                    "provider_config": json.dumps({
                        "mock_delay_ms": 500,
                        "mock_success_rate": 1.0
                    }),
                    "is_active": True
                }
            )
            
            # Create job categories
            logger.info("Creating job categories...")
            
            categories = [
                ("plumbing", "Plumbing Services", "All types of plumbing work"),
                ("hvac", "HVAC Services", "Heating, ventilation, and air conditioning"),
                ("electrical", "Electrical Services", "Electrical work and repairs"),
                ("appliance_repair", "Appliance Repair", "Home appliance repairs"),
                ("general_repairs", "General Repairs", "General home maintenance"),
                ("handyman", "Handyman Services", "Various small repairs and tasks"),
                ("water_heater", "Water Heater Services", "Water heater installation and repair"),
                ("emergency_repairs", "Emergency Repairs", "Urgent repair services")
            ]
            
            category_ids = {}
            for category_key, category_name, category_description in categories:
                category_id = uuid4()
                await session.execute(
                    text("""
                    INSERT INTO job_categories (id, name, description, parent_category_id)
                    VALUES (:id, :name, :description, :parent_category_id)
                    """),
                    {
                        "id": category_id,
                        "name": category_name,
                        "description": category_description,
                        "parent_category_id": None
                    }
                )
                category_ids[category_key] = category_id
            
            # Create test technicians
            logger.info("Creating test technicians...")
            
            technician1_id = uuid4()
            await session.execute(
                text("""
                INSERT INTO technicians (id, name, phone, email, company_id)
                VALUES (:id, :name, :phone, :email, :company_id)
                """),
                {
                    "id": technician1_id,
                    "name": "John Smith",
                    "phone": "(555) 123-4567",
                    "email": "john@abcplumbing.com",
                    "company_id": servicetitan_company_id
                }
            )
            
            technician2_id = uuid4()
            await session.execute(
                text("""
                INSERT INTO technicians (id, name, phone, email, company_id)
                VALUES (:id, :name, :phone, :email, :company_id)
                """),
                {
                    "id": technician2_id,
                    "name": "Sarah Johnson",
                    "phone": "(555) 987-6543",
                    "email": "sarah@xyzhome.com",
                    "company_id": mock_company_id
                }
            )
            
            technician3_id = uuid4()
            await session.execute(
                text("""
                INSERT INTO technicians (id, name, phone, email, company_id)
                VALUES (:id, :name, :phone, :email, :company_id)
                """),
                {
                    "id": technician3_id,
                    "name": "Mike Davis",
                    "phone": "(555) 456-7890",
                    "email": "mike@electrofix.com",
                    "company_id": housecall_company_id
                }
            )
            
            requesting_tech_id = uuid4()
            await session.execute(
                text("""
                INSERT INTO technicians (id, name, phone, email, company_id)
                VALUES (:id, :name, :phone, :email, :company_id)
                """),
                {
                    "id": requesting_tech_id,
                    "name": "Alex Rodriguez",  # Técnico que IDENTIFICA necessidades
                    "phone": "(555) 000-0000",
                    "email": "alex.rodriguez@homeservices.com",
                    "company_id": requesting_company_id
                }
            )
            
            # Commit all changes
            await session.commit()
            
            logger.info("✅ Test data seeded successfully!")
            logger.info("📊 Companies created:")
            logger.info(f"   • ABC Plumbing & HVAC Services (ServiceTitan) - Expert in plumbing & HVAC")
            logger.info(f"   • XYZ Home Solutions (Mock) - Intermediate in general repairs & appliances")
            logger.info(f"   • ElectroFix Electrical & Plumbing (Housecall Pro) - Expert in electrical, intermediate in plumbing")
            logger.info(f"   • Home Services Co. (Mock) - Job coordination company")
            
            logger.info("🔧 Skills & Categories:")
            logger.info(f"   • Plumbing: Expert level (ABC, ElectroFix)")
            logger.info(f"   • HVAC: Expert level (ABC)")
            logger.info(f"   • Electrical: Expert level (ElectroFix)")
            logger.info(f"   • General Repairs: Intermediate level (XYZ)")
            logger.info(f"   • Appliance Repair: Intermediate level (XYZ)")
            
            logger.info("👷 Technicians created:")
            logger.info(f"   • John Smith (ABC) - Plumbing specialist")
            logger.info(f"   • Sarah Johnson (XYZ) - General repairs")
            logger.info(f"   • Mike Davis (ElectroFix) - Electrical specialist")
            logger.info(f"   • Alex Rodriguez (Home Services Co.) - Job coordinator")
            
            logger.info("🚀 Ready for job creation and intelligent matching!")
            
    except Exception as e:
        logger.error(f"❌ Seeding failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    import os
    asyncio.run(seed_database())