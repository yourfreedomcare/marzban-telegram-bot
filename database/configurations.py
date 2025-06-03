'''
File includes schema for telegram_users_configurations table
'''

from sqlalchemy import Column, Integer, String,ForeignKey,DateTime, func
from sqlalchemy.orm import relationship
from .base import Base, Session

class Configurations(Base): 
    __tablename__ = 'telegram_users_configurations'
    
    id = Column(Integer, primary_key=True)
    vless_link = Column(String(8000))
    telegram_user_id = Column(String(255), ForeignKey('telegram_users.telegram_user_id', ondelete='CASCADE'))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    user = relationship('User', back_populates='configurations') 

    def __init__(self, telegram_user_id, vless_link):
        self.telegram_user_id = telegram_user_id
        self.vless_link = vless_link
