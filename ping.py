from src.api.mikrotik import Mikrotik
from src.db.db import Database
from src.utils.utils import Tools

from dotenv import load_dotenv
import os

# Importar módulos de logging
import logging
from logging.handlers import RotatingFileHandler

tools = Tools()

# Define o caminho para o arquivo config.json com base no diretório raiz do script
root_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(root_dir, 'config.json')

logger = logging.getLogger(__name__)
configs = tools.read_configuration(config_path)

load_dotenv()

db = Database(
    database=os.getenv('MYSQL_DB'),
    host=os.getenv('MYSQL_HOST'),
    passwd=os.getenv('MYSQL_PASSW'),
    port=os.getenv('MYSQL_PORT'),
    user=os.getenv('MYSQL_USER')
)

mikrotik = Mikrotik(
    ip=os.getenv("MK_ADDRESS"),
    user=os.getenv('MK_USERNAME'),
    password=os.getenv('MK_PASSWORD'),
    port=os.getenv('MK_PORT')
)

targets = db.get_ping_target()

operators = configs['operadoras']

logger.debug('Teste de latência iniciado.')

for target in targets:
    for operator in operators:

        gateway = operator.get('gateway')
        list_name = operator.get('list_name')
        domain = target['domain']
        target_id = target['id']

        # Faz o teste de ping e coleta o resultado em INT
        response = mikrotik.ping(address=domain, src=gateway)
        ping = tools.extract_ping_time(result=response)
        success = 1

        if not isinstance(ping, int):
            success = 0

        if success == 0:
            ping = None

        db.insert_ping_target_test(target_id, ping, list_name, success)
        logger.debug(f"Target: {domain} Success: {success} Latency: {ping}")
        
logger.debug('Teste de latência concluido')

