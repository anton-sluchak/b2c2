import logging
import requests
import re
from PyInquirer import prompt
from pprint import pprint
import uuid

API_TOKEN = 'e13e627c49705f83cbe7b60389ac411b6f86fee7'
API_URL = 'https://api.uat.b2c2.net'
BASE_CURRENCY = 'BTC'


class PrimitiveTrader:

    def __init__(self, token: str, url: str, base_currency: str):
        self.headers = {'Authorization': 'Token %s' % token}
        self.url = url
        self.base_currency = base_currency

    def __send_post_request(self, endpoint: str, data: dict):
        response = requests.post(
            '{url}/{endpoint}/'.format(url=self.url, endpoint=endpoint),
            json=data,
            headers=self.headers
        )
        if response.status_code != requests.status_codes.codes.CREATED:
            self.process_http_error(endpoint, response)

        return response.json()

    def __send_get_request(self, endpoint: str, data: dict = None):
        response = requests.get(
            '{url}/{endpoint}/'.format(url=self.url, endpoint=endpoint),
            params=data,
            headers=self.headers
        )

        if response.status_code != requests.status_codes.codes.OK:
            self.process_http_error(endpoint, response)
        return response.json()

    def __get_tradable_instruments(self) -> list:
        instruments = self.__send_get_request('instruments')
        all_instruments = [i.get('name') for i in instruments]
        return list(filter(lambda value: value.startswith(self.base_currency), all_instruments))

    def process_http_error(self, endpoint, response):
        pprint('HTTP STATUS RESPONSE CODE {code}'.format(code=response.status_code))
        logging.warning("{endpoint} generated status code {code}".format(endpoint=endpoint, code=response.status_code))

    def log_errors(self, errors):
        pprint('Errors occured:')
        for error in errors:
            pprint(error.get('message'))

    def request_for_quote(self):
        tradable_instruments_list = self.__get_tradable_instruments()
        data = prompt([
            {
                'type': 'list',
                'name': 'instrument',
                'message': 'Please, pick an instrument?',
                'choices': tradable_instruments_list,
            },
            {
                'type': 'list',
                'name': 'side',
                'message': 'Please, pick a side?',
                'choices': ['buy', 'sell'],
            },
            {
                'type': 'input',
                'name': 'quantity',
                'message': 'Please, enter quantity?',
                'filter': lambda val: re.sub(r"\D", "", val),
                'validate': lambda val: len(val) <= 4 or 'The number is too big'
            }
        ])

        data['client_rfq_id'] = str(uuid.uuid4())

        rfq = self.__send_post_request('request_for_quote', data)

        pprint(rfq)

        if rfq.get('errors') is None:
            execution = prompt([
                {
                    'type': 'list',
                    'name': 'execution',
                    'message': 'Would you like to execute?',
                    'choices': ['yes', 'no'],
                }
            ]).get('execution')
            if execution == 'yes':
                self.order(rfq)
        else:
            self.log_errors(rfq.get('errors'))

    def order(self, rfq):
        post_data = {
            'instrument': rfq.get('instrument'),
            'side': rfq.get('side'),
            'quantity': rfq.get('quantity'),
            'client_order_id': rfq.get('client_rfq_id'),
            'price': rfq.get('price'),
            'order_type': 'FOK',
            'valid_until': rfq.get('valid_until'),
            'executing_unit': 'risk-adding-strategy',
        }
        posted_order = self.__send_post_request('order', post_data)
        if posted_order.get('errors') is None:
            pprint(posted_order)
        else:
            self.log_errors(posted_order.get('errors'))

    def execute(self, option):
        if option == 'info':
            pprint(self.__send_get_request('account_info'))
        elif option == 'balance':
            pprint(self.__send_get_request('balance'))
        elif option == 'rfq':
            self.request_for_quote()
        elif option == 'exit':
            print('Good bye!')


if __name__ == '__main__':
    Trader = PrimitiveTrader(API_TOKEN, API_URL, BASE_CURRENCY)
    option = ''
    while option != 'exit':
        main_menu = [
            {
                'type': 'list',
                'name': 'action',
                'message': 'What would you like to do?',
                'choices': ['Balance', 'RFQ', 'Info', 'exit'],
                'filter': lambda val: val.lower()
            }
        ]
        option = prompt(main_menu).get('action')
        Trader.execute(option)
