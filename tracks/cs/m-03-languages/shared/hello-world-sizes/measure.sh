#!/usr/bin/env bash
# Замер: размер файла + пиковая резидентная память (RSS) + время старта.
# Всё, что печатает эта штука, можно показывать на доске.
set -u
cd "$(dirname "$0")"

RUNS=${RUNS:-20}
TIME=/usr/bin/time            # именно GNU time, а не встроенный bash-овый

# printf считает байты, а не символы, поэтому кириллицу выравниваем сами
pad() { local s="$1" w="$2"; local n=$(( w - ${#s} )); printf '%s' "$s"; while (( n-- > 0 )); do printf ' '; done; }
rpad() { local s="$1" w="$2"; local n=$(( w - ${#s} )); while (( n-- > 0 )); do printf ' '; done; printf '%s' "$s"; }

line() { pad "$1" 28; rpad "$2" 10; rpad "$3" 11; rpad "$4" 12; echo; }

row() {                        # row "Имя" "путь-для-размера" команда...
    local name="$1" sizefile="$2"; shift 2
    local bytes rss us t0 t1 r

    bytes=$(stat -c %s "$sizefile" 2>/dev/null || echo 0)

    rss=0                      # пиковый RSS: максимум из 3 прогонов, в килобайтах
    for _ in 1 2 3; do
        r=$("$TIME" -f '%M' "$@" 2>&1 >/dev/null | tail -1)
        [[ "$r" =~ ^[0-9]+$ ]] && (( r > rss )) && rss=$r
    done

    t0=$(date +%s%N)           # время старта: среднее по RUNS прогонам
    for _ in $(seq "$RUNS"); do "$@" >/dev/null 2>&1; done
    t1=$(date +%s%N)
    us=$(( (t1 - t0) / RUNS / 1000 ))

    line "$name" \
         "$(numfmt --to=iec --suffix=B "$bytes")" \
         "$(numfmt --to=iec --suffix=B $((rss*1024)))" \
         "$(printf '%d.%03d ms' $((us/1000)) $((us%1000)))"
}

line "ВАРИАНТ" "ФАЙЛ" "ПИК RSS" "СТАРТ"
printf '%.0s-' {1..61}; echo

row "C, без libc (syscall)"    build/hello_bare   ./build/hello_bare
row "C, -Os -s (динамика)"     build/hello_opt    ./build/hello_opt
row "C, -O0 (как учат)"        build/hello_dyn    ./build/hello_dyn
row "C, статический"           build/hello_static ./build/hello_static
row "Python (исходник)"        hello.py           python3 hello.py
row "Python -> PyInstaller"    build/hello_py     ./build/hello_py
command -v node >/dev/null && row "Node.js (исходник)" hello.js node hello.js

echo
echo "Для справки:"
echo "  libc.so.6 = $(numfmt --to=iec --suffix=B $(stat -c %s /lib/*/libc.so.6 2>/dev/null | head -1)) на диске, одна на всю систему"
echo "  /usr/lib/python3.x = $(du -sh /usr/lib/python3.* 2>/dev/null | head -1 | cut -f1) на диске"
echo "  ядро: $(uname -m), gcc $(gcc -dumpversion), $(python3 -V)"
