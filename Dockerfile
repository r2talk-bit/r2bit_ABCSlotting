FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PORT=8080
ENV HOST=0.0.0.0

# Expose the port that Streamlit will run on
EXPOSE 8080

# Command to run the application
CMD streamlit run --server.port $PORT --server.address $HOST streamlit_app.py
