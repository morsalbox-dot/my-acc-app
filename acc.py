from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

import os
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))
# إنشاء قاعدة البيانات والجداول عند تشغيل التطبيق
def init_db():
    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()
    # جدول البنود (الشرائح الرئيسية مثل: رواتب، إيجار، مبيعات...)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL -- 'وارد' أو 'مصروف'
        )
    ''')
    # جدول المعاملات المالية
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            category_id INTEGER,
            description TEXT,
            amount REAL NOT NULL,
            type TEXT NOT NULL, -- 'وارد' أو 'مصروف'
            balance_after REAL,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    ''')
    conn.commit()
    conn.close()

# دالة لحساب الرصيد المتاح الحالي
def get_current_balance():
    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance_after FROM transactions ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0.0

@app.route('/')
def index():
    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()
    
    # جلب البنود والعمليات لعرضها
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    
    cursor.execute('''
        SELECT t.id, t.date, c.name, t.description, t.amount, t.type, t.balance_after 
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        ORDER BY t.id DESC
    ''')
    transactions = cursor.fetchall()
    conn.close()
    
    current_balance = get_current_balance()
    return render_template('index.html', categories=categories, transactions=transactions, current_balance=current_balance)

# إضافة بند جديد (صرف أو إيراد)
@app.route('/add_category', methods=['POST'])
def add_category():
    name = request.form['name']
    cat_type = request.form['type']
    
    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO categories (name, type) VALUES (?, ?)", (name, cat_type))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# إضافة معاملة مالية جديدة (وارد أو مصروف)
@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    category_id = request.form['category_id']
    description = request.form['description']
    amount = float(request.form['amount'])
    date_str = request.form['date'] or datetime.now().strftime('%Y-%m-%d')
    
    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()
    
    # معرفة نوع البند المختار
    cursor.execute("SELECT type FROM categories WHERE id = ?", (category_id,))
    cat_type = cursor.fetchone()[0]
    
    # حساب الرصيد الجديد بعد هذه العملية
    current_balance = get_current_balance()
    if cat_type == 'وارد':
        new_balance = current_balance + amount
    else:
        new_balance = current_balance - amount
        
    cursor.execute('''
        INSERT INTO transactions (date, category_id, description, amount, type, balance_after)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (date_str, category_id, description, amount, cat_type, new_balance))
    
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# تقرير المصروفات خلال فترة محددة للطباعة
@app.route('/report')
def report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()
    
    # جلب المصروفات فقط خلال الفترة المحددة
    cursor.execute('''
        SELECT t.date, c.name, t.description, t.amount, t.balance_after 
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.type = 'مصروف' AND t.date BETWEEN ? AND ?
        ORDER BY t.date ASC
    ''', (start_date, end_date))
    
    report_data = cursor.fetchall()
    
    # حساب إجمالي المصروفات في هذه الفترة
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE type = 'مصروف' AND date BETWEEN ? AND ?", (start_date, end_date))
    total_spent = cursor.fetchone()[0] or 0.0
    
    conn.close()
    return render_template('report.html', report_data=report_data, start_date=start_date, end_date=end_date, total_spent=total_spent)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)