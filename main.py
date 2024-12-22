import threading
import time

import requests

api_url = 'https://api.mexc.com/api/v3/'

last_order_price_10sec = 0
last_order_price_30sec = 0
last_order_price_1min = 0
last_order_price_5min = 0

change_order_10sec = 0
change_order_30sec = 0
change_order_1min = 0
change_order_5min = 0

last_trade_price_10sec = 0
last_trade_price_30sec = 0
last_trade_price_1min = 0
last_trade_price_5min = 0

change_trade_10sec = 0
change_trade_30sec = 0
change_trade_1min = 0
change_trade_5min = 0

lock = threading.Lock()

TELEGRAM_BOT_TOKEN = '7663401015:AAEnpvk5PoMw1KXGWXnehfZUlvZ_PvPG7aE'
TELEGRAM_CHAT_IDS = ['717664582', '508884173']

mapper = {
    'change_order_10sec': '10 секунд',
    'change_trade_10sec': '10 секунд',
    'change_order_30sec': '30 секунд',
    'change_trade_30sec': '30 секунд',
    'change_order_1min': '1 минута',
    'change_trade_1min': '1 минута',
    'change_order_5min': '5 минут',
    'change_trade_5min': '5 минут',
}

last_notification_time = {}


def send_telegram_notification(message, change_var_name):
    now = time.time()
    smaller_intervals = {
        '10sec': [],
        '30sec': ['10sec'],
        '1min': ['10sec', '30sec'],
        '5min': ['10sec', '30sec', '1min'],
    }
    current_interval = [key for key in smaller_intervals.keys() if key in change_var_name][0]
    for smaller_interval in smaller_intervals[current_interval]:
        if last_notification_time.get(f"change_order_{smaller_interval}") or \
           last_notification_time.get(f"change_trade_{smaller_interval}"):
            # Уведомление за меньший интервал уже отправлено
            return

    # Отправляем уведомление и обновляем время последнего отправления
    last_notification_time[change_var_name] = now
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    for chat_id in TELEGRAM_CHAT_IDS:
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"Ошибка при отправке в Telegram: {response.text}")


def fetch_trade_price(interval, storage_var_name, change_var_name):
    global last_trade_price_10sec, last_trade_price_30sec, last_trade_price_1min, last_trade_price_5min
    global change_trade_10sec, change_trade_30sec, change_trade_1min, change_trade_5min

    previous_price = 0

    while True:
        try:
            method = 'trades'
            params = {'symbol': 'FTNUSDT', 'limit': 1}
            response = requests.get(api_url + method, params)
            response.raise_for_status()
            trade = response.json()[0]
            if trade:
                current_price = float(trade['price'])
                with lock:
                    if previous_price:
                        change = ((current_price - previous_price) / previous_price) * 100
                    else:
                        change = 0
                    if abs(change) >= 0.01:
                        message = (
                            f"🔔 <b>Изменение курса!</b>\n"
                            f"Обнаружено по: {'стакану' if 'order' in change_var_name else 'сделкам'}\n"
                            f"Временной промежуток: <i>{mapper[change_var_name]}</i>\n"
                            f"Изменение: <b>{change:.2f}%</b>\n"
                        )
                        send_telegram_notification(message, change_var_name)
                    globals()[storage_var_name] = current_price
                    globals()[change_var_name] = change
                previous_price = current_price
        except Exception as e:
            print(f"Error fetching price for {storage_var_name}: {e}")
        time.sleep(interval)


def fetch_order_price(interval, storage_var_name, change_var_name):
    global last_order_price_10sec, last_order_price_30sec, last_order_price_1min, last_order_price_5min
    global change_order_10sec, change_order_30sec, change_order_1min, change_order_5min

    previous_price = 0

    while True:
        try:
            method = 'depth'
            params = {'symbol': 'FTNUSDT', 'limit': 1}
            response = requests.get(api_url + method, params)
            response.raise_for_status()
            bids = response.json().get('bids')
            if bids:
                current_price = float(bids[0][0])
                with lock:
                    if previous_price:
                        change = ((current_price - previous_price) / previous_price) * 100
                    else:
                        change = 0
                    if abs(change) >= 0.01:
                        message = (
                            f"🔔 <b>Изменение курса!</b>\n"
                            f"Обнаружено по: {'стакану' if 'order' in change_var_name else 'сделкам'}\n"
                            f"Временной промежуток: <i>{mapper[change_var_name]}</i>\n"
                            f"Изменение: <b>{change:.2f}%</b>\n"
                        )
                        send_telegram_notification(message, change_var_name)
                    globals()[storage_var_name] = current_price
                    globals()[change_var_name] = change
                previous_price = current_price
        except Exception as e:
            print(f"Error fetching price for {storage_var_name}: {e}")
        time.sleep(interval)


def main():
    threading.Thread(target=fetch_order_price, args=(10, 'last_order_price_10sec', 'change_order_10sec'),
                     daemon=True).start()
    threading.Thread(target=fetch_order_price, args=(30, 'last_order_price_30sec', 'change_order_30sec'),
                     daemon=True).start()
    threading.Thread(target=fetch_order_price, args=(60, 'last_order_price_1min', 'change_order_1min'),
                     daemon=True).start()
    threading.Thread(target=fetch_order_price, args=(300, 'last_order_price_5min', 'change_order_5min'),
                     daemon=True).start()

    threading.Thread(target=fetch_trade_price, args=(10, 'last_trade_price_10sec', 'change_trade_10sec'),
                     daemon=True).start()
    threading.Thread(target=fetch_trade_price, args=(30, 'last_trade_price_30sec', 'change_trade_30sec'),
                     daemon=True).start()
    threading.Thread(target=fetch_trade_price, args=(60, 'last_trade_price_1min', 'change_trade_1min'),
                     daemon=True).start()
    threading.Thread(target=fetch_trade_price, args=(300, 'last_trade_price_5min', 'change_trade_5min'),
                     daemon=True).start()

    while True:
        with lock:
            print('still working...')
        time.sleep(5)


if __name__ == '__main__':
    main()
