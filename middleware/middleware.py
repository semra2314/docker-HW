import asyncio
import json
import os
import sys
import time
from metrics import MetricsCollector
from strategies import HtmlFormatter, CsvFormatter, JsonFormatter
from handlers import FilterHandler, SecurityHandler, EnrichmentHandler

class BufferedWriter:
    """
    Yüksek Performanslı Asenkron Disk Yazıcı.
    Logları tek tek diske yazmak yerine tampon belleğe (buffer) alır
    ve belirli limitlere ulaşınca toplu (batch) yazar. Disk I/O darboğazını engeller.
    """
    def __init__(self, filepath: str, strategy, buffer_limit: int = 1000):
        self.filepath = filepath
        self.strategy = strategy
        self.buffer = []
        self.buffer_limit = buffer_limit
        
        # Dizinlerin varlığını kontrol et, yoksa oluştur
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        
        # Dosyayı başlangıç başlığı (Header) ile sıfırla/başlat
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.write(self.strategy.get_header())

    def write(self, log: dict):
        # Stratejiye göre logu formatla
        formatted = self.strategy.format(log)
        self.buffer.append(formatted)
        
        # Tampon sınırına ulaşıldıysa diske yaz
        if len(self.buffer) >= self.buffer_limit:
            self.flush()

    def flush(self):
        if not self.buffer:
            return
        
        lines = "".join(self.buffer)
        self.buffer = []
        try:
            with open(self.filepath, "a", encoding="utf-8") as f:
                f.write(lines)
        except Exception as e:
            print(f"[BufferedWriter] Diske yazılırken hata oluştu ({self.filepath}): {e}")

    def close(self):
        # Kalan tamponu temizle ve kapanış şablonunu (Footer) ekle
        self.flush()
        try:
            with open(self.filepath, "a", encoding="utf-8") as f:
                f.write(self.strategy.get_footer())
        except Exception as e:
            print(f"[BufferedWriter] Kapanış verisi yazılırken hata oluştu ({self.filepath}): {e}")


# Global Değişkenler
writers = {}
pipeline = None
metrics = MetricsCollector()

async def handle_client(reader, writer):
    """
    Soket üzerinden bağlanan her veri üretici (generator) istemcisini asenkron yönetir.
    """
    addr = writer.get_extra_info('peername')
    print(f"[Middleware] Veri kaynağı bağlandı: {addr}")
    
    try:
        while True:
            # Satır sonu karakterine kadar oku (NDJSON standardı)
            line = await reader.readline()
            if not line:
                break # İstemci bağlantıyı kapattı
                
            metrics.record_received()
            start_time = time.time()
            
            try:
                log_data = json.loads(line.decode('utf-8'))
            except Exception as e:
                print(f"[Middleware] JSON dönüştürme hatası: {e}")
                continue
                
            # Chain of Responsibility zincirini çalıştır
            processed_log = pipeline.handle(log_data)
            
            if processed_log:
                # Log filtreleri geçtiyse rollere ait BufferedWriter'lara gönder
                for role, buf_writer in writers.items():
                    buf_writer.write(processed_log)
                
                # Performans ve gecikme ölçümü
                latency = time.time() - start_time
                metrics.record_processed(latency)
                
    except Exception as e:
        print(f"[Middleware] Veri akışı sırasında hata: {e}")
    finally:
        print(f"[Middleware] Veri kaynağı bağlantısı kesildi: {addr}")
        # Bağlantı kesildiğinde tamponları diske boşaltalım
        for role, buf_writer in writers.items():
            buf_writer.flush()
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

async def report_metrics():
    """
    Her 2 saniyede bir ara katmanın anlık ve genel performans raporunu konsola yazar.
    """
    metrics.start()
    while True:
        await asyncio.sleep(2.0)
        report = metrics.get_report()
        print(
            f"\n--- [ARA KATMAN CANLI PERFORMANS RAPORU - {report['elapsed_seconds']:.1f}s] ---\n"
            f"Alınan Toplam Log         : {report['total_received']:,}\n"
            f"Filtrelenerek Elenen Log  : {report['total_filtered']:,}\n"
            f"İşlenen (Aktif Log)       : {report['total_processed']:,}\n"
            f"Maskelenen Hassas Log     : {report['total_anonymized']:,}\n"
            f"Anlık İşlem Hızı (TPS)    : {report['current_interval_tps']:,.2f} log/sn\n"
            f"Ortalama İşlem Hızı (TPS) : {report['overall_avg_tps']:,.2f} log/sn\n"
            f"Ortalama Gecikme (Latency): {report['avg_latency_ms']:.4f} ms\n"
            f"-----------------------------------------------------------------\n",
            flush=True
        )

def shutdown():
    """
    Uygulama sonlandırılırken tampon verileri diske kaydeder ve HTML/CSV dosyalarını kapatır.
    """
    print("[Middleware] Kapatılıyor. Tüm tampon bellekler diske yazılıyor...")
    for role, writer in writers.items():
        writer.close()
    print("[Middleware] Güvenli kapatma tamamlandı.")

async def main():
    global pipeline
    
    # Çıktı klasörü yapılandırması
    logs_dir = os.environ.get("LOGS_DIR", "logs")
    
    # Rol Stratejilerini Tanımla (Strategy Pattern)
    html_strategy = HtmlFormatter()
    csv_strategy = CsvFormatter()
    json_strategy = JsonFormatter()
    
    # BufferedWriter'ları Oluştur (Gereksiz I/O engellemek için yüksek buffer limiti)
    writers["admin"] = BufferedWriter(os.path.join(logs_dir, "system_admin.html"), html_strategy, buffer_limit=500)
    writers["cybersec"] = BufferedWriter(os.path.join(logs_dir, "cybersec.csv"), csv_strategy, buffer_limit=500)
    writers["webdev"] = BufferedWriter(os.path.join(logs_dir, "web_dev.json"), json_strategy, buffer_limit=500)
    
    # Sorumluluk Zincirini Tanımla (Chain of Responsibility Pattern)
    filter_handler = FilterHandler()
    security_handler = SecurityHandler()
    enrich_handler = EnrichmentHandler()
    
    # Zincir sırası: Filtreleme -> Maskeleme (Güvenlik) -> Zenginleştirme
    filter_handler.set_next(security_handler).set_next(enrich_handler)
    pipeline = filter_handler
    
    # Soket Sunucu Bağlantı Ayarları
    host = os.environ.get("MIDDLEWARE_HOST", "0.0.0.0")
    port = int(os.environ.get("MIDDLEWARE_PORT", 9999))
    
    server = await asyncio.start_server(handle_client, host, port)
    addr = server.sockets[0].getsockname()
    print(f"[Middleware] Sunucu başlatıldı: {addr}")
    
    # Arka plan performans metrik raporlayıcı görevini başlat
    metrics_task = asyncio.create_task(report_metrics())
    
    try:
        async with server:
            await server.serve_forever()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        metrics_task.cancel()
        shutdown()

if __name__ == "__main__":
    import signal
    
    def handle_signal(signum, frame):
        print(f"\n[Middleware] Kapatma sinyali alındı ({signum}). Temizleniyor...")
        shutdown()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
