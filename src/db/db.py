import mysql.connector
import time


class Database():

    def __init__(self, host, user, passwd, database, port = 3306) -> None:
        self.host = host
        self.user = user
        self.passwd = passwd
        self.port = port
        self.database = database
        self.connect = None

        self.create_table()


    def openConnection(self) -> any:
        self.connect = mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.passwd,
            database=self.database,
            port=self.port
        )

        return self.connect


    def insert_manipulation(self, action, address, lantecy, operator):
        try:
            if(self.connect.is_connected() == False):
                    self.openConnection()

            cursor = self.connect.cursor()

            sql = 'INSERT INTO manipulation (action, address, latency, operator) VALUES (%s, %s, %s, %s)'
            values = (action, address, lantecy, operator)
            cursor.execute(sql, values)

            self.connect.commit()
            cursor.close()
        except mysql.connector.Error as err:
                print("Something went wrong: {}".format(err))

    def select(self, limit: int = 50, oderBy: str = 'ASC', ) -> [] :
        connection = self.openConnection()
        cursor = connection.cursor()

        cursor.execute('SELECT * FROM manipulation LIMIT {limit} ORDER BY manipulation.id {orderBy}')
        result = cursor.fetchall()

        cursor.close()
        connection.close()

        return result

    def insert_ping_test(self, list_name, gateway, address, latency):

        if isinstance(latency, int):
            try:
                if(self.connect.is_connected() == False):
                    connection = self.openConnection()


                cursor = self.connect.cursor()

                sql = 'INSERT INTO ping (list_name, gatewey, address, latency) VALUES (%s, %s, %s, %s)'
                values = (list_name, gateway, address, latency)
                cursor.execute(sql, values)

                self.connect.commit()
                cursor.close()

            except mysql.connector.Error as err:
                print("Something went wrong: {}".format(err))


    def create_table(self):
        self.openConnection()
        cursor = self.connect.cursor()

        cursor.execute('CREATE TABLE IF NOT EXISTS `' + self.database + '`.`manipulation` (`id` INT(10) NOT NULL AUTO_INCREMENT , `action` VARCHAR(7) NOT NULL , `address` VARCHAR(15) NOT NULL , `operator` VARCHAR(45) NULL , `latency` SMALLINT UNSIGNED NULL , `created_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP , PRIMARY KEY (`id`)) ENGINE = InnoDB;')
        cursor.execute('CREATE TABLE IF NOT EXISTS `' + self.database + '`.`ping` (`id` INT(10) NOT NULL AUTO_INCREMENT , `list_name` VARCHAR(75) NOT NULL , `gatewey` VARCHAR(15) NOT NULL , `address` VARCHAR(15) NOT NULL , `latency` INT(10) NOT NULL , `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP , PRIMARY KEY (`id`)) ENGINE = InnoDB;')

        cursor.close()

    def close_all_connection(self):
        self.connect.close()