import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "root")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "labelhub_agent")

    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "127.0.0.1")
    RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")

    AI_AUDIT_BASE_URL: str = os.getenv("AI_AUDIT_BASE_URL", "")
    AI_AUDIT_API_KEY: str = os.getenv("AI_AUDIT_API_KEY", "")
    AI_AUDIT_MODEL: str = os.getenv("AI_AUDIT_MODEL", "gpt-4o-mini")

    @property
    def has_llm(self) -> bool:
        return bool(self.AI_AUDIT_API_KEY and self.AI_AUDIT_BASE_URL and self.AI_AUDIT_MODEL)

    @property
    def db_url(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"
        )

    @property
    def rabbitmq_url(self) -> str:
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/%2F"
        )


config = Config()