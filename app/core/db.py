"""Single shared Prisma client.

The client is connected/disconnected by the FastAPI lifespan handler in
`app.main`. Routers import `db` and use it directly; Prisma issues
parameterised queries under the hood (a key SQL-injection mitigation).
"""
from prisma import Prisma

db = Prisma(auto_register=True)
