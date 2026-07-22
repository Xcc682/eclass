# 沉浸式场景媒体清单

## 使用原则

- 所有场景图在界面中持续标注“AI 艺术化情景复原”或“AI 当代场景示意”。
- 画面人物均为不对应真实个体的群像，不作为史料照片使用。
- 史实说明、人物行为与短字幕以每卷 `sources` 登记的政府网站、纪念馆和公开党史资料为依据。
- 不把叙事字幕写成未经来源支持的历史人物原话。
- 音频默认关闭；未生成或播放失败时，阅读与互动仍可完整进行。

## 当前画面资产

| 文件 | 数量 | 用途 | 生成方式 | 许可记录 |
|---|---:|---|---|---|
| `history-{1..5}-{01..06}.webp` | 30 | 五卷党史的抵达、探索、人物、抉择、结果与归档画面 | 内置 imagegen 为每卷生成独立六分镜，再由项目脚本切分压缩 | 项目内使用 |
| `tour-{1..5}-{01..06}.webp` | 30 | 五站研学的当代抵达、历史之窗、寻迹、人物、追问与归档画面 | 内置 imagegen 为每站生成独立六分镜，再由项目脚本切分压缩 | 项目内使用 |

共 60 张 WebP。每一卷、每一站均有独立母图，不再从通用母图重复裁切。H5 将资源编译进站点；微信小程序只保留文件名映射，通过 `VITE_MEDIA_BASE_URL` 从后端、MinIO 或 CDN 获取，避免主包膨胀。

生成母图保存在 `backend/app/static/immersive/storyboards/`。每张 `{book-id}-sheet.png` 都是严格的 3×2 六分镜。执行以下命令可重复完成分镜间隔去除、16:10 裁切、WebP 压缩以及前后端目录同步：

```bash
python backend/scripts/prepare_immersive_storyboards.py
```

替换素材后应立即运行重复图审计：

```bash
python backend/scripts/audit_immersive_media.py
```

审计默认要求 60 张文件全部存在，并把精确重复、同卷高相似及跨卷 90% 以上高相似视为失败。必要时可通过 `--threshold` 调整感知相似度阈值。

## 旁白生产

在后端容器内运行：

```bash
python scripts/build_immersive_media.py --upload
```

脚本使用 `zh-CN-YunxiNeural` 预生成 MP3，通过 S3 兼容接口上传到 MinIO、OSS 或 COS，并把最终地址写入跨页数据。运行时不会实时调用 TTS。
