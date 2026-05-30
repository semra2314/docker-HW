from abc import ABC, abstractmethod
import json
import time

class FormatterStrategy(ABC):
    """
    Strategy (Strateji) Tasarım Kalıbı Arayüzü.
    Farklı kullanıcı rolleri için çıktı formatlama davranışını soyutlar.
    """
    @abstractmethod
    def format(self, log: dict) -> str:
        """Log verisini ilgili formata dönüştürür."""
        pass
    
    @abstractmethod
    def get_header(self) -> str:
        """Dosya başlangıcında yazılması gereken başlık (örn: HTML tagleri veya CSV kolon adları)."""
        pass

    @abstractmethod
    def get_footer(self) -> str:
        """Dosya sonlandırılırken yazılması gereken kapanış şablonu."""
        pass


class HtmlFormatter(FormatterStrategy):
    """
    System Admin rolü için tasarlanmış HTML formatlayıcı.
    Kritiklik seviyelerine göre renk kodlamalı şık bir tablo çıktısı verir.
    """
    def format(self, log: dict) -> str:
        level = log.get("level", "INFO").upper()
        # Seviyeye göre CSS sınıfı belirleyelim
        level_class = f"level-{level.lower()}"
        
        # Zaman damgasını okunabilir formata dönüştürelim
        readable_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(log.get("timestamp", time.time())))
        
        user_details = log.get("user_details", {})
        name = user_details.get("name", "N/A")
        tc_no = user_details.get("tc_no", "N/A")
        cc_no = user_details.get("credit_card", "N/A")
        email = user_details.get("email", "N/A")
        ip = user_details.get("ip_address", "N/A")
        
        # Ek zenginleştirilmiş bilgiler
        sender_id = log.get("sender_id", "N/A")
        txn_no = log.get("transaction_no", "N/A")
        log_type = log.get("type", "N/A")
        status = log.get("status", "N/A")
        message = log.get("message", "")
        criticality = log.get("error_criticality", "N/A")
        
        return f"""        <tr class="{level_class}">
            <td>{readable_time}</td>
            <td><strong>{level}</strong></td>
            <td>{sender_id}</td>
            <td>{txn_no}</td>
            <td>{log_type}</td>
            <td>{status}</td>
            <td>{criticality}</td>
            <td>{message}</td>
            <td>{name}</td>
            <td>{tc_no}</td>
            <td>{cc_no}</td>
            <td>{email}</td>
            <td>{ip}</td>
        </tr>
"""

    def get_header(self) -> str:
        return """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Sistem Admin Log Raporu</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #0f172a;
            color: #f1f5f9;
            padding: 20px;
            margin: 0;
        }
        h1 {
            color: #38bdf8;
            border-bottom: 2px solid #334155;
            padding-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background-color: #1e293b;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            border-radius: 8px;
            overflow: hidden;
        }
        th {
            background-color: #334155;
            color: #38bdf8;
            text-align: left;
            padding: 12px 15px;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        tr {
            border-bottom: 1px solid #334155;
            transition: background-color 0.2s;
        }
        tr:hover {
            background-color: #1e293b90 !important;
        }
        td {
            padding: 10px 15px;
            font-size: 13px;
            word-break: break-all;
        }
        .level-critical { background-color: #7f1d1d40; color: #fca5a5; border-left: 5px solid #ef4444; }
        .level-error { background-color: #7c2d1240; color: #fdba74; border-left: 5px solid #f97316; }
        .level-warning { background-color: #713f1240; color: #fde047; border-left: 5px solid #eab308; }
        .level-info { background-color: #064e3b40; color: #6ee7b7; border-left: 5px solid #10b981; }
    </style>
</head>
<body>
    <h1>Borsa İşlemleri Canlı Log İzleme Paneli (System Admin)</h1>
    <p>Bu rapor sistem yöneticileri için kritiklik durumlarına göre renklendirilmiştir.</p>
    <table>
        <thead>
            <tr>
                <th>Zaman</th>
                <th>Seviye</th>
                <th>Gönderici ID</th>
                <th>İşlem No</th>
                <th>Tip</th>
                <th>Durum</th>
                <th>Kritiklik</th>
                <th>Mesaj</th>
                <th>Kullanıcı</th>
                <th>TC Kimlik</th>
                <th>Kredi Kartı</th>
                <th>E-Posta</th>
                <th>IP Adresi</th>
            </tr>
        </thead>
        <tbody>
"""

    def get_footer(self) -> str:
        return """        </tbody>
    </table>
</body>
</html>
"""


class CsvFormatter(FormatterStrategy):
    """
    CyberSec (Siber Güvenlik) rolü için tasarlanmış CSV formatlayıcı.
    Veriyi virgülle ayrılmış, kolayca SIEM araçlarına aktarılabilir şekilde sunar.
    """
    def format(self, log: dict) -> str:
        user_details = log.get("user_details", {})
        
        # CSV formatı için değerlerin temizlenmesi ve çift tırnak içine alınması (kaçış karakteriyle)
        def escape_csv(val):
            val_str = str(val).replace('"', '""')
            return f'"{val_str}"'

        row = [
            escape_csv(log.get("timestamp", "")),
            escape_csv(log.get("level", "")),
            escape_csv(log.get("sender_id", "")),
            escape_csv(log.get("transaction_no", "")),
            escape_csv(log.get("type", "")),
            escape_csv(log.get("status", "")),
            escape_csv(log.get("error_criticality", "NONE")),
            escape_csv(log.get("message", "")),
            escape_csv(user_details.get("name", "")),
            escape_csv(user_details.get("tc_no", "")),
            escape_csv(user_details.get("credit_card", "")),
            escape_csv(user_details.get("email", "")),
            escape_csv(user_details.get("ip_address", ""))
        ]
        return ",".join(row) + "\n"

    def get_header(self) -> str:
        # CSV Kolon Başlıkları
        headers = ["timestamp", "level", "sender_id", "transaction_no", "type", "status", "criticality", "message", "name", "tc_no", "credit_card", "email", "ip_address"]
        return ",".join(headers) + "\n"

    def get_footer(self) -> str:
        return ""


class JsonFormatter(FormatterStrategy):
    """
    Web Dev (Web Geliştirici) rolü için tasarlanmış JSON formatlayıcı.
    İşlenmiş log nesnesini direkt temiz JSON formatında (NDJSON/JSON-Lines) sunar.
    """
    def format(self, log: dict) -> str:
        return json.dumps(log, ensure_ascii=False) + "\n"

    def get_header(self) -> str:
        return ""

    def get_footer(self) -> str:
        return ""
