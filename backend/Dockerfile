FROM tiangolo/uvicorn-gunicorn:python3.11


# ✅ Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y \
  libgl1 \
  libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /app/requirements.txt

# ✅ Upgrade pip
RUN pip install --upgrade pip

COPY ./init_container.sh /app/init_container.sh

RUN chmod +x  /app/init_container.sh


# ✅ Install torch separately (CPU only)
RUN pip install --no-cache-dir \
  docling==2.74.0

# ✅ Then install rest WITHOUT torch
# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

#RUN /app/init_container.sh

EXPOSE 90/tcp
