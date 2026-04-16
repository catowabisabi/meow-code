# OpenClaw Daily YouTube → Podcast → Telegram/YouTube Workflow

## 完整自動化工作流設計

### 目標
每日自動：
1. 監控 YouTube 頻道列表
2. 檢測當日新影片
3. 下載影片音頻
4. Speech-to-Text 轉文字
5. AI 改寫為中英文 Podcast 腳本
6. TTS 生成雙語語音
7. 合成 MP4（封面 + 音頻 + 字幕）
8. 發送到 Telegram
9. 自動上傳到 YouTube
10. 記錄已處理影片 ID

---

## 工作流架構

### Layer 1: Data Pipeline（自己寫）
- YouTube RSS → fetch new videos
- yt-dlp → download audio
- faster-whisper → transcribe
- LLM → rewrite script

### Layer 2: Distribution（用 ClawHub Skills）
- ElevenLabs / Edge TTS → voice
- FFmpeg → render MP4
- telegram-api → send to Telegram
- youtube-uploader → upload YouTube

---

## ClawHub Skill Mapping

| Step | 功能 | ClawHub Skill | Install Command | 評分/下載 |
|------|------|---------------|-----------------|-----------|
| ① | YouTube 頻道監控 | **youtube-summarizer** | `git clone` | ⭐ 1, 43 stars |
| ② | 下載影片/音頻 | **yt-dlp-downloader** | `clawhub install apollo1234/yt-dlp-downloader-skill` | ⭐ 5, 5.2k downloads |
| ③ | Speech-to-Text | **faster-whisper** | `clawhub install theplasmak/faster-whisper` | ⭐ 4, 5.1k downloads |
| ④ | AI 改寫腳本 | ❌ 需自寫 | LLM call 自己寫 | - |
| ⑤ | TTS 雙語語音 | **ElevenLabs TTS** | `clawhub install elevenlabs-tts` | 272 installs |
| ⑥ | 合併 MP4 | **ffmpeg-video-editor** | `clawhub install mahmoudadelbghany/ffmpeg-video-editor` | ⭐ 16, 10.1k |
| ⑦ | 發送 Telegram | **telegram-api** | `clawhub install byungkyu/telegram-api` | ⭐ 9, 6.5k |
| ⑧ | 上傳 YouTube | **youtube-uploader** | `clawhub install vk/youtube-uploader` | ⭐ 4, 924 |

---

## 詳細步驟

### Step 1: 每日 Scheduler
建議每日朝早 7:00 自動執行。
```yaml
schedule:
  cron: "0 7 * * *"
  timezone: "America/Toronto"
```

### Step 2: YouTube Channel List Source
建立配置文件：
```yaml
channels:
  - UCxxxxxxx1
  - UCxxxxxxx2
  - UCxxxxxxx3
```
或使用 RSS：
```
https://www.youtube.com/feeds/videos.xml?channel_id=XXXX
```

### Step 3: 搜尋當日新影片
邏輯：
- 讀取 channel 最新影片
- 比對 publishedAt
- 只處理今日影片
- 避免重覆處理

```python
if video.publish_date.date() == today:
    process(video)
```

保存 processed_videos.json：
```json
{
  "done": ["abc123", "def456"]
}
```

### Step 4: 下載影片 / 音訊
使用 yt-dlp：
```bash
yt-dlp -x --audio-format mp3 <youtube_url>
# 如果有字幕：
yt-dlp --write-auto-sub --sub-lang en
```

### Step 5: Speech to Text
如果無字幕，直接用 Whisper：
```python
transcript = whisper.transcribe(audio_file)
# 輸出：
# - 原始逐字稿 transcript.txt
```

### Step 6: AI 改寫為雙語 Podcast
Prompt 模板：
```
請將以下 YouTube 影片內容整理成 podcast 對話稿。

要求：
1. 先中文（廣東話口語）
2. 再英文版本
3. 風格自然似 podcast host
4. 保留重點資訊
5. 長度控制 5-8 分鐘
6. 適合旁白朗讀

輸出：
- script_zh.txt
- script_en.txt
```

### Step 7: TTS 語音生成
可分兩條音軌：
```python
voice_zh = tts(script_zh)
voice_en = tts(script_en)
# 最後合併：
final_audio = merge(voice_zh, voice_en)
```

### Step 8: 生成 MP4
用固定 Podcast Cover + waveform：
```bash
ffmpeg -loop 1 -i cover.jpg -i audio.mp3 \
  -shortest -c:v libx264 -c:a aac output.mp4
# 加字幕：
ffmpeg -vf subtitles=subtitle.srt
```

### Step 9: 發送 Telegram
```python
bot.send_video(chat_id, "output.mp4")
# Caption：
# 今日 YouTube 精華 Podcast 已生成
# 來源: Channel Name
```

### Step 10: 自動上傳 YouTube
標題格式：
```
Daily AI Podcast | {影片主題} | 中英雙語
```

Description：
```
由 AI 自動整理當日 YouTube 內容並生成 Podcast。
```

Tags：
```
podcast, ai summary, bilingual, daily news
```

---

## ClawHub Skill 詳情

### ① YouTube Summarizer
- GitHub: github.com/happynocode/openclaw-skill-youtube
- 功能: Dual-method transcript fetching, batch processing, cron-friendly
- 特色: RSS watcher + AI summary generation

### ② yt-dlp Downloader
- ClawHub: clawhub.ai/skills/yt-dlp-downloader-skill
- 安裝: `pip install yt-dlp`, `brew install ffmpeg`
- 注意: YouTube 建議用 cookies 避免 403

### ③ faster-whisper
- ClawHub: clawhub.ai/skills/faster-whisper
- 功能: 本地運行，比 Whisper 快 4-6x，支援 GPU
- 輸出: SRT, VTT, ASS, LRC, CSV, TXT

### ④ AI Rewrite（需自寫）
- 使用 LLM API 包裝
- Prompt template 需要自己設計

### ⑤ ElevenLabs TTS
- ClawHub: clawhub.ai/skills/elevenlabs-tts
- Alternative: Edge TTS（免費）
- ClawHub: clawhub.ai/skills/edge-tts

### ⑥ FFmpeg Video Editor
- ClawHub: clawhub.ai/skills/ffmpeg-video-editor
- 功能: 自然語言 → FFmpeg 命令
- 特色: 壓縮、剪輯、合併、音頻提取

### ⑦ Telegram API
- ClawHub: clawhub.ai/skills/telegram-api
- 功能: Bot API 整合，send video/photo/audio
-  Alternative: tsend (CLI)
- ClawHub: clawskills.sh/skills/shingwha-tsend

### ⑧ YouTube Uploader
- ClawHub: clawhub.ai/skills/youtube-uploader
- 功能: OAuth2 認證，上傳視頻 + 縮圖
- 安全性: VirusTotal: Benign

---

## 安全警告

| Skill | 安全性 | 建議 |
|-------|--------|------|
| `youtube-uploader` | ✅ VirusTotal: Benign | 可用 |
| `telegram-api` | ✅ VirusTotal: Benign | 可用 |
| `faster-whisper` | ✅ 本地運行 | 私隱安全 |
| `yt-dlp-downloader` | ⚠️ 多個版本 | 建議自己寫命令 |
| `ffmpeg-video-editor` | ⚠️ flagged | 檢查 SKILL.md |

---

## 下一步

可以幫你寫成 production-ready Python workflow script，包含：
- Scheduler / cron
- Telegram bot integration
- YouTube API upload
- FFmpeg render
- OpenClaw task chain

全部代碼可直接 deploy 到 Ubuntu / Synology server。
