from src.utils.Geoip2 import Geoip2
from src.api.mikrotik import Mikrotik
from src.utils.utils import Tools
from src.db.db import Database


from dotenv import load_dotenv
import os

import time
import threading
from typing import List

# Carregar as variáveis do arquivo .env para o ambiente
load_dotenv()


tools = Tools()
geoIp2 = Geoip2()

configs = tools.read_configuration('config.json')
mikrotik = Mikrotik(ip=os.getenv("MK_ADDRESS"), user=os.getenv('MK_USERNAME'), password=os.getenv('MK_PASSWORD'), port=os.getenv('MK_PORT'))

operators = configs['operadoras']
black_list = configs['black_list']

db = Database(database=configs['mysql_db'], host=configs['mysql_host'], passwd=configs['mysql_passwd'], port=configs['mysql_port'], user=configs['mysql_user'])



start_time = time.time()

#limpa os dados atuais da tabela da lista de isp do firewall
db.clear_current_address_list()

list_address_mapped = [operadora["list_name"] for operadora in operators]

#Pegar todas as firewall/address-list
address_list = mikrotik.get_address_list(list_address_mapped)

db.insert_curruent_address_list(address_list)

#Pegar todos os ips do firewall/connections
connections_address = mikrotik.get_connection_address()

#Abrir a sessão com bd local;
geoIp2.open()

# Conjunto para armazenar os blocos IP já vistos
seen_ip_blocks = {}

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
        print(f"Erro ao obter o bloco IP para {address}: {e}")
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

print(f"Total de blocos IP únicos processados: {len(seen_ip_blocks)} em {time.time() - start_time} segundos")

total_blocks = len(seen_ip_blocks)

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

        t = threading.Thread(target=db.insert_ping_test, args=(list_name, gateway, address, ping))
        t.start()
        t.join()

    if not latency_tests:
        continue

    best = tools.get_best_latency(
        latency_test=latency_tests, debug=False, index=index, total=total_blocks
    )

    # Verificar se 'best' é None ou vazio
    if best is None:
        print("Erro: get_best_latency retornou None.")
        continue

    # Verificar o valor específico de 'network' em 'best'
    if best.get('network') is None:
        print("Aviso: best['network'] é None, pulando este item.")
        continue

    print(f"{best['network']} - {best['address']} - {best['latency']}ms - {best['operator']}")

    result = db.get_list_name_to_current_address_list(best['network'])

    address = best.get('address')
    network = best.get('network')
    list_name = best.get('list_name')
    ping = best.get('latency')

    if result is None:

        mikrotik.add_ip_in_address_list(address=network, list_name=list_name)

        print(f"Nova rota adicionada, {best['network']} - {list_name}\n")

        db.insert_one_current_address_list(best)

        t = threading.Thread(target=db.insert_manipulation, args=("ADDED", network, ping, list_name))
        t.start()
        t.join()



    elif result['list_name'] != list_name:

        address_list = mikrotik.get_address_list_by_address(address=network)

        mikrotik.remove_ip_in_address_list(address_list[0]['.id'])

        mikrotik.add_ip_in_address_list(address=network, list_name=list_name)

        db.update_current_address_list(best)

        t = threading.Thread(target=db.insert_manipulation, args=("REMOVED", network, None, list_name))
        t.start()
        t.join()

        print(f"{best['network']} trocado de rota para {list_name}.\n")
        