FROM python:3.13-slim

WORKDIR /app

# Creating the Streamlit runtime configuration
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_PORT=8501

# Include the system dependencies required by OpenCV, FFmpeg and video processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install the project's pinned Python environment
COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy only the application/runtime parts of the project.
# Training datasets and development artifacts are not needed at runtime.
COPY backend /app/backend
COPY model/pitchvision /app/model/pitchvision
COPY model/scripts /app/model/scripts
COPY model/results/checkpoints /app/model/results/checkpoints

# Make model available as a Python import root
ENV PYTHONPATH=/app/model

EXPOSE 8501

CMD ["streamlit", "run", "backend/app/streamlit_app.py"]