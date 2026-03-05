"""
db_connector.py — Modul Database Connector untuk KieroOPS
Menangani koneksi dan eksekusi query ke MySQL dan PostgreSQL
menggunakan Connection String URI (RFC 3986).
"""

import re
from urllib.parse import urlparse, unquote


def get_connection_string(service_config):
    """
    Membaca Connection String URI langsung dari config database.
    Field: database.connection_url (e.g. mysql://root@localhost:3306/kawalo_db)
    
    Returns:
        str: Connection string URI atau None jika tidak ditemukan.
    """
    db_config = service_config.get("database", {})
    return db_config.get("connection_url", "") or None


def parse_connection_uri(uri_string):
    """
    Parse Connection String URI menjadi komponen koneksi.
    Supports: mysql://user:pass@host:port/dbname
              postgresql://user:pass@host:port/dbname
    
    Returns:
        dict: {scheme, username, password, host, port, database}
    """
    parsed = urlparse(uri_string)
    
    scheme = parsed.scheme.lower()
    # Normalize scheme aliases
    if scheme in ('mysql', 'mysql+pymysql', 'mariadb'):
        scheme = 'mysql'
    elif scheme in ('postgresql', 'postgres', 'postgresql+psycopg2'):
        scheme = 'postgresql'
    
    return {
        "scheme": scheme,
        "username": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "host": parsed.hostname or "localhost",
        "port": parsed.port or (3306 if scheme == "mysql" else 5432),
        "database": parsed.path.lstrip("/") if parsed.path else ""
    }


def is_read_only_query(query_string):
    """
    Memeriksa apakah query adalah read-only (SELECT, SHOW, DESCRIBE, EXPLAIN).
    Returns True jika query aman, False jika berbahaya.
    """
    cleaned = query_string.strip()
    cleaned = re.sub(r'^(--[^\n]*\n|/\*.*?\*/\s*)*', '', cleaned, flags=re.DOTALL)
    cleaned = cleaned.strip().upper()
    
    allowed_prefixes = ("SELECT", "SHOW", "DESCRIBE", "DESC", "EXPLAIN")
    return cleaned.startswith(allowed_prefixes)


def test_db_connection(service_config):
    """
    Test koneksi database — hanya buka dan tutup koneksi.
    
    Returns:
        dict: {"success": True, "message": "..."} atau {"success": False, "error": "..."}
    """
    db_config = service_config.get("database", {})
    engine = db_config.get("engine", "").lower()
    
    conn_string = get_connection_string(service_config)
    if not conn_string:
        return {"success": False, "error": f"Connection string not found. Set '{db_config.get('connection_env_key', '?')}' in the service .env file."}
    
    try:
        parsed = parse_connection_uri(conn_string)
        
        if engine == "mysql" or parsed["scheme"] == "mysql":
            return _test_mysql(parsed)
        elif engine == "postgresql" or parsed["scheme"] == "postgresql":
            return _test_postgresql(parsed)
        else:
            return {"success": False, "error": f"Unsupported database engine: {engine}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _test_mysql(parsed):
    """Test koneksi MySQL."""
    try:
        import pymysql
    except ImportError:
        return {"success": False, "error": "pymysql not installed. Run: pip install pymysql"}
    
    try:
        conn = pymysql.connect(
            host=parsed["host"],
            port=parsed["port"],
            user=parsed["username"],
            password=parsed["password"],
            database=parsed["database"],
            connect_timeout=5
        )
        conn.close()
        return {"success": True, "message": f"Connection established successfully to {parsed['host']}:{parsed['port']}/{parsed['database']}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _test_postgresql(parsed):
    """Test koneksi PostgreSQL."""
    try:
        import psycopg2
    except ImportError:
        return {"success": False, "error": "psycopg2 not installed. Run: pip install psycopg2-binary"}
    
    try:
        conn = psycopg2.connect(
            host=parsed["host"],
            port=parsed["port"],
            user=parsed["username"],
            password=parsed["password"],
            dbname=parsed["database"],
            connect_timeout=5
        )
        conn.close()
        return {"success": True, "message": f"Connection established successfully to {parsed['host']}:{parsed['port']}/{parsed['database']}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_db_query(service_config, query_string):
    """
    Mengeksekusi query database dan mengembalikan hasil.
    Rows dikembalikan sebagai array-of-objects (untuk kompatibilitas AG Grid).
    
    Returns:
        dict: {"success": True, "columns": [...], "rows": [{...}, ...], "row_count": N}
              atau {"error": "..."}
    """
    db_config = service_config.get("database", {})
    engine = db_config.get("engine", "").lower()
    
    conn_string = get_connection_string(service_config)
    if not conn_string:
        return {"error": f"Connection string not found. Set '{db_config.get('connection_env_key', '?')}' in the service .env file."}
    
    # Read-only guard
    if not is_read_only_query(query_string):
        return {"error": "Only SELECT, SHOW, DESCRIBE, and EXPLAIN queries are allowed (read-only mode)"}
    
    try:
        parsed = parse_connection_uri(conn_string)
        
        if engine == "mysql" or parsed["scheme"] == "mysql":
            return _execute_mysql(parsed, query_string)
        elif engine == "postgresql" or parsed["scheme"] == "postgresql":
            return _execute_postgresql(parsed, query_string)
        else:
            return {"error": f"Unsupported database engine: {engine}"}
    except Exception as e:
        return {"error": str(e)}


def _execute_mysql(parsed, query_string):
    """Eksekusi query pada MySQL menggunakan pymysql."""
    try:
        import pymysql
    except ImportError:
        return {"error": "pymysql not installed. Run: pip install pymysql"}
    
    conn = None
    try:
        conn = pymysql.connect(
            host=parsed["host"],
            port=parsed["port"],
            user=parsed["username"],
            password=parsed["password"],
            database=parsed["database"],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.Cursor,
            connect_timeout=5,
            read_timeout=10
        )
        
        with conn.cursor() as cursor:
            cursor.execute(query_string)
            
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            raw_rows = cursor.fetchmany(500)
            
            # Convert to array-of-objects (AG Grid compatible)
            rows = []
            for row in raw_rows:
                row_dict = {}
                for i, val in enumerate(row):
                    col_name = columns[i] if i < len(columns) else f"col_{i}"
                    if val is None:
                        row_dict[col_name] = None
                    elif isinstance(val, bytes):
                        row_dict[col_name] = val.decode('utf-8', errors='replace')
                    else:
                        row_dict[col_name] = str(val)
                rows.append(row_dict)
            
            return {
                "success": True,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "truncated": cursor.rowcount > 500 if cursor.rowcount and cursor.rowcount > 0 else False
            }
    finally:
        if conn:
            conn.close()


def _execute_postgresql(parsed, query_string):
    """Eksekusi query pada PostgreSQL menggunakan psycopg2."""
    try:
        import psycopg2
    except ImportError:
        return {"error": "psycopg2 not installed. Run: pip install psycopg2-binary"}
    
    conn = None
    try:
        conn = psycopg2.connect(
            host=parsed["host"],
            port=parsed["port"],
            user=parsed["username"],
            password=parsed["password"],
            dbname=parsed["database"],
            connect_timeout=5
        )
        conn.set_session(readonly=True, autocommit=True)
        
        with conn.cursor() as cursor:
            cursor.execute(query_string)
            
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            raw_rows = cursor.fetchmany(500)
            
            rows = []
            for row in raw_rows:
                row_dict = {}
                for i, val in enumerate(row):
                    col_name = columns[i] if i < len(columns) else f"col_{i}"
                    if val is None:
                        row_dict[col_name] = None
                    elif isinstance(val, (bytes, memoryview)):
                        row_dict[col_name] = str(val)
                    else:
                        row_dict[col_name] = str(val)
                rows.append(row_dict)
            
            return {
                "success": True,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "truncated": cursor.rowcount > 500 if cursor.rowcount and cursor.rowcount > 0 else False
            }
    finally:
        if conn:
            conn.close()
