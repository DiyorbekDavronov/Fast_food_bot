import psycopg2

def connect_database():
    database = psycopg2.connect(
        host="localhost",
        database="pro_food_th_19_30",
        user="postgres",
        password="123456"
    )
    cursor = database.cursor()
    return database, cursor


database, cursor = connect_database()


def create_users_table():
    cursor.execute("""CREATE TABLE IF NOT EXISTS users(
        user_id SERIAL PRIMARY KEY,
        full_name VARCHAR(30) NOT NULL,
        telegram_id INTEGER NOT NULL UNIQUE
    )""")


def create_carts_table():
    cursor.execute("""CREATE TABLE IF NOT EXISTS carts(
        cart_id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(user_id) UNIQUE,
        total_products INTEGER DEFAULT 0,
        total_price DECIMAL(8, 2) DEFAULT 0
    )""")


def create_cart_products_table():
    # cart_product => продукт который находится в корзине
    cursor.execute("""CREATE TABLE IF NOT EXISTS cart_products(
        cart_product_id SERIAL PRIMARY KEY,
        cart_id INTEGER REFERENCES carts(cart_id),
        product_name VARCHAR(30) NOT NULL,
        quantity INTEGER NOT NULL,
        final_price DECIMAL(9, 2) NOT NULL,
        
        UNIQUE(cart_id, product_name)
    )""")


def create_orders_table():
    cursor.execute("""CREATE TABLE IF NOT EXISTS orders(
        order_id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(user_id),
        time_create TIMESTAMP NOT NULL, 
        total_products INTEGER,
        total_price DECIMAL(8, 2)
    )""")


def create_order_products_table():
    cursor.execute("""CREATE TABLE IF NOT EXISTS order_products(
        order_product_id SERIAL PRIMARY KEY,
        order_id INTEGER REFERENCES orders(order_id),
        product_name VARCHAR(30) NOT NULL,
        quantity INTEGER NOT NULL,
        final_price DECIMAL(9, 2) NOT NULL,

        UNIQUE(order_id, product_name)
    )""")


def create_categories_table():
    cursor.execute("""CREATE TABLE IF NOT EXISTS categories(
        category_id SERIAL PRIMARY KEY,
        category_name VARCHAR(15) NOT NULL UNIQUE
    )""")


def create_products_table():
    cursor.execute("""CREATE TABLE IF NOT EXISTS products(
        product_id SERIAL PRIMARY KEY,
        product_name VARCHAR(30) NOT NULL,
        price DECIMAL(9, 2) NOT NULL,
        image VARCHAR(50) NOT NULL,
        ingredients VARCHAR(255),
        
        UNIQUE(product_name, image)
    )""")

# DECIMAL -
# 12 - максимальное кол-во цифр в числе
# 2 - максимальное кол-во цифр после запятой
# 1234567890.23


create_users_table()
create_carts_table()
create_cart_products_table()
create_categories_table()
create_products_table()

create_orders_table()
create_order_products_table()
database.commit()
database.close()
