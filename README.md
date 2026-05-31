# CENG302 - Data Middleware Projesi

Borsa Kuruluşu İçin Yüksek Performanslı, KVKK/GDPR Uyumlu Veri Ara Katmanı ve Dockerize Simülasyonu

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-enabled-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)

Bu proje, yüksek hacimli borsa işlem ve sistem günlüklerini (log verilerini) simüle eden bir **Veri Üretici (Data Generator)** ile bu günlükleri gerçek zamanlı olarak toplayıp işleyen, regülasyonlara (KVKK/GDPR) uygun olarak maskeleyen ve farklı ekiplerin ihtiyaçlarına göre formatlayan bir **Veri Ara Katmanı (Data Middleware)** sistemidir.

Proje, yazılım mühendisliği prensiplerine (SOLID) sadık kalınarak **Nesne Yönelimli Tasarım Kalıpları (Design Patterns)** ile inşa edilmiş olup, **Python Asyncio** kullanılarak yüksek yük altında saniyede binlerce işlemi kararlı bir şekilde işleyebilecek şekilde optimize edilmiştir. Sistem tamamen **Docker** konteynerleri üzerinde çalışacak şekilde yapılandırılmıştır.

---

## 🏗️ Sistem Mimarisi ve Veri Akışı

Sistem, izole Docker ağları üzerinde haberleşen iki bağımsız modülden oluşmaktadır:

```
+-----------------------------------+             +-----------------------------------------+
|      data-generator (Client)      |             |        data-middleware (Server)         |
|                                   |             |                                         |
| +-------------------------------+ |  TCP Soket  | +-------------------------------------+ |
| |       LogFactory              | |  (NDJSON)   | |            TCP Sunucu               | |
| | (Senaryolara Göre Log Üretimi)| |             | |       (Asenkron Bağlantı Kabulü)    | |
| +-------------------------------+ | ------------> +-------------------------------------+ |
|                                   |  Stream üzerinden                                      |
| +-------------------------------+ |  satır satır| +-------------------------------------+ |
| |       Asenkron TCP Client     | |  veri akışı | |      Chain of Responsibility        | |
| |  (Hız Sınırlı / Sınırsız)     | |             | |  (Filtreleme -> KVKK -> Zenginleş.) | |
| +-------------------------------+ |             | +-------------------------------------+ |
|                                   |             |                    |                    |
|                                   |             |                    v                    |
|                                   |             | +-------------------------------------+ |
|                                   |             |          Strategy Pattern           | |
|                                   |             |       (HTML / CSV / JSON Seçim)       | |
|                                   |             | +-------------------------------------+ |
|                                   |             |                    |                    |
|                                   |             |                    v                    |
|                                   |             | +-------------------------------------+ |
|                                   |             |          BufferedWriter             | |
|                                   |             |      (Toplu Asenkron Diske Yazım)     | |
|                                   |             | +-------------------------------------+ |
+-----------------------------------+             +-----------------------------------------+
```

1. **data-generator**: [generator.py](file:///c:/Users/semra/Desktop/docker%20ödevi/generator/generator.py) dosyası tarafından yönetilir. Borsa işlem senaryolarını (işlem başarısı, hata, güvenlik uyarısı vb.) [LogFactory](file:///c:/Users/semra/Desktop/docker%20ödevi/generator/log_factory.py) aracılığıyla nesneleştirir ve TCP soketi üzerinden NDJSON (Newline Delimited JSON) biçiminde asenkron olarak ara katmana aktarır.
2. **data-middleware**: [middleware.py](file:///c:/Users/semra/Desktop/docker%20ödevi/middleware/middleware.py) tarafından yönetilir. Asenkron TCP sunucusu ile gelen log akışını kabul eder, logları filtreleme, KVKK maskeleme ve zenginleştirme adımlarından geçirir ve seçilen çıktı formatlarına göre diske yazar.

---

## 🛠️ Uygulanan Tasarım Kalıpları (Design Patterns)

Proje kapsamında modülerliği, sürdürülebilirliği ve genişletilebilirliği sağlamak adına **4 farklı tasarım kalıbı** kullanılmıştır:

* **Factory Method Pattern (Yaratısal):** [LogFactory](file:///c:/Users/semra/Desktop/docker%20ödevi/generator/log_factory.py) sınıfı borsa simülasyonundaki log tiplerini (`transaction_success`, `transaction_warning`, `transaction_error`, `critical_security_alert`) parametrik olarak üretir. Nesne oluşturma mantığı istemci koddan tamamen soyutlanmıştır.
* **Singleton Pattern (Yaratısal):** [MetricsCollector](file:///c:/Users/semra/Desktop/docker%20ödevi/middleware/metrics.py) sınıfı, sistem genelindeki TPS (saniyelik işlem), gecikme ve filtreleme metriklerini toplayan tekil bir bellek nesnesidir. Thread-safe (iş parçacığı güvenli) olacak şekilde tasarlanmıştır.
* **Chain of Responsibility Pattern (Davranışsal):** Logların işlenme süreci [LogHandler](file:///c:/Users/semra/Desktop/docker%20ödevi/middleware/handlers.py) zinciri üzerinden gerçekleştirilir:
  1. `FilterHandler`: Kritik olmayan log seviyelerini (`INFO`, `WARNING`) ilk adımda eler.
  2. `SecurityHandler`: Hassas verileri KVKK/GDPR standartlarında maskeler.
  3. `EnrichmentHandler`: Loga sunucu adı, işlem zamanı ve ek mikroservis etiketleri ekler.
* **Strategy Pattern (Davranışsal):** [FormatterStrategy](file:///c:/Users/semra/Desktop/docker%20ödevi/middleware/strategies.py) ve türevleri (`HtmlFormatter`, `CsvFormatter`, `JsonFormatter`) sayesinde log çıktıları, sistemi kullanan ekiplerin rollerine (Sistem Yöneticisi, Siber Güvenlik, Web Geliştirici) göre dinamik olarak farklı formatlarda üretilir.

---

## 🔒 KVKK / GDPR Maskeleme Standartları

[SecurityHandler](file:///c:/Users/semra/Desktop/docker%20ödevi/middleware/handlers.py) sınıfı, log akışındaki ve mesaj içeriklerindeki hassas verileri Regex taramalarıyla otomatik olarak tespit edip şu kurallara göre maskeler:

* **T.C. Kimlik Numarası (11 Hane):** İlk 3 ve son 2 hane açık, aradaki 6 hane gizlenir. (Örn: `12345678901` ➔ `123******01`)
* **Kredi Kartı Numarası (16 Hane):** İlk 4 ve son 4 hane açık, aradaki haneler gizlenir. (Örn: `4532-1234-5678-9012` ➔ `4532-****-****-9012`)
* **E-Posta Adresi:** Kullanıcı adının baş ve son karakteri hariç tümü maskelenir, domain adresi açık bırakılır. (Örn: `ahmet.yilmaz@borsa.com.tr` ➔ `a***********z@borsa.com.tr`)

---

## ⚡ Performans ve Benchmark Sonuçları

Ara katman sunucusunda performansı artırmak ve disk I/O darboğazlarını önlemek amacıyla loglar diske tek tek değil, asenkron bir `BufferedWriter` vasıtasıyla **500'erli paketler halinde toplu** yazılmaktadır. 100.000 log ile gerçekleştirilen benchmark sonuçları aşağıdaki gibidir:

| Metrik | Değer | Açıklama |
| :--- | :--- | :--- |
| **Toplam Ham Log** | 100.000 adet | Simülatör tarafından üretilen log sayısı |
| **Filtrelenen Log** | 80.123 adet (%80,1) | `INFO`/`WARNING` seviyesinde elenen loglar |
| **İşlenen Log** | 19.877 adet (%19,9) | Ara katmanda maskelenen/zenginleştirilen loglar |
| **Ortalama İşlem Hızı (TPS)** | **~3.354 log/saniye** | Saniyede işlenen ortalama log adedi |
| **Ortalama Gecikme (Latency)** | **0,113 milisaniye** | Log başına harcanan asenkron işlem süresi |

---

## 📁 Proje Dosya Yapısı

```text
docker ödevi/
├── CENG302_Donem_Sonu_Proje_Raporu.md  # Detaylı dönem sonu proje raporu
├── README.md                           # GitHub README belgesi
├── docker-compose.yml                  # Konteyner orkestrasyon dosyası
├── generator/                          # Veri Üretici Modülü
│   ├── Dockerfile
│   ├── generator.py                    # Simülasör ana döngüsü & TCP client
│   └── log_factory.py                  # Log üretici Factory sınıfı
├── middleware/                         # Veri Ara Katmanı Modülü
│   ├── Dockerfile
│   ├── middleware.py                   # TCP Sunucu & BufferedWriter asenkron yapısı
│   ├── handlers.py                     # Chain of Responsibility log işleyicileri
│   ├── metrics.py                      # Singleton metrik toplayıcı
│   └── strategies.py                   # Strategy format dönüştürücüler
└── logs/                               # Konteyner dışına bağlanan log çıktıları (Volume)
    ├── debug_output.html               # Sistem Yöneticisi için HTML rapor
    ├── security_audit.csv              # Siber Güvenlik için CSV logları
    └── app_logs.json                   # Web Geliştiriciler için JSON logları
```

---

## 🚀 Kurulum ve Çalıştırma Kılavuzu

### 1. Docker ile Çalıştırma (Önerilen)

Sistemi tamamen izole ve Dockerize edilmiş şekilde çalıştırmak için:

1. Bilgisayarınızda **Docker Desktop** uygulamasının açık olduğundan emin olun.
2. Proje ana dizininde bir terminal (PowerShell veya CMD) açıp şu komutu yürütün:
   ```bash
   docker compose up --build
   ```
3. Konteynerler derlenecek ve log akışı başlayacaktır. Ekranda saniyelik performans metrikleri görüntülenecektir.
4. İşlem tamamlandığında, `logs/` klasöründe çıktı dosyaları otomatik olarak belirecektir.

### 2. Yerel Python Ortamında Çalıştırma (Alternatif)

Eğer sistemi Docker olmadan doğrudan Python ile çalıştırmak isterseniz:

1. **Ara Katman Sunucusunu Başlatın**:
   ```bash
   python middleware/middleware.py
   ```
2. **Veri Üretici İstemcisini Başlatın** (Ayrı bir terminalde):
   ```bash
   python generator/generator.py
   ```

## Güvenlik & KVKK Maskelemesi
Log akışında yakalanan şu hassas veriler otomatik olarak maskelenir:
* **T.C. Kimlik Numarası**: `12345678901` -> `123******01`
* **Kredi Kartı Numarası**: `4532-1234-5678-9012` -> `4532-****-****-9012`
* **E-Posta Adresi**: `ahmet.yilmaz@borsa.com.tr` -> `a***********z@borsa.com.tr`
