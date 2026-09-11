FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 保留 engine/ 这一层目录：app.py / main.py 用的是 `from engine.xxx import` 绝对导入
COPY . ./engine/

EXPOSE 8000

CMD ["uvicorn", "engine.app:app", "--host", "0.0.0.0", "--port", "8000"]
