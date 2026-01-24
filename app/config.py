import os
from dotenv import load_dotenv

load_dotenv()

def get_env_variable(var_name: str) -> str:
    value = os.environ.get(var_name)
    if value is None:
        raise ValueError(f"Missing required environment variable: {var_name}")
    return value

ENV = os.getenv("ENV", "prod")
DATABASE_URL = get_env_variable("DATABASE_URL")
TEST_DATABASE_URL = get_env_variable("TEST_DATABASE_URL")
JWT_SECRET_KEY = get_env_variable("JWT_SECRET_KEY")
# JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
# JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", 60))