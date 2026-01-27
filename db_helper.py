import os
import mysql.connector
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

def get_db_connection():
    """Membuat koneksi ke database Kawalo."""
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASS', ''),
            database=os.getenv('DB_NAME')
        )
        return conn
    except Exception as e:
        print(f"DB Error: {e}")
        return None

def get_active_users():
    """Mengambil daftar user dari tabel tkuser dengan status dan last activity."""
    conn = get_db_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    # Query dari tabel tkuser yang memiliki tracking last activity
    query = """
        SELECT 
            tu.UserId,
            tu.UserName,
            tu.UserEmail as Email,
            tu.UserDuty,
            tu.UserDutyDT,
            tu.UserStateDT,
            tu.MyLatLongDT,
            tu.UserProfilePic,
            tug.GroupUID,
            tug.Roles as Role
        FROM tkuser tu
        LEFT JOIN tkusergroup tug ON tu.UserEmail = tug.Email
        ORDER BY 
            CASE WHEN tu.UserDuty = 'On Duty' THEN 0 ELSE 1 END,
            COALESCE(tu.UserStateDT, tu.MyLatLongDT) DESC
        LIMIT 30
    """
    
    try:
        cursor.execute(query)
        result = cursor.fetchall()
        conn.close()
        
        # Tambahkan computed fields untuk online status
        now = datetime.now()
        for user in result:
            # Ambil last activity dari UserStateDT atau MyLatLongDT
            last_activity = user.get('UserStateDT') or user.get('MyLatLongDT')
            user['LastActivity'] = last_activity
            
            # Tentukan status online (aktif dalam 5 menit terakhir)
            if last_activity:
                time_diff = now - last_activity
                if time_diff < timedelta(minutes=5):
                    user['OnlineStatus'] = 'Online'
                elif time_diff < timedelta(minutes=30):
                    user['OnlineStatus'] = 'Away'
                else:
                    user['OnlineStatus'] = 'Offline'
            else:
                user['OnlineStatus'] = 'Unknown'
            
        return result
    except Exception as e:
        print(f"Query Error: {e}")
        return []

def get_msuser_list():
    """Mengambil daftar admin user dari tabel msuser."""
    conn = get_db_connection()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT 
            Email,
            Roles as Role,
            GroupId
        FROM msuser 
        ORDER BY Email ASC 
        LIMIT 20
    """
    
    try:
        cursor.execute(query)
        result = cursor.fetchall()
        conn.close()
        return result
    except Exception as e:
        print(f"Query Error: {e}")
        return []


