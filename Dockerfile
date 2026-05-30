FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirement files and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose Streamlit default port
EXPOSE 8501

# Set environment variables for Streamlit
ENV PYTHONUNBUFFERED=1

# Run the Streamlit app
CMD ["streamlit", "run", "frontend/streamlit_app.py", "--server.port=8501", "--server.enableCORS=false", "--server.enableXsrfProtection=false", "--server.headless=true"]
