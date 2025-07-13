from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

DATABASE_URL = os.getenv("DATABASE_URL")

Base = declarative_base()

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    level = Column(String)



async def set_user_level(user_id, level):
    async with async_session() as session:
        async with session.begin():
            user = await session.get(User, user_id)
            if user:
                user.level = level
            else:
                session.add(User(user_id=user_id, level=level))
        print(f"✅ Saved user {user_id} with level {level}")

async def get_user_level(user_id):
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user:
            print(f"✅ Fetched level for user {user_id}: {user.level}")
            return user.level
        print(f"❌ No level found for user {user_id}")
        return None

class UserInteraction(Base):
    __tablename__ = "user_interactions"

    user_id = Column(Integer, primary_key=True)
    last_user_message_ts = Column(DateTime, nullable=True)
    last_bot_message_ts = Column(DateTime, nullable=True)
    messages_sent_today = Column(Integer, default=0)
    last_reset_date = Column(DateTime, default=datetime.utcnow)

async def get_user_interaction(user_id: int):
        async with async_session() as session:
            return await session.get(UserInteraction, user_id)

