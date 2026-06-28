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

    PG_HOST: str = os.getenv("PG_HOST", os.getenv("MYSQL_HOST", "127.0.0.1"))
    PG_PORT: str = os.getenv("PG_PORT", "5432")
    PG_USER: str = os.getenv("PG_USER", os.getenv("MYSQL_USER", "postgres"))
    PG_PASSWORD: str = os.getenv("PG_PASSWORD", os.getenv("MYSQL_PASSWORD", ""))
    PG_DATABASE: str = os.getenv("PG_DATABASE", os.getenv("MYSQL_DATABASE", "labelhub_agent"))

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
            f"postgresql+psycopg2://{self.PG_USER}:{self.PG_PASSWORD}"
            f"@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DATABASE}"
        )

    @property
    def rabbitmq_url(self) -> str:
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/%2F"
        )


config = Config()