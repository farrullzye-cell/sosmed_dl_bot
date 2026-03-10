import asyncio
from dataclasses import dataclass

FRAMES = ["⏳", "⌛", "🔄", "📥", "📦", "🚀"]

@dataclass
class Spinner:
    message: object
    task: asyncio.Task | None = None

    @classmethod
    async def start(cls, update, context, text: str, interval: float = 1.4, max_seconds: int = 120):
        msg = await update.effective_message.reply_text(f"{FRAMES[0]} {text}")
        task = context.application.create_task(cls._run(msg, text, interval, max_seconds))
        return cls(message=msg, task=task)

    @staticmethod
    async def _run(msg, text: str, interval: float, max_seconds: int):
        t = 0.0
        i = 0
        last = None
        while t < max_seconds:
            i = (i + 1) % len(FRAMES)
            dots = "." * ((i % 3) + 1)
            new_text = f"{FRAMES[i]} {text}{dots}"
            try:
                if new_text != last:
                    await msg.edit_text(new_text)
                    last = new_text
            except Exception:
                # bisa gagal kalau message sudah hilang / rate limit / dll
                pass
            await asyncio.sleep(interval)
            t += interval

    async def stop(self, final_text: str = None, delete: bool = False):
        try:
            if self.task:
                self.task.cancel()
        except Exception:
            pass

        if delete:
            try:
                await self.message.delete()
            except Exception:
                pass
            return

        if final_text:
            try:
                await self.message.edit_text(final_text)
            except Exception:
                pass
