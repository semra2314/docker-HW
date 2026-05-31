# Bu dosyanın amacı Singleton Pattern (Tekil Tasarım Kalıbı) kullanarak,

# sistemin canlı performans verilerini (anlık/ortalama TPS, filtreleme oranları, gecikme süreleri)
# tüm ara katman boyunca tek bir merkezi sayaçtan takip etmektir.

import threading
import time

class MetricsCollector:
    """
    Singleton (Tekil) Tasarım Kalıbı.
    Ara katmanın tüm çalışma süresi boyunca performans metriklerini
    (işlenen log sayısı, elenen log sayısı, anlık ve genel TPS, gecikme vb.)
    merkezi olarak kaydeder ve raporlar.
    """
    _instance = None
    _lock = threading.Lock() # Çoklu iş parçacığı güvenliği (thread-safety) için lock

    def __new__(cls, *args, **kwargs):
        # Double-Checked Locking (Çift Kontrollü Kilitleme) ile Singleton koruması
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(MetricsCollector, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        self.total_received = 0
        self.total_processed = 0
        self.total_filtered = 0
        self.total_anonymized = 0
        self.start_time = None
        self.last_report_time = None
        self.last_report_count = 0
        self.latencies = [] # Son işlenen logların gecikme süreleri (milisaniye cinsinden)

    def start(self):
        self.start_time = time.time()
        self.last_report_time = self.start_time

    def record_received(self):
        self.total_received += 1

    def record_processed(self, latency: float = 0.0):
        self.total_processed += 1
        if latency > 0:
            self.latencies.append(latency)
            # Bellek birikmesini önlemek için son 10.000 gecikme verisini tutuyoruz
            if len(self.latencies) > 10000:
                self.latencies = self.latencies[-10000:]

    def record_filtered(self):
        self.total_filtered += 1

    def record_anonymized(self):
        self.total_anonymized += 1

    def get_report(self) -> dict:
        now = time.time()
        elapsed = now - self.start_time if self.start_time else 0.001
        
        # Son raporlamadan bu yana geçen süredeki anlık TPS hesabı
        interval = now - self.last_report_time if self.last_report_time else 0.001
        interval_count = self.total_received - self.last_report_count
        current_tps = interval_count / interval
        
        # Aralık değerlerini güncelle
        self.last_report_time = now
        self.last_report_count = self.total_received

        overall_tps = self.total_received / elapsed
        avg_latency_ms = (sum(self.latencies) / len(self.latencies)) * 1000 if self.latencies else 0.0

        return {
            "elapsed_seconds": elapsed,
            "total_received": self.total_received,
            "total_processed": self.total_processed,
            "total_filtered": self.total_filtered,
            "total_anonymized": self.total_anonymized,
            "overall_avg_tps": overall_tps,
            "current_interval_tps": current_tps,
            "avg_latency_ms": avg_latency_ms
        }
