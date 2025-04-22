import mysql.connector
from mysql.connector import Error
from datetime import datetime

#Importar o log para o sistema
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, host, user, passwd, database, port=3306):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.port = port
        self.database = database
        self.connection = None  # Usando 'self.connection' consistentemente
        self.create_table()

    def open_connection(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.passwd,
                database=self.database,
                port=self.port
            )
            if self.connection.is_connected():
                logger.debug("Conectado ao banco de dados MySql.")
        except Error as e:
            logger.error(f"Erro na conexão com o MySql: {e}")

#    def close_connection(self):
#        if self.connection and self.connection.is_connected():
#            self.connection.close()
#            logger.debug("Conexão MySql encerrada.")

    def execute_query(self, query, params=None):
        """
        Método auxiliar para executar queries que não retornam resultados (INSERT, UPDATE, DELETE).
        """
        try:
            if self.connection is None or not self.connection.is_connected():
                self.open_connection()
            cursor = self.connection.cursor()
            try:
                cursor.execute(query, params)
                self.connection.commit()
            finally:
                cursor.close()
        except Error as e:
            logger.error(f"Erro ao executar a query: {e}")
            self.connection.rollback()  # se aplicável
            raise

    def fetch_query(self, query, params=None):
        """
        Método auxiliar para executar queries que retornam resultados (SELECT).
        """
        try:
            if self.connection is None or not self.connection.is_connected():
                self.open_connection()
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params)
            result = cursor.fetchall()
            cursor.close()
            return result
        except Error as e:
            print(f"Error fetching data: {e}")
            return None

    def create_table(self):
        """
        Cria as tabelas necessárias no banco de dados, caso não existam.
        """
        table_queries = [
            '''
            CREATE TABLE IF NOT EXISTS manipulation (
                id INT(10) NOT NULL AUTO_INCREMENT,
                action VARCHAR(7) NOT NULL,
                address VARCHAR(20) NOT NULL,
                operator VARCHAR(45) NULL,
                latency SMALLINT UNSIGNED NULL,
                created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id)
            ) ENGINE = InnoDB;
            ''',
            '''
            CREATE TABLE IF NOT EXISTS ping (
                id INT(10) NOT NULL AUTO_INCREMENT,
                list_name VARCHAR(75) NOT NULL,
                gateway VARCHAR(20) NOT NULL,
                address VARCHAR(20) NOT NULL,
                latency INT(10) NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id)
            ) ENGINE = InnoDB;
            ''',
            '''
            CREATE TABLE IF NOT EXISTS current_address_list (
                id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                list_name VARCHAR(100) NOT NULL,
                address VARCHAR(16) NOT NULL,
                prefix_length TINYINT UNSIGNED,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE = InnoDB;
            ''',
            '''
            CREATE TABLE IF NOT EXISTS ping_target (
                id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                domain VARCHAR(100) NOT NULL,
                active TINYINT(1) NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE = InnoDB;
            ''',
            '''
            CREATE TABLE IF NOT EXISTS ping_target_result (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ping_target_id BIGINT UNSIGNED NOT NULL,
                latency INT,
                success TINYINT(1) NOT NULL,
                list_name VARCHAR(40),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ping_target_id) REFERENCES ping_target(id)
            );
            ''',
                        '''
            CREATE TABLE IF NOT EXISTS system_efficiency (
                id INT AUTO_INCREMENT PRIMARY KEY,
                qtt_ip INT UNSIGNED NOT NULL,
                seconds INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            '''

        ]
        try:
            if self.connection is None or not self.connection.is_connected():
                self.open_connection()
            cursor = self.connection.cursor()
            for query in table_queries:
                cursor.execute(query)
            self.connection.commit()
            cursor.close()
            logger.info("Tabelas criadas ou validadas com sucesso,")
        except Error as e:
            logger.error(f"Erro ao criar as tabelas: {e}")

    def insert_manipulation(self, action, address, latency, operator):
        query = '''
            INSERT INTO manipulation (action, address, latency, operator)
            VALUES (%s, %s, %s, %s)
        '''
        try:
            if self.connection is None or not self.connection.is_connected():
                self.open_connection()
            params = (action, address, latency, operator)
            logger.debug(f"query: {query} params: {params}")
            self.execute_query(query, params)
        except Error as e:
                logger.error(f"Erro ao inserir os dados na tabela Mysql: {e}")

    def select(self, limit=50, order_by='ASC'):
        query = f'''
            SELECT * FROM manipulation
            ORDER BY id {order_by}
            LIMIT %s
        '''
        params = (limit,)
        return self.fetch_query(query, params)


    def insert_ping_test(self, list_name, gateway, address, latency):
        if isinstance(latency, int):
            query = '''
                    INSERT INTO ping (list_name, gateway, address, latency)
                    VALUES (%s, %s, %s, %s)
                '''
            try:
                if self.connection is None or not self.connection.is_connected():
                    self.open_connection()

                params = (list_name, gateway, address, latency)
                logger.debug(f"query: {query} params: {params}")
                self.execute_query(query, params)
            except Error as e:
                logger.error(f"Erro ao inserir os dados na tabela Mysql: {e}")
        else:
                print("Latency must be an integer")


    def clear_current_address_list(self):
        query = "TRUNCATE TABLE current_address_list;"
        logger.debug(query)
        self.execute_query(query)

    def insert_current_address_list(self, data):
        query = '''
            INSERT INTO current_address_list (list_name, address, prefix_length, created_at)
            VALUES (%s,%s, %s, %s)
        '''
        try:
            if self.connection is None or not self.connection.is_connected():
                self.open_connection()
            cursor = self.connection.cursor()
            for entry in data:
                if not entry: continue
                list_name = entry['list']
                address_full = entry['address']
                if '/' in address_full:
                    address, prefix_length = address_full.split('/')
                else:
                    address = address_full
                    prefix_length = None
                created_at = entry.get('creation-time', None)
                params = (list_name, address, int(prefix_length) if prefix_length else None, created_at)
                logger.debug(f"query: {query} params: {params}")
                cursor.execute(query, params)
            self.connection.commit()
            cursor.close()
        except Error as e:
            logger.error(f"Erro ao inserir os dados na tabela Mysql: {e}")

    def get_list_name_to_current_address_list(self, address : str):
        query = '''
            SELECT id, list_name FROM current_address_list WHERE address = %s AND prefix_length = %s;
        '''
        try:
            if self.connection is None or not self.connection.is_connected():
                self.open_connection()

            address, prefix_length = address.split('/')
            params = (address, prefix_length)
            results = self.fetch_query(query,params)
            logger.debug(f"query: {query} params: {params}")
            if len(results) > 0: 
                return results[0] 
            else: None

        except Error as e:
            logger.error(f"Erro ao selecionar dados na tabela MySql: {e}")

    def insert_one_current_address_list(self, entry):
        query = '''
            INSERT INTO current_address_list (list_name, address, prefix_length, created_at)
            VALUES (%s, %s, %s, %s)
        '''

        cursor = None
        try:
            if self.connection is None or not self.connection.is_connected():
                self.open_connection()

            list_name = entry.get('list_name')
            network = entry.get('network', '')

            parts = network.split('/')
            address = parts[0] if len(parts) > 0 else None
            prefix_length = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None

            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            params = (list_name, address, prefix_length, created_at)

            cursor = self.connection.cursor()  # Criar o cursor aqui
            cursor.execute(query, params)

            self.connection.commit()
            cursor.close()
            logger.debug(f"query: {query} params: {params}")

        except Error as e:
            logger.error(f"Erro ao inserir dados na tabela MySQL: {e}")

        finally:
            if cursor:
                cursor.close()  # Fechar o cursor manualmente no bloco finally

    def update_current_address_list(self, entry):
    
        query = '''
            UPDATE current_address_list SET list_name = %s WHERE address = %s AND prefix_length = %s
        '''
        try:
            if self.connection is None or not self.connection.is_connected():
                self.open_connection()

            #address, prefix_length = entry['network'].split('/')

            parts = entry['network'].split('/')
            address = parts[0] if len(parts) > 0 else None
            prefix_length = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None

            params = (entry['list_name'],address, prefix_length)

            cursor = self.connection.cursor()
            cursor.execute(query, params)

            self.connection.commit()
            cursor.close()
            logger.debug(f"query: {query} params: {params}")
        except Error as e:
            logger.error(f"Erro ao atualizar current_address_list: {e}")


    def insert_ping_target_test(self, id, latency, list_name, success):
        query = '''
                INSERT INTO ping_target_result (ping_target_id, latency, list_name, success) 
                VALUES (%s,%s,%s,%s)
        '''
        try:
            if self.connection is None or not self.connection.is_connected():
                self.open_connection()

            params = (id, latency, list_name, success)
            logger.debug(f"query: {query} params: {params}")
            self.execute_query(query, params)

        except Error as e:
            logger.error(f"Erro ao inserir ping_target_result: {e}")


    def get_ping_target(self):
        query = '''
            SELECT id, domain FROM ping_target WHERE active = 1
        '''
        try:
            if self.connection is None or not self.connection.is_connected():
                self.open_connection()

            logger.debug(f"query: {query} params: {None}")
            results = self.fetch_query(query)
            return results
        except Error as e:
            logger.error(f"Erro ao selecionar ping_target: {e}")



