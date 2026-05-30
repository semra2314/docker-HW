import asyncio
import json
import os
import random
import sys
import time
from log_factory import LogFactory

# Ortam değişkenlerinden (environment variables) yapılandırma bilgilerini çekelim
MIDDLEWARE_HOST = os.environ.get("MIDDLEWARE_HOST", "localhost")
MIDDLEWARE_PORT = int(os.environ.get("MIDDLEWARE_PORT", 9999))
RATE_LIMIT = int(os.environ.get("RATE_LIMIT", 5000))  # Saniyede gönderilecek log sayısı (0 ise sınırsız/en hızlı)
TOTAL_LOGS = int(os.environ.get("TOTAL_LOGS", 100000)) # Benchmark için üretilecek toplam log sayısı

async def send_logs():
    print(f"[Generator] Ara Katmana bağlanılıyor: {MIDDLEWARE_HOST}:{MIDDLEWARE_PORT}...")
    
    # Sunucu henüz açılmamış olabilir (özellikle Docker Compose başlatılırken).
    # Bu yüzden bağlantı kurulana kadar yeniden deneme (retry) mekanizması ekliyoruz.
    retry_count = 0
    writer = None
    while retry_count < 15:
        try:
            reader, writer = await asyncio.open_connection(MIDDLEWARE_HOST, MIDDLEWARE_PORT)
            print("[Generator] Ara Katman sunucusuna bağlantı başarıyla sağlandı!")
            break
        except Exception as e:
            retry_count += 1
            print(f"[Generator] Bağlantı kurulamadı. Yeniden deneniyor ({retry_count}/15)... Hata: {e}")
            await asyncio.sleep(2)
            
    if not writer:
        print("[Generator] Sunucuya bağlanılamadı. Uygulama sonlandırılıyor.")
        sys.exit(1)

    # Gerçekçi bir borsa trafiğindeki logların dağılımı (Senaryolar ve Ağırlıkları)
    # Çoğunluk INFO/WARNING loglarından oluşur, bu sayede filtreleme performansını iyi gözlemleriz.
    scenarios = ["transaction_success", "transaction_warning", "transaction_error", "critical_security_alert", "unauthorized_access"]
    weights = [0.60, 0.20, 0.10, 0.05, 0.05] # %60 Başarılı, %20 Sınır Uyarısı, %10 Hata, %5 Güvenlik Uyarısı, %5 Yetkisiz Erişim
    
    sent_count = 0
    start_time = time.time()
    
    print(f"[Generator] Log akışı başlatılıyor. Toplam Log: {TOTAL_LOGS}, Hız Sınırı: {RATE_LIMIT} log/sn.")
    
    try:
        batch_size = 100 # Soket yazma işlemini optimize etmek için paketler halinde (batch) yazıyoruz
        while sent_count < TOTAL_LOGS:
            current_batch = min(batch_size, TOTAL_LOGS - sent_count)
            batch_start = time.time()
            
            for _ in range(current_batch):
                # Ağırlıklarına göre rastgele bir senaryo seçip fabrikadan (Factory Pattern) log üretiyoruz
                scenario = random.choices(scenarios, weights=weights)[0]
                log_data = LogFactory.create_log(scenario)
                
                # Newline-Delimited JSON (NDJSON) formatında TCP sokete yazıyoruz
                log_str = json.dumps(log_data) + "\n"
                writer.write(log_str.encode('utf-8'))
                sent_count += 1
                
            # Tampon bellekteki (buffer) verileri ağa gönderiyoruz
            await writer.drain()
            
            # Hız sınırlama (Throttling) mekanizması
            if RATE_LIMIT > 0:
                elapsed = time.time() - batch_start
                expected_time = current_batch / RATE_LIMIT
                if elapsed < expected_time:
                    await asyncio.sleep(expected_time - elapsed)
                    
            # Her 10.000 logda bir durum raporu veriyoruz
            if sent_count % 10000 == 0:
                elapsed_total = time.time() - start_time
                avg_tps = sent_count / elapsed_total
                print(f"[Generator] Gönderilen Log: {sent_count}/{TOTAL_LOGS}. Anlık Ortalama Hız: {avg_tps:.2f} log/sn.")
                
    except Exception as e:
        print(f"[Generator] Log gönderimi sırasında hata oluştu: {e}")
    finally:
        print(f"[Generator] Bağlantı kapatılıyor. Toplam gönderilen log: {sent_count}")
        writer.close()
        await writer.wait_closed()
        
    elapsed_total = time.time() - start_time
    print(f"[Generator] Tamamlanma süresi: {elapsed_total:.2f} saniye. Ortalama Gönderim Hızı: {sent_count / elapsed_total:.2f} log/sn.")

if __name__ == "__main__":
    asyncio.run(send_logs())
