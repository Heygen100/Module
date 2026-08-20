# Güvenli hata mesajı düzeltmeleri

Bu paket, modüllerin kullanıcıya gönderdiği hata yanıtlarında ham istisna metinlerinin, yerel klasör adlarının ve dosya yollarının görünmesini engellemek için hazırlanmıştır.

## Düzeltilen dosyalar

`sendergifts-DoxTeam-repo.py` içinde banner görseli `https://raw.githubusercontent.com/Heygen100/Module/main/DoxPNG.png` olarak güncellendi. Hediye gönderimi başarısız olduğunda kullanıcıya artık ham Python/Telegram istisnası gösterilmiyor; ayrıntı yalnızca modül loguna yazılıyor.

`afk_mod-DoxTeam-repo.py` incelendi. AFK komutları ve AFK watcher zaten kullanıcıya genel hata mesajı gösteriyor ve hatayı `kernel.handle_error` üzerinden işliyor; bu dosyada doğrudan klasör yolu veya `str(e)` sızıntısı bulunmadığı için davranış değiştirilmedi.

`admin-mod-DoxTeam-repo.py`, `core-loader-DoxTeam-repo.py`, `fastfetch-DoxTeam-repo.py`, `k-accoutdata-DoxTeam-repo.py`, `liber/gitrepo-DoxTeam-liber.py`, `liber/pictostories-DoxTeam-liber.py`, `liber/zenqutes-DoxTeam-liber.py`, `liber/spam-sms-DoxTeam-liber.py`, `shorturl-DoxTeam-repo.py`, `tabfix-tool-DoxTeam-repo.py`, `watcher-last-fm-DoxTeam-repo.py` ve `ytm-beta-DoxTeam-repo.py` içinde kullanıcıya gösterilen ham hata ayrıntıları güvenli genel mesajlarla değiştirildi.

## Doğrulama

Paket içindeki Python dosyaları `python3 -m compileall` ile kontrol edildi ve sözdizimi hatası bulunmadı. Son taramada kullanıcıya açık `str(e)`, `str(exc)`, `error=str(...)`, `err=str(...)` ve benzeri ham hata kalıpları kalmadı.

> Not: Loglara yazılan tanı amaçlı hata kayıtları korunmuştur. Değişiklik yalnızca Telegram sohbetine veya komut yanıtına gönderilen hata metnini sınırlar.
