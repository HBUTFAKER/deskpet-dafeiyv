# 蓝色大肥鱼 · 桌宠

一只住在桌面上的鲸鱼娘（🐋），能听你说话、用古河渚系少女音说日语、用中文气泡跟你聊。
基于 [dsh-pet](https://github.com/deepseek-ai/dsh) 桌宠框架 + 本地语音链路（faster-whisper 识别 / edge-tts 与 VOICEVOX 合成）。

> 本项目**不含任何明文密钥**，运行所需的 API Key 只存在你本机的 `config.local.json`（已被 `.gitignore` 排除）。

---

## 一、前提条件（好友安装前先确认）

| 项目 | 是否必须 | 说明 |
|------|----------|------|
| Windows 10/11 | ✅ | 桌面宠物 + 快捷键 + `.lnk` 均为 Windows 专属 |
| WorkBuddy / dsh 框架 + **dsh-pet 桌宠插件** | ✅ | 鱼的形象和窗口由 dsh-pet 渲染；没有它桌宠不会出现。本项目里的 `patch_*.py` 会给它加「右键退出 / 切换语言」菜单 |
| Python 3.11+ | ✅ | 由 WorkBuddy 自带，或自己装；`setup.bat` 会自动发现 |
| 自己的 DeepSeek API Key | ✅ | **别用别人的**，自己到平台申请，填进 `config.local.json` 或环境变量 `DEEPSEEK_API_KEY` |
| VOICEVOX 引擎（windows-cpu 版） | ⚠️ 可选 | 想要日语「古河渚系少女音」才需要；没装的话日语会自动退回 edge 音色 |

---

## 二、安装（好友视角）

```bat
git clone <本仓库地址> 蓝色大肥鱼
cd 蓝色大肥鱼
setup.bat
```

`setup.bat` 会自动：
1. 用 WorkBuddy 自带的 Python 建虚拟环境 `.venv`；
2. 安装 `requirements.txt` 里的依赖；
3. 在桌面生成「蓝色大肥鱼」快捷方式；
4. 给 dsh-pet 打补丁（右键菜单增强）。

### 填 Key
把 `config.example.json` 复制成 `config.local.json`，填入你自己的 DeepSeek Key：
```json
{
  "api_key": "sk-你的key",
  "voicevox_dir": "D:\\voicevox\\windows-cpu"
}
```
或直接设置环境变量 `DEEPSEEK_API_KEY`。

### 关于语音识别模型
`models/` 目录**没有**提交进仓库（约 460MB）。首次运行时程序会自动从 HuggingFace 下载 `whisper-small`（约 1.5GB，仅需一次，之后缓存）。
离线环境可手动把 `whisper-small` 放到 `models/` 下（需含 `model.bin`）。

---

## 三、使用

- **启动**：双击桌面「蓝色大肥鱼」。
- **退出**：右键屏幕上的鱼本体 → 「退出大肥鱼」（会先结束宿主再结束鱼，不会反复弹窗）。
- **切语言**：右键鱼本体 → 「切换语言」（中文 / 日本語）。
- **语音唤醒**：对着麦克风喊唤醒词（默认「小鱼」），再用中文或日语跟她说话。
- **日语模式**：声音是日语，但聊天气泡文字是中文。

---

## 四、目录说明

| 文件 | 作用 |
|------|------|
| `launcher.py` | 一键启动：宿主 → 日语引擎 → 语音桥 |
| `pet_voice.py` | 语音桥主循环（识别 / 合成 / 对话） |
| `pet_lang.py` | 中 / 日双语语言包 |
| `voicevox_pool.py` / `edge_tts_pool.py` | 两个 TTS 引擎封装 |
| `quit.py` | 清场脚本（被右键退出调用） |
| `patch_*.py` / `patch_all.py` | 给 dsh-pet 打补丁（幂等，可重跑） |
| `_make_lnk.py` | 生成桌面快捷方式 |
| `config.py` | 配置加载（密钥 / 路径，**不含明文**） |
| `config.example.json` | 配置模板 |
| `fatuiyu.ico` / `fatuiyu.png` | 桌面图标素材 |

> `config.local.json`、`*.log`、`models/`、`samples/`、`backup_dshpet/`、`.venv/` 等已被 `.gitignore` 排除，不会进仓库。
