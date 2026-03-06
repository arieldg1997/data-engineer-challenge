import psycopg2


def get_connection(db_config):
    return psycopg2.connect(
        host=db_config["host"],
        port=db_config["port"],
        dbname=db_config["dbname"],
        user=db_config["user"],
        password=db_config["password"],
    )


def execute_sql_file(connection, file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        sql = f.read()

    with connection.cursor() as cur:
        cur.execute(sql)

    connection.commit()