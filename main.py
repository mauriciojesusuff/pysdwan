from src.api.mikrotik import Mikrotik
from src.utils.utils import Tools
from src.db.db import Database

import datetime
import time
import threading


#ative para ver mais informações das ações do software:
debug = True

tools = Tools()
configs = tools.read_configuration('config.json')
await_time = configs['await_time']


db = Database(database=configs['mysql_db'], host=configs['mysql_host'], passwd=configs['mysql_passwd'], port=configs['mysql_port'], user=configs['mysql_user'])


operadoras = configs['operadoras']

mikrotik = Mikrotik(ip=configs['address'], user=configs['username'], password=configs['password'], port=configs['port'])

if(debug): print('[DEBUG - ' + tools.get_datetime_now() + '] - Registrando os endereços já presentes na lista de endereços do firewall\n')
responses = mikrotik.get_address_list()

#Variável responsável por rastrear a associação de cada endereço IP com sua respectiva lista de endereços.

operadoras = tools.insert_address_in_list(responses, operadoras, debug=debug)

while(True):
    responses = mikrotik.get_connection_address()
    valides_ips = []

    if debug : print('[SYSTEM ' + tools.get_datetime_now() +'] - Validando os endereços IP das conexões no firewall.\n')
    for response in responses:
        src_adrres = response['dst-address'].split(':')[0]
        if not tools.is_private_ip(src_adrres):
            if src_adrres not in valides_ips and src_adrres not in configs['black_list']:
                valides_ips.append(src_adrres)

                if debug : print('[DEBUG ' + tools.get_datetime_now() +'] - O endereco ' + src_adrres + ' foi validado.')

    print('[SYSTEM ' + tools.get_datetime_now() +'] - Os endereços IP das conexões no firewall foram validadas.\n')

    print('[SYSTEM - ' + tools.get_datetime_now() + '] - Iniciando otimização das rotas de acesso.\n')

    if debug : print('[DEBUG - ' + tools.get_datetime_now() + '] - Executando testes em ' + str(len(valides_ips)) + ' endereços IP.\n')

    datetime_after = datetime.datetime.now()

    best_lantencys = []
    index = 0

    for address in valides_ips:
        latancy_test = []
        index += 1

        for operadora in operadoras:
            response = mikrotik.ping(address=address, src=operadora['gatewey'])

            ping = tools.extract_ping_time(result=response)

            threading.Thread(target=db.insert_ping_test, args=(operadora['list_name'], operadora['gatewey'], address, ping)).start()

            latancy_test.append({'operadora' : operadora['name'], 'latency' : ping, 'list_name' : operadora['list_name'], 'address' : address})

        best = tools.get_best_latency(latency_test=latancy_test, debug=debug, index=index, total=len(valides_ips))
        if(best != None):

            for operadora in operadoras:
                if best['address'] in operadora['addresses']:
                    if best['list_name'] != operadora['list_name']:

                        if debug : print(f'[DEBUG ' + tools.get_datetime_now() + '] - Trocando a rota.')
                        results = mikrotik.get_address_list()

                        for result in results:
                            address = result['address']
                            if not tools.is_private_ip(address) and address not in configs['black_list']:
                                if best['address'] == address:
                                    index_id = result['.id']

                                    mikrotik.remove_ip_in_address_list(index_id)
                                    if address in operadora['addresses']:
                                        operadora['addresses'].remove(address)

                                    threading.Thread(target=db.insert_manipulation, args=("REMOVED", best['address'], None, operadora['name'])).start()

                                    if debug : print(f'[DEBUG {tools.get_datetime_now()}] - O endereco {address} foi removido da lista {operadora["list_name"]}')

                        for best_operadora in operadoras:
                            if best['list_name'] == best_operadora['list_name']:

                                mikrotik.add_ip_in_address_list(best['address'], best_operadora['list_name'])
                                best_operadora['addresses'].append(best['address'])

                                threading.Thread(target=db.insert_manipulation, args=("ADDED", best['address'], best['latency'], best_operadora['name'])).start()

                                if debug : print(f'[DEBUG {tools.get_datetime_now()}] - O endereco {best["address"]} foi adicionado à lista {best_operadora["list_name"]} \n')
                                break
                if best['list_name'] == operadora['list_name'] and best['address'] not in operadora['addresses']:
                    mikrotik.add_ip_in_address_list(best['address'], operadora['list_name'])

                    operadora['addresses'].append(best['address'])

                    threading.Thread(target=db.insert_manipulation, args=("ADDED", best['address'], best['latency'], operadora['name'])).start()

                    if debug : print(f'[DEBUG {tools.get_datetime_now()}] - O endereco {best["address"]} foi adicionado à lista {operadora["list_name"]} \n')


    print(f'[SYSTEM - ' + tools.get_datetime_now() + '] - Atualização das melhores rotas encontradas foram concluidas. Tempo de processo ' + str(datetime.datetime.now() - datetime_after) + '\n')
    print(f'[SYSTEM {tools.get_datetime_now()}] Teste será executado novamente em ' + str(await_time) +' segundos.')
    time.sleep(await_time)

