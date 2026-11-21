// Лаунчер DiktovkaMac (значок запуска).
//
// Важно: рабочий процесс должен стартовать НЕ из этого пакета, а через launchd
// (LaunchAgent com.diktovkamac.agent). Тогда macOS относит его к python3.12
// (стабильная подпись, разрешение «Универсальный доступ» уже выдано),
// а не к нашему ad-hoc-пакету — переподписи которого сбрасывали права.
// Поэтому здесь мы лишь перезапускаем агента; прямой запуск python — запасной путь.
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <spawn.h>
#include <sys/wait.h>
#include <mach-o/dyld.h>

extern char **environ;

static char BASE[4096];

static int run(const char *path, char *const argv[]) {
    pid_t pid;
    if (posix_spawn(&pid, path, NULL, NULL, argv, environ) != 0) return -1;
    int status = 0;
    if (waitpid(pid, &status, 0) < 0) return -1;
    if (WIFEXITED(status)) return WEXITSTATUS(status);
    return -1;
}

int main(void) {
    char path[4096];
    uint32_t size = sizeof(path);
    if (_NSGetExecutablePath(path, &size) != 0) return 1;
    char real[4096];
    if (realpath(path, real) != NULL) snprintf(path, sizeof(path), "%s", real);
    snprintf(BASE, sizeof(BASE), "%s", path);
    for (int i = 0; i < 4; i++) {   // убрать /DiktovkaMac.app/Contents/MacOS/DiktovkaMac
        char *p = strrchr(BASE, '/');
        if (!p) return 1;
        *p = 0;
    }

    char logf[4600];
    snprintf(logf, sizeof(logf), "%s/DiktovkaMac.log", BASE);
    int fd = open(logf, O_WRONLY | O_CREAT | O_APPEND, 0644);
    if (fd >= 0) { dup2(fd, STDOUT_FILENO); dup2(fd, STDERR_FILENO); if (fd > STDERR_FILENO) close(fd); }

    char domain[32], service[72];
    snprintf(domain,  sizeof(domain),  "gui/%d", getuid());
    snprintf(service, sizeof(service), "%s/com.diktovkamac.agent", domain);
    char *kick[] = { "/bin/launchctl", "kickstart", "-k", service, NULL };

    // 1) перезапускаем агента: процесс поднимется под launchd с правильной атрибуцией
    if (run("/bin/launchctl", kick) == 0) return 0;

    // 2) агент ещё не загружен – грузим plist и стартуем
    char plist[4600];
    snprintf(plist, sizeof(plist),
             "%s/Library/LaunchAgents/com.diktovkamac.agent.plist", getenv("HOME"));
    char *bootfull[] = { "/bin/launchctl", "bootstrap", domain, plist, NULL };
    run("/bin/launchctl", bootfull);
    run("/bin/launchctl", kick);

    // 3) запасной вариант – запустить python напрямую
    char py[4600], script[4600];
    snprintf(py,     sizeof(py),     "%s/venv/bin/python", BASE);
    snprintf(script, sizeof(script), "%s/DiktovkaMac.py",  BASE);
    char *pyargv[] = { py, script, NULL };
    if (run(py, pyargv) != 0)
        dprintf(STDERR_FILENO, "launcher: не удалось запустить %s\n", py);
    return 0;
}
