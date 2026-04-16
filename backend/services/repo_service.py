# app/services/repo_service.py
import requests
from io import BytesIO
from zipfile import ZipFile
from database import get_database
from models.repo_model import RepoModel
from analysis.import_extractor import detect_language

# Only allow real source code files
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".java", ".go", ".rb", ".cs",
    ".cpp", ".c", ".h", ".hpp"
}

async def create_repository(github_url: str):
    db = get_database()

    # Extract owner and repo name
    parts = github_url.rstrip("/").split("/")
    owner = parts[-2]
    repo_name = parts[-1]

    # 1️⃣ Get repo metadata
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}"
    repo_response = requests.get(api_url)
    repo_response.raise_for_status()

    repo_data = repo_response.json()
    default_branch = repo_data["default_branch"]

    # 2️⃣ Download correct branch zip
    zip_url = f"https://codeload.github.com/{owner}/{repo_name}/zip/refs/heads/{default_branch}"
    zip_response = requests.get(zip_url)
    zip_response.raise_for_status()

    repo_files = []

    with ZipFile(BytesIO(zip_response.content)) as zip_file:
        for file_info in zip_file.infolist():
            if file_info.is_dir():
                continue

            full_path = file_info.filename

            # Remove root folder prefix (GitHub zip includes repo-name-branch/)
            path_parts = full_path.split("/", 1)
            if len(path_parts) < 2:
                continue

            relative_path = path_parts[1]

            # Skip .git and hidden folders
            if relative_path.startswith(".") or "/." in relative_path:
                continue

            # Check extension
            if "." not in relative_path:
                continue

            ext = "." + relative_path.split(".")[-1].lower()
            if ext not in CODE_EXTENSIONS:
                continue

            try:
                content = zip_file.read(file_info.filename).decode("utf-8", errors="ignore")
            except Exception:
                continue  # skip unreadable files

            file_name = relative_path.split("/")[-1]
            language = detect_language(file_name)

            repo_files.append({
                "file_name": file_name,
                "file_path": relative_path.replace("\\", "/"),
                "language": language,
                "content": content
            })

    # 🚨 If no files found, stop early
    if not repo_files:
        raise Exception("No source code files found in this repository.")

    # 3️⃣ Store repo metadata
    repo = RepoModel(name=repo_name, github_url=github_url)
    result = await db.repositories.insert_one(repo.to_dict())
    repo_id = result.inserted_id

    # 4️⃣ Attach repo_id to each file
    for f in repo_files:
        f["repo_id"] = repo_id

    await db.files.insert_many(repo_files)

    return str(repo_id)

