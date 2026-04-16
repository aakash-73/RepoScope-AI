from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    global client, db
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DB_NAME]

    await db.repositories.create_index("repo_id", unique=True)
    await db.repositories.create_index("unique_key", unique=True)

    await db.files.create_index(
        [("repo_id", 1), ("path", 1)],
        unique=True,
        name="repo_file_unique_index",
    )

    await db.repo_understandings.create_index(
        "repo_id",
        unique=True,
        name="repo_understanding_unique_index",
    )

    await db.file_explanations.create_index(
        [("repo_id", 1), ("path", 1)],
        unique=True,
        name="file_explanation_unique_index",
    )

    await db.repo_chat_history.create_index(
        "repo_id", unique=True, name="chat_history_repo_index"
    )

    await db.language_registry.create_index(
        "key", unique=True, name="language_registry_key_index"
    )
    await db.language_registry.create_index(
        [("category", 1), ("sub_category", 1)],
        name="language_registry_cat_sub_index",
    )

    # Pre-analysis indexes
    await db.node_analysis.create_index([("repo_id", 1), ("file_path", 1)], unique=True)
    await db.node_analysis.create_index([("repo_id", 1), ("status", 1)])
    await db.repo_analysis.create_index([("repo_id", 1)], unique=True)

    print("Connected to MongoDB Atlas")


async def close_db():
    global client
    if client:
        client.close()
        print("MongoDB connection closed")


def get_db():
    if db is None:
        raise RuntimeError(
            "Database not initialized. Ensure connect_db() has been called "
            "during application startup before handling any requests."
        )
    return db
