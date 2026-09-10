import os

from dotenv import load_dotenv
from mysql.connector import connect, Error

load_dotenv()


def get_db_config():
    config = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD"),
        "database": os.getenv("MYSQL_DATABASE"),
        "charset": os.getenv("MYSQL_CHARSET", "utf8mb4"),
        "autocommit": True,
    }

    config = {k: v for k, v in config.items() if v is not None}

    required_keys = ["user", "password", "database"]
    missing_keys = [k for k in required_keys if k not in config]

    if missing_keys:
        raise ValueError(f"缺少必要配置项: {', '.join(missing_keys)}")

    return config


def list_sql_tables() -> str:
    """列出数据库中所有可用的表"""
    print("----正在查询数据库中的表名...")
    try:
        with connect(**get_db_config()) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES;")
                result = cursor.fetchall()
                if not result:
                    return "没有可用的表"
                table_names_str = ",".join([item[0] for item in result])
                return f"可用的表：{table_names_str}"
    except Error as e:
        return f"连接数据库失败：{str(e)}"


def get_table_data(table_name: str) -> str:
    """获取指定表名前至多100条数据，同时返回字段名"""
    print(f"----正在查询表 {table_name} 的数据...")
    try:
        with connect(**get_db_config()) as conn:
            with conn.cursor() as cursor:
                sql = f"SELECT * FROM {table_name} LIMIT 100;"
                cursor.execute(sql)
                column_names_str = ",".join(cursor.column_names)
                result = cursor.fetchall()
                if not result:
                    return f"查询表 {table_name}，结果没有数据"
                data_str = "\n".join([",".join(map(str, item)) for item in result])
                return column_names_str + "\n" + data_str
    except Error as e:
        return f"连接数据库失败：{str(e)}"


def execute_sql_query(sql: str) -> str:
    """执行指定 SQL，返回字段名和结果数据"""
    print(f"----正在执行 SQL：{sql}")
    try:
        with connect(**get_db_config()) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                column_names_str = ",".join(cursor.column_names)
                result = cursor.fetchall()
                if not result:
                    return f"执行语句 {sql}，结果没有数据"
                data_str = "\n".join([",".join(map(str, item)) for item in result])
                return column_names_str + "\n" + data_str
    except Error as e:
        return f"连接数据库失败：{str(e)}"


if __name__ == "__main__":
    print(list_sql_tables())
    print()
    print(get_table_data("drugs"))
    print()
    print(execute_sql_query("SELECT * FROM drugs LIMIT 5"))