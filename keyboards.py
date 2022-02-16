from aiogram.types.reply_keyboard import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types.inline_keyboard import InlineKeyboardMarkup, InlineKeyboardButton

from database import connect_database


def build_inline_keyboard(
        markup: InlineKeyboardMarkup, lst: list, prefix: str, in_row: int = 2
):
    rows = len(lst) // in_row
    if len(lst) % in_row != 0:
        rows += 1

    start = 0
    end = in_row  # 2

    for row in range(rows):
        new_lst = []
        for id, title in lst[start:end]:
            new_lst.append(
                InlineKeyboardButton(
                    text=title,
                    callback_data=f"{prefix}_{id}"
                )
            )
        markup.row(*new_lst)
        start = end
        end += in_row


def generate_main_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton(text="✅ Начать заказ")],
        [
            KeyboardButton(text="🛒 Корзина"),
            KeyboardButton(text="📋 Список заказов")
        ]
    ], resize_keyboard=True)


def generate_categories_menu():
    markup = InlineKeyboardMarkup()
    database, cursor = connect_database()

    cursor.execute("""SELECT category_id, category_name
        FROM categories
    """)
    categories = cursor.fetchall()  # 7 -> 4
    database.close()

    build_inline_keyboard(
        markup=markup,
        lst=categories,
        prefix="category"
    )

    return markup


def generate_products_menu(category_id: int):
    markup = InlineKeyboardMarkup()
    database, cursor = connect_database()

    # Получение продуктов из БД
    cursor.execute("""SELECT product_id, product_name
        FROM products
        WHERE category_id = %s
    """, (category_id,))
    products = cursor.fetchall()
    database.close()

    build_inline_keyboard(
        markup=markup,
        lst=products,
        prefix="product"
    )

    markup.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data=f"back_main"
        )
    )

    return markup


def generate_product_detail_menu(product_id: int, category_id: int):
    markup = InlineKeyboardMarkup()
    numbers_list = list(range(1, 10))

    in_row = 3
    rows = len(numbers_list) // in_row
    if len(numbers_list) % in_row != 0:
        rows += 1

    start = 0
    end = in_row

    for row in range(rows):
        new_lst = []
        for number in numbers_list[start:end]:
            new_lst.append(
                InlineKeyboardButton(
                    text=str(number),
                    callback_data=f"cart_{product_id}_{number}"
                )
            )
        markup.row(*new_lst)
        start = end
        end += in_row
    markup.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data=f"back_category_{category_id}"
        )
    )
    return markup


def generate_cart_menu(cart_products: list, cart_id: int):
    markup = InlineKeyboardMarkup()

    markup.row(
        InlineKeyboardButton(text="Очистить корзину", callback_data=f"clear_cart_{cart_id}"),
        InlineKeyboardButton(text="Оформить заказ", callback_data=f"create_order_{cart_id}")
    )

    for cart_product_id, product_name in cart_products:
        markup.row(
            InlineKeyboardButton(
                text=f"❌  {product_name}",
                callback_data=f"delete_{cart_product_id}"
            )
        )
    return markup
