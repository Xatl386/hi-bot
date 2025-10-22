"""
Модуль для работы с базой данных
"""
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, BigInteger, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from config import DATABASE_URL
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class User(Base):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    chat_id = Column(BigInteger, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    subscribed = Column(Boolean, default=False)
    subscription_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    reminder_3min_sent = Column(Boolean, default=False)
    reminder_10min_sent = Column(Boolean, default=False)
    reminder_30min_sent = Column(Boolean, default=False)
    reminder_9hours_sent = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<User(user_id={self.user_id}, username={self.username}, subscribed={self.subscribed})>"


class Mailing(Base):
    """Модель рассылки"""
    __tablename__ = 'mailings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_text = Column(Text, nullable=False)
    image_path = Column(String(500), nullable=True)
    scheduled_time = Column(DateTime, nullable=True)
    status = Column(String(50), default='draft')  # draft, test_sent, sent, sending
    created_by = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<Mailing(id={self.id}, status={self.status}, created_at={self.created_at})>"


class ReminderText(Base):
    """Модель для хранения текстов напоминаний"""
    __tablename__ = 'reminder_texts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    reminder_type = Column(String(50), unique=True, nullable=False)  # reminder_3min, reminder_10min, etc.
    text = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ReminderText(reminder_type={self.reminder_type})>"


class BotSettings(Base):
    """Модель для хранения настроек бота"""
    __tablename__ = 'bot_settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    setting_key = Column(String(100), unique=True, nullable=False)  # channel_invite_link, welcome_message, etc.
    setting_value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<BotSettings(setting_key={self.setting_key})>"


def init_db():
    """Инициализация базы данных"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("База данных успешно инициализирована")
        
        # Инициализация текстов напоминаний по умолчанию
        db = SessionLocal()
        try:
            from config import DEFAULT_REMINDER_TEXT, DEFAULT_GREETING_MESSAGE
            
            # Инициализация напоминаний
            reminder_types = ['reminder_3min', 'reminder_10min', 'reminder_30min', 'reminder_9hours']
            for reminder_type in reminder_types:
                existing = db.query(ReminderText).filter_by(reminder_type=reminder_type).first()
                if not existing:
                    reminder_text = ReminderText(
                        reminder_type=reminder_type,
                        text=DEFAULT_REMINDER_TEXT
                    )
                    db.add(reminder_text)
            
            # Инициализация приветственного сообщения по умолчанию
            greeting_setting = db.query(BotSettings).filter_by(setting_key='greeting_message').first()
            if not greeting_setting:
                greeting_setting = BotSettings(
                    setting_key='greeting_message',
                    setting_value=DEFAULT_GREETING_MESSAGE
                )
                db.add(greeting_setting)
                logger.info("Инициализировано приветственное сообщение по умолчанию")
            
            db.commit()
            logger.info("Тексты напоминаний и приветствий по умолчанию инициализированы")
        except Exception as e:
            db.rollback()
            logger.error(f"Ошибка при инициализации текстов: {e}")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise


def get_db() -> Session:
    """Получить сессию базы данных"""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


