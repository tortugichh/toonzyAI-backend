import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Теперь импортируем модули
try:
    from sqlalchemy import create_engine
    from db.avatar_repository import Base, DATABASE_URL
    from dotenv import load_dotenv
    
    # Загружаем переменные окружения
    load_dotenv()
    
    def init_db():
        """Initialize database tables."""
        database_url = os.getenv("DATABASE_URL") or DATABASE_URL
        
        if not database_url:
            print("ERROR: DATABASE_URL not found in environment variables")
            print("Please check your .env file or environment variables")
            return False
        
        try:
            print(f"Connecting to database...")
            engine = create_engine(database_url, echo=True)
            
            print("Creating tables...")
            Base.metadata.create_all(engine)
            
            print("Database tables created successfully!")
            return True
            
        except Exception as e:
            print(f"Error creating database tables: {e}")
            return False

    if __name__ == "__main__":
        success = init_db()
        if success:
            print("✅ Database initialization completed successfully!")
        else:
            print("❌ Database initialization failed!")
            sys.exit(1)
            
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this script from the project root directory")
    print("Or use: python -m db.init_db")
    sys.exit(1)