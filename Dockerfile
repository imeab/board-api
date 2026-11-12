FROM python:3.14-slim

# uv로 의존성 설치
RUN pip install --no-cache-dir uv
WORKDIR /code
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev

COPY app ./app
EXPOSE 8000
CMD ["uv", "run", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
