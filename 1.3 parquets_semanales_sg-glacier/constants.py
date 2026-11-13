from dotenv import load_dotenv
import os

load_dotenv()

dhd_org =  150
dhd_dest = 150
weeks = 1
cols_duplicates = ['Posted', 'CityOrigin', 'StateOrigin', 'CityDestination', 'StateDestination',
                                           'RateTotal', 'PickUp', 'Equip', 'Broker_Shipper', 'Broker_Shipper_Phone',
                                           'Broker_Shipper_Email', 'Weight', 'Size']
#loadboards = ['tsmarter', 'chr', 'doft', 'dat']
loadboards = ['chr']
keepdup = True

keys = {"indicators_dev":(os.getenv('AWS_ACCESS_KEY_ID_S'),os.getenv('AWS_SECRET_ACCESS_KEY_S')),
        "indicators_prod":(os.getenv('AWS_ACCESS_KEY_ID_P'), os.getenv('AWS_SECRET_ACCESS_KEY_P'))}

owner_telegram_id = {'consumption_rate':['1543457856'],
                     'interpreter_one':['1543457856']}