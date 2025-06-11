'''
File includes the facade for all communications with MarzbanAPI wrapped in a class isolated from 
the bot file, accessed through marzban service
'''

import requests
import os
from logger import logger


class MarzbanApiFacade():

    @staticmethod
    def get_access_token(): 
        try:
            url = f'{os.getenv("MARZBAN_API_HOST")}/api/admin/token'
            data = {
                'username': os.getenv("MARZBAN_ADMIN_USERNAME"),
                'password': os.getenv("MARZBAN_ADMIN_PASSWORD"),
                'grant_type': 'password'
            }
            response = requests.post(url, data=data)
            return response.json()['access_token']
        except Exception: 
            logger.error(f'Exception -> get_access_token -> ', exc_info=True)

    @staticmethod
    def get_user(telegram_user_id , access_token):
        try:
            url = f'{os.getenv("MARZBAN_API_HOST")}/api/user/{telegram_user_id}'
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            response = requests.get(url, headers=headers)
            return [response.json(), response.status_code]
        except Exception: 
            logger.error(f'Exception -> get_user -> ', exc_info=True)

    
    @staticmethod
    def create_user(telegram_user_id, access_token):
        print("In create User")
        print("telegram_user_id", telegram_user_id) 
        try:
            url = f'{os.getenv("MARZBAN_API_HOST")}/api/user'
            data = {
                    "username": telegram_user_id,
                    "proxies": {
                        "vless": {
                            "flow": "xtls-rprx-vision"
                        }
                    },
                    "inbounds": {
                        "vless": [
                            "VLESS TCP REALITY"
                        ]
                    },
                    "expire": 0,
                    "data_limit": 0,
                    "data_limit_reset_strategy": "no_reset",
                    "status": "active"
                }

            headers = {
                'Authorization': f'Bearer {access_token}'
            }

            response = requests.post(url, headers=headers, json=data)
            return [response.json(), response.status_code]
        except Exception: 
            logger.error(f'Exception -> get_user -> ', exc_info=True)
