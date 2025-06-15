import json
import mysql.connector

conn = mysql.connector.connect(user='django_user', password='FAKE_DB_PASSWORD', host='localhost', database='jobs_manager')
cursor = conn.cursor()

with open('steel_and_tube_products.json', 'r', encoding='utf-8') as jsonfile:
    data = json.load(jsonfile)
    
    for item in data:
        # Convert dict values to list, pad if fewer columns than your table expects
        if isinstance(item, dict):
            row = list(item.values())
        else:
            row = item if isinstance(item, list) else [item]
        
        row += [''] * (13 - len(row))
        # sql = """
        #     INSERT INTO quoting_supplierproduct_staging
        #     (col1, col2, col3, col4, col5, col6, col7, col8, col9, col10,
        #      col11, col12, col13, col14, col15, col16, col17, col18, col19, col20)
        #     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
        #             %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        # """
        sql = """
            INSERT INTO quoting_supplierproduct
            (product_name, item_no, description, specifications, variant_width, variant_length, variant_price, price_unit, variant_available_stock, variant_id,
             url, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s)
        """
        cursor.execute(sql, row)

conn.commit()
cursor.close()
conn.close()