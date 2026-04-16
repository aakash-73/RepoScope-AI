# app/models/repo_model.py
from datetime import datetime

class RepoModel:
    def __init__(self, name, github_url):
        self.name = name
        self.github_url = github_url
        self.primary_language = None
        self.status = "cloned"
        self.created_at = datetime.utcnow()
        self.last_analyzed_at = None

    def to_dict(self):
        return {
            "name": self.name,
            "github_url": self.github_url,
            "primary_language": self.primary_language,
            "status": self.status,
            "created_at": self.created_at,
            "last_analyzed_at": self.last_analyzed_at
        }

