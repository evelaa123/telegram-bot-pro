"""
Fix missing PostgreSQL enum values for requesttype.

Run this script to add missing values (presentation, video_animate, long_video)
to the 'requesttype' PostgreSQL enum type.

Usage:
    python scripts/fix_requesttype_enum.py

This is needed when the Python RequestType enum was extended but the
database enum type was not updated (no migration was run).
"""
import asyncio
import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from database.connection import engine


REQUIRED_ENUM_VALUES = [
    'text', 'image', 'video', 'voice', 'document',
    'presentation', 'video_animate', 'long_video',
]


async def fix_enum():
    """Add missing values to the requesttype enum in PostgreSQL."""
    print("Checking requesttype enum values...")
    
    async with engine.begin() as conn:
        # Check if the enum type exists
        result = await conn.execute(text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM pg_type WHERE typname = 'requesttype'"
            ")"
        ))
        enum_exists = result.scalar()
        
        if not enum_exists:
            print("Enum type 'requesttype' does not exist. "
                  "It will be created when tables are initialized.")
            return
        
        # Get current enum values
        result = await conn.execute(text(
            "SELECT enumlabel FROM pg_enum "
            "JOIN pg_type ON pg_enum.enumtypid = pg_type.oid "
            "WHERE pg_type.typname = 'requesttype' "
            "ORDER BY pg_enum.enumsortorder"
        ))
        current_values = {row[0] for row in result}
        print(f"Current enum values: {sorted(current_values)}")
        
        # Find missing values
        missing = [v for v in REQUIRED_ENUM_VALUES if v not in current_values]
        
        if not missing:
            print("All enum values are present. No changes needed.")
            return
        
        print(f"Missing values: {missing}")
        
        # Add missing values
        for value in missing:
            print(f"  Adding '{value}' to requesttype enum...")
            await conn.execute(text(
                f"ALTER TYPE requesttype ADD VALUE IF NOT EXISTS '{value}'"
            ))
        
        print("Done! All enum values are now present.")
    
    # Also check daily_limits columns
    async with engine.begin() as conn:
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'daily_limits'"
        ))
        existing_columns = {row[0] for row in result}
        
        needed_columns = {
            'presentation_count': "ALTER TABLE daily_limits ADD COLUMN presentation_count INTEGER NOT NULL DEFAULT 0",
            'video_animate_count': "ALTER TABLE daily_limits ADD COLUMN video_animate_count INTEGER NOT NULL DEFAULT 0",
            'long_video_count': "ALTER TABLE daily_limits ADD COLUMN long_video_count INTEGER NOT NULL DEFAULT 0",
        }
        
        for col_name, ddl in needed_columns.items():
            if col_name not in existing_columns:
                print(f"  Adding column '{col_name}' to daily_limits...")
                await conn.execute(text(ddl))
            else:
                print(f"  Column '{col_name}' already exists in daily_limits.")
    
    print("\nAll fixes applied successfully!")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(fix_enum())
