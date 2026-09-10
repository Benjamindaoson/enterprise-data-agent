"""
Web 服务器

提供 HTTP 接口和 Web 界面。
"""

import json
import threading
import time
import http.server
import socketserver
from typing import Dict, Any, Tuple, List


class RequestHandler(http.server.SimpleHTTPRequestHandler):
    """请求处理器"""

    # 存储会话数据
    sessions: Dict[str, Dict] = {}

    def do_GET(self):
        """处理 GET 请求"""
        if self.path == '/' or self.path == '/index.html':
            self.send_html()
        else:
            super().do_GET()

    def do_POST(self):
        """处理 POST 请求"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        if self.path == '/api':
            self.handle_chat(post_data)
        elif self.path == '/clear':
            self.handle_clear()
        else:
            self.send_error(404)

    def send_html(self):
        """发送 HTML 页面"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(self.get_html().encode('utf-8'))

    def handle_chat(self, post_data: bytes):
        """处理聊天请求"""
        try:
            data = json.loads(post_data.decode('utf-8'))
            message = data.get('msg', '')

            if not message:
                self.send_json({'reply': '请输入问题'})
                return

            reply, logs = self.process_message(message)
            self.send_json({'reply': reply, 'logs': logs})

        except Exception as e:
            self.send_json({'reply': f'错误: {str(e)}', 'logs': []})

    def handle_clear(self):
        """处理清除请求"""
        self.sessions.clear()
        self.send_json({'ok': True})

    def process_message(self, message: str) -> Tuple[str, List[Dict]]:
        """处理消息"""
        # 获取或创建会话
        session_id = self.headers.get('Cookie', 'default')
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'messages': [self.get_system_prompt()],
                'history': []
            }

        session = self.sessions[session_id]
        session['messages'].append({"role": "user", "content": message})
        session['history'].append({"role": "user", "content": message})

        logs = []

        try:
            response = self.call_llm(session['messages'])
            msg = response.choices[0].message

            if msg.tool_calls:
                session['messages'].append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": msg.tool_calls
                })

                for tc in msg.tool_calls:
                    func_name = tc.function.name
                    args = json.loads(tc.function.arguments)

                    logs.append({"text": f"调用: {func_name}", "ok": True})

                    try:
                        result = self.execute_function(func_name, args)
                        logs.append({"text": f"结果: {str(result)[:100]}", "ok": True})

                        session['messages'].append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": func_name,
                            "content": str(result)
                        })
                    except Exception as e:
                        logs.append({"text": f"错误: {str(e)}", "err": True})

                # 再次调用 LLM
                response = self.call_llm(session['messages'])
                reply = response.choices[0].message.content or "处理完成"
            else:
                reply = msg.content or "我没有理解您的问题。"

        except Exception as e:
            reply = f"错误: {str(e)}"

        session['messages'].append({"role": "assistant", "content": reply})
        session['history'].append({"role": "assistant", "content": reply})

        return reply, logs

    def call_llm(self, messages: List[Dict]):
        """调用 LLM"""
        import openai
        from openai import OpenAI

        openai.api_key = self.get_config().get('api_key')
        openai.api_base = self.get_config().get('api_base')

        client = OpenAI(
            api_key=openai.api_key,
            base_url=openai.api_base
        )

        return client.chat.completions.create(
            model=self.get_config().get('model', 'gpt-3.5-turbo'),
            messages=messages,
            tools=self.get_tools(),
            tool_choice="auto",
        )

    def execute_function(self, name: str, args: Dict) -> Any:
        """执行函数"""
        functions = {
            'sql_inter': self.sql_inter,
            'extract_data': self.extract_data,
            'python_inter': self.python_inter,
        }

        if name not in functions:
            raise ValueError(f"函数 {name} 不存在")

        return functions[name](**args)

    def sql_inter(self, sql_query: str) -> str:
        """SQL 查询"""
        import pymysql
        conn = pymysql.connect(
            host='localhost', user='iquery_agent',
            passwd='iquery_agent', db='iquery', charset='utf8'
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql_query)
                return json.dumps(cursor.fetchall(), ensure_ascii=False)
        finally:
            conn.close()

    def extract_data(self, sql_query: str, df_name: str) -> str:
        """数据提取"""
        import pymysql
        import pandas as pd

        conn = pymysql.connect(
            host='localhost', user='iquery_agent',
            passwd='iquery_agent', db='iquery', charset='utf8'
        )
        try:
            df = pd.read_sql(sql_query, conn)
            # 保存到全局命名空间
            import __main__
            setattr(__main__, df_name, df)
            return f"已创建 {df_name}，共 {len(df)} 行"
        finally:
            conn.close()

    def python_inter(self, py_code: str) -> str:
        """Python 执行"""
        try:
            exec(py_code, globals())
            return "执行完成"
        except Exception as e:
            return f"执行错误: {str(e)}"

    def send_json(self, data: dict):
        """发送 JSON 响应"""
        response = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(response))
        self.end_headers()
        self.wfile.write(response)

    def get_config(self) -> Dict:
        """获取配置"""
        from src.config.settings import settings
        return {
            'api_key': settings.api.api_key,
            'api_base': settings.api.base_url,
            'model': settings.api.model,
        }

    def get_tools(self) -> List[Dict]:
        """获取工具定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "sql_inter",
                    "description": "执行 SQL 查询",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sql_query": {"type": "string", "description": "SQL 查询语句"}
                        },
                        "required": ["sql_query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "extract_data",
                    "description": "提取数据到 DataFrame",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sql_query": {"type": "string"},
                            "df_name": {"type": "string"}
                        },
                        "required": ["sql_query", "df_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "python_inter",
                    "description": "执行 Python 代码",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "py_code": {"type": "string"}
                        },
                        "required": ["py_code"]
                    }
                }
            }
        ]

    def get_system_prompt(self) -> Dict:
        """获取系统提示"""
        return {
            "role": "system",
            "content": """你是 iQuery 智能数据分析助手。
你有以下工具可以使用：
- sql_inter: 执行 SQL 查询数据库
- extract_data: 提取数据到 DataFrame
- python_inter: 执行 Python 代码进行分析

请用中文回答。"""
        }

    def get_html(self) -> str:
        """获取 HTML 页面"""
        return '''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>iQuery - 智能数据分析平台</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh; padding: 20px;
}
.container { max-width: 900px; margin: 0 auto; }
.header { text-align: center; color: white; margin-bottom: 20px; }
.header h1 { font-size: 2.5em; }
.card { background: white; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.2); overflow: hidden; }
.quick-btns { padding: 12px 15px; background: #f5f5f5; display: flex; gap: 8px; flex-wrap: wrap; border-bottom: 1px solid #eee; }
.quick-btn { padding: 8px 14px; background: white; border: 1px solid #ddd; border-radius: 20px; cursor: pointer; transition: all 0.2s; }
.quick-btn:hover { background: #667eea; color: white; border-color: #667eea; }
.chat { height: 450px; overflow-y: auto; padding: 20px; background: #f8f9fa; }
.msg { margin-bottom: 15px; padding: 14px 18px; border-radius: 14px; max-width: 85%; }
.msg.user { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; margin-left: auto; }
.msg.assistant { background: white; border: 1px solid #e0e0e0; }
.log-box { background: #fff3cd; border: 1px solid #ffc107; padding: 8px 12px; border-radius: 8px; font-size: 0.85em; margin: 8px 0; }
.log-box.success { background: #d4edda; border-color: #28a745; }
.log-box.error { background: #f8d7da; border-color: #dc3545; }
.input-area { padding: 15px; border-top: 1px solid #e0e0e0; display: flex; gap: 10px; }
.input-area input { flex: 1; padding: 14px 18px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 1em; }
.input-area input:focus { outline: none; border-color: #667eea; }
.input-area button { padding: 14px 28px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; cursor: pointer; }
.input-area button:hover { opacity: 0.9; }
.input-area button:disabled { opacity: 0.5; }
.status { padding: 10px 15px; background: #f8f9fa; border-top: 1px solid #e0e0e0; font-size: 0.8em; color: #666; display: flex; justify-content: space-between; }
.loading { display: inline-block; width: 14px; height: 14px; border: 2px solid #f3f3f3; border-top: 2px solid #667eea; border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="container">
    <div class="header"><h1>iQuery</h1><p>智能数据分析平台</p></div>
    <div class="card">
        <div class="quick-btns">
            <button class="quick-btn" onclick="sendQuick('查询数据库有哪些表')">查看数据表</button>
            <button class="quick-btn" onclick="sendQuick('提取 user_demographics 表')">提取数据</button>
            <button class="quick-btn" onclick="sendQuick('统计用户流失率')">流失率统计</button>
            <button class="quick-btn" onclick="sendQuick('生成用户年龄分布图')">年龄分布图</button>
            <button class="quick-btn" onclick="clearChat()" style="background:#dc3545;color:white;border-color:#dc3545">清除</button>
        </div>
        <div class="chat" id="chat">
            <div class="msg assistant">欢迎使用 iQuery 智能数据分析平台！<br><br>我可以帮您：<br>- 查询数据库中的表和数据<br>- 提取数据进行分析<br>- 生成可视化图表<br><br>请告诉我您想做什么？</div>
        </div>
        <div class="input-area">
            <input type="text" id="msgInput" placeholder="输入问题，按回车发送..." onkeypress="if(event.key==='Enter')sendMsg()">
            <button id="sendBtn" onclick="sendMsg()">发送</button>
        </div>
        <div class="status"><span id="status">就绪</span><span>iQuery v2.0</span></div>
    </div>
</div>
<script>
let busy = false;
function sendMsg() {
    if (busy) return;
    const input = document.getElementById('msgInput');
    const msg = input.value.trim();
    if (!msg) return;
    addMsg('user', msg);
    input.value = '';
    setBusy(true);
    fetch('/api', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({msg: msg})})
        .then(r => r.json())
        .then(d => {
            if (d.logs) d.logs.forEach(l => addLog(l));
            addMsg('assistant', d.reply);
            setBusy(false);
        })
        .catch(e => { addMsg('assistant', '错误: ' + e.message); setBusy(false); });
}
function sendQuick(msg) { document.getElementById('msgInput').value = msg; sendMsg(); }
function addMsg(role, content) {
    const chat = document.getElementById('chat');
    const div = document.createElement('div');
    div.className = 'msg ' + role;
    div.innerHTML = '<div>' + content + '</div>';
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}
function addLog(log) {
    const chat = document.getElementById('chat');
    const div = document.createElement('div');
    div.className = 'log-box ' + (log.ok ? 'success' : (log.err ? 'error' : ''));
    div.textContent = (log.ok ? '[OK] ' : (log.err ? '[ERR] ' : '')) + log.text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}
function setBusy(b) { busy = b; document.getElementById('sendBtn').disabled = b; document.getElementById('status').innerHTML = b ? '<span class="loading"></span> 处理中...' : '就绪'; }
function clearChat() { if (!confirm('确定清除？')) return; fetch('/clear', {method: 'POST'}).then(() => location.reload()); }
</script>
</body>
</html>'''


def run_web(host: str = '127.0.0.1', port: int = 9999):
    """
    启动 Web 服务器

    Args:
        host: 主机地址
        port: 端口
    """
    print("=" * 60)
    print("       iQuery 智能数据分析平台 v2.0")
    print("=" * 60)
    print(f"\n服务已启动！")
    print(f"\n请在浏览器打开: http://{host}:{port}")
    print("\n按 Ctrl+C 停止服务")
    print("=" * 60)

    # 自动打开浏览器
    def open_browser():
        time.sleep(1)
        import webbrowser
        webbrowser.open(f'http://{host}:{port}')

    threading.Thread(target=open_browser, daemon=True).start()

    with socketserver.TCPServer((host, port), RequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n服务已停止")
