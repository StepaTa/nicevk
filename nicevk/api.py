import asyncio
import dotenv
import json

from functools import wraps
from pathlib import Path
from loguru import logger
from python_rucaptcha.ImageCaptcha import ImageCaptcha, aioImageCaptcha
from vkbottle import User, Message, VKError
from vkbottle.framework import Middleware
from nicevk.errors import CaptchaError


nicevk_folder = Path.home().joinpath("nicevk").absolute()

env = dotenv.dotenv_values(str(nicevk_folder.joinpath(".env")))

user = User(env["TOKEN"])

commands = [".help"]


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


@user.middleware.middleware_handler()
class NoBotMiddleware(Middleware):
    async def middleware(self, message: Message):
        return message.from_id == user.user_id


rucaptcha = aioImageCaptcha(rucaptcha_key=env.get("RUCAPTCHA_TOKEN", ""))


@logger.catch
async def solve_captcha(e: VKError):
    captcha_img, captcha_sid = e.raw_error["captcha_img"], e.raw_error["captcha_sid"]
    while True:
        resp = await rucaptcha.captcha_handler(captcha_link=captcha_img)
        if not resp["error"]:
            print(e.method_requested)
            print(e.params_requested)
            print(e.raw_error)
            await user.api.api(
                method="messages.edit",
                params={
                    **e.params_requested,
                    "captcha_key": resp["captchaSolve"],
                    "captcha_sid": captcha_sid,
                },
            )
            return
        else:
            raise CaptchaError(resp["errorBody"]["text"])


state_file = nicevk_folder / "state.json"
state_file.touch(exist_ok=True)
state = json.loads(state_file.read_text("utf-8") or "{}")


def save_state():
    state_file.write_text(json.dumps(state))
