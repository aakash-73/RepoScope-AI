import asyncio
import logging
from database import connect_db, close_db, get_db

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
_log = logging.getLogger(__name__)

EXTENSIONS = [
    # Frontend
    {"ext": ".js",        "category": "frontend", "sub": "javascript",  "unambiguous": True},
    {"ext": ".mjs",       "category": "frontend", "sub": "javascript",  "unambiguous": True},
    {"ext": ".cjs",       "category": "frontend", "sub": "javascript",  "unambiguous": True},
    {"ext": ".jsx",       "category": "frontend", "sub": "react",       "unambiguous": True},
    {"ext": ".ts",        "category": "frontend", "sub": "typescript",  "unambiguous": True},
    {"ext": ".tsx",       "category": "frontend", "sub": "react",       "unambiguous": True},
    {"ext": ".vue",       "category": "frontend", "sub": "vue",         "unambiguous": True},
    {"ext": ".svelte",    "category": "frontend", "sub": "svelte",      "unambiguous": True},
    {"ext": ".astro",     "category": "frontend", "sub": "astro",       "unambiguous": True},
    {"ext": ".elm",       "category": "frontend", "sub": "elm",         "unambiguous": True},
    {"ext": ".coffee",    "category": "frontend", "sub": "coffeescript","unambiguous": True},
    # HTML
    {"ext": ".html",      "category": "html",     "sub": "html",        "unambiguous": False},
    {"ext": ".htm",       "category": "html",     "sub": "html",        "unambiguous": False},
    {"ext": ".xhtml",     "category": "html",     "sub": "html",        "unambiguous": False},
    {"ext": ".jinja",     "category": "html",     "sub": "jinja",       "unambiguous": False},
    {"ext": ".jinja2",    "category": "html",     "sub": "jinja",       "unambiguous": False},
    {"ext": ".j2",        "category": "html",     "sub": "jinja",       "unambiguous": False},
    {"ext": ".njk",       "category": "html",     "sub": "nunjucks",    "unambiguous": False},
    {"ext": ".hbs",       "category": "html",     "sub": "handlebars",  "unambiguous": False},
    {"ext": ".mustache",  "category": "html",     "sub": "mustache",    "unambiguous": False},
    {"ext": ".ejs",       "category": "html",     "sub": "ejs",         "unambiguous": False},
    {"ext": ".pug",       "category": "html",     "sub": "pug",         "unambiguous": False},
    {"ext": ".haml",      "category": "html",     "sub": "haml",        "unambiguous": False},
    {"ext": ".erb",       "category": "html",     "sub": "erb",         "unambiguous": False},
    {"ext": ".php",       "category": "html",     "sub": "php",         "unambiguous": False},
    # CSS
    {"ext": ".css",       "category": "css",      "sub": "css",         "unambiguous": True},
    {"ext": ".scss",      "category": "css",      "sub": "scss",        "unambiguous": True},
    {"ext": ".sass",      "category": "css",      "sub": "sass",        "unambiguous": True},
    {"ext": ".less",      "category": "css",      "sub": "less",        "unambiguous": True},
    {"ext": ".styl",      "category": "css",      "sub": "stylus",      "unambiguous": True},
    {"ext": ".pcss",      "category": "css",      "sub": "postcss",     "unambiguous": True},
    # Backend — Python
    {"ext": ".py",        "category": "backend",  "sub": "python",      "unambiguous": True},
    {"ext": ".pyi",       "category": "backend",  "sub": "python",      "unambiguous": True},
    {"ext": ".pyw",       "category": "backend",  "sub": "python",      "unambiguous": True},
    # Backend — Ruby
    {"ext": ".rb",        "category": "backend",  "sub": "ruby",        "unambiguous": True},
    {"ext": ".rake",      "category": "backend",  "sub": "ruby",        "unambiguous": True},
    # Backend — JVM
    {"ext": ".java",      "category": "backend",  "sub": "java",        "unambiguous": True},
    {"ext": ".kt",        "category": "backend",  "sub": "kotlin",      "unambiguous": True},
    {"ext": ".kts",       "category": "backend",  "sub": "kotlin",      "unambiguous": True},
    {"ext": ".groovy",    "category": "backend",  "sub": "groovy",      "unambiguous": True},
    {"ext": ".scala",     "category": "backend",  "sub": "scala",       "unambiguous": True},
    {"ext": ".clj",       "category": "backend",  "sub": "clojure",     "unambiguous": True},
    # Backend — Go
    {"ext": ".go",        "category": "backend",  "sub": "go",          "unambiguous": True},
    # Backend — Rust
    {"ext": ".rs",        "category": "backend",  "sub": "rust",        "unambiguous": True},
    # Backend — C/C++
    {"ext": ".c",         "category": "backend",  "sub": "c",           "unambiguous": True},
    {"ext": ".h",         "category": "backend",  "sub": "c",           "unambiguous": True},
    {"ext": ".cpp",       "category": "backend",  "sub": "cpp",         "unambiguous": True},
    {"ext": ".cc",        "category": "backend",  "sub": "cpp",         "unambiguous": True},
    {"ext": ".cxx",       "category": "backend",  "sub": "cpp",         "unambiguous": True},
    {"ext": ".hpp",       "category": "backend",  "sub": "cpp",         "unambiguous": True},
    {"ext": ".hxx",       "category": "backend",  "sub": "cpp",         "unambiguous": True},
    # Backend — C#
    {"ext": ".cs",        "category": "backend",  "sub": "csharp",      "unambiguous": True},
    # Backend — other
    {"ext": ".pl",        "category": "backend",  "sub": "perl",        "unambiguous": True},
    {"ext": ".pm",        "category": "backend",  "sub": "perl",        "unambiguous": True},
    {"ext": ".ex",        "category": "backend",  "sub": "elixir",      "unambiguous": True},
    {"ext": ".exs",       "category": "backend",  "sub": "elixir",      "unambiguous": True},
    {"ext": ".erl",       "category": "backend",  "sub": "erlang",      "unambiguous": True},
    {"ext": ".hrl",       "category": "backend",  "sub": "erlang",      "unambiguous": True},
    {"ext": ".lua",       "category": "backend",  "sub": "lua",         "unambiguous": True},
    {"ext": ".hs",        "category": "backend",  "sub": "haskell",     "unambiguous": True},
    {"ext": ".lhs",       "category": "backend",  "sub": "haskell",     "unambiguous": True},
    {"ext": ".sh",        "category": "backend",  "sub": "shell",       "unambiguous": True},
    {"ext": ".bash",      "category": "backend",  "sub": "shell",       "unambiguous": True},
    {"ext": ".zsh",       "category": "backend",  "sub": "shell",       "unambiguous": True},
    {"ext": ".fish",      "category": "backend",  "sub": "shell",       "unambiguous": True},
    {"ext": ".ps1",       "category": "backend",  "sub": "powershell",  "unambiguous": True},
    {"ext": ".psm1",      "category": "backend",  "sub": "powershell",  "unambiguous": True},
    # Database
    {"ext": ".sql",       "category": "database", "sub": "sql",         "unambiguous": False},
    {"ext": ".ddl",       "category": "database", "sub": "sql",         "unambiguous": False},
    {"ext": ".psql",      "category": "database", "sub": "sql",         "unambiguous": False},
    {"ext": ".prisma",    "category": "database", "sub": "prisma",      "unambiguous": False},
    {"ext": ".graphql",   "category": "database", "sub": "graphql",     "unambiguous": False},
    {"ext": ".gql",       "category": "database", "sub": "graphql",     "unambiguous": False},
    # Mobile
    {"ext": ".swift",     "category": "mobile",   "sub": "swift",       "unambiguous": True},
    {"ext": ".m",         "category": "mobile",   "sub": "objc",        "unambiguous": True},
    {"ext": ".mm",        "category": "mobile",   "sub": "objc",        "unambiguous": True},
    {"ext": ".dart",      "category": "mobile",   "sub": "dart",        "unambiguous": True},
    {"ext": ".xaml",      "category": "mobile",   "sub": "xaml",        "unambiguous": False},
    # DevOps
    {"ext": ".tf",        "category": "devops",   "sub": "terraform",   "unambiguous": False},
    {"ext": ".tfvars",    "category": "devops",   "sub": "terraform",   "unambiguous": False},
    {"ext": ".hcl",       "category": "devops",   "sub": "hcl",         "unambiguous": False},
    {"ext": ".dockerfile","category": "devops",   "sub": "dockerfile",  "unambiguous": False},
    {"ext": ".nix",       "category": "devops",   "sub": "nix",         "unambiguous": False},
    # Config
    {"ext": ".json",      "category": "config",   "sub": "json",        "unambiguous": False},
    {"ext": ".json5",     "category": "config",   "sub": "json",        "unambiguous": False},
    {"ext": ".jsonc",     "category": "config",   "sub": "json",        "unambiguous": False},
    {"ext": ".toml",      "category": "config",   "sub": "toml",        "unambiguous": False},
    {"ext": ".yaml",      "category": "config",   "sub": "yaml",        "unambiguous": False},
    {"ext": ".yml",       "category": "config",   "sub": "yaml",        "unambiguous": False},
    {"ext": ".ini",       "category": "config",   "sub": "ini",         "unambiguous": False},
    {"ext": ".cfg",       "category": "config",   "sub": "ini",         "unambiguous": False},
    {"ext": ".conf",      "category": "config",   "sub": "conf",        "unambiguous": False},
    {"ext": ".env",       "category": "config",   "sub": "env",         "unambiguous": False},
    {"ext": ".lock",      "category": "config",   "sub": "lockfile",    "unambiguous": False},
    {"ext": ".gradle",    "category": "config",   "sub": "gradle",      "unambiguous": False},
    # Docs
    {"ext": ".md",        "category": "docs",     "sub": "markdown",    "unambiguous": False},
    {"ext": ".mdx",       "category": "docs",     "sub": "markdown",    "unambiguous": False},
    {"ext": ".rst",       "category": "docs",     "sub": "rst",         "unambiguous": False},
    {"ext": ".txt",       "category": "docs",     "sub": "text",        "unambiguous": False},
    {"ext": ".tex",       "category": "docs",     "sub": "latex",       "unambiguous": False},
    # Shader
    {"ext": ".glsl",      "category": "shader",   "sub": "glsl",        "unambiguous": False},
    {"ext": ".vert",      "category": "shader",   "sub": "glsl",        "unambiguous": False},
    {"ext": ".frag",      "category": "shader",   "sub": "glsl",        "unambiguous": False},
    {"ext": ".hlsl",      "category": "shader",   "sub": "hlsl",        "unambiguous": False},
    {"ext": ".wgsl",      "category": "shader",   "sub": "wgsl",        "unambiguous": False},
    # Data
    {"ext": ".csv",       "category": "data",     "sub": "csv",         "unambiguous": False},
    {"ext": ".tsv",       "category": "data",     "sub": "csv",         "unambiguous": False},
    {"ext": ".xml",       "category": "data",     "sub": "xml",         "unambiguous": False},
    {"ext": ".proto",     "category": "data",     "sub": "protobuf",    "unambiguous": False},
]

NAMED_FILES = [
    {"name": "dockerfile",          "category": "devops",   "sub": "dockerfile"},
    {"name": "docker-compose.yml",  "category": "devops",   "sub": "docker-compose"},
    {"name": "docker-compose.yaml", "category": "devops",   "sub": "docker-compose"},
    {"name": ".dockerignore",       "category": "devops",   "sub": "dockerfile"},
    {"name": "makefile",            "category": "devops",   "sub": "makefile"},
    {"name": "rakefile",            "category": "backend",  "sub": "ruby"},
    {"name": "gemfile",             "category": "config",   "sub": "ruby-deps"},
    {"name": "gemfile.lock",        "category": "config",   "sub": "lockfile"},
    {"name": "package.json",        "category": "config",   "sub": "npm"},
    {"name": "package-lock.json",   "category": "config",   "sub": "lockfile"},
    {"name": "yarn.lock",           "category": "config",   "sub": "lockfile"},
    {"name": "pnpm-lock.yaml",      "category": "config",   "sub": "lockfile"},
    {"name": "cargo.toml",          "category": "config",   "sub": "rust-deps"},
    {"name": "cargo.lock",          "category": "config",   "sub": "lockfile"},
    {"name": "go.mod",              "category": "config",   "sub": "go-deps"},
    {"name": "go.sum",              "category": "config",   "sub": "lockfile"},
    {"name": "requirements.txt",    "category": "config",   "sub": "python-deps"},
    {"name": "pipfile",             "category": "config",   "sub": "python-deps"},
    {"name": "pipfile.lock",        "category": "config",   "sub": "lockfile"},
    {"name": "pyproject.toml",      "category": "config",   "sub": "python-deps"},
    {"name": "setup.py",            "category": "config",   "sub": "python-deps"},
    {"name": "setup.cfg",           "category": "config",   "sub": "python-deps"},
    {"name": "pubspec.yaml",        "category": "config",   "sub": "dart-deps"},
    {"name": "pubspec.lock",        "category": "config",   "sub": "lockfile"},
    {"name": "build.gradle",        "category": "config",   "sub": "gradle"},
    {"name": "build.gradle.kts",    "category": "config",   "sub": "gradle"},
    {"name": "pom.xml",             "category": "config",   "sub": "maven"},
    {"name": "tsconfig.json",       "category": "config",   "sub": "typescript"},
    {"name": "jsconfig.json",       "category": "config",   "sub": "javascript"},
    {"name": ".eslintrc",           "category": "config",   "sub": "eslint"},
    {"name": ".eslintrc.js",        "category": "config",   "sub": "eslint"},
    {"name": ".eslintrc.json",      "category": "config",   "sub": "eslint"},
    {"name": ".prettierrc",         "category": "config",   "sub": "prettier"},
    {"name": ".babelrc",            "category": "config",   "sub": "babel"},
    {"name": "vite.config.js",      "category": "config",   "sub": "vite"},
    {"name": "vite.config.ts",      "category": "config",   "sub": "vite"},
    {"name": "webpack.config.js",   "category": "config",   "sub": "webpack"},
    {"name": "next.config.js",      "category": "config",   "sub": "nextjs"},
    {"name": "next.config.ts",      "category": "config",   "sub": "nextjs"},
    {"name": "tailwind.config.js",  "category": "config",   "sub": "tailwind"},
    {"name": "tailwind.config.ts",  "category": "config",   "sub": "tailwind"},
    {"name": "readme.md",           "category": "docs",     "sub": "markdown"},
    {"name": "changelog.md",        "category": "docs",     "sub": "markdown"},
    {"name": "license",             "category": "docs",     "sub": "text"},
    {"name": "license.md",          "category": "docs",     "sub": "text"},
    {"name": ".gitignore",          "category": "config",   "sub": "gitignore"},
    {"name": ".gitattributes",      "category": "config",   "sub": "gitignore"},
    {"name": ".env",                "category": "config",   "sub": "env"},
    {"name": ".env.example",        "category": "config",   "sub": "env"},
    {"name": ".env.local",          "category": "config",   "sub": "env"},
]

FINGERPRINTS = [
    {
        "priority": 10,
        "pattern": r"import\s+['\"]package:flutter|runApp\s*\(|StatelessWidget|StatefulWidget|Widget\s+build|MaterialApp\s*\(|CupertinoApp\s*\(|Scaffold\s*\(",
        "category": "flutter", "sub": "flutter",
        "description": "Flutter framework",
    },
    {
        "priority": 20,
        "pattern": r"import\s+['\"]dart:|void\s+main\s*\(\s*\)|Future<|Stream<",
        "category": "mobile", "sub": "dart",
        "description": "Dart language",
    },
    {
        "priority": 30,
        "pattern": r"from\s+['\"]react['\"]|React\.createElement|ReactDOM\.render|useEffect\s*\(|useState\s*\(",
        "category": "frontend", "sub": "react",
        "description": "React framework",
    },
    {
        "priority": 40,
        "pattern": r"from\s+['\"]next/|getServerSideProps|getStaticProps|NextApiRequest",
        "category": "frontend", "sub": "nextjs",
        "description": "Next.js framework",
    },
    {
        "priority": 50,
        "pattern": r"<template>|createApp\s*\(|defineComponent\s*\(|from\s+['\"]vue['\"]",
        "category": "frontend", "sub": "vue",
        "description": "Vue framework",
    },
    {
        "priority": 60,
        "pattern": r"<script\s+lang=|export\s+let\s+\w+\s*;|on:click=|bind:value=",
        "category": "frontend", "sub": "svelte",
        "description": "Svelte framework",
    },
    {
        "priority": 70,
        "pattern": r"@Component\s*\(|@NgModule\s*\(|@Injectable|from\s+['\"]@angular",
        "category": "frontend", "sub": "angular",
        "description": "Angular framework",
    },
    {
        "priority": 80,
        "pattern": r"from\s+fastapi|FastAPI\s*\(|@app\.(get|post|put|delete|patch)\s*\(",
        "category": "backend", "sub": "fastapi",
        "description": "FastAPI framework",
    },
    {
        "priority": 90,
        "pattern": r"from\s+django\.|import\s+django|urlpatterns\s*=|models\.Model",
        "category": "backend", "sub": "django",
        "description": "Django framework",
    },
    {
        "priority": 100,
        "pattern": r"from\s+flask\s+import|Flask\s*\(__name__\)|@app\.route\s*\(",
        "category": "backend", "sub": "flask",
        "description": "Flask framework",
    },
    {
        "priority": 110,
        "pattern": r"require\s*\(['\"]express['\"]|express\s*\(\s*\)|router\.(get|post|put|delete)\s*\(",
        "category": "backend", "sub": "express",
        "description": "Express.js framework",
    },
    {
        "priority": 120,
        "pattern": r"@Controller\s*\(|@Module\s*\(|@Injectable\s*\(\)|from\s+['\"]@nestjs",
        "category": "backend", "sub": "nestjs",
        "description": "NestJS framework",
    },
    {
        "priority": 130,
        "pattern": r"namespace\s+App\\|use\s+Illuminate\\|Route::get\s*\(",
        "category": "backend", "sub": "laravel",
        "description": "Laravel framework",
    },
    {
        "priority": 140,
        "pattern": r"class\s+\w+\s*<\s*ApplicationController|ActiveRecord::Base|before_action\s*:",
        "category": "backend", "sub": "rails",
        "description": "Ruby on Rails",
    },
    {
        "priority": 150,
        "pattern": r"type\s+Query\s*\{|type\s+Mutation\s*\{|scalar\s+\w+",
        "category": "database", "sub": "graphql",
        "description": "GraphQL schema",
    },
    {
        "priority": 160,
        "pattern": r"model\s+\w+\s*\{|datasource\s+db\s*\{|generator\s+client",
        "category": "database", "sub": "prisma",
        "description": "Prisma schema",
    },
    {
        "priority": 170,
        "pattern": r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE\s+TABLE|ALTER\s+TABLE)\b",
        "category": "database", "sub": "sql",
        "description": "SQL statements",
        "flags": "IGNORECASE",
    },
    {
        "priority": 180,
        "pattern": r"^FROM\s+\w|^RUN\s+|^COPY\s+|^WORKDIR\s+|^EXPOSE\s+",
        "category": "devops", "sub": "dockerfile",
        "description": "Dockerfile instructions",
        "flags": "MULTILINE",
    },
    {
        "priority": 190,
        "pattern": r"on:\s*push:|jobs:\s*\n|steps:\s*\n\s+-\s+uses:",
        "category": "devops", "sub": "github-actions",
        "description": "GitHub Actions workflow",
    },
    {
        "priority": 200,
        "pattern": r"resource\s+\"aws_|provider\s+\"aws|terraform\s*\{",
        "category": "devops", "sub": "terraform",
        "description": "Terraform config",
    },
    {
        "priority": 210,
        "pattern": r"describe\s*\(['\"]|it\s*\(['\"]|test\s*\(['\"]|expect\s*\(",
        "category": "test", "sub": "jest",
        "description": "Jest/Mocha tests",
    },
    {
        "priority": 220,
        "pattern": r"def\s+test_\w+\s*\(|import\s+pytest|@pytest\.fixture",
        "category": "test", "sub": "pytest",
        "description": "pytest tests",
    },
    {
        "priority": 230,
        "pattern": r"cy\.visit\s*\(|cy\.get\s*\(|describe\s*\(['\"]",
        "category": "test", "sub": "cypress",
        "description": "Cypress tests",
    },
    {
        "priority": 240,
        "pattern": r"^#!/bin/(ba)?sh|^#!/usr/bin/env\s+(ba)?sh",
        "category": "backend", "sub": "shell",
        "description": "Shell shebang",
        "flags": "MULTILINE",
    },
    {
        "priority": 250,
        "pattern": r"^#!/usr/bin/env\s+python|^#!/usr/bin/python",
        "category": "backend", "sub": "python",
        "description": "Python shebang",
        "flags": "MULTILINE",
    },
    {
        "priority": 260,
        "pattern": r"^#!/usr/bin/env\s+node",
        "category": "backend", "sub": "nodejs",
        "description": "Node.js shebang",
        "flags": "MULTILINE",
    },
]

PATH_PATTERNS = [
    {"priority": 10,  "pattern": r"/lib/(widgets?|screens?|pages?|views?|components?)/|\.dart$", "category": "flutter",  "sub": "flutter",        "description": "Flutter lib structure"},
    {"priority": 20,  "pattern": r"/test/.*_test\.dart$|/integration_test/",                     "category": "test",     "sub": "flutter-test",   "description": "Flutter test files"},
    {"priority": 30,  "pattern": r"/__tests__/|/test/|/tests/|/spec/|\.test\.|\.spec\.|_test\.|_spec\.", "category": "test", "sub": "test",        "description": "Test directories"},
    {"priority": 40,  "pattern": r"\.stories\.(jsx?|tsx?)$",                                      "category": "frontend", "sub": "storybook",      "description": "Storybook stories"},
    {"priority": 50,  "pattern": r"/(server|srv|app)\.(js|ts|py|rb|go)$",                        "category": "backend",  "sub": "server",         "description": "Server entry points"},
    {"priority": 60,  "pattern": r"/(routes?|controllers?|handlers?)/",                           "category": "backend",  "sub": "routes",         "description": "Route/controller files"},
    {"priority": 70,  "pattern": r"/middleware/",                                                  "category": "backend",  "sub": "middleware",     "description": "Middleware files"},
    {"priority": 80,  "pattern": r"/(migrations?|seeds?|seeders?|models?)/",                      "category": "database", "sub": "migration",      "description": "DB migrations/models"},
    {"priority": 90,  "pattern": r"/(components?|widgets?|ui)/",                                  "category": "frontend", "sub": "component",      "description": "UI components"},
    {"priority": 100, "pattern": r"/(pages?|views?|screens?)/",                                   "category": "frontend", "sub": "page",           "description": "Frontend pages"},
    {"priority": 110, "pattern": r"/hooks?/|/use[A-Z]",                                           "category": "frontend", "sub": "hook",           "description": "React hooks"},
    {"priority": 120, "pattern": r"/(store|stores|redux|zustand|recoil|atoms?)/",                 "category": "frontend", "sub": "store",          "description": "State management"},
    {"priority": 130, "pattern": r"(^|/)Dockerfile(\.|$)",                                        "category": "devops",   "sub": "dockerfile",     "description": "Dockerfile"},
    {"priority": 140, "pattern": r"docker-compose",                                               "category": "devops",   "sub": "docker-compose", "description": "Docker Compose"},
    {"priority": 150, "pattern": r"/\.github/workflows/|/\.gitlab-ci|/\.circleci/|/\.travis",    "category": "devops",   "sub": "ci",             "description": "CI/CD configs"},
    {"priority": 160, "pattern": r"\.env(\.|$)",                                                  "category": "config",   "sub": "env",            "description": "Env files"},
    {"priority": 170, "pattern": r"/(config|settings?|configuration)\.(js|ts|py|json|yaml|yml)$","category": "config",   "sub": "config",         "description": "Config files"},
    {"priority": 180, "pattern": r"/(docs?|documentation)/|README|CHANGELOG|CONTRIBUTING|LICENSE","category": "docs",    "sub": "docs",           "description": "Documentation"},
]

CATEGORY_COLORS = [
    {"category": "frontend",  "color": "#4ADE80", "description": "React, Vue, Angular, plain JS/TS"},
    {"category": "backend",   "color": "#60A5FA", "description": "Python, Node, Go, Java, Ruby"},
    {"category": "html",      "color": "#FB923C", "description": "HTML/Jinja/Handlebars templates"},
    {"category": "css",       "color": "#F472B6", "description": "CSS, SCSS, SASS, Less"},
    {"category": "database",  "color": "#A78BFA", "description": "SQL, migrations, ORM, Prisma"},
    {"category": "mobile",    "color": "#34D399", "description": "Swift, Kotlin, Dart/Flutter"},
    {"category": "flutter",   "color": "#54C5F8", "description": "Flutter/Dart UI framework"},
    {"category": "devops",    "color": "#FBBF24", "description": "Dockerfile, CI, Terraform"},
    {"category": "config",    "color": "#94A3B8", "description": "JSON, TOML, YAML, .env"},
    {"category": "test",      "color": "#F87171", "description": "Jest, pytest, Cypress, spec files"},
    {"category": "docs",      "color": "#CBD5E1", "description": "Markdown, RST, TXT"},
    {"category": "shader",    "color": "#C084FC", "description": "GLSL, HLSL, WGSL"},
    {"category": "data",      "color": "#67E8F9", "description": "CSV, Parquet, JSON data"},
    {"category": "other",     "color": "#6B7280", "description": "Unrecognized files"},
]

EDGE_COLORS = [
    {"src": "frontend",  "tgt": "frontend",  "color": "#4ADE80"},
    {"src": "backend",   "tgt": "backend",   "color": "#60A5FA"},
    {"src": "frontend",  "tgt": "backend",   "color": "#C084FC"},
    {"src": "backend",   "tgt": "frontend",  "color": "#C084FC"},
    {"src": "html",      "tgt": "frontend",  "color": "#FB923C"},
    {"src": "html",      "tgt": "css",       "color": "#F472B6"},
    {"src": "frontend",  "tgt": "css",       "color": "#F472B6"},
    {"src": "backend",   "tgt": "database",  "color": "#A78BFA"},
    {"src": "frontend",  "tgt": "database",  "color": "#A78BFA"},
    {"src": "html",      "tgt": "html",      "color": "#67E8F9"},
    {"src": "flutter",   "tgt": "flutter",   "color": "#54C5F8"},
    {"src": "mobile",    "tgt": "mobile",    "color": "#34D399"},
]

async def seed():
    await connect_db()
    db = get_db()

    async def upsert_all(collection_name: str, docs: list[dict], key_fields: tuple) -> None:
        col = db[collection_name]
        inserted = 0
        updated = 0
        for doc in docs:
            query = {k: doc[k] for k in key_fields}
            result = await col.update_one(
                query,
                {"$setOnInsert": doc},
                upsert=True,
            )
            if result.upserted_id:
                inserted += 1
            else:
                updated += 1
        _log.info("%-35s  inserted=%d  skipped(existing)=%d", collection_name, inserted, updated)

    _log.info("Seeding classifier rules into MongoDB...")

    await upsert_all("classifier_extensions",    EXTENSIONS,       ("ext",))
    await upsert_all("classifier_named_files",   NAMED_FILES,      ("name",))
    await upsert_all("classifier_fingerprints",  FINGERPRINTS,     ("priority",))
    await upsert_all("classifier_path_patterns", PATH_PATTERNS,    ("priority",))
    await upsert_all("classifier_categories",    CATEGORY_COLORS,  ("category",))
    
    # Drop and recreate edge colors to fix old bug where src was used as solitary key
    await db.classifier_edge_colors.drop()
    await upsert_all("classifier_edge_colors",   EDGE_COLORS,      ("src", "tgt"))

    await db.classifier_extensions.create_index("ext",      unique=True)
    await db.classifier_named_files.create_index("name",    unique=True)
    await db.classifier_fingerprints.create_index("priority")
    await db.classifier_path_patterns.create_index("priority")
    await db.classifier_categories.create_index("category", unique=True)

    _log.info("Done. Run again anytime — existing rules are preserved.")
    await close_db()


if __name__ == "__main__":
    asyncio.run(seed())
