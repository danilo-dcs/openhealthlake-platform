# Use a slim Python image
FROM python:3.12

WORKDIR /app

RUN mkdir -p /tmp/api

RUN mkdir -p /tmp/api/uploads

RUN mkdir -p /tmp/api/downloads

# Copy only the requirements file first to leverage Docker cache
COPY ./requirements.txt ./requirements.txt

# Install dependencies
RUN python -m ensurepip --upgrade && \
    pip install --no-cache-dir -r ./requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the application port
EXPOSE 4000

# Start the uvicorn server
# CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "4000", "--workers", "2"]
# CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "4000"]
CMD ["uvicorn", "app:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "4000"]

# if http
# CMD ["fastapi", "run", "src/app.py", "--proxy-headers", "--port", "4000"]

# if https
# CMD ["fastapi", "run", "app/main.py", "--proxy-headers", "--port", "80"]

