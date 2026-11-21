// Лаунчер DiktovkaMac: находит папку приложения (BASE) от собственного пути
// и запускает DiktovkaMac.py из venv. Скомпилированный бинарник нужен,
// чтобы macOS Gatekeeper принимал .app (bash-скрипт не проходит оценку).
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <mach-o/dyld.h>

int main(void) {
    char path[4096];
    uint32_t size = sizeof(path);
    if (_NSGetExecutablePath(path, &size) != 0) return 1;
    // раскрываем возможные симлинки (например, со значка рабочего стола)
    char real[4096];
    if (realpath(path, real) != NULL) {
        snprintf(path, sizeof(path), "%s", real);
    }
    // BASE = папка, где лежит DiktovkaMac.app: минус /DiktovkaMac.app/Contents/MacOS/DiktovkaMac
    for (int i = 0; i < 4; i++) {
        char *p = strrchr(path, '/');
        if (!p) return 1;
        *p = 0;
    }
    char script[4600], logf[4600], py[4600];
    snprintf(py,     sizeof(py),     "%s/venv/bin/python", path);
    snprintf(script, sizeof(script), "%s/DiktovkaMac.py",  path);
    snprintf(logf,   sizeof(logf),   "%s/DiktovkaMac.log", path);

    int fd = open(logf, O_WRONLY | O_CREAT | O_APPEND, 0644);
    if (fd >= 0) {
        dup2(fd, STDOUT_FILENO);
        dup2(fd, STDERR_FILENO);
        if (fd > STDERR_FILENO) close(fd);
    }
    execl(py, py, script, (char *)NULL);
    // не запустилось — оставим след в логе
    dprintf(STDERR_FILENO, "launcher: не удалось запустить %s\n", py);
    return 1;
}
