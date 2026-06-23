import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class OpenAIService:
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return cls._client

    @classmethod
    def get_embedding(cls, text: str):
        client = cls.get_client()
        response = client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding