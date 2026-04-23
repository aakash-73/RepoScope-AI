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

    await db.files.create_index("exports")
    await db.files.create_index("imports")
    await db.files.create_index(
        [("path", "text"), ("content", "text")],
        language_override="dummy_language"
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
    await db.node_analysis.create_index("analysis.architectural_role")
    await db.node_analysis.create_index("analysis.functional_categories")
    await db.node_analysis.create_index("analysis.key_patterns")
    # Knowledge Graph indexes
    await db.kg_nodes.create_index([("repo_id", 1), ("id", 1)], unique=True)
    await db.kg_nodes.create_index([("repo_id", 1), ("type", 1)])
    await db.kg_edges.create_index([("repo_id", 1), ("source", 1)])
    await db.kg_edges.create_index([("repo_id", 1), ("target", 1)])
    await db.kg_edges.create_index([("repo_id", 1), ("relation", 1)])

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
