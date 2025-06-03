'''
File includes a set of functions that communcations with the api facade 
to provide the services that the api presents 
'''

from .marzban_api_facade import MarzbanApiFacade
class MarzbanService():

    @staticmethod
    def access_token(): 
        access_token = MarzbanApiFacade.get_access_token()
        return access_token


    @staticmethod 
    def create_marzaban_user(telegram_user_id): 
        access_token =  MarzbanService.access_token()
        api_response, status_code = MarzbanApiFacade.create_user(telegram_user_id, access_token)

        return [api_response, status_code, access_token]

    @staticmethod
    def get_marzaban_user(telegram_user_id, access_token): 
        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("GETTING MARZBAN USER")
        api_response, status_code = MarzbanApiFacade.get_user(telegram_user_id, access_token)

        return [api_response, status_code]
