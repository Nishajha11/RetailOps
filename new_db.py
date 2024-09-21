import sqlite3
import pandas as pd

# Connect to the SQLite database
con = sqlite3.connect('ims.db')

# Create a list of tables to export
tables = ['category', 'product','customer']

# Create an Excel writer object
with pd.ExcelWriter('ims_data.xlsx', engine='openpyxl') as writer:
    for table in tables:
        # Read the table into a DataFrame
        df = pd.read_sql_query(f"SELECT * FROM {table}", con)
        # Write the DataFrame to the Excel file, using the table name as the sheet name
        df.to_excel(writer, sheet_name=table, index=False)

# Close the connection
con.close()