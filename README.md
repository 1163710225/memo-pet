# MemoPet

A minimalist desktop memo pet for Windows - a floating note-taking widget that sits on your desktop.

## Features

- **Desktop Pet Widget** - Draggable floating icon, always on top
- **One-click Expand** - Click the pet to open the memo window
- **Auto-save** - Content auto-saves 1.2s after typing
- **Minimal UI** - Clean design inspired by modern AI products
- **Note Management** - Create, delete, and switch between notes
- **Custom Icon** - Replace `widget_icon.png` with your own image
- **Frameless Design** - Both the widget and editor are borderless windows
- **Resizable** - Drag window edges to resize

## Getting Started

### Run Directly

```bash
pip install customtkinter Pillow numpy
python memo.py
```

### Build EXE

Double-click `build.bat`. Output: `dist/MemoPet.exe`

### Custom Widget Icon

Place your PNG image (preferably with transparency) in the project root as `widget_icon.png`, then restart or rebuild.

## Controls

| Action | How |
|--------|-----|
| Open memo | Click the desktop widget |
| Close memo | Press `Esc` or click the close button |
| Move widget | Drag the widget icon |
| Move window | Drag the top bar area |
| Resize window | Drag from window edges |
| New note | Click `+ New Note` |
| Delete note | Select a note, then click `Delete` |
| Exit app | Right-click widget -> `Exit` |

## Tech Stack

- **GUI** - tkinter + customtkinter
- **Image** - Pillow + NumPy
- **Storage** - Local JSON file
- **Packaging** - PyInstaller

## License

MIT
