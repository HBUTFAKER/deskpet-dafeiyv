# 蓝色大肥鱼 · 桌宠

一只住在桌面上的鲸鱼娘：听见唤醒词后听你说话，用中文或日语回应，中文文字同步显示在头顶气泡里。

语音链路是本项目自己实现的：faster-whisper 本地识别 → DeepSeek 对话 → edge-tts / VOICEVOX 合成。
形象、动画和气泡由 `dsh-pet` 的**独立模式**渲染（本机 3080 端口），不需要原来的 dsh web 宿主。

> 密钥只存在本机 `config.local.json`，已被 `.gitignore` 排除，不入库。

---

## 一、运行环境

| 项目 | 是否必须 | 说明 |
|------|----------|------|
| Windows 10/11 | ✅ | 桌面透明窗、快捷方式均依赖 Windows |
| Python 3.12+ | ✅ | `numpy==2.5.4` 要求 ≥3.12；WorkBuddy 自带 Python 可直接用 |
| Node.js 22+ | ✅ | 用于 npm 安装 `dsh-pet` 独立模式 |
| DeepSeek API Key | ✅ | 自己的 Key，填 `config.local.json` 或环境变量 `DEEPSEEK_API_KEY` |
| VOICEVOX（windows-cpu） | ⚠️ 可选 | 想要日语「古河渚系少女音」才需要；不装则日语退回 edge 的 `ja-JP-NanamiNeural` |

---

## 二、安装

```bat
git clone <本仓库地址> 蓝色大肥鱼
cd 蓝色大肥鱼
setup.bat
```

`setup.bat` 依次做：

1. 用 WorkBuddy 自带的 Python 建 `.venv`（已有则跳过）；
2. 走清华镜像装 `requirements.txt`（默认源在部分网络环境下会卡在下载）；
3. npm 全局装 `dsh-pet@0.4.7`，得到 `dsh-pet-standalone.cmd`；
4. 从 `hf-mirror.com` 直连下载 `whisper-small`（约 460MB）到 `models/whisper-small/`；
5. 生成桌面快捷方式「蓝色大肥鱼」。

### 填 Key

把 `config.example.json` 复制为 `config.local.json`，只填 `api_key`，其余字段留空字符串即走自动探测：

```json
{
  "api_key": "sk-你的key",
  "voicevox_dir": "D:\\voicevox\\windows-cpu"
}
```

全部可填字段：`api_key` / `node_dir` / `voicevox_dir` / `dsh_pet_dir` / `pet_exe` / `pet_host`。
对应环境变量：`DEEPSEEK_API_KEY` / `WORKBUDDY_NODE_DIR` / `VOICEVOX_DIR` / `DSH_PET_DIR` / `DSH_PET_EXE` / `DSH_PET_HOST`。

---

## 三、使用

- **启动**：双击桌面「蓝色大肥鱼」。重复双击不会多开。
- **唤醒**：喊「小鱼」（日语模式喊「さかなちゃん」），之后 45 秒内直接说话即可。
- **切语言**：右键鱼 →「切换语言」；或说「说日语 / 说中文」；或直接改 `pet_lang.json` 的 `mode`，语音桥 1.5s 内热切换。
- **退出**：右键鱼 →「退出大肥鱼」；或命令行 `.venv\Scripts\python.exe quit.py`。
- **日语模式**：声音是日语，气泡文字仍是中文。

---

## 四、进程与端口

| 进程 | 端口 | 作用 |
|------|------|------|
| `dsh-pet-standalone.cmd` | 3080 | 桌宠窗口；提供 `/dsh-pet-7340/state` 与 `/broadcast` |
| `pet_voice.py` | 47823 | 语音桥：识别 / 对话 / 合成 / 推气泡 |
| `pet_menu.py` | 47824 | 右键菜单桥：注册退出与切语言，监听点击 |
| `VOICEVOX run.exe` | 50021 | 可选，日语音色 |

`launcher.py` 按顺序拉起，逐个探活后再进下一个；已经跑着的会跳过。

独立模式会在 `~/.dsh/dsh-pet/standalone-runtime.json` 写本机访问令牌，
语音桥和菜单桥推气泡 / 注册菜单时都从那里读 token（插件模式没有这个文件就不带，兼容旧行为）。

---

## 五、目录说明

| 文件 | 作用 |
|------|------|
| `launcher.py` | 一键启动与探活编排 |
| `pet_voice.py` | 语音桥主循环（识别 / 合成 / 对话 / 记忆） |
| `pet_menu.py` | 右键菜单桥（0.4.7 的官方第三方菜单 API） |
| `pet_lang.py` | 中 / 日双语语言包 |
| `voicevox_pool.py` / `edge_tts_pool.py` | 两个 TTS 引擎封装 |
| `quit.py` | 清场脚本 |
| `_make_lnk.py` | 生成桌面快捷方式 |
| `config.py` / `config.example.json` | 配置加载与模板 |
| `patch_*.py` / `patch_all.py` | 旧版给插件文件打补丁的脚本，对 dsh-pet 0.4.7 锚点已失效，保留仅作参考 |
| `fatuiyu.ico` / `fatuiyu.png` | 图标素材 |

运行时产物（已排除入库）：`config.local.json`、`*.log`、`pids.json`、`pet_lang.json`、
`pet_memory.json`、`models/`、`.venv/`。

---

## 六、排错

日志都在项目根目录：`launcher.log` / `host.log` / `run.log` / `menu.log` / `quit.log`。

| 现象 | 查哪里 |
|------|--------|
| 桌宠窗口不出来 | `host.log`，首次会下载 Electron 到 `~/.dsh/electron`（约 138MB，走 npmmirror） |
| 听得到声音、没气泡 | `curl http://127.0.0.1:3080/dsh-pet-7340/state` 是否 200；`run.log` 里的 BUBBLE 行 |
| 对话回「网络不听使唤」 | Key 没填或失效；`config.local.json` 的 `api_key` |
| 识别不了 | `models/whisper-small/model.bin` 是否完整（约 462MB） |
| 日语没有少女音 | 装 VOICEVOX 并在 `config.local.json` 填 `voicevox_dir` |
| 依赖装不动 | `setup.bat` 已固定走清华镜像；模型走 hf-mirror 直连 |

---

## 七、授权

`dsh-pet` 的许可证：**代码 MIT；素材禁止商用；二创在公开渠道须署名**
（来源 <https://github.com/PC2005-cloud/dsh-pet>）。

商业化交付前需自行替换动画素材或取得授权，这一点在对外发布前必须确认。
