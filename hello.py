import os
from typing import List, Dict
import sqlite3
import requests
from dotenv import load_dotenv

# ===== 初始化 =====
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-deepseek-api-key-here")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

# ===== 数据库设置 =====
def init_db():
    """初始化SQLite数据库"""
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        priority TEXT DEFAULT 'medium',
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    return conn

# ===== 任务管理函数 =====
def add_task(conn, title: str, description: str = ""):
    """添加新任务"""
    c = conn.cursor()
    c.execute('INSERT INTO tasks (title, description) VALUES (?, ?)',
              (title, description))
    conn.commit()
    return c.lastrowid

def list_tasks(conn) -> List[Dict]:
    """列出所有任务"""
    c = conn.cursor()
    c.execute('SELECT id, title, description, priority, status FROM tasks')
    tasks = c.fetchall()
    return [{"id": t[0], "title": t[1], "desc": t[2], "priority": t[3], "status": t[4]} 
            for t in tasks]

def update_task_status(conn, task_id: int, status: str):
    """更新任务状态"""
    c = conn.cursor()
    c.execute('UPDATE tasks SET status = ? WHERE id = ?', (status, task_id))
    conn.commit()

def update_task_priority(conn, task_id: int, priority: str):
    """更新任务优先级"""
    c = conn.cursor()
    c.execute('UPDATE tasks SET priority = ? WHERE id = ?', (priority, task_id))
    conn.commit()

# ===== DeepSeek API 调用函数 =====
def call_deepseek_api(messages: List[Dict], temperature: float = 0.7, max_tokens: int = 1000) -> str:
    """调用DeepSeek API"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            return "❌ API返回异常结果"
    
    except requests.exceptions.Timeout:
        return "❌ 请求超时，请稍后重试"
    except requests.exceptions.ConnectionError:
        return "❌ 网络连接错误，请检查网络"
    except requests.exceptions.HTTPError as e:
        return f"❌ API错误: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"❌ 发生错误: {str(e)}"

# ===== AI助手函数 =====
def ai_breakdown_task(task_title: str, task_desc: str = "") -> str:
    """AI帮助拆分任务"""
    prompt = f"""
    用户想完成这个任务: "{task_title}"
    任务描述: {task_desc if task_desc else "无"}
    
    请帮我:
    1. 将其拆分成3-5个具体的子任务
    2. 为每个子任务估算时间
    3. 建议优先级顺序
    
    用清晰的列表格式回复。
    """
    
    messages = [{"role": "user", "content": prompt}]
    return call_deepseek_api(messages, temperature=0.7, max_tokens=500)

def ai_suggest_priority(task_title: str) -> str:
    """AI建议任务优先级"""
    prompt = f"根据任务名称 '{task_title}'，这个任务的优先级应该是什么？(高/中/低)。请用一句话解释。"
    
    messages = [{"role": "user", "content": prompt}]
    return call_deepseek_api(messages, temperature=0.5, max_tokens=100)

def ai_smart_assistant(user_query: str, tasks: List[Dict]) -> str:
    """智能助手 - 回答关于任务的问题"""
    tasks_text = "\n".join([f"- {t['title']} (状态: {t['status']}, 优先级: {t['priority']})" for t in tasks])
    
    prompt = f"""
    我的当前任务列表:
    {tasks_text if tasks_text else "暂无任务"}
    
    用户问: {user_query}
    
    请基于我的任务列表给出建议或回答。如果没有任务，请提供一般性的建议。
    """
    
    messages = [{"role": "user", "content": prompt}]
    return call_deepseek_api(messages, temperature=0.7, max_tokens=300)

def ai_time_estimation(task_title: str, task_desc: str = "") -> str:
    """AI估算任务完成时间"""
    prompt = f"""
    任务名称: {task_title}
    任务描述: {task_desc if task_desc else "无详细描述"}
    
    请估算完成这个任务需要多少时间？
    请提供:
    1. 预计耗时
    2. 影响时间的主要因素
    3. 建议如何提高效率
    """
    
    messages = [{"role": "user", "content": prompt}]
    return call_deepseek_api(messages, temperature=0.5, max_tokens=300)

def ai_task_suggestions(current_tasks: List[Dict]) -> str:
    """AI根据当前任务给出建议"""
    tasks_text = "\n".join([f"- {t['title']} (状态: {t['status']})" for t in current_tasks])
    
    prompt = f"""
    用户的当前任务:
    {tasks_text if tasks_text else "暂无任务"}
    
    请基于这些任务给出:
    1. 优化任务顺序的建议
    2. 可能遗漏的重要任务
    3. 时间管理建议
    """
    
    messages = [{"role": "user", "content": prompt}]
    return call_deepseek_api(messages, temperature=0.7, max_tokens=400)

# ===== 主程序 =====
def main():
    print("🚀 正在初始化AI任务助手...\n")
    
    # 检查API Key
    if DEEPSEEK_API_KEY == "your-deepseek-api-key-here":
        print("⚠️  警告: 未设置DeepSeek API Key!")
        print("请设置环境变量或在.env文件中添加:")
        print("DEEPSEEK_API_KEY=your_actual_api_key")
        print("\n继续使用？(y/n): ", end="")
        if input().lower() != 'y':
            return
    
    conn = init_db()
    print("✅ 数据库初始化完成\n")
    
    while True:
        print("\n" + "="*40)
        print("    🤖 DeepSeek AI 任务助手")
        print("="*40)
        print("1.  ➕ 添加新任务")
        print("2.  📋 列出所有任务")
        print("3.  🧠 AI拆分任务")
        print("4.  ⭐ AI建议优先级")
        print("5.  ⏱️  AI估算耗时")
        print("6.  💡 AI智能助手问答")
        print("7.  🎯 AI任务建议")
        print("8.  ✅ 标记任务完成")
        print("0.  🚪 退出")
        print("="*40)
        
        choice = input("\n选择操作 (0-8): ").strip()
        
        if choice == "1":
            title = input("输入任务名称: ").strip()
            if not title:
                print("❌ 任务名称不能为空")
                continue
            desc = input("输入任务描述 (可选): ").strip()
            task_id = add_task(conn, title, desc)
            print(f"\n✅ 任务已添加 (ID: {task_id})")
        
        elif choice == "2":
            tasks = list_tasks(conn)
            if not tasks:
                print("\n📋 暂无任务")
            else:
                print("\n" + "="*60)
                print(f"{'ID':<5} {'任务名称':<20} {'优先级':<8} {'状态':<10}")
                print("="*60)
                for task in tasks:
                    status_emoji = "✅" if task['status'] == "completed" else "⏳"
                    print(f"{task['id']:<5} {task['title']:<20} {task['priority']:<8} {status_emoji} {task['status']:<8}")
                print("="*60)
        
        elif choice == "3":
            title = input("输入要拆分的任务名称: ").strip()
            if not title:
                print("❌ 任务名称不能为空")
                continue
            desc = input("输入任务描述 (可选): ").strip()
            print("\n🤔 AI正在分析任务...\n")
            result = ai_breakdown_task(title, desc)
            print("AI分析结果:")
            print("-" * 50)
            print(result)
            print("-" * 50)
        
        elif choice == "4":
            title = input("输入任务名称: ").strip()
            if not title:
                print("❌ 任务名称不能为空")
                continue
            print("\n🤔 AI正在分析优先级...\n")
            result = ai_suggest_priority(title)
            print("AI建议:")
            print("-" * 50)
            print(result)
            print("-" * 50)
        
        elif choice == "5":
            title = input("输入任务名称: ").strip()
            if not title:
                print("❌ 任务名称不能为空")
                continue
            desc = input("输入任务描述 (可选): ").strip()
            print("\n🤔 AI正在估算耗时...\n")
            result = ai_time_estimation(title, desc)
            print("AI估算结果:")
            print("-" * 50)
            print(result)
            print("-" * 50)
        
        elif choice == "6":
            query = input("请输入你的问题: ").strip()
            if not query:
                print("❌ 问题不能为空")
                continue
            tasks = list_tasks(conn)
            print("\n🤔 AI正在思考...\n")
            result = ai_smart_assistant(query, tasks)
            print("AI回复:")
            print("-" * 50)
            print(result)
            print("-" * 50)
        
        elif choice == "7":
            tasks = list_tasks(conn)
            print("\n🤔 AI正在分析...\n")
            result = ai_task_suggestions(tasks)
            print("AI建议:")
            print("-" * 50)
            print(result)
            print("-" * 50)
        
        elif choice == "8":
            tasks = list_tasks(conn)
            if not tasks:
                print("❌ 暂无任务")
                continue
            print("\n待完成任务:")
            for task in tasks:
                if task['status'] != 'completed':
                    print(f"[{task['id']}] {task['title']}")
            task_id = input("输入任务ID: ").strip()
            try:
                update_task_status(conn, int(task_id), "completed")
                print("✅ 任务已标记为完成")
            except ValueError:
                print("❌ 无效的任务ID")
        
        elif choice == "0":
            conn.close()
            print("\n👋 感谢使用AI任务助手，再见！\n")
            break
        
        else:
            print("❌ 无效选择，请重试")

if __name__ == "__main__":
    main()