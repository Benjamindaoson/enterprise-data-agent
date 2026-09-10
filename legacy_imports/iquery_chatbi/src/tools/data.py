"""Legacy iQuery DataFrame extraction tool. Reference only."""

import os
from typing import Dict


class DataTool:
    def __init__(self):
        self._schema = {
            "name": "extract_data",
            "description": "将数据库查询结果提取为 Python DataFrame，供后续分析使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_query": {"type": "string", "description": "SQL 查询语句"},
                    "df_name": {"type": "string", "description": "DataFrame 变量名称"},
                },
                "required": ["sql_query", "df_name"],
            },
        }

    def execute(self, sql_query: str, df_name: str) -> str:
        import pandas as pd
        import pymysql
        connection = pymysql.connect(
            host=os.getenv("IQUERY_DB_HOST", "localhost"),
            user=os.getenv("IQUERY_DB_USER", ""),
            passwd=os.getenv("IQUERY_DB_PASSWORD", ""),
            db=os.getenv("IQUERY_DB_NAME", "iquery"),
            charset="utf8",
        )
        try:
            df = pd.read_sql(sql_query, connection)
            import __main__
            setattr(__main__, df_name, df)
            return f"已成功创建 {df_name}，共 {len(df)} 行 {len(df.columns)} 列"
        finally:
            connection.close()

    def get_schema(self) -> Dict:
        return self._schema
