import ros_api
import ipaddress
import re

########################
#ativar debug no console:
debug = True
#ativar debug no console
########################

# variaiveis globais de configurações
operators = [
    {'name': 'Ola Telecom',     'address' : '131.0.119.246',        'address_list' : 'servicos-link-out-ollatelecom'},
    {'name': 'Oi Fibra',        'address' : '192.168.64.243',       'address_list' : 'servicos-link-out-oifibra'},
    {'name': 'Onda Agil',       'address' : '10.1.1.3',             'address_list' : 'servicos-link-out-ondaagil'},
    {'name': 'Vivo Fibra',      'address' : '192.168.67.14',        'address_list' : 'servicos-link-out-vivofibra'},
    {'name': 'Junto Telecom',   'address' : '10.48.2.250',          'address_list' : 'servicos-link-out-juntotelecom'},
    {'name': 'Satelite',        'address' : '201.32.177.202',       'address_list' : 'servicos-link-out-satelite'},
    {'name': 'RNP',             'address' : '200.129.130.170',      'address_list' : 'servicos-link-out-rnp'},
            ]

#Lista de conexões do firewall
address_list = [
    {'name' : 'servicos-link-out-juntotelecom', 'address' : []},
    {'name' : 'servicos-link-out-oifibra', 'address' : []},
    {'name' : 'servicos-link-out-ollatelecom', 'address' : []},
    {'name' : 'servicos-link-out-ondaagil', 'address' : []},
    {'name' : 'servicos-link-out-rnp', 'address' : []},
    {'name' : 'servicos-link-out-satelite', 'address' : []},
    {'name' : 'servicos-link-out-vivofibra', 'address' : []},
]

#ips que não serão manipulados.
black_list = ['131.0.119.246', '192.168.64.243', '10.1.1.3', '192.168.67.14', '10.48.2.250', '201.32.177.202', '200.129.130.170', 'fast.com']

#Variavel global que salva os ips validos da conexão do firewall
valide_ips = []

#Instancia da conexão da RouterBoard Mikrotik
print('\n>> Efetuando login...')
router = ros_api.Api('131.0.119.246', user='api', password='Flug@1701#')
print('\n>> Conexão estabelecida...\n')

# teste = router.talk('/ip/firewall/address-list/add =address=192.1.1.1 =list=servicos-link-out-juntotelecom')
# teste = router.talk('/ip/firewall/address-list/print')
# print(teste)
# breakpoint()

"""
Verifica se um endereço IP é privado ou público.

Args:
    ip: O endereço IP para verificar.

Returns:
    True se o endereço IP é privado, False se for público.
"""
def is_private_ip(ip: str) -> bool:

    try:
        ip_address = ipaddress.ip_address(ip)
        return ip_address.is_private
    except ValueError:
        # Se o endereço IP não puder ser analisado, é considerado inválido e público.
        return False
    

# """Extrair o valor do ping do comando da Routerboard Mikrotik."""

# """Checa se a requesição obteve um status diferente de OK"""
def extract_ping_time(result):

    if 'status' in result[0]:
            return result[0]['status']

    time_str = result[0]['time']
    time_ms = re.findall(r'\d+', time_str)[0]
    return int(time_ms)

def get_ms(obj):
    ms = obj["latency"]
    if isinstance(ms, str):
        if ms.isdigit():
            return float(ms)
        else:
            return float("inf")
    else:
        return ms

print('\n>> Recebendo conexões do firewall...\n')
firewall_connections = router.talk('/ip/firewall/connection/print')
for response in firewall_connections:
    src_adrres = response['dst-address'].split(':')[0]
    if not is_private_ip(src_adrres):
        # print(src_adrres + ' -> ', is_private_ip(src_adrres))
        if not src_adrres in valide_ips:
            if not src_adrres in black_list:
                valide_ips.append(src_adrres)
            
            #opção de debug. Caso queria habilitar ou desabilitar, vá a linha 7
            if debug : print('\n[DEBUG] >> Endereço: (' + str(src_adrres) + ') salvo.')
print('\n>> Conexões recebidas!\n')

print('\n>>Anexando os endereços já existente na address-list do firewall...\n')
response_addres = router.talk('/ip/firewall/address-list/print')
for response in response_addres:
    src_adrres = response['address']
    list_name = response['list']
    for address in address_list:
        if address['name'] == list_name:
            address['address'].append(src_adrres)

            #opção de debug. Caso queria habilitar ou desabilitar, vá à linha 7
            if debug : print('\n[DEBUG] >> Endereço: (' + str(src_adrres) + ') foi salvo na lista: ' + str(address['name']))

print('\n>>Endereços anexados com sucesso!\n')

print('\n>>Executando teste de lantecias em ' + str(len(valide_ips)) + ' endereços...')
#inicializar as variaveis.
latency_test = []
best_operators = []
# debug_list = []

for address in valide_ips:
    # print('\n Teste te ping address ' + str(address))

    #resetando os valores da varaivel.
    latency_test = []
    for operator in operators:
        response_ping = router.talk('/ping \n =address=' + str(address) +' \n =src-address=' + operator['address'] +' =count=1')
        ms = extract_ping_time(response_ping)
        #Adicionando os resultados dos testes dentro da lista.
        
        latency_test.append({'operator' : operator['name'], 'latency' : ms, 'address_list' : operator['address_list']})
        # debug_list.append({'operator' : operator['name'], 'latency' : ms, 'dst-address' : address})
                                         
    best_operator = sorted(latency_test, key=get_ms)[0]
    if str(best_operator['latency']).isdigit():
        best_operators.append({'operator' : best_operator['operator'], 'latency' : best_operator['latency'], 'dst-address' : address })
        if debug : print('\n[DEBUG] >> Endereço: (' + str(address) + ') está com a melhor lantência em: ' + best_operator['operator'] + ' com ' + str(ms) + ' ms')
    else:
        if debug : print('\n[DEBUG] >> Endereço: (' + str(address) + ') recebeu timeout ou não foi possivel executar o teste')
    #opção de debug. Caso queria habilitar ou desabilitar, vá a linha 7

    #Verificar se houve mudanças de latencia entre as conexões.
    for index in address_list:
        for ip in index['address']:
            if ip == str(address):
                if index['name'] != best_operator['address_list']:

                    result_search = router.talk('/ip/firewall/address-list/print')

                    for result in result_search:
                        address_search = result['address']
                        if not is_private_ip(address_search):
                            if address == address_search:
                                index_address = result['.id']
                                router.talk('/ip/firewall/address-list/remove =numbers=' + str(index_address))
                                

                    index['address'].remove(address)
                    # address_list_where = router.talk('/ipfirewall/address-list/print \n =where= \n =address=' + str(address))
                    #opção de debug. Caso queria habilitar ou desabilitar, vá a linha 7
                    if debug: print('\n[DEBUG] >> O endereço: ' + str(address) + ' foi removido da lista: ' + index['name'])

    #Colocar na lista de endereços com do link com a menor latência.
    for index in address_list:
        if index['name'] == best_operator['address_list']:
            # print(index['name'], operator['address_list'])
            if str(best_operator['latency']).isdigit():
                if not str(address) in index['address']:

                    #Adicionando ip na addres-list do firewall
                    router.talk('/ip/firewall/address-list/add =address=' + str(address) + ' =list=' + str(index['name']) + '')

                    #Cacheando os dados
                    index['address'].append(str(address))

                    #opção de debug. Caso queria habilitar ou desabilitar, vá a linha 7
                    print('\n[DEBUG] >> O endereço: ' + str(address) + ' foi adicionado à lista: ' + index['name'])

print('\n>> Os tentes de lantência foram concluidos.\n')


# # print('\nTodos os testes feitos:')
# # for debug in debug_list:
# #     print('Operadora: ' + debug['operator'] + ' lantecy: ' + str(debug['latency']) + ' dst-address: ' + str(debug['dst-address']))

# print('\nMelhores latências encontradas:')
# for best in best_operators:
#     print('Operadora: ' + best['operator'] + ' Destino: ' + str(best['dst-address']) + ' latência: ' + str(best['latency']))

for result in address_list:
    print('Address list: ' + result['name'] + '    addrress: ' + str(result['address']))