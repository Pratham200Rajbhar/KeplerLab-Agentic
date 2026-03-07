import asyncio
import httpx
import json

async def run():
    async with httpx.AsyncClient() as client:
        # Create a user in sqlite or use an existing one
        user_id = "00000000-0000-0000-0000-000000000000"
        import sqlite3
        conn = sqlite3.connect('/disk1/KeplerLab_Agentic/backend/prisma/dev.db')
        c = conn.cursor()
        c.execute("SELECT id FROM users LIMIT 1")
        res = c.fetchone()
        if res:
            user_id = res[0]
            
        print(f"Using user {user_id}")
        
        # We need an access token! Wait, backend API has protection.
        # Can we just simulate the chat service directly?
        import sys
        sys.path.append("/disk1/KeplerLab_Agentic/backend")
        from app.routes.chat import _route_pure_llm
        from app.models.chat import ChatRequest
        from app.models.user import User
        import time
        from types import SimpleNamespace
        
        req = ChatRequest(notebook_id=user_id, message="hii", stream=True)
        # Mock user
        class DummyUser:
            id = user_id
        
        user = DummyUser()
        
        resp = await _route_pure_llm(req, "test_session", user, time.time())
        print(resp)
        # It's a StreamingResponse. Let's consume it.
        async for chunk in resp.body_iterator:
            print(chunk)

asyncio.run(run())
