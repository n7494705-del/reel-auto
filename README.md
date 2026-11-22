# Avtomat Reel (mutlaqo bepul)

Har kuni o'zi: ssenariy yozadi (Gemini) -> o'zbekcha ovoz (edge-tts) -> rasmlar (Pollinations) -> video (ffmpeg) -> Instagramga joylaydi.
Hammasi GitHub Actions'da ishlaydi, kompyuteringiz yoki telefoningiz o'chiq bo'lsa ham.

## Sozlash (bir marta)

1. **GitHub'da repo oching** (Public bo'lsa Actions cheksiz bepul). Shu papkadagi hamma fayllarni yuklang.
2. **Gemini kaliti** (bepul): https://aistudio.google.com/apikey dan oling.
3. **Instagram tokeni**: Meta Developers'da ilova yarating, `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement` ruxsatlari bilan Graph API Explorer'dan token oling, uni uzoq muddatli (long-lived) qiling. Instagram akkauntingiz Facebook sahifasiga ulangan bo'lishi kerak. Bu eng qiyin qadam: Claude'ga yozing, birga bosqichma-bosqich qilamiz.
4. Repo -> Settings -> Secrets and variables -> Actions -> **New repository secret**:
   - `GEMINI_API_KEY`
   - `IG_TOKEN`
5. Repo -> Actions -> Reel -> **Run workflow** (mode: `draft`). Tugagach `reel` artifact'ini yuklab oling va videoni ko'ring.
6. Yoqsa, `config.json` da `"mode": "auto"` qiling. Shundan keyin har kuni 20:00 (Toshkent) da o'zi joylaydi.

## Hamma narsani o'zgartirish (config.json)

| Maydon | Nima qiladi |
|---|---|
| `mode` | `draft` faqat video yasaydi, `auto` Instagramga joylaydi |
| `niche`, `style`, `topics` | kontent yo'nalishi, uslub, mavzular ro'yxati |
| `scenes`, `seconds` | sahnalar soni, taxminiy davomiylik |
| `voice` | `uz-UZ-SardorNeural` (erkak) yoki `uz-UZ-MadinaNeural` (ayol) |
| `hashtags` | izohga qo'shiladigan teglar |
| `gemini_model` | Gemini modeli nomi (eskirsa yangilang) |

Vaqtni o'zgartirish: `.github/workflows/reel.yml` ichidagi `cron` qatori (UTC).
Fon musiqasi: `music/bg.mp3` faylini qo'ying, o'zi pastroq ovozda qo'shiladi.

## Muhim eslatmalar

- Bu kod hali haqiqiy akkauntlarda sinab ko'rilmagan. Birinchi ishga tushirishda xato chiqsa, Actions logini Claude'ga yuboring.
- Ovoz sun'iy (AI), rasmlar bepul xizmatdan: sifat pullik vositalardan past bo'ladi.
- Bepul xizmatlar (Gemini limiti, Pollinations) shartlarini o'zgartirishi mumkin.
- Instagram tokeni muddati tugaydi (uzoq muddatli token ~60 kun, sahifa tokeni cheksiz). Tugasa, `IG_TOKEN` ni yangilang.
- GitHub 60 kun faolsiz public repo'dagi jadvalni o'chiradi; `history.json` har kuni yangilanib turgani uchun bu bo'lmaydi.
