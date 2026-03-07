import requests
import sqlite3

def test_chat():
    conn = sqlite3.connect('/disk1/KeplerLab_Agentic/backend/prisma/dev.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users LIMIT 1')
    res = cursor.fetchone()
    if not res:
        print("No user found")
        return
    user_id = res[0]
    
    # We need a token, but the DB has refresh_tokens, not active access tokens, 
    # and /api/chat requires Bearer token! 
    # Actually wait! The user screenshot shows the UI is working, so the backend IS running and receiving requests.
    print(f"User ID found: {user_id}")
    
test_chat()
