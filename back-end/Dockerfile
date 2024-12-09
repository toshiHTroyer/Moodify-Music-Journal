FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    --no-install-recommends && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install pipenv
RUN pip install --no-cache-dir pipenv

# Set working directory
WORKDIR /app

# Copy Pipfile and Pipfile.lock first to leverage Docker's caching
COPY Pipfile Pipfile.lock /app/

# Install dependencies
RUN pipenv install --system --deploy --ignore-pipfile

# Copy the rest of the application code
COPY . /app/

# Expose Flask port
EXPOSE 5000

# Command to run the Flask application
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
