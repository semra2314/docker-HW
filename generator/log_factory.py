import random
import time
import uuid

class LogFactory:
    """
    Factory Method Tasarım Kalıbı.
    Farklı finansal borsa senaryoları için aslına uygun (ve hassas KVKK verileri içeren)
    log yapıları üretir.
    """
    
    @staticmethod
    def generate_random_tc() -> str:
        # Türkiye Cumhuriyeti Kimlik Numarası üretimi (11 hane)
        first = str(random.randint(1, 9))
        rest = "".join(str(random.randint(0, 9)) for _ in range(10))
        return first + rest

    @staticmethod
    def generate_random_cc() -> str:
        # Kredi kartı numarası üretimi (16 hane, tireli veya düz formatta)
        prefix = str(random.choice([4, 5])) # 4: Visa, 5: Mastercard
        rest = "".join(str(random.randint(0, 9)) for _ in range(15))
        if random.choice([True, False]):
            return f"{prefix}{rest[:3]}-{rest[3:7]}-{rest[7:11]}-{rest[11:15]}"
        return prefix + rest

    @staticmethod
    def generate_random_email(name: str) -> str:
        # E-posta adresi üretimi
        domains = ["gmail.com", "yahoo.com", "outlook.com", "borsa.com.tr", "yatirim.com"]
        cleaned_name = name.lower().replace(" ", "").replace("ı", "i").replace("ö", "o").replace("ü", "u").replace("ş", "s").replace("ç", "c").replace("ğ", "g")
        return f"{cleaned_name}{random.randint(10, 99)}@{random.choice(domains)}"

    @classmethod
    def create_log(cls, scenario: str) -> dict:
        """
        Factory Method: Verilen senaryo türüne göre log sözlüğü (JSON şablonu) oluşturur.
        """
        names = ["Ahmet Yilmaz", "Mehmet Demir", "Ayse Kaya", "Fatma Celik", "Mustafa Sahin", "Emine Yildiz", "Can Ozkan", "Elif Aksu"]
        symbols = ["THYAO", "ASELS", "EREGL", "GARAN", "AKBNK", "BTCUSD", "ETHUSD", "KOCMT"]
        
        name = random.choice(names)
        tc_no = cls.generate_random_tc()
        cc_no = cls.generate_random_cc()
        email = cls.generate_random_email(name)
        sender_id = f"USR-{random.randint(1000, 9999)}"
        transaction_no = f"TXN-{uuid.uuid4().hex[:12].upper()}"
        timestamp = time.time()
        
        # KVKK kapsamına girecek hassas verileri içeren temel log şablonu
        log_base = {
            "timestamp": timestamp,
            "sender_id": sender_id,
            "transaction_no": transaction_no,
            "user_details": {
                "name": name,
                "tc_no": tc_no,
                "credit_card": cc_no,
                "email": email,
                "ip_address": f"{random.randint(192, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
            }
        }
        
        # Senaryoya göre log seviyesinin (level) ve detayların belirlenmesi
        if scenario == "transaction_success":
            log_base.update({
                "level": "INFO",
                "message": f"Successfully completed stock buy order for {random.randint(1, 100)} shares of {random.choice(symbols)}.",
                "type": "TRADE_EXECUTION",
                "status": "SUCCESS"
            })
        elif scenario == "transaction_warning":
            log_base.update({
                "level": "WARNING",
                "message": f"High value transaction warning: Buy order of {random.randint(10000, 50000)} shares of {random.choice(symbols)} exceeds daily average limit.",
                "type": "THRESHOLD_WARNING",
                "status": "PENDING_APPROVAL"
            })
        elif scenario == "transaction_error":
            log_base.update({
                "level": "ERROR",
                "message": f"Failed to execute sell order for {random.choice(symbols)}. Insufficient shares in portfolio.",
                "type": "TRADE_FAILURE",
                "status": "FAILED",
                "error_code": "ERR_INSUFFICIENT_SHARES"
            })
        elif scenario == "critical_security_alert":
            log_base.update({
                "level": "CRITICAL",
                "message": f"Suspicious IP range detected trying to authorize high-volume transaction. Suspicious email context: {email}.",
                "type": "SECURITY_BREACH",
                "status": "BLOCKED",
                "alert_id": f"SEC-{random.randint(10000, 99999)}"
            })
        elif scenario == "unauthorized_access":
            log_base.update({
                "level": "ERROR",
                "message": "Multiple failed login attempts with incorrect credentials.",
                "type": "AUTH_FAILURE",
                "status": "REJECTED"
            })
        else:
            log_base.update({
                "level": "INFO",
                "message": "Heartbeat check. System status healthy.",
                "type": "SYSTEM_HEARTBEAT",
                "status": "OK"
            })
            
        return log_base
