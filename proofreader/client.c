/* 獨立的本機連線程式，不在鼠鬚管載入任何外部動態函式庫。
 * 保留原廠程式簽章與 Library Validation。socket 操作共用 50ms 截止時間。
 */
#include <sys/socket.h>
#include <sys/un.h>
#include <poll.h>
#include <fcntl.h>
#include <unistd.h>
#include <time.h>
#include <string.h>
#include <errno.h>
#include <stdio.h>

static long long now_ms(void) {
  struct timespec t;
  clock_gettime(CLOCK_MONOTONIC, &t);
  return t.tv_sec * 1000LL + t.tv_nsec / 1000000;
}

static int ready(int fd, short events, long long deadline) {
  struct pollfd p = {fd, events, 0};
  int left = (int)(deadline - now_ms());
  return left > 0 && poll(&p, 1, left) > 0 && (p.revents & events);
}

int main(int argc, char **argv) {
  if (argc != 4) return 0;
  const char *path = argv[1];
  size_t path_size = strlen(path);
  char request[512];
  int length = snprintf(request, sizeof(request), "%s\t%s\n", argv[2], argv[3]);
  if (length < 0 || (size_t)length >= sizeof(request)) return 0;
  size_t request_size = (size_t)length;
  struct sockaddr_un address = {0};
  int fd = -1;
  char response[256];
  size_t used = 0, sent = 0;
  long long deadline = now_ms() + 50;
  if (path_size >= sizeof(address.sun_path) || request_size > 512) goto fail;
  address.sun_family = AF_UNIX;
  memcpy(address.sun_path, path, path_size);
  fd = socket(AF_UNIX, SOCK_STREAM, 0);
  if (fd < 0) goto fail;
  int one = 1;
  setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &one, sizeof(one));
  fcntl(fd, F_SETFL, O_NONBLOCK);
  if (connect(fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
    if (errno != EINPROGRESS || !ready(fd, POLLOUT, deadline)) goto fail;
    int error = 0;
    socklen_t size = sizeof(error);
    if (getsockopt(fd, SOL_SOCKET, SO_ERROR, &error, &size) || error) goto fail;
  }
  while (sent < request_size) {
    if (!ready(fd, POLLOUT, deadline)) goto fail;
    ssize_t count = send(fd, request + sent, request_size - sent, 0);
    if (count <= 0) goto fail;
    sent += (size_t)count;
  }
  while (used < sizeof(response)) {
    if (!ready(fd, POLLIN, deadline)) goto fail;
    ssize_t count = recv(fd, response + used, sizeof(response) - used, 0);
    if (count <= 0) goto fail;
    used += (size_t)count;
    char *end = memchr(response, '\n', used);
    if (end) {
      close(fd);
      fwrite(response, 1, (size_t)(end - response), stdout);
      putchar('\n');
      return 0;
    }
  }
fail:
  if (fd >= 0) close(fd);
  return 0;
}
