FROM python:3.11-slim

WORKDIR /app

# PyPI 源可通过构建参数覆盖（国内服务器建议用镜像源，否则 pip 会非常慢）
ARG PIP_INDEX_URL=https://pypi.org/simple

COPY requirements.txt .
RUN pip install --no-cache-dir -i ${PIP_INDEX_URL} -r requirements.txt

# 保留 engine/ 这一层目录：app.py / main.py 用的是 `from engine.xxx import` 绝对导入
COPY . ./engine/

EXPOSE 8000

CMD ["uvicorn", "engine.app:app", "--host", "0.0.0.0", "--port", "8000"]
