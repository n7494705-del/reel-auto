#!/usr/bin/env python3
"""Avtomat Instagram Reel: ssenariy (Gemini) -> ovoz (edge-tts) -> rasm -> video (ffmpeg) -> Instagram."""
import os, json, subprocess, asyncio, urllib.request, urllib.parse, urllib.error, time, random, pathlib

ROOT = pathlib.Path(__file__).parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
HIST_F = ROOT / "history.json"
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)
W, H = 1080, 1920
MODE = os.environ.get("MODE_OVERRIDE") or CFG.get("mode", "draft")


def http(url, data=None, headers=None, method=None, timeout=120):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} {url.split('?')[0]}: {e.read()[:600]!r}")


def make_script(past_titles):
    key = os.environ["GEMINI_API_KEY"]
    topics = CFG.get("topics") or []
    topic = random.choice(topics) if topics else "o'zing tanla"
    prompt = f"""Sen Instagram Reels ssenariy yozuvchisan. Til: {CFG['language']}.
Yo'nalish: {CFG['niche']}. Uslub: {CFG['style']}. Mavzu: {topic}.
Oxirgi videolar (takrorlama): {past_titles[-15:]}
{CFG['scenes']} ta sahna. Hamma diktor matni birga o'qilganda taxminan {CFG['seconds']} soniya bo'lsin.
Ekranda yozuv bo'lmaydi, faqat diktor ovozi. Birinchi sahna kuchli ilgak bo'lsin, oxirgisi qiziqish qoldirsin.
Faqat JSON qaytar, shu shaklda:
{{"title": "qisqa sarlavha", "caption": "Instagram izohi", "scenes": [{{"narration": "diktor matni", "image_prompt": "ingliz tilida vertikal sinematik rasm tavsifi, matnsiz"}}]}}"""
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{CFG['gemini_model']}:generateContent?key={key}"
    last = None
    for _ in range(4):
        try:
            r = json.loads(http(url, body, {"Content-Type": "application/json"}))
            d = json.loads(r["candidates"][0]["content"]["parts"][0]["text"])
            assert d["scenes"] and all("narration" in s and "image_prompt" in s for s in d["scenes"])
            return d
        except Exception as e:  # 429/503 yoki noto'g'ri JSON: qayta urinish
            last = e
            print("Gemini xato:", e)
            time.sleep(25)
    raise SystemExit(f"Gemini ishlamadi: {last}")


async def _edge(text, path):
    import edge_tts
    await edge_tts.Communicate(text, CFG["voice"], rate=CFG.get("rate", "+0%")).save(str(path))


def tts(text, path):
    try:
        asyncio.run(_edge(text, path))
        if path.stat().st_size < 1000:
            raise RuntimeError("bo'sh audio")
    except Exception as e:
        print("edge-tts xato, gTTS ishlatiladi:", e)
        from gtts import gTTS
        gTTS(text, lang="uz").save(str(path))


def duration(p):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)])
    return float(out.decode().strip())


def get_image(prompt, path):
    q = urllib.parse.quote(prompt + ", vertical 9:16, cinematic, no text, no watermark")
    url = f"https://image.pollinations.ai/prompt/{q}?width={W}&height={H}&nologo=true&seed={random.randint(1, 99999)}"
    for _ in range(3):
        try:
            b = http(url, timeout=180)
            if len(b) > 5000:
                path.write_bytes(b)
                return
        except Exception as e:
            print("Rasm xato:", e)
        time.sleep(8)
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=0x12121c:s={W}x{H}", "-frames:v", "1", str(path)],
                   check=True, capture_output=True)


def make_clip(img, audio, d, out):
    dd = d + 0.4
    frames = int(dd * 30) + 1
    fc = (f"[0:v]scale=1620:-2,zoompan=z='min(zoom+0.0008,1.15)':d={frames}:"
          f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps=30,format=yuv420p[v];"
          f"[1:a]apad=pad_dur=0.4[a]")
    subprocess.run(["ffmpeg", "-y", "-i", str(img), "-i", str(audio), "-filter_complex", fc,
                    "-map", "[v]", "-map", "[a]", "-t", f"{dd:.2f}",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                    "-c:a", "aac", "-ar", "44100", "-ac", "2", str(out)], check=True, capture_output=True)


def ig_post(video, caption):
    tok = os.environ["IG_TOKEN"]
    uid = CFG["ig_user_id"]
    g = f"https://graph.facebook.com/{CFG.get('graph_version', 'v23.0')}"

    def post(url, fields):
        return json.loads(http(url, urllib.parse.urlencode(fields).encode(),
                               {"Content-Type": "application/x-www-form-urlencoded"}))

    c = post(f"{g}/{uid}/media", {"media_type": "REELS", "upload_type": "resumable",
                                  "caption": caption, "access_token": tok})
    cid, uri = c["id"], c["uri"]
    data = video.read_bytes()
    http(uri, data, {"Authorization": "OAuth " + tok, "offset": "0", "file_size": str(len(data))},
         method="POST", timeout=600)
    for _ in range(40):
        s = json.loads(http(f"{g}/{cid}?fields=status_code,status&access_token={tok}"))
        print("Holat:", s)
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise SystemExit("Instagram xato: " + json.dumps(s))
        time.sleep(15)
    else:
        raise SystemExit("Instagram vaqti tugadi")
    r = post(f"{g}/{uid}/media_publish", {"creation_id": cid, "access_token": tok})
    print("Joylandi:", r)


def main():
    hist = json.loads(HIST_F.read_text(encoding="utf-8")) if HIST_F.exists() else []
    d = make_script([h["title"] for h in hist])
    print("Sarlavha:", d["title"])
    work = OUT / "work"
    work.mkdir(exist_ok=True)
    clips = []
    for i, s in enumerate(d["scenes"]):
        a, im, c = work / f"a{i}.mp3", work / f"i{i}.jpg", work / f"c{i}.mp4"
        tts(s["narration"], a)
        get_image(s["image_prompt"], im)
        make_clip(im, a, duration(a), c)
        clips.append(c)
        print(f"Sahna {i + 1}/{len(d['scenes'])} tayyor")
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    raw, final = work / "raw.mp4", OUT / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(raw)],
                   check=True, capture_output=True)
    music = ROOT / "music" / "bg.mp3"
    if music.exists():
        subprocess.run(["ffmpeg", "-y", "-i", str(raw), "-stream_loop", "-1", "-i", str(music), "-filter_complex",
                        f"[1:a]volume={CFG.get('music_volume', 0.12)}[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]",
                        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-shortest", str(final)],
                       check=True, capture_output=True)
    else:
        raw.replace(final)
    caption = d["caption"].strip() + "\n\n" + " ".join(CFG.get("hashtags", []))
    (OUT / "caption.txt").write_text(caption, encoding="utf-8")
    (OUT / "script.json").write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    posted = False
    if MODE == "auto":
        ig_post(final, caption)
        posted = True
    else:
        print("Draft rejimi: video Instagramga joylanmadi, 'out' papkasida saqlandi.")
    hist.append({"title": d["title"], "date": time.strftime("%Y-%m-%d"), "posted": posted})
    HIST_F.write_text(json.dumps(hist[-100:], ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
