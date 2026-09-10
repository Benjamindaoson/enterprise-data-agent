# 主 Agent 组装与执行

from deepagents import create_deep_agent

from agent.llm import llm
from agent.load_prompt import main_agent_config
from agent.sub_agents.db_sub_agent import db_sub_agent


main_agent = create_deep_agent(
    model=llm,
    system_prompt=main_agent_config["system_prompt"],
    subagents=[db_sub_agent],
    tools=[],
)


if __name__ == "__main__":
    result = main_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "基于所有销售记录，计算每个药品的总库存、总销量、库存销量比=总库存/总销量，找出库存销量比最高的前三个药品，并分析库存风险。不要使用近6个月口径。",
                }
            ]
        }
    )

    print(result["messages"][-1].content)