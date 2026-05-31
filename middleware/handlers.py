# Bu dosyanın amacı Chain of Responsibility Pattern (Sorumluluk Zinciri Tasarım Kalıbı) kullanarak,

# gelen borsa loglarını sırasıyla Filtreleme (FilterHandler), KVKK/GDPR Maskeleme (SecurityHandler)
# ve Metadata Ekleme/Zenginleştirme (EnrichmentHandler) işlemlerinden geçirmektir.
# Her handler işini yaptıktan sonra veriyi zincirdeki bir sonraki halkaya iletir.

from abc import ABC, abstractmethod
import re
import socket
import time
from metrics import MetricsCollector

class LogHandler(ABC):
    """
    Chain of Responsibility (Sorumluluk Zinciri) Tasarım Kalıbı Taban Sınıfı.
    Her işleyici (handler) bir sonraki işleyiciyi işaret eder.
    """
    def __init__(self):
        self.next_handler = None

    def set_next(self, handler: 'LogHandler') -> 'LogHandler':
        self.next_handler = handler
        return handler

    @abstractmethod
    def handle(self, log: dict) -> dict:
        """Log verisini işler ve bir sonraki işleyiciye aktarır."""
        if self.next_handler:
            return self.next_handler.handle(log)
        return log


class FilterHandler(LogHandler):
    """
    Performans / Filtreleme İşleyicisi.
    INFO ve WARNING seviyesindeki önemsiz logları eler,
    sadece ERROR ve CRITICAL loglarının işlenmeye devam etmesini sağlar.
    """
    def handle(self, log: dict) -> dict:
        level = log.get("level", "INFO").upper()
        
        # Filtreleme Kuralı: INFO veya WARNING ise işlemi durdur
        if level in ["INFO", "WARNING"]:
            MetricsCollector().record_filtered()
            return None # Zinciri sonlandır, alt adımlara iletme
            
        return super().handle(log)


class SecurityHandler(LogHandler):
    """
    Güvenlik / KVKK Anonimleştirme İşleyicisi.
    Log içindeki Kredi Kartı, TC Kimlik Numarası ve E-Posta bilgilerini maskeler.
    """
    # Regex şablonları (Log mesajlarının içinde geçen verileri de yakalamak için)
    EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
    TC_REGEX = re.compile(r'\b\d{11}\b')
    CC_REGEX = re.compile(r'\b(?:\d[ -]?){15,16}\b')

    def mask_email(self, email: str) -> str:
        if not email or "@" not in email:
            return email
        username, domain = email.split("@", 1)
        if len(username) <= 2:
            masked_username = "*" * len(username)
        else:
            # İlk ve son harfi açıkta bırak, arayı yıldızla
            masked_username = username[0] + "*" * (len(username) - 2) + username[-1]
        return f"{masked_username}@{domain}"

    def mask_tc(self, tc: str) -> str:
        if not tc or len(tc) != 11:
            return tc
        # İlk 3 ve son 2 hane açık, ortası yıldızlı (KVKK standardı)
        return tc[:3] + "*" * 6 + tc[-2:]

    def mask_cc(self, cc: str) -> str:
        # Tire ve boşlukları temizleyelim
        cleaned = cc.replace(" ", "").replace("-", "")
        if len(cleaned) < 15 or len(cleaned) > 16:
            return cc
        
        # İlk 4 ve son 4 hane açık, ortası yıldızlı
        masked = cleaned[:4] + "*" * (len(cleaned) - 8) + cleaned[-4:]
        
        # Eğer orijinal kredi kartı tire içeriyorsa formatı koru
        if "-" in cc:
            return f"{masked[:4]}-{masked[4:8]}-{masked[8:12]}-{masked[12:]}"
        return masked

    def handle(self, log: dict) -> dict:
        user_details = log.get("user_details", {})
        anonymized = False
        
        # 1. Yapısal verileri maskele
        if "credit_card" in user_details:
            orig = user_details["credit_card"]
            user_details["credit_card"] = self.mask_cc(orig)
            if orig != user_details["credit_card"]:
                anonymized = True
                
        if "tc_no" in user_details:
            orig = user_details["tc_no"]
            user_details["tc_no"] = self.mask_tc(orig)
            if orig != user_details["tc_no"]:
                anonymized = True
                
        if "email" in user_details:
            orig = user_details["email"]
            user_details["email"] = self.mask_email(orig)
            if orig != user_details["email"]:
                anonymized = True

        # 2. Düz metin olan "message" alanı içinde KVKK verisi geçiyorsa regex ile maskele
        message = log.get("message", "")
        if message:
            orig_msg = message
            
            # E-postaları maskele
            message = self.EMAIL_REGEX.sub(lambda m: self.mask_email(m.group(0)), message)
            # Kredi kartlarını maskele
            message = self.CC_REGEX.sub(lambda m: self.mask_cc(m.group(0)), message)
            # TC No'ları maskele
            message = self.TC_REGEX.sub(lambda m: self.mask_tc(m.group(0)), message)
            
            log["message"] = message
            if orig_msg != message:
                anonymized = True
            
        if anonymized:
            MetricsCollector().record_anonymized()
            
        return super().handle(log)


class EnrichmentHandler(LogHandler):
    """
    Zenginleştirme İşleyicisi.
    Loglara mikroservislerin daha kolay analiz edebilmesi için ek bilgiler, etiketler
    ve debug parametreleri ekler.
    """
    HOSTNAME = socket.gethostname()

    def handle(self, log: dict) -> dict:
        level = log.get("level", "INFO").upper()
        
        # 1. Hata kritik olma durumu ("error_criticality")
        if level == "CRITICAL":
            log["error_criticality"] = "HIGH_CRITICALITY"
        elif level == "ERROR":
            log["error_criticality"] = "MEDIUM_CRITICALITY"
        else:
            log["error_criticality"] = "LOW_CRITICALITY"
            
        # 2. İşlendiği sunucu/konteyner bilgisi
        log["processed_node"] = self.HOSTNAME
        
        # 3. Mikroservisler için yönlendirme etiketi
        log["microservice_route"] = "security-monitoring-service" if level == "CRITICAL" else "transaction-archive-service"
        
        # 4. Debug ve gecikme (latency) ölçüm verileri
        log["debug"] = {
            "received_timestamp": log["timestamp"],
            "processed_timestamp": time.time(),
            "latency_offset_ms": (time.time() - log["timestamp"]) * 1000
        }
        
        return super().handle(log)
