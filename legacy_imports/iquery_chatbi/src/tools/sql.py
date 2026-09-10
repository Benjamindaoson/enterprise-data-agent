"""Legacy iQuery SQL tool, preserved as a reference implementation only.

This migrated copy replaces the original hard-coded local credentials with
environment variables. It must not be connected directly to the governed
production execution path without read-only validation and query limits.
"""

import json
import os
from typing import Dict


class SQLTool:
    def __init__(self):
        self._schema = {
            "name": "sql_inter",
            "description": "执行 SQL 查询语句，返回 JSON 格式的查询结果。",
            "parameters": {
                "type": "object",
                "properties": {"sql_query": {"type": "string", "description": "SQL 查询语句"}},
                "required": ["sql_query"],
            },
        }

    def execute(self, sql_query: str) -> str:
        import pymysql
        connection = pymysql.connect(
            host=os.getenv("IQUERY_DB_HOST", "localhost"),
            user=os.getenv("IQUERY_DB_USER", ""),
            passwd=os.getenv("IQUERY_DB_PASSWORD", ""),
            db=os.getenv("IQUERY_DB_NAME", "iquery"),
            charset="utf8",
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                results = cursor.fetchall()
            return json.dumps(results, ensure_ascii=False)
        finally:
            connection.close()

    def get_schema(self) -> Dict:
        return self._schema
