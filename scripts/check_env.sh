#!/usr/bin/env bash
# Check JetPack / CUDA / TensorRT / PyTorch / OpenCV GStreamer / camera

echo "== L4T ==";        cat /etc/nv_tegra_release 2>/dev/null || echo "not a Jetson?"
echo "== Power mode =="; sudo nvpmodel -q 2>/dev/null | head -n 2
echo "== CUDA ==";       (nvcc --version 2>/dev/null || /usr/local/cuda/bin/nvcc --version) | tail -n 1
echo "== Camera ==";     ls /dev/video* 2>/dev/null || echo "no /dev/video*"

python3 - <<'EOF'
def check(name, fn):
    try:
        print(f"== {name} ==\n{fn()}")
    except Exception as e:
        print(f"== {name} ==\nFAILED: {e}")

check("TensorRT", lambda: __import__("tensorrt").__version__)
check("PyTorch", lambda: (lambda t: f"{t.__version__} cuda={t.cuda.is_available()}")(__import__("torch")))
check("Ultralytics", lambda: __import__("ultralytics").__version__)
check("OpenCV", lambda: (lambda c: c.__version__ + " | " + " ".join(
    l.strip() for l in c.getBuildInformation().splitlines() if "GStreamer" in l))(__import__("cv2")))
EOF
