import pymysql
import pymysql.cursors
from contextlib import contextmanager
from config import Config

def get_connection():
    """Create and return a new MySQL connection with dictionary cursor and SSL support."""
    ssl_config = None
    if Config.DB_SSL_ENABLED:
        ssl_config = {}
        if Config.DB_SSL_CA:
            ssl_config['ca'] = Config.DB_SSL_CA
        else:
            ssl_config['check_hostname'] = False

    conn_kwargs = {
        'host': Config.DB_HOST,
        'port': Config.DB_PORT,
        'user': Config.DB_USER,
        'password': Config.DB_PASSWORD,
        'database': Config.DB_NAME,
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor,
        'autocommit': False,
        'connect_timeout': 10
    }
    if ssl_config is not None:
        conn_kwargs['ssl'] = ssl_config

    return pymysql.connect(**conn_kwargs)

@contextmanager
def get_db():
    """
    Context manager for database connections and transactions.
    Automatically commits on success or rolls back on exception.
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def execute_query(query, params=None, fetch_all=True, fetch_one=False):
    """
    Execute a parameterized SQL query safely.
    Returns:
        - List of dicts if fetch_all is True
        - Single dict if fetch_one is True
        - Last insert ID or affected row count otherwise
    """
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            if fetch_one:
                return cursor.fetchone()
            if fetch_all:
                return cursor.fetchall()
            return cursor.lastrowid or cursor.rowcount

def execute_non_query(query, params=None):
    """
    Execute an INSERT, UPDATE, or DELETE parameterized query.
    Returns the affected rows count and last insert id.
    """
    with get_db() as conn:
        with conn.cursor() as cursor:
            affected = cursor.execute(query, params or ())
            return {
                'affected_rows': affected,
                'last_insert_id': cursor.lastrowid
            }
