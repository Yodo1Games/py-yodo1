import logging
import time
import random

logger = logging.getLogger('yodo1.progress')


class ProgressBar:
    WIDTH = 30

    def __init__(self, total: int, desc: str, step: int = 50) -> None:
        self.index = 0
        self.total = total
        self.step = step
        self.desc = desc

        self._start_at = 0

    def _format_time(self, secs: float) -> str:
        if secs < 3600:
            return f"{secs // 60:02.0f}:{secs % 60:02.0f}"
        else:
            return f"{secs // 3600:02.0f}:{secs // 60:02.0f}:{secs % 60:02d}"

    def _get_time_string(self) -> str:
        spend_time = time.time() - self._start_at
        estimated_time = spend_time / self.index * self.total

        return f"{self._format_time(spend_time)}<{self._format_time(estimated_time)}"

    def update(self, n: int = 1) -> None:
        if self.index == 0:
            self._start_at = time.time()

        self.index += n

        if self.index % self.step == 0 or self.index == self.total:
            fill_count = int(ProgressBar.WIDTH * self.index / self.total)
            if fill_count > ProgressBar.WIDTH:
                fill_count = ProgressBar.WIDTH

            progress = f" {100 * self.index / self.total:.1f}%"
            text = f"{progress:<8s}|" + '#' * fill_count + '-' * (ProgressBar.WIDTH - fill_count) + "| " + f"{self.index}/{self.total} "
            text += f"[{self._get_time_string()}] {self.desc}"
            logger.info(text)


if __name__ == '__main__':
    import logging

    logging.basicConfig(level='DEBUG')
    p = ProgressBar(total=20, desc="Hacking ...", step=20 // 6)

    for i in range(20):
        p.update()
        time.sleep(random.randint(0, 60) / 300)
