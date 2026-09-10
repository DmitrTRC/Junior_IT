#!/usr/bin/env bash
# Сборка всех вариантов Hello World. Linux, gcc. Требуется python3 + pyinstaller
# для последнего варианта (pip3 install pyinstaller).
set -eu
cd "$(dirname "$0")"
mkdir -p build

echo "==> C, как обычно учат (без оптимизаций, с отладочными символами)"
gcc -O0                     -o build/hello_dyn    hello.c

echo "==> C, ужатый: -Os и strip"
gcc -Os -s                  -o build/hello_opt    hello.c

echo "==> C, статический: libc внутри файла"
gcc -Os -static -s          -o build/hello_static hello.c

echo "==> C, без libc вообще: только _start и два syscall"
gcc -Os -nostdlib -static   -o build/hello_bare   hello_bare.c
strip build/hello_bare

echo "==> Python -> один бинарник (PyInstaller)"
if python3 -c "import PyInstaller" 2>/dev/null; then
    tmp=$(mktemp -d)
    cp hello.py "$tmp/"
    ( cd "$tmp" && python3 -m PyInstaller --onefile --name hello_py \
        --clean --noconfirm --log-level WARN hello.py >/dev/null )
    cp "$tmp/dist/hello_py" build/hello_py
    chmod +x build/hello_py
    rm -rf "$tmp"
else
    echo "    PyInstaller не установлен, пропускаю (pip3 install pyinstaller)"
fi

echo
ls -l build/
echo
echo "Теперь: ./measure.sh"
