from database import engine, Base, SessionLocal
import models

print("Connecting to PostgreSQL...")

try:
    # This command tells SQLAlchemy to generate the SQL to create your tables
    models.Base.metadata.create_all(bind=engine)
    print("Success! Created 'users' and 'projects' tables in the database.")
    
    # Let's test inserting a dummy user
    db = SessionLocal()
    
    # Check if user already exists to avoid errors on multiple runs
    existing_user = db.query(models.User).filter(models.User.email == "founder@docusync.ai").first()
    
    if not existing_user:
        print("Creating dummy user and project...")
        test_user = models.User(email="founder@docusync.ai")
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        test_project = models.Project(name="DocuSync Core API", owner_id=test_user.id)
        db.add(test_project)
        db.commit()
        
        print(f"Inserted: User '{test_user.email}' with Project '{test_project.name}'")
    else:
        print("Dummy user already exists. Database is working perfectly!")
        
    db.close()
    
except Exception as e:
    print(f"\n--- ERROR CAUGHT ---")
    print(e)