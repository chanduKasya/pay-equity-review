# Pay Equity Review: the pipeline and the Streamlit dashboard in one image.
#
# Build:  docker build -t pay-equity-review .
# Run:    docker run --rm -p 8501:8501 pay-equity-review
# Then open http://localhost:8501

# Python 3.12 on a small Debian base. The project needs Python 3.10 or newer.
FROM python:3.12-slim

# Do not write .pyc files, and print output straight away.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install the dashboard's packages first. Docker caches this step, so it is
# only repeated when the requirements file changes.
COPY requirements-app.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements-app.txt -r requirements.txt

# Copy the project: code, the generated datasets and the results.
COPY . .

# Streamlit's default port.
EXPOSE 8501

# 0.0.0.0 lets the browser on the host machine reach the app in the container.
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
