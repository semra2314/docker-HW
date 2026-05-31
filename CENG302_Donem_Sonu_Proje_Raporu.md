# CENG302 DÖNEM SONU ÖDEVİ: DATA MIDDLEWARE PROJE RAPORU


**Proje Başlığı:** Borsa Kuruluşu İçin Yüksek Performanslı, KVKK/GDPR Uyumlu Veri Ara Katmanı ve Dockerize Simülasyonu  
**Ders:** CENG302 Yazılım Mühendisliği / Nesne Yönelimli Tasarım

---

## 1. PROJE ÖZETİ VE AMACI

Bu projede, bir borsa kuruluşunun ürettiği yüksek hacimli işlem ve sistem günlüklerini (log verilerini) simüle eden bir **Veri Üretici (Data Generator)** ile bu logları gerçek zamanlı olarak işleyen, regülasyonlara (KVKK/GDPR) uygun hale getiren ve farklı ekiplerin ihtiyaçlarına göre biçimlendiren bir **Veri Ara Katmanı (Data Middleware)** geliştirilmiştir.

Proje, yazılım mühendisliği prensiplerine sadık kalınarak **Nesne Yönelimli Tasarım Kalıpları (Design Patterns)** ile inşa edilmiş ve yüksek yük altında saniyede binlerce işlemi kararlı bir şekilde işleyebilecek performans sınırlarına ulaştırılmıştır. Sistem, dağıtık mimarilere uyumluluk açısından tamamen **Docker** konteynerleri üzerinde çalışacak şekilde tasarlanmıştır.

---

## 2. SİSTEM MİMARİSİ VE VERİ AKIŞI

Sistem, birbirleriyle ağ üzerinden haberleşen iki bağımsız modülden (Docker konteynerinden) oluşmaktadır:

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

### Neden TCP Soket ve Asenkron Girdi/Çıktı (Async I/O)?

- **TCP Protokolü**: Log verilerinin kayıpsız iletilmesi finansal sistemler için kritiktir. HTTP protokolünün getirdiği başlık (header) ek yüklerini engellemek için doğrudan ham TCP soket bağlantısı kullanılmıştır. Loglar, aralarında satır sonu (`\n`) karakteri barındıran JSON verileri (NDJSON) olarak sürekli bir akış (stream) halinde iletilir.
- **Python Asyncio**: Ara katman servisinde `asyncio` kütüphanesi kullanılmıştır. Geleneksel çoklu iş parçacığı (multi-threading) mimarilerindeki "bağlam geçişi (context switch)" ve kilitlenme (lock) maliyetleri olmadan, tek bir işlemci çekirdeğinde binlerce soket bağlantısı ve disk yazma işlemi asenkron olarak bloke edilmeden yönetilir.

---

## 3. UYGULANAN TASARIM KALIPLARI (DESIGN PATTERNS)

Ödev gereksinimlerinde en az iki tasarım kalıbı istenmiş olmasına karşın, projenin modülerliğini ve genişletilebilirliğini en üst seviyeye çıkarmak amacıyla **4 farklı tasarım kalıbı** kullanılmıştır:

### A. Factory Method Pattern (Yaratısal)

- **Kullanıldığı Yer**: `generator/log_factory.py` içindeki `LogFactory` sınıfı.
- **Amacı**: Nesne oluşturma mantığını istemci koddan soyutlamak.
- **Nasıl Uygulandı?**: Veri üretici, borsa sistemindeki farklı durumları simüle etmek zorundadır. `LogFactory.create_log(scenario)` metodu; `transaction_success` (başarılı işlem), `transaction_warning` (sınır uyarısı), `transaction_error` (hata) veya `critical_security_alert` (güvenlik ihlali) gibi senaryo parametrelerine göre uygun veri yapılarını ve KVKK verilerini otomatik olarak oluşturup döner.

### B. Singleton Pattern (Yaratısal)

- **Kullanıldığı Yer**: `middleware/metrics.py` içindeki `MetricsCollector` sınıfı.
- **Amacı**: Sistem genelinde performansı (TPS, gecikme, işlem miktarları) izleyen tek bir merkezi sayaç nesnesinin bulunmasını garanti etmek.
- **Nasıl Uygulandı?**: Sınıfın `__new__` metodu özelleştirilerek ve `threading.Lock()` kullanılarak thread-safe (iş parçacığı güvenli) tekil bir nesne yaratılması sağlanmıştır. Ara katmanın herhangi bir noktasından çağrılan `MetricsCollector()` ifadesi her zaman bellekteki aynı nesneye erişerek performans verilerini toplar.

### C. Chain of Responsibility Pattern (Davranışsal)

- **Kullanıldığı Yer**: `middleware/handlers.py` içindeki `LogHandler` zinciri.
- **Amacı**: Log işleme adımlarını (filtreleme, maskeleme, zenginleştirme) gevşek bağlı (loosely coupled) ve sıralı sınıflar halinde yürütmek.
- **Nasıl Uygulandı?**: Soyut bir `LogHandler` sınıfından türetilen üç adet somut işleyici yazılmıştır:
  1.  `FilterHandler`: Gelen logun seviyesini kontrol eder. `INFO` veya `WARNING` ise logu eler ve zinciri sonlandırır. `ERROR` veya `CRITICAL` ise logu bir sonraki işleyiciye aktarır.
  2.  `SecurityHandler`: KVKK kapsamındaki hassas kişisel verileri maskeler ve logu iletir.
  3.  `EnrichmentHandler`: Mikroservislerin analizi için loga etiketler, sunucu bilgisi ve debug gecikme metrikleri ekler.

### D. Strategy Pattern (Davranışsal)

- **Kullanıldığı Yer**: `middleware/strategies.py` içindeki `FormatterStrategy` arayüzü ve türevleri.
- **Amacı**: Farklı rollerin (System Admin, CyberSec, Web Dev) istediği çıktı formatlarını dinamik olarak yönetebilmek.
- **Nasıl Uygulandı?**: `FormatterStrategy` soyut sınıfından türetilen 3 somut strateji sınıfı tanımlanmıştır:
  - `HtmlFormatter`: Sistem yöneticileri için görsel olarak zenginleştirilmiş, kritiklik seviyesine göre renklendirilmiş (kırmızı/turuncu) HTML satırları üretir.
  - `CsvFormatter`: Siber güvenlik uzmanlarının SIEM araçlarına kolayca aktarabilmesi için virgülle ayrılmış (CSV) satırlar üretir.
  - `JsonFormatter`: Web geliştiricilerin veri tabanlarına kolayca yazabilmesi için standart JSON Lines çıktısı üretir.

---

## 4. GÜVENLİK VE KVKK/GDPR UYUMLULUĞU

Borsa sistemleri hassas finansal ve kişisel veriler barındırır. Ara katmandaki `SecurityHandler` modülü, log akışındaki verileri analiz ederek şu maskeleme kurallarını uygulamaktadır:

1.  **T.C. Kimlik Numarası (11 Hane)**: İlk 3 hane ve son 2 hane açık bırakılır, aradaki 6 hane gizlenir. (Örn: `12345678901` -> `123******01`)
2.  **Kredi Kartı Numarası (16 Hane)**: İlk 4 ve son 4 hane açık bırakılır, aradaki haneler gizlenir. Tireli ve düz formatların ikisi de desteklenir. (Örn: `4532-1234-5678-9012` -> `4532-****-****-9012`)
3.  **E-Posta Adresi**: E-posta adresindeki kullanıcı adının ilk ve son harfi hariç tüm karakterleri maskelenir, domain adresi açık bırakılır. (Örn: `ahmet.yilmaz@borsa.com.tr` -> `a***********z@borsa.com.tr`)

> [!NOTE]
> **Dinamik İçerik Tarama**: Güvenlik filtresi sadece logun yapısal JSON alanlarını maskelemekle kalmaz, logun **mesaj (message)** gövdesinde düz metin olarak geçen T.C. Kimlik, kart veya e-posta verilerini de Regex (Düzenli İfadeler) ile tarayıp otomatik olarak maskeler.

---

## 5. PERFORMANS ANALİZİ VE TEST SONUÇLARI

Sistem performans sınırlarını ölçmek amacıyla, veri üretici modül sınırsız hız moduna alınmış ve ara katmana **100.000 adet ham log** gönderilmiştir.

### Performans Metrikleri Tablosu

| Metrik                         | Ölçülen Değer         | Açıklama                                                       |
| :----------------------------- | :-------------------- | :------------------------------------------------------------- |
| **Toplam Gönderilen Log**      | 100.000               | Veri üreticinin ürettiği toplam ham log miktarı.               |
| **Filtrelenen (Elenen) Log**   | 80.123 (%80,1)        | `INFO` ve `WARNING` seviyesinde olduğu için elenen log sayısı. |
| **İşlenen (Aktif) Log**        | 19.877 (%19,9)        | Ara katmanda maskelenip zenginleştirilen log sayısı.           |
| **Maskelenen Hassas Log**      | 19.877                | KVKK maskelemesi yapılan log sayısı.                           |
| **Ortalama İşlem Hızı (TPS)**  | **~3.354 log/saniye** | Saniyede işlenen ortalama log adedi.                           |
| **Ortalama Gecikme (Latency)** | **0,113 milisaniye**  | Log başına harcanan ortalama işlem süresi.                     |

### Performans Değerlendirmesi

1.  **Filtrelemenin Gücü**: Ara katman, önemsiz logların %80'ini ilk adımda eleyerek disk yazma işlemlerini ve CPU döngülerini devasa oranda azaltmıştır. Bu durum, veri tabanları ve mikroservislerin üzerindeki gereksiz yükü kaldırır.
2.  **Gecikme (Latency)**: Log başına harcanan sürenin `0.11 ms` gibi çok küçük bir değer olması, sistemin gerçek zamanlı (real-time) borsa sistemlerine tamamen entegre olabileceğini gösterir.
3.  **Tampon Bellek (Buffered I/O) Etkisi**: Tasarladığımız `BufferedWriter` sınıfı sayesinde loglar diske tek tek değil, 500'lü paketler halinde toplu yazılmıştır. Bu sayede işletim sisteminin disk yazma limitlerine takılmadan saniyede 3.000'in üzerinde işlem hızı stabil şekilde korunmuştur.

---

## 6. KONTEYNERLEŞTİRME VE DOCKER ORTAMI

Proje, dağıtım kolaylığı ve bağımsız çalışabilirlik için Dockerize edilmiştir.

### docker-compose.yml Yapısı

Compose dosyasında iki adet servis tanımlanmıştır:

1.  `middleware`: TCP sunucusunu 9999 portunda ayağa kaldırır. Çıktı dosyalarının bilgisayardan (host) anlık olarak incelenebilmesi için `./logs` dizini konteyner içindeki `/app/logs` dizinine bağlanmıştır (Volume Mount).
2.  `generator`: Başlangıçta ara katmanın açılmasını bekler (`depends_on`). Ardından ara katmana bağlanıp log akışını başlatır.

---

## 7. ÇALIŞTIRMA KILAVUZU VE SORUN GİDERME

### A. Docker Engine Bulunamadı Hatası Çözümü

Eğer terminalde `docker compose` çalıştırdığınızda `"The term 'docker' is not recognized"` hatası alıyorsanız, bilgisayarınızda Docker komut satırı araçları yüklü değildir veya PATH ortam değişkenlerine eklenmemiştir.

**Adım Adım Çözüm:**

1.  [Docker Desktop Resmi Sitesi](https://www.docker.com/products/docker-desktop/) adresinden Windows için Docker Desktop'ı indirin ve kurun.
2.  Kurulum sırasında **WSL 2** veya **Hyper-V** seçeneklerini etkinleştirin (varsayılan olarak etkindir).
3.  Kurulum tamamlandıktan sonra bilgisayarınızı yeniden başlatın veya oturumu kapatıp açın (PATH değişkenlerinin güncellenmesi için bu gereklidir).
4.  Docker Desktop uygulamasını çalıştırın ve sol alttaki ikonun **yeşil (running)** olduğundan emin olun.
5.  VS Code terminalini (veya PowerShell'i) kapatıp **yeni bir pencere** olarak tekrar açın.
6.  Aşağıdaki komutu çalıştırarak test edin:
    ```powershell
    docker compose up --build
    ```

### B. Projeyi Docker Olmadan Doğrudan Çalıştırma (Alternatif Hızlı Test)

Eğer Docker kurmadan projeyi doğrudan kendi bilgisayarınızda test etmek ve videoda göstermek isterseniz:

1.  **Ara Katmanı Başlatın**:
    Bir terminal açıp proje ana dizininde şu komutu çalıştırın:

    ```powershell
    python middleware/middleware.py
    ```

    _(Konsolda `[Middleware] Sunucu başlatıldı: ('0.0.0.0', 9999)` yazısını göreceksiniz.)_

2.  **Veri Üreticiyi Başlatın**:
    İkinci bir terminal açıp şu komutu çalıştırın:

    ```powershell
    python generator/generator.py
    ```

    _(Veri üretici hemen bağlanacak ve log akışını başlatacaktır. Ekranda saniyelik performans raporları akmaya başlayacaktır.)_

3.  **Çıktıları Kontrol Edin**:
    İşlem bittiğinde proje dizininde otomatik olarak oluşan `logs/` klasöründeki dosyaları inceleyebilirsiniz.

---

## 8. SONUÇ

Bu proje kapsamında geliştirilen veri ara katmanı; asenkron yapısı, Nesne Yönelimli Tasarım ilkelerine (Factory, Singleton, Chain of Responsibility, Strategy) tam uyumu ve üstün performans verileriyle borsa gibi kritik finans kuruluşlarının ihtiyaçlarını tam olarak karşılayacak seviyededir. Sistem, güvenlik regülasyonlarını (KVKK) en katı kurallarla işletirken, rol bazlı çıktı formatlarıyla kurumsal ekiplerin (Sistem Admin, Siber Güvenlik, Yazılım) entegrasyon süreçlerini minimize etmektedir.
