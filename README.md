# MemoPet 🐾

桌面备忘录宠物 —— 一款极简的 Windows 桌面悬浮便签工具。

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ 特性

- **桌面宠物图标** — 可拖动的悬浮书本/自定义图标，始终置顶
- **一键展开** — 点击桌面宠物弹出极简备忘录窗口
- **自动保存** — 输入内容 1.2 秒后自动持久化
- **极简 UI** — 参考 AI 产品设计，去边框、去阴影、留白为主
- **便签管理** — 新建、删除、切换便签，标题自动取首行
- **窗口拖动** — 顶部栏任意位置拖动窗口，边缘拖拽调整大小
- **自定义图标** — 支持替换 `widget_icon.png` 为自定义桌面宠物图标
- **无边框设计** — 展开窗口和桌宠均为无边框窗口

## 📦 使用方法

### 直接运行

```bash
pip install customtkinter Pillow numpy
python memo.py
```

### 打包为 EXE

```bash
双击 build.bat
```

输出文件：`dist/MemoPet.exe`

### 自定义桌面图标

将你的 PNG 图片（建议带透明通道）放到项目根目录，命名为 `widget_icon.png`，重新运行或打包即可。

## 🎮 操作指南

| 操作 | 方式 |
|------|------|
| 打开备忘录 | 点击桌面宠物图标 |
| 收起备忘录 | 按 `Esc` 或 点击展开窗口 `✕` |
| 拖动桌宠 | 按住桌宠图标拖动 |
| 拖动窗口 | 按住展开窗口顶部区域拖动 |
| 调整窗口大小 | 鼠标移到窗口边缘拖拽 |
| 新建便签 | 点击 `＋ 新建便签` |
| 删除便签 | 选中便签后点击底部 `删除` |
| 退出程序 | 右键桌宠 → `退出` |

## 🛠 技术栈

- **GUI** — tkinter + customtkinter
- **图像处理** — Pillow + NumPy
- **数据存储** — JSON 本地文件
- **打包** — PyInstaller

## 📁 项目结构

```
memo_app/
├── memo.py              # 主程序
├── build.bat             # 打包脚本
├── widget_icon.png       # 自定义桌面图标（可选）
├── memo_data.json        # 便签数据（自动生成）
└── README.md
```

## 📄 License

MIT
