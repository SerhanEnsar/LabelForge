# LabelForge — YOLO Dataset Editor (Tactical Edition)

![Ana Ekran Görünümü](assets/images/Ekran%20Resmi%202026-05-17%2001.54.54.png)

LabelForge, bilgisayarlı görü (computer vision) projelerinde sıklıkla kullanılan YOLO formatındaki veri setlerini hızlı, güvenilir ve detaylı bir şekilde düzenlemek, incelemek ve genişletmek için geliştirilmiş güçlü bir masaüstü uygulamasıdır. Özel "Tactical" (koyu yeşil/siyah) teması ile göz yormadan uzun süreli çalışmalara imkan tanır. Uygulama Tkinter, CustomTkinter ve Pillow (PIL) kullanılarak geliştirilmiş olup, yüksek performanslı görsel ve etiket manipülasyonu sunar.

## Temel Özellikler

![Özellikler Görünümü](assets/images/Ekran%20Resmi%202026-05-17%2001.55.39.png)

### Modern ve Gelişmiş Kullanıcı Arayüzü
LabelForge, klasik ve sıkıcı arayüzlerin aksine CustomTkinter tabanlı "Dark" temalı bir tasarım sunar. Uygulama, çalışma alanınızı maksimize etmek için çoklu panel düzeni (paned window) kullanır. Sol panelde görseller ve sınıflar, orta panelde orijinal ve etiketli görseller, sağ panelde ise etiket listesi ve araçlar bulunur.

### Kapsamlı Görsel ve Etiket Yönetimi
- **Otomatik Tarama:** Seçilen klasördeki görseller ve YOLO formatındaki (`.txt`) etiketler saniyeler içinde taranıp eşleştirilir.
- **Sınıf (Class) Yönetimi:** `classes.txt` dosyası otomatik olarak okunur. Arayüz üzerinden yeni sınıflar eklenebilir, isimleri değiştirilebilir veya gereksiz sınıflar tamamen silinebilir. Renk atamaları her bir sınıf için benzersiz ve görsel olarak ayırt edici şekilde yapılır.
- **İncelendi İşaretleme:** Uzun veri setlerinde nerede kaldığınızı unutmamak için görselleri "İncelendi" (Reviewed) olarak işaretleyebilirsiniz (Görsel ismine çift tıklayarak). Bu veri, oturumlar arasında kaydedilir.

### Profesyonel Bounding Box (BBox) Çizimi ve Düzenlemesi

![BBox Çizim Ekranı](assets/images/Ekran%20Resmi%202026-05-17%2001.55.53.png)

- **Gelişmiş Görüntüleme:** Fare tekerleği (Scroll/Pinch) ile hassas yakınlaştırma (Zoom) ve sürükleyerek kaydırma (Pan) özellikleri mevcuttur. "FIT" butonu ile görsel anında orijinal görünümüne sıfırlanabilir.
- **Manuel Çizim Modu:** Eksik veya yeni tespit edilecek objeler için özel "Manuel BBox Çiz" ekranı açılabilir. Buradan istediğiniz sınıfı seçip sürükle-bırak yöntemiyle yeni sınırlayıcı kutular ekleyebilirsiniz.
- **Seçme ve Silme:** Tam ekran "Annotated" (Etiketli) görünümünde, tıklayarak veya sürükleyerek birden fazla BBox seçilebilir ve `DEL` veya `Command+Backspace` (Mac) tuşuyla hızlıca silinebilir.
- **Geri Alma / Yineleme (Undo / Redo):** Yapılan yanlış düzenlemeleri ve silmeleri anında geri alabilir veya yineleyebilirsiniz (`Ctrl+Z`, `Ctrl+Y`).

### Tam Ekran Detay Görünümü

![Tam Ekran İnceleme](assets/images/Ekran%20Resmi%202026-05-17%2001.56.11.png)

Görsellerdeki küçük detayları daha iyi inceleyebilmek adına "Orijinal" veya "Etiketli" (Annotated) görseller tam ekran penceresinde açılabilir. Tam ekran modundayken gelişmiş fare ve klavye kontrolleri aktif kalır.

### Oturum Kaydetme (Session Tracking)
Yaptığınız klasör seçimleri, sınıflar, "incelendi" olarak işaretlediğiniz dosyalar ve en son görüntülenen dosya, uygulamanın bir sonraki açılışında otomatik olarak yüklenmek üzere kaydedilir (`~/.labelforge_session.json`).

---

## Gereksinimler ve Kurulum

Projeyi bilgisayarınızda çalıştırmak için aşağıdaki Python kütüphanelerinin kurulu olması gerekmektedir:

- Python 3.8 veya üzeri
- `customtkinter`
- `Pillow`

**Kurulum Adımları:**

1. Repoyu bilgisayarınıza klonlayın:
   ```bash
   git clone https://github.com/KULLANICI_ADINIZ/LabelForge.git
   cd LabelForge
   ```

2. Gerekli kütüphaneleri yükleyin:
   ```bash
   pip install customtkinter Pillow
   ```

3. Uygulamayı başlatın:
   ```bash
   python labelforge.py
   ```

---

## Kullanım Rehberi

![Kullanım Arayüzü](assets/images/Ekran%20Resmi%202026-05-17%2001.57.47.png)

Projeyi başlattıktan sonra aşağıdaki adımları izleyerek etiketleme işlemine başlayabilirsiniz:

### 1. Klasörleri Seçme
Üst barda yer alan menüden:
- **DATASET:** Eğer veri setiniz ana bir dizinde (içinde `images`, `labels` ve `classes.txt` barındırıyorsa) bulunuyorsa bu klasörü seçmeniz yeterlidir. Diğer klasörler otomatik algılanır.
- Veya manuel olarak **GÖRSELLER** ve **ETİKETLER** klasörlerini ayrı ayrı seçebilirsiniz.
- Klasörleri seçtikten sonra **TARA** butonuna tıklayarak görselleri sol panele yükleyin.

### 2. Arayüz Kontrolleri
- **Sol Tık ve Sürükle:** Görüntüyü kaydırır (Pan).
- **Fare Tekerleği (Mouse Wheel/Touchpad):** Farenin bulunduğu noktaya yakınlaştırma/uzaklaştırma yapar (Zoom).
- **Yön Tuşları:** Görsel listesinde hızlıca gezinmeyi veya çizim ekranında görseli kaydırmayı sağlar.

### 3. Etiket Düzenleme
- Sağ panelden mevcut kutular listesini görebilir, yanlarındaki "✕" butonu ile silebilirsiniz.
- Orijinal görüntü ekranındaki **✏ MANUEL BBOX ÇİZ** butonuna basarak yeni etiketleme penceresine geçiş yapabilirsiniz.
- Çizim modunda sol menüden sınıfınızı seçin, görsel üzerinde sol tıkla sürükleyerek kutuyu çizin ve "Uygula" butonuna basarak kaydedin.

### 4. Sınıf (Class) Ayarları
Sol alt kısımda yer alan "SINIF ETİKETLERİ" panelinden her bir sınıfın yanındaki "⋯" (üç nokta) ikonuna tıklayarak o sınıfı silebilir, yeniden adlandırabilir veya o sınıfa ait o anki görseldeki tüm etiketleri tek seferde kaldırabilirsiniz.

---

## Katkıda Bulunma

Bu proje açık kaynaklıdır. Projeye katkıda bulunmak isterseniz:
1. Bu depoyu "Fork"layın.
2. Yeni bir özellik dalı oluşturun (`git checkout -b ozellik/YeniOzellik`).
3. Değişikliklerinizi commit edin (`git commit -m 'Yeni bir özellik eklendi'`).
4. Dalınıza push yapın (`git push origin ozellik/YeniOzellik`).
5. Bir "Pull Request" oluşturun.

## Lisans
Bu proje [MIT Lisansı](LICENSE) altında lisanslanmıştır. İstediğiniz gibi kullanabilir ve geliştirebilirsiniz.
