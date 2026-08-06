FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .

# Use mainland mirrors for Debian packages and PyPI.  PyTorch deliberately
# stays on its official CPU-wheel index because third-party CPU mirrors often
# lag behind or do not carry all supported Python versions.
# Install torch's pure-Python dependencies first: the PyTorch CPU index can
# otherwise redirect these small packages back to the public PyPI host.
ARG PYPI_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
RUN sed -i 's|deb.debian.org/debian|mirrors.aliyun.com/debian|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --timeout 600 --retries 10 --index-url ${PYPI_INDEX_URL} filelock typing-extensions sympy networkx jinja2 fsspec \
    && pip install --no-cache-dir --timeout 600 --retries 10 --no-deps --index-url https://download.pytorch.org/whl/cpu "torch>=2.1,<3.0" \
    && pip install --no-cache-dir --timeout 600 --retries 10 --index-url ${PYPI_INDEX_URL} -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
