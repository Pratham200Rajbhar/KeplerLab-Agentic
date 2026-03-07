import requests
import sqlite3

# Get a user email from DB
conn = sqlite3.connect('/disk1/KeplerLab_Agentic/backend/prisma/dev.db')
c = conn.cursor()
c.execute("SELECT email FROM users LIMIT 1")
res = c.fetchone()
if not res:
    print("No users found")
    exit(1)
email = res[0]

# Now let's try to get a token. Wait, password is required. 
# We don't know the password.
print(f"User email: {email}")
