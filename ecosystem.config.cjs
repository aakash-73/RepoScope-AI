module.exports = {
  apps: [
    {
      name: "ollama",
      script: "ollama",
      args: "serve",
      autorestart: true,
      watch: false,
    },
    {
      name: "reposcope-backend",
      cwd: "./backend",
      script: "uvicorn",
      args: "main:app --host 0.0.0.0 --port 8000",
      interpreter: "python3",
      watch: false,
      env: {
        PYTHONUNBUFFERED: "1",
      },
      error_file: "./logs/backend-err.log",
      out_file: "./logs/backend-out.log",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
    },
    {
      name: "reposcope-frontend",
      cwd: "./frontend",
      script: "npm",
      args: "run preview -- --port 4173 --host 0.0.0.0",
      watch: false,
      error_file: "./logs/frontend-err.log",
      out_file: "./logs/frontend-out.log",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
    },
  ],
};
