FROM python:3.11-slim

# Python çıktılarının tamponlanmadan konsola anında yazdırılmasını sağlar
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Sadece gerekli kod dosyalarını kopyalayalım
COPY log_factory.py .
COPY generator.py .

# Uygulamayı çalıştıralım
CMD ["python", "generator.py"]
