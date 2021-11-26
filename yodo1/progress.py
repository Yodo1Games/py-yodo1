import logging

logger = logging.getLogger('yodo1.progress')


class ProgressBar:
    WIDTH = 50

    def __init__(self, total: int, desc: str, step: int = 50) -> None:
        self.index = 0
        self.total = total
        self.step = step
        self.desc = desc

    def update(self, n=1) -> None:
        self.index += n

        if self.index % self.step == 0:
            fill_count = int(ProgressBar.WIDTH * self.index / self.total)
            if fill_count > ProgressBar.WIDTH:
                fill_count = ProgressBar.WIDTH

            progress = f" {100 * self.index / self.total:.1f}%"
            text = f"{progress:<8s}|" + '>' * fill_count + ' ' * (ProgressBar.WIDTH - fill_count) + "| "
            text += self.desc
            logger.info(text)
