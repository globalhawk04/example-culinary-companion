# FILE: database.py

import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the database URL from environment variables
# We default to a local SQLite database file named 'cookbook.db'
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./cookbook.db")

# The engine is the core interface to the database
engine = create_async_engine(DATABASE_URL)

# The sessionmaker provides a factory for creating database sessions (i.e., conversations)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# This is the base class that our database models will inherit from
class Base(DeclarativeBase):
    pass
