'''
File includes the schemas for telegram_users table
as well as all the direct querying logic for the full app through UserRepository Class
'''

from sqlalchemy import Column, String,DateTime, func

from sqlalchemy.orm import relationship

from .base import Base, Session
from .configurations import Configurations

from sqlalchemy import Column, String, Boolean, update
from sqlalchemy.orm import relationship
from .base import Base
from marzban_api.marzban_api_facade import MarzbanApiFacade
from logger import logger

class User(Base):
    __tablename__ = 'telegram_users'

    telegram_user_id = Column(String(255), primary_key=True)
    chat_id = Column(String(255))
    is_updated = Column(Boolean)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    configurations = relationship('Configurations', back_populates='user', cascade='all, delete-orphan')

    def __init__(self, telegram_user_id, chat_id=None):
        self.telegram_user_id = telegram_user_id
        self.chat_id = chat_id
        self.is_updated = True

class UserRepository(): 

    @staticmethod
    def get_users(): 
        with Session() as session: 
            with session.begin(): 
                try: 
                    logger.info('get_users -> getting all users data')
                    users = session.query(User).all()
                except Exception: 
                    logger.error("Exception -> get_users: ", exc_info=True)
                    session.rollback
                finally: 
                    session.close()
        return users

    @staticmethod
    def get_user(telegram_user_id):
        with Session() as session: 
            with session.begin(): 
                try: 
                    logger.info(f'get_user {telegram_user_id} -> grabbing user\'s data')
                    user = session.query(User).filter_by(telegram_user_id=telegram_user_id).first()
                    configurations = None if user == None else user.configurations
                    session.close()
                except Exception:
                    logger.error(f"Exception -> get_user: ", exc_info=True)
                    session.rollback()
        return [user, configurations]
    
    @staticmethod
    def get_user_configurations(telegram_user_id):
        with Session() as session: 
            with session.begin(): 
                try: 
                    configurations = session.query(Configurations).filter_by(telegram_user_id=telegram_user_id).all()
                    logger.info('get_user_configurations -> grabbing users configs')
                    configurations = session.query(Configurations).filter_by(telegram_user_id=telegram_user_id).all()
                    session.close()
                except Exception:
                    logger.error(f"Exception -> get_user_configurations: ", exc_info=True)
                    session.rollback()
        return configurations


    @staticmethod
    def create_new_user(telegram_user_id, chat_id): 
        with Session() as session: 
            with session.begin(): 
                try: 
                    logger.info('create_new_user -> creating new user')
                    new_user = User(telegram_user_id, chat_id)
                    session.add(new_user)
                except Exception:
                    logger.error(f"Exception -> create_new_user: ", exc_info=True)
                    session.rollback()
                finally:
                    session.commit()
        
    @staticmethod
    def insert_configurations(telegram_user_id, chat_id, links): 
        try: 
            with Session() as session: 
                user = session.query(User).filter_by(telegram_user_id=telegram_user_id).first()
                if user is None:
                    user = User(telegram_user_id, chat_id)
                    session.add(user)
                    session.flush()

                configs = [Configurations(telegram_user_id=telegram_user_id, vless_link=link) for link in links]
                session.bulk_save_objects(configs)
                session.commit()
        except Exception as e:
            logger.error(f"Exception -> insert_configurations: {e}", exc_info=True)


    @staticmethod
    def refresh_configs(access_token): 
        session = Session()
        users = session.query(User).all()
        for user in users: 
            user_marzban_data, status_code = MarzbanApiFacade.get_user(user.telegram_user_id, access_token)
            if status_code == 200:
                new_configs = [Configurations(user.telegram_user_id, link) for link in user_marzban_data['links']]
                try:
                    existing_configs = session.query(Configurations).filter_by(telegram_user_id=user.telegram_user_id).all()
                    for config in existing_configs:
                        session.delete(config)
                    session.bulk_save_objects(new_configs)
                    session.commit()
                except Exception:
                    logger.error(f"Exception -> refresh_configs: ", exc_info=True)
                    session.rollback()
            else: 
                if status_code == 404: 
                    try: 
                        if len(user.configurations) > 0: 
                            session.delete(user)
                            session.commit()
                    except: 
                        logger.error(f"Exception -> refresh_configs: ", exc_info=True)
                        session.rollback()
                else: 
                    continue
    
    @staticmethod
    def mark_users_for_update():
        with Session() as session: 
            with session.begin(): 
                try: 
                    session.execute(
                        update(User).
                        values(is_updated=False)
                    )
                    session.commit()
                except:
                    logger.error("Exception -> mark_users_for_update", exc_info=True)
                    session.rollback()
                finally:
                    session.close()

    @staticmethod 
    def mark_user_as_updated(telegram_user_id): 
        with Session() as session: 
            with session.begin(): 
                try: 
                    session.execute(
                        update(User).
                        where(User.telegram_user_id == telegram_user_id). 
                        values(is_updated=True)
                    )
                    
                    session.commit()
                except: 
                    logger.error("Exception -> mark_user_as_updated", exc_info=True)
                    session.rollback()
                finally:
                    session.close()
                    


