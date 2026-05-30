FROM python:3.11-slim

# Python çıktılarının tamponlanmadan konsola anında yazdırılmasını sağlar
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Gerekli kod dosyalarını kopyalayalım
COPY metrics.py .
COPY strategies.py .
COPY handlers.py .
COPY middleware.py .

# Logların yazılacağı çıktı klasörü
RUN mkdir -p /app/logs

# Portu dışarı açalım
EXPOSE 9999

# Log çıktılarını ana bilgisayarla (host) paylaşabilmek için volume tanımlayalım
VOLUME ["/app/logs"]

# Uygulamayı çalıştıralım
CMD ["python", "middleware.py"]
