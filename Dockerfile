FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Cloud Run will send traffic to this port
ENV PORT=8080

# Start the app with gunicorn (WSGI server)
CMD ["gunicorn", "-b", ":8080", "app:app"]
