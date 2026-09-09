/* То же самое, но БЕЗ стандартной библиотеки.
 * Нет printf, нет crt0, нет линковки с libc.
 * Точка входа _start вызывается ядром напрямую,
 * вывод и выход - сырые системные вызовы.
 *
 * Собирать:  gcc -nostdlib -static -Os -o hello_bare hello_bare.c && strip hello_bare
 */

static long sys_call3(long nr, long a, long b, long c)
{
#if defined(__aarch64__)
    register long x8 __asm__("x8") = nr;
    register long x0 __asm__("x0") = a;
    register long x1 __asm__("x1") = b;
    register long x2 __asm__("x2") = c;
    __asm__ volatile ("svc #0" : "+r"(x0) : "r"(x8), "r"(x1), "r"(x2) : "memory", "cc");
    return x0;
#elif defined(__x86_64__)
    long ret;
    __asm__ volatile ("syscall"
                      : "=a"(ret)
                      : "a"(nr), "D"(a), "S"(b), "d"(c)
                      : "rcx", "r11", "memory", "cc");
    return ret;
#else
#  error "Добавь свою архитектуру"
#endif
}

#if defined(__aarch64__)
#  define SYS_write 64
#  define SYS_exit  93
#else
#  define SYS_write 1
#  define SYS_exit  60
#endif

static const char msg[] = "Hello, World!\n";

void _start(void)
{
    sys_call3(SYS_write, 1, (long)msg, sizeof(msg) - 1);
    sys_call3(SYS_exit, 0, 0, 0);
    __builtin_unreachable();
}
