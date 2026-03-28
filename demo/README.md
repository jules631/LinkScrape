# Demo Recording

`simulate_run.py` plays back a realistic LinkScrape terminal session so you can record it without needing live LinkedIn credentials.

## Test the script first

```bash
python demo/simulate_run.py --fast   # instant output, no delays
python demo/simulate_run.py          # realistic timing
```

## Option A — asciinema + agg (best quality)

```bash
# Install tools
pip install asciinema
# agg: https://github.com/asciinema/agg/releases — download binary for your OS

# Record
asciinema rec demo/demo.cast --command "python demo/simulate_run.py"

# Convert to GIF
agg demo/demo.cast assets/demo.gif --font-size 14
```

## Option B — screen recorder (no extra tools)

1. Open a terminal and resize it to ~100×30 characters
2. Start your screen recorder:
   - **macOS**: QuickTime Player → New Screen Recording → crop to terminal window
   - **Linux**: `peek`, `byzanz`, or `ffmpeg -f x11grab ...`
   - **Windows**: ShareX or built-in Xbox Game Bar
3. Run `python demo/simulate_run.py`
4. Stop recording and export/convert to GIF
5. Move the GIF to `assets/demo.gif`

## After recording

Commit the GIF:

```bash
git add assets/demo.gif
git commit -m "Add demo GIF"
git push
```

The README already references `assets/demo.gif` — it will render automatically on GitHub once committed.
