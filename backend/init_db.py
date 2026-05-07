from database import engine, Base
import models

print("Connecting to Docker Postgres and creating tables...")
try:
    Base.metadata.create_all(bind=engine)
    print("Success! Tables created: users, projects.")
except Exception as e:
    print(f"Error: {e}")