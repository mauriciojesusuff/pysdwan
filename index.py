from src.utils.Geoip2 import Geoip2
from src.api.mikrotik import Mikrotik
from src.utils.utils import Tools
from src.db.db import Database

from dotenv import load_dotenv
import os
import time
from typing import List

# Importar módulos de logging
import logging
from logging.handlers import RotatingFileHandler

# Carregar as variáveis do arquivo .env para o ambiente
load_dotenv()

# Configurar o logging
logging.basicConfig(level=logging.INFO)

# Criar um handler com um limite de aproximadamente 1k linhas
handler = RotatingFileHandler('app.log', maxBytes=1000000, backupCount=1)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.addHandler(handler)

tools = Tools()
geoIp2 = Geoip2()

# Define o caminho para o arquivo config.json com base no diretório raiz do script
root_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(root_dir, 'config.json')

configs = tools.read_configuration(config_path)
mikrotik = Mikrotik(
    ip=os.getenv("MK_ADDRESS"),
    user=os.getenv('MK_USERNAME'),
    password=os.getenv('MK_PASSWORD'),
    port=os.getenv('MK_PORT')
)

operators = configs['operadoras']
black_list = configs['black_list']

db = Database(
    database=os.getenv('MYSQL_DB'),
    host=os.getenv('MYSQL_HOST'),
    passwd=os.getenv('MYSQL_PASSW'),
    port=os.getenv('MYSQL_PORT'),
    user=os.getenv('MYSQL_USER')
)

start_time = time.time()
logger.info("Script iniciado.")

# Limpa os dados atuais da tabela da lista de ISP do firewall
db.clear_current_address_list()
logger.info("Lista de endereços atual no banco de dados foi limpa.")

list_address_mapped = [operadora["list_name"] for operadora in operators]

# Pegar todas as firewall/address-list
address_list = mikrotik.get_address_list(list_address_mapped)
logger.info("Lista de endereços obtida do Mikrotik.")

db.insert_current_address_list(address_list)
logger.info("Lista de endereços atual inserida no banco de dados.")

# Pegar todos os IPs do firewall/connections
connections_address = mikrotik.get_connection_address()
logger.info("Endereços de conexão obtidos do Mikrotik.")

# Abrir a sessão com banco de dados local
geoIp2.open()
logger.info("Sessão GeoIP2 aberta.")

# Conjunto para armazenar os blocos IP já vistos
seen_ip_blocks = {}

#Abrir uma nova conexão com o banco de dados

index = 0
for address_info in connections_address:
    # Extrair o endereço IP (removendo a porta, se houver)
    address = address_info['dst-address'].split(':')[0]

    # Validar se é um IP válido
    if not tools.is_valid_ip(address):
        continue

    # Verificar se o IP é privado e pular se for
    if tools.is_private_ip(address):
        continue

    if tools.is_ip_in_blacklist(address, black_list):
        continue

    try:
        # Obter o bloco IP do endereço
        ip_block = geoIp2.getIpBlock(address)
    except Exception as e:
        logger.error(f"Erro ao obter o bloco IP para {address}: {e}")
        continue

    # Converter o bloco IP para string
    ip_block_str = ip_block

    # Verificar se o bloco IP já foi processado
    if ip_block_str in seen_ip_blocks:
        continue  # Pular este IP

    # Adicionar o bloco IP ao conjunto de blocos já vistos
    seen_ip_blocks[ip_block_str] = address

# Fechar a sessão com o banco de dados local
geoIp2.close()
logger.info("Sessão GeoIP2 fechada.")

logger.info(f"Total de blocos IP únicos processados: {len(seen_ip_blocks)} em {time.time() - start_time} segundos")

total_blocks = len(seen_ip_blocks)

db.open_connection()

for index, (block, address) in enumerate(seen_ip_blocks.items(), start=1):
    latency_tests = []

    for operator in operators:
        gateway = operator.get('gateway')
        list_name = operator.get('list_name')
        operator_name = operator.get('name')

        # Faz o teste de ping e coleta o resultado em INT
        response = mikrotik.ping(address=address, src=gateway)
        ping = tools.extract_ping_time(result=response)

        if not isinstance(ping, int):
            continue

        latency_tests.append({
            'operator': operator_name,
            'latency': ping,
            'list_name': list_name,
            'network': block,
            'address': address
        })

        db.insert_ping_test(list_name, gateway, address, ping)

    if not latency_tests:
        continue

    best = tools.get_best_latency(
        latency_test=latency_tests, debug=False, index=index, total=total_blocks
    )

    # Verificar se 'best' é None ou vazio
    if best is None:
        logger.error("Erro: get_best_latency retornou None.")
        continue

    # Verificar o valor específico de 'network' em 'best'
    if best.get('network') is None:
        logger.warning("Aviso: best['network'] é None, pulando este item.")
        continue

    logger.info(f"{best['network']} - {best['address']} - {best['latency']}ms - {best['operator']}")

    result = db.get_list_name_to_current_address_list(best['network'])

    address = best.get('address')
    network = best.get('network')
    list_name = best.get('list_name')
    ping = best.get('latency')

    if result is None:
        mikrotik.add_ip_in_address_list(address=network, list_name=list_name)

        db.insert_one_current_address_list(best)
        db.insert_manipulation("ADDED", network, ping, list_name)

        logger.info(f">> Nova rota adicionada: {best['network']} - {list_name}")

    elif result['list_name'] != list_name:
        address_lists = mikrotik.get_address_list_by_address(address=network)

        for address_list in address_lists:
            mikrotik.remove_ip_in_address_list(address_list['.id'])

        mikrotik.add_ip_in_address_list(address=network, list_name=list_name)

        db.update_current_address_list(best)
        db.insert_manipulation('REMOVED', network, None, list_name)

        logger.info(f">> Rota de {best['network']} trocada para {list_name}.")
