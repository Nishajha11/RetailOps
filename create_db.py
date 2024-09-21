import sqlite3
def create_db():
    con = sqlite3.connect(database=r'ims.db')
    cur=con.cursor()
    
    cur.execute("CREATE TABLE IF NOT EXISTS customer(invoice INTEGER PRIMARY KEY AUTOINCREMENT , name text, contact text, desc text)")
    con.commit()
    cur.execute("CREATE TABLE IF NOT EXISTS category(cid INTEGER PRIMARY KEY AUTOINCREMENT,name text)")
    con.commit()

    cur.execute("CREATE TABLE IF NOT EXISTS supplier (invoice INTEGER PRIMARY KEY AUTOINCREMENT,name text,contact text,desc text)")
    con.commit()

    cur.execute("CREATE TABLE IF NOT EXISTS product (pid INTEGER PRIMARY KEY AUTOINCREMENT,Supplier text,Category text,name text,price text,qty text,status text)")
    con.commit()
    #cur.execute("PRAGMA table_info(product)")
    #columns = cur.fetchall()
    #column_names = [column[1] for column in columns]
    #if 'qty' not in column_names:
        #cur.execute("ALTER TABLE product ADD COLUMN quantity TEXT")
        #con.commit()
create_db()    