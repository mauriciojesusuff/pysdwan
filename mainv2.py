from src.api.mikrotik import Mikrotik
from src.utils.utils import Tools
from src.objects.NetworkAddress import NetworkAddress
from src.db.db import Database

import sys
import time
import threading

tools = Tools()

configs = tools.read_configuration('config.json')
mikrotik = Mikrotik(ip=configs['address'], user=configs['username'], password=configs['password'], port=configs['port'])
operators = configs['operadoras']
black_list = configs['black_list']
list_name_block = configs['list_name_block']

db = Database(database=configs['mysql_db'], host=configs['mysql_host'], passwd=configs['mysql_passwd'], port=configs['mysql_port'], user=configs['mysql_user'])

debug = True

while True:

    addresses_list = mikrotik.get_address_list()

    list_block_address = []

    for address in addresses_list:
        
        #Limpando o valor retornado pelo comando "ip/firewall/connection/print"
        address_cleared = tools.clear_address_with_mask(address['address'])

        #Verifico se a varivel não é vazia.
        if address_cleared is None: continue

        #Verifica se o endereço coletado não é um ip prvivado.
        if tools.is_private_ip(address_cleared): continue

        #Verifico se o endereço coletado não esta na blacklist.
        if address_cleared in black_list: continue
        
        if address['list'] in list_name_block: continue

        address_with_mask = tools.get_block_ip(address_cleared, '24')
        
        if address_with_mask is None: continue

        if not list_block_address:
            list_block_address.append(NetworkAddress(network=address_with_mask, address=None, addresses=[address_cleared], list_name=[address['list']]))

        in_inside = False
        for block in list_block_address:
            if tools.inside_block_address(block=block.network, address=address_cleared):

                if address_cleared not in block.addresses:
                    block.addresses.append(address_cleared)

                in_inside = True
                break
        
        if not in_inside:
            list_block_address.append(NetworkAddress(network=address_with_mask, address=None, addresses=[address_cleared], list_name=address['list']))

    #Pegar os ips no firewall connection
    connections = mikrotik.get_connection_address()

    #Verificar endereço por enderço
    for conn in connections:

        #Normalizar o endereço IP
        address_cleared = conn['dst-address'].split(':')[0]

        #Verificar se a normalização não retornou um endereço vazio
        if address_cleared is None: continue

        #Verifica se o endereço não é um ip privado.
        if tools.is_private_ip(address_cleared): continue

        #Verifica o endereço ip não esta na black list;
        if address_cleared in black_list: continue


        #Transforma o endereço em um bloco /24;
        address_with_mask = tools.get_block_ip(address_cleared, '24')
        
        #Verifica se a transformação do endereço ip para um bloco de endereço ip não é vazio.
        if address_with_mask is None: continue

        in_inside = False
        for block in list_block_address:
            if tools.inside_block_address(block=block.network, address=address_cleared):

                if address_cleared not in block.addresses:
                    block.addresses.append(address_cleared)

                if block.address == None: block.address = address_cleared

                in_inside = True
                break
        
        if not in_inside:
            list_block_address.append(NetworkAddress(network=address_with_mask, address=address_cleared, addresses=[address_cleared]))

    index = 0
    for network in list_block_address:

        #Valida se o valor do campo address não é vazio.
        if network.address == None: continue

        latancy_test = []
        index+=1

        #Começa a executar os tentes entre as operadoras configuradas.
        for operator in operators:

            #Faz o teste de ping e coleta o resultado em INT
            response = mikrotik.ping(address=network.address, src=operator['gatewey'])
            ping = tools.extract_ping_time(result=response)

            #Adiciona na lista os testes fetios.
            latancy_test.append({'operator' : operator['name'], 'latency' : ping, 'list_name' : operator['list_name'], 'network': network, 'address' : network.address})

            t = threading.Thread(target=db.insert_ping_test, args=(operator['list_name'], operator['gatewey'], network.address, ping))
            t.start()
            t.join()
        
        #Pega o melhor teste feito.
        best = tools.get_best_latency(latency_test=latancy_test, debug=debug, index=index, total=len(list_block_address))
        
        if best == None: continue

        best_list_name = best['list_name']
        network = best['network']

        addresses_lists = mikrotik.get_address_list()
        
        modifier = False
        for address_list in addresses_lists:

            if address_list['list'] in list_name_block: continue

            address_cleared = tools.clear_address_with_mask(address_list['address'])

            if(tools.is_private_ip(address_cleared)): continue

            address_with_mask = tools.get_block_ip(address_cleared, '24')

            if address_with_mask == network.network:    
                if best_list_name == address_list['list']: 
                    modifier = True
                    continue

                print(f'[DEBUG] Removendo o bloco ip {address_with_mask} da lista {network.list_name}')

                mikrotik.remove_ip_in_address_list(address_list['.id'])

                t = threading.Thread(target=db.insert_manipulation, args=("REMOVED", best['address'], None, network.list_name))
                t.start()
                t.join()

                print(f'[DEBUG] Adicionado o bloco ip {address_with_mask} na lista {best_list_name}\n')

                mikrotik.add_ip_in_address_list(str(address_with_mask), best_list_name)
                network.list_name = best_list_name

                modifier = True
                t = threading.Thread(target=db.insert_manipulation, args=("ADDED", best['address'], best['latency'], network.list_name))
                t.start()
                t.join()
                continue

        if not modifier:
            print(f'[DEBUG] Adicionado o bloco ip {network.network} na lista {best_list_name}\n')
            mikrotik.add_ip_in_address_list(str(network.network), best_list_name)
            t = threading.Thread(target=db.insert_manipulation, args=("ADDED", best['address'], best['latency'], network.list_name))
            t.start()
            t.join()

    print(f'Manipulações concluídas. Recomençando em {configs["await_time"]} segundos.')
    time.sleep(configs['await_time'])