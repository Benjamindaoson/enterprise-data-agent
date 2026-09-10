from agent.load_prompt import sub_agents_config
from tools.mysql_tools import (
    list_sql_tables,
    get_table_data,
    execute_sql_query,
)


db_sub_agent = {
    "name": sub_agents_config["db"]["name"],
    "description": sub_agents_config["db"]["description"],
    "system_prompt": sub_agents_config["db"]["system_prompt"],
    "tools": [
        list_sql_tables,
        get_table_data,
        execute_sql_query,
    ],
}


if __name__ == "__main__":
    print(db_sub_agent)