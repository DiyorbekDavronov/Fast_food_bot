from aiogram import Bot, Dispatcher, executor
from aiogram.types import Message, CallbackQuery

from database import connect_database
from keyboards import (generate_main_menu, generate_categories_menu,
                       generate_products_menu, generate_product_detail_menu, generate_cart_menu)

from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()


token = os.getenv("BOT_TOKEN")
provider_token = os.getenv("PROVIDER_TOKEN")
bot = Bot(token, parse_mode="HTML")
dp = Dispatcher(bot)


@dp.message_handler(commands=["start"])
async def start(message: Message):
    chat_id = message.chat.id
    full_name = message.from_user.full_name

    await register_user(message)
    await register_cart(message)
    await bot.send_message(chat_id, f"Привет, {full_name}")
    await show_main_menu(message)


async def register_user(message: Message):
    chat_id = message.chat.id
    full_name = message.from_user.full_name

    database, cursor = connect_database()

    try:
        cursor.execute("""INSERT INTO users (full_name, telegram_id) 
            VALUES (%s, %s)
        """, (full_name, chat_id))
        database.commit()
        await bot.send_message(chat_id, "Регистрация прошла успешно !")
    except Exception as exp:
        print(f"{exp.__class__.__name__}: {exp}")
    finally:
        database.close()


async def register_cart(message: Message):
    chat_id = message.chat.id
    database, cursor = connect_database()
    try:
        cursor.execute("""INSERT INTO carts (user_id)
            VALUES ((
                SELECT user_id
                FROM users
                WHERE telegram_id = %s
            ))
        """, (chat_id,))
        database.commit()
    except Exception as exp:
        print(f"{exp.__class__.__name__}: {exp}")
    finally:
        database.close()


async def show_main_menu(message: Message):
    chat_id = message.chat.id
    await bot.send_message(chat_id, "Выберите направление: ",
                           reply_markup=generate_main_menu())


@dp.message_handler(lambda message: "Начать заказ" in message.text)
async def make_order(message: Message):
    chat_id = message.chat.id
    await bot.send_message(chat_id, "Выберите категорию: ",
                           reply_markup=generate_categories_menu())


@dp.message_handler(lambda message: "Корзина" in message.text)
async def show_cart_menu(message: Message, cart_id: int = None, edit: bool = False):
    chat_id = message.chat.id
    message_id = message.message_id

    database, cursor = connect_database()

    if not cart_id:
        # Получить корзину
        cursor.execute("""SELECT cart_id
            FROM carts
            WHERE user_id = (
                SELECT user_id
                FROM users
                WHERE telegram_id = %s
            )
        """, (chat_id,))
        cart_id = cursor.fetchone()[0]

    # Обновить состояние корзины
    cursor.execute("""UPDATE carts
        SET total_products = (
            SELECT SUM(quantity)
            FROM cart_products
            WHERE cart_id = %(cart_id)s
        ), total_price = (
            SELECT SUM(final_price)
            FROM cart_products
            WHERE cart_id = %(cart_id)s
        )
        WHERE cart_id = %(cart_id)s
        RETURNING total_products, total_price
    """, {"cart_id": cart_id})
    database.commit()
    total_products, total_price = cursor.fetchone()

    # Получить cart_products
    cursor.execute("""SELECT cart_product_id, product_name, quantity, final_price
        FROM cart_products
        WHERE cart_id = %s
    """, (cart_id,))
    cart_products = cursor.fetchall()  # [(product_name, quantity, final_price), (product_name, quantity, final_price), ()]

    # Если корзина пуста ...
    if not cart_products:
        await bot.delete_message(chat_id, message_id)
        await bot.send_message(chat_id, "Ваша корзина пуста !!!")
        return

    text = "Ваша корзина: \n\n"
    i = 0
    cart_products_name_id = []
    for cart_product_id, product_name, quantity, final_price in cart_products:
        cart_products_name_id.append((cart_product_id, product_name))
        i += 1
        text += f"""{i}. <strong>{product_name}</strong>
        <em>Кол-во: {quantity} шт</em>
        <em>Общая стоимость: {final_price} сум</em>\n"""

    text += f"""\n\nОбщее количество продуктов: {total_products} шт
Общая стоимость корзины: {total_price} сум"""

    if edit:
        await bot.edit_message_text(text, chat_id, message_id,
                                    reply_markup=generate_cart_menu(
                                        cart_products=cart_products_name_id,
                                        cart_id=cart_id
                                    )
                                    )
    else:
        await bot.send_message(chat_id, text,
                               reply_markup=generate_cart_menu(
                                   cart_products=cart_products_name_id,
                                   cart_id=cart_id
                               )
                               )


@dp.message_handler(lambda message: "Список заказов" in message.text)
async def show_list_orders(message: Message):
    chat_id = message.chat.id

    database, cursor = connect_database()
    # Получить user_id
    cursor.execute("""SELECT user_id
        FROM users
        WHERE telegram_id = %s
    """, (chat_id, ))
    user_id = cursor.fetchone()

    # Получить список заказов
    cursor.execute("""SELECT order_id, time_create, total_products, total_price
        FROM orders
        WHERE user_id = %s
    """, (user_id, ))
    orders = cursor.fetchall()

    text = "Ваши заказы: \n\n"
    i = 0
    for order_id, time_create, total_products, total_price in orders:
        i += 1
        text += f"""Заказ № {i}\n\tДата создания: {time_create}"""

        cursor.execute("""SELECT product_name, quantity, final_price
            FROM order_products
            WHERE order_id = %s
        """, (order_id, ))
        order_products = cursor.fetchall()

        x = 0
        for product_name, quantity, final_price in order_products:
            x += 1
            text += f"""{x}. {product_name}
Количество: {quantity}
Общая стоимость: {final_price}"""
        text += f"""Общее кол-во продуктов в заказе: {total_products}
Общая стоимость заказа: {total_price}"""
    await bot.send_message(chat_id, text)


@dp.callback_query_handler(lambda call: call.data.startswith("category"))
async def show_products_menu(call: CallbackQuery, category_id: int = None, edit: bool = True):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    if not category_id:
        _, category_id = call.data.split("_")  # -> ["category", "1"]
        category_id = int(category_id)

    if edit:
        await bot.edit_message_text(
            text="Выберите продукт",
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=generate_products_menu(category_id)
        )
    else:
        await bot.delete_message(chat_id, message_id)
        await bot.send_message(
            text="Выберите продукт",
            chat_id=chat_id,
            reply_markup=generate_products_menu(category_id)
        )


@dp.callback_query_handler(lambda call: "back_main" in call.data)
async def return_back_main(call: CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    await bot.delete_message(chat_id, message_id)
    await make_order(call.message)


@dp.callback_query_handler(lambda call: call.data.startswith("back_category"))
async def return_back_category(call: CallbackQuery):
    _, _, category_id = call.data.split("_")
    await show_products_menu(call, category_id, edit=False)


@dp.callback_query_handler(lambda call: "product" in call.data)  # product_1
async def show_product_detail(call: CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    _, product_id = call.data.split("_")

    database, cursor = connect_database()
    cursor.execute("""SELECT category_id, product_name, price, image, ingredients
        FROM products
        WHERE product_id = %s
    """, (product_id,))
    category_id, product_name, price, image, ingredients = cursor.fetchone()
    database.close()

    text = f"""<strong>{product_name}</strong>

Стоимость: {price}
Ингредиенты: {ingredients}

<i>Выберите кол-во</i>"""
    await bot.delete_message(chat_id, message_id)
    with open(image, mode="rb") as img:
        await bot.send_photo(chat_id, photo=img, caption=text,
                             reply_markup=generate_product_detail_menu(
                                 product_id,
                                 category_id
                             ))


@dp.callback_query_handler(lambda call: call.data.startswith("cart"))
async def add_cart_product(call: CallbackQuery):
    chat_id = call.message.chat.id
    _, product_id, quantity = call.data.split("_")  # cart_1_5
    product_id, quantity = int(product_id), int(quantity)

    database, cursor = connect_database()

    # Получение продукта
    cursor.execute("""SELECT product_name, price
        FROM products
        WHERE product_id = %s 
    """, (product_id,))
    product_name, price = cursor.fetchone()

    # Получение корзины
    cursor.execute("""SELECT cart_id
        FROM carts
        WHERE user_id = (
            SELECT user_id
            FROM users
            WHERE telegram_id = %s
        )
    """, (chat_id,))
    cart_id = cursor.fetchone()[0]

    # Создание cart_product
    final_price = price * quantity
    try:
        cursor.execute("""INSERT INTO cart_products (cart_id, product_name, quantity, final_price)
            VALUES (%s, %s, %s, %s)
        """, (cart_id, product_name, quantity, final_price))
        database.commit()
        await bot.answer_callback_query(call.id, "Продукт успешно добавлен !")
    except:
        # TODO: Нужно откатить транзакцию
        cursor.execute("""UPDATE cart_products
            SET quantity = %s, 
                final_price = %s
            WHERE product_name = %s
        """, (quantity, final_price, product_name))
        database.commit()
        await bot.answer_callback_query(call.id, "Кол-во продукта успешно изменено !")
    finally:
        database.close()


@dp.callback_query_handler(lambda call: "delete" in call.data)
async def delete_cart_product(call: CallbackQuery):
    _, cart_product_id = call.data.split("_")
    cart_product_id = int(cart_product_id)

    database, cursor = connect_database()
    # Удалить cart_product
    cursor.execute("""DELETE FROM cart_products
        WHERE cart_product_id = %s
        RETURNING cart_id
    """, (cart_product_id,))
    cart_id = cursor.fetchone()[0]
    database.commit()
    database.close()

    await bot.answer_callback_query(call.id, "Продукт успешно удалён !")
    # Обновить состояние корзины
    await show_cart_menu(
        message=call.message,
        cart_id=cart_id,
        edit=True
    )


@dp.callback_query_handler(lambda call: call.data.startswith("clear_cart"))
async def clear_cart(call: CallbackQuery):
    # clear_cart_1
    _, _, cart_id = call.data.split("_")

    database, cursor = connect_database()
    # Удалить все cart_product
    cursor.execute("""DELETE FROM cart_products
        WHERE cart_id = %s
    """, (cart_id, ))
    database.commit()
    database.close()

    await bot.answer_callback_query(call.id, "Корзина успешно очищена !")
    await show_cart_menu(
        message=call.message,
        cart_id=cart_id,
        edit=True
    )


@dp.callback_query_handler(lambda call: call.data.startswith("create_order"))
async def create_order(call: CallbackQuery):
    # create_order_1
    _, _, cart_id = call.data.split("_")
    cart_id = int(cart_id)
    chat_id = call.message.chat.id

    database, cursor = connect_database()
    # Получить cart_products
    cursor.execute("""SELECT product_name, quantity, final_price
        FROM cart_products
        WHERE cart_id = %s
    """, (cart_id, ))
    cart_products = cursor.fetchall()

    # Создать заказ и получить его id
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""INSERT INTO orders (user_id, time_create)
        VALUES ((
            SELECT user_id
            FROM users
            WHERE telegram_id = %s
        ), %s)
        RETURNING order_id
    """, (chat_id, current_datetime))
    database.commit()
    order_id = cursor.fetchone()[0]

    # Создать order_products
    for product_name, quantity, final_price in cart_products:
        cursor.execute("""INSERT INTO order_products (order_id, product_name, quantity, final_price)
            VALUES (%s, %s, %s, %s)
        """, (order_id, product_name, quantity, final_price))
        database.commit()

    # Посчитать total_products / total_price
    cursor.execute("""UPDATE orders
            SET total_products = (
                SELECT SUM(quantity)
                FROM order_products
                WHERE order_id = %(order_id)s
            ), total_price = (
                SELECT SUM(final_price)
                FROM order_products
                WHERE order_id = %(order_id)s
            )
            WHERE order_id = %(order_id)s
        """, {"order_id": order_id})
    database.commit()

    # Удалим cart_products
    cursor.execute("""DELETE FROM cart_products
        WHERE cart_id = %s
    """, (cart_id, ))
    database.commit()

    # Обнулим корзину
    cursor.execute("""UPDATE carts
        SET total_products = 0, total_price = 0
        WHERE cart_id = %s
    """, (cart_id, ))
    database.commit()

    await bot.answer_callback_query(call.id, "Заказ успешно оформлен !")


executor.start_polling(dp, skip_updates=True)
