# Data Middleware Geliştirme Görevleri

- `[x]` **Bileşen 1: Altyapı ve Veri Üretici (Generator)**
  - `[x]` Proje dizin yapısının oluşturulması
  - `[x]` `generator/log_factory.py` (Factory Method) dosyasının yazılması
  - `[x]` `generator/generator.py` asenkron log üretici ve TCP istemcisinin yazılması
- `[x]` **Bileşen 2: Ara Katman (Middleware) Core Yapı**
  - `[x]` `middleware/metrics.py` (Singleton) performans ölçüm sınıfının yazılması
  - `[x]` `middleware/strategies.py` (Strategy) HTML, CSV ve JSON çıktı sınıflarının yazılması
  - `[x]` `middleware/handlers.py` (Chain of Responsibility) filtre, güvenlik ve zenginleştirme zincirinin yazılması
  - `[x]` `middleware/middleware.py` asenkron TCP sunucusunun ve işlem akışının yazılması
- `[x]` **Bileşen 3: Performans, Docker ve Testler**
  - `[x]` `generator/Dockerfile`, `middleware/Dockerfile` ve `docker-compose.yml` dosyalarının yazılması
  - `[x]` Local ortamda testlerin çalıştırılması ve performans ölçümlerinin alınması
