from app.core.database import SessionLocal
from app.repositories.user_repository import UserRepository

db = SessionLocal()

repo = UserRepository(db)

print(repo.get_by_email("test@test.com"))