import sqlite3
import pandas as pd
import os

def check_db():
    db_path = "invoices.db"
    print(f"检查数据库文件: {db_path}")
    
    if not os.path.exists(db_path):
        print("错误: 数据库文件不存在！")
        return

    try:
        conn = sqlite3.connect(db_path)
        
        # 1. 检查表结构
        print("\n[表结构]")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"存在的数据表: {tables}")
        
        if not tables or ('invoices',) not in tables:
            print("错误: invoices 表不存在！")
            conn.close()
            return

        cursor.execute("PRAGMA table_info(invoices)")
        columns = cursor.fetchall()
        print("字段列表:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")

        # 2. 检查数据总数
        print("\n[数据统计]")
        df = pd.read_sql_query("SELECT * FROM invoices", conn)
        print(f"总行数: {len(df)}")
        if not df.empty:
            print("前 5 条数据:")
            print(df[['id', 'user_id', 'file_name', 'total', 'created_at']].head().to_string())
        else:
            print("表是空的。")
            
        # 3. 尝试插入一条测试数据
        print("\n[写入测试]")
        try:
            cursor.execute("""
                INSERT INTO invoices (user_id, file_name, date, total, status) 
                VALUES ('default_user', 'test_debug.jpg', '2026/01/01', 100, 'DEBUG')
            """)
            conn.commit()
            print("写入测试成功！")
            
            # 再次读取确认
            df_new = pd.read_sql_query("SELECT * FROM invoices WHERE file_name='test_debug.jpg'", conn)
            if not df_new.empty:
                print(f"读取验证成功: 找到了 {len(df_new)} 条测试数据")
                
                # 清理测试数据
                cursor.execute("DELETE FROM invoices WHERE file_name='test_debug.jpg'")
                conn.commit()
                print("清理测试数据成功。")
            else:
                print("错误: 写入后无法读取！")
                
        except Exception as e:
            print(f"写入测试失败: {e}")

        conn.close()

    except Exception as e:
        print(f"连接数据库失败: {e}")

if __name__ == "__main__":
    check_db()
