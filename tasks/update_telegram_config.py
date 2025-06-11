import os
import requests
import datetime
import sqlite3
from time import sleep
from sqlalchemy.sql import text
from database.base import Session, engine
from logger import logger



MARZBAN_API_HOST = os.getenv("MARZBAN_API_HOST")
MARZBAN_ADMIN_USERNAME = os.getenv("MARZBAN_ADMIN_USERNAME")
MARZBAN_ADMIN_PASSWORD = os.getenv("MARZBAN_ADMIN_PASSWORD")

ACCESS_TOKEN = None

def get_access_token():
    global ACCESS_TOKEN
    url = f"{MARZBAN_API_HOST}/api/admin/token"
    data = {
        "username": MARZBAN_ADMIN_USERNAME,
        "password": MARZBAN_ADMIN_PASSWORD,
        "grant_type": "password"
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        ACCESS_TOKEN = response.json().get("access_token")
        return ACCESS_TOKEN
    return None

def fetch_marzban_users():
    global ACCESS_TOKEN
    if not ACCESS_TOKEN:
        ACCESS_TOKEN = get_access_token()
        if not ACCESS_TOKEN:
            return None
    url = f"{MARZBAN_API_HOST}/api/users"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()["users"]
    elif response.status_code == 401:
        ACCESS_TOKEN = get_access_token()
        return fetch_marzban_users()
    else:
        return None

def fetch_marzban_hosts():
    conn = sqlite3.connect('db/marzban_db.sqlite3')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hosts")
    data = cursor.fetchall()
    conn.close()
    return data

def update_telegram_config():
    users = fetch_marzban_users()
    if not users:
        return

    session = Session()
    try:
        for user in users:
            telegram_id = user["username"]
            vless_links = user.get("links", [])
            current_time = datetime.datetime.now()

            user_exists = session.execute(
                text("SELECT COUNT(*) FROM telegram_users WHERE telegram_user_id = :telegram_id"),
                {"telegram_id": telegram_id}
            ).scalar()

            if not user_exists:
                continue

            session.execute(
                text("DELETE FROM telegram_users_configurations WHERE telegram_user_id = :telegram_id"),
                {"telegram_id": telegram_id}
            )

            for vless_link in vless_links:
                session.execute(
                    text("""
                        INSERT INTO telegram_users_configurations 
                        (telegram_user_id, vless_link, created_at, updated_at) 
                        VALUES (:telegram_id, :vless_link, :created_at, :updated_at)
                    """),
                    {
                        "telegram_id": telegram_id,
                        "vless_link": vless_link,
                        "created_at": current_time,
                        "updated_at": current_time
                    }
                )

        session.commit()
    except Exception as e:
        session.rollback()
    finally:
        session.close()

def compare_selected_columns(list1, list2, column_indexes):
    """
    Compares selected columns from two lists of tuples.
    
    Args:
        list1 (list): First list of tuples (e.g., rows from DB1).
        list2 (list): Second list of tuples (e.g., rows from DB2).
        column_indexes (list): Indexes of columns to compare, e.g., [1] or [1, 2].

    Returns:
        bool: True if selected columns are equal, False otherwise.
    """
    def extract_columns(rows):
        return sorted([tuple(row[i] for i in column_indexes) for row in rows])

    return extract_columns(list1) == extract_columns(list2)

def sync_hosts():
    print("🔄 Sync started")

    marzban_hosts = fetch_marzban_hosts()
    session = Session()
    try:
        db_hosts = session.execute(text("SELECT * FROM hosts")).fetchall()
        db_hosts = [tuple(row) for row in db_hosts]

        # Compare by 'remark' only (column index 1)
        if not compare_selected_columns(marzban_hosts, db_hosts, [1]):
            print("🗑️ Deleting old hosts...")
            session.execute(text("DELETE FROM hosts"))

            insert_query = text("""
                INSERT INTO hosts (
                    id, remark, address, port, inbound_tag, sni, host, security, alpn,
                    fingerprint, allowinsecure, is_disabled, path, mux_enable,
                    fragment_setting, random_user_agent, noise_setting, use_sni_as_host
                ) VALUES (
                    :id, :remark, :address, :port, :inbound_tag, :sni, :host, :security, :alpn,
                    :fingerprint, :allowinsecure, :is_disabled, :path, :mux_enable,
                    :fragment_setting, :random_user_agent, :noise_setting, :use_sni_as_host
                )
            """)

            for host in marzban_hosts:
                host_dict = {
                    "id": host[0], "remark": host[1], "address": host[2], "port": host[3],
                    "inbound_tag": host[4], "sni": host[5], "host": host[6], "security": host[7],
                    "alpn": host[8], "fingerprint": host[9], "allowinsecure": host[10],
                    "is_disabled": host[11], "path": host[12], "mux_enable": host[13],
                    "fragment_setting": host[14], "random_user_agent": host[15],
                    "noise_setting": host[16], "use_sni_as_host": host[17]
                }
                session.execute(insert_query, host_dict)
                print(f"➕ Host inserted: {host_dict['remark']}")

            session.commit()
            print("✅ Hosts updated in database.")
            print("⏳ Updating Telegram configurations...")
            update_telegram_config()
        else:
            print("✅ No changes in host data.")
    except Exception as e:
        session.rollback()
        print(f"❌ Host Sync Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Sync script started...")
    while True:
        sync_hosts()
        logger.info("Sleeping for 20 seconds before next sync...")
        sleep(20)
