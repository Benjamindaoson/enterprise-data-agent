"""
命令行入口

提供命令行交互界面。
"""

from src.agent.core import Agent


class CLI:
    """命令行界面"""

    STAGES = ["数据探索", "数据清洗", "数据分析", "数据建模"]

    def __init__(self):
        self.agent = Agent()
        self.current_stage = None
        self.conversation_history = []

    def run(self):
        """运行命令行界面"""
        print("\n" + "=" * 60)
        print("       iQuery 智能数据分析平台 v2.0")
        print("=" * 60)
        print("\n可用功能：")
        print("  - 查询数据库中的表和数据")
        print("  - 提取数据到 DataFrame")
        print("  - 执行数据分析和统计")
        print("  - 生成可视化图表")
        print("\n" + "-" * 60)
        print("分析阶段：1.数据探索  2.数据清洗  3.数据分析  4.数据建模")
        print("-" * 60)
        print("\n命令：退出 | 状态 | 清除")
        print("=" * 60 + "\n")

        while True:
            try:
                user_input = input("您: ").strip()
                if not user_input:
                    continue

                if user_input.lower() in ["退出", "exit"]:
                    print("\n感谢使用，再见！")
                    break

                elif user_input.lower() == "状态":
                    self._show_status()
                    continue

                elif user_input.lower() == "清除":
                    self.agent.reset()
                    print("已清除对话历史")
                    continue

                # 处理消息
                print("\n[思考中...]")
                response = self.agent.chat(user_input)
                print(f"\niQuery: {response}")

                self.conversation_history.append((user_input, response))

            except KeyboardInterrupt:
                print("\n\n程序已退出")
                break
            except Exception as e:
                print(f"\n错误: {e}")

    def _show_status(self):
        """显示状态"""
        info = self.agent.get_context_info()
        print("\n" + "-" * 40)
        print(f"Token: {info['tokens']}")
        print(f"阶段: {info['stage'] or '自由对话'}")
        print(f"DataFrame: {info['dataframes']}")
        print(f"图表: {info['figures']} 个")
        print("-" * 40)


def main():
    """主入口"""
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
