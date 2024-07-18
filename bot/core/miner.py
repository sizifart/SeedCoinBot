import time
import asyncio
from urllib.parse import unquote
import dateutil.parser
from typing import Any, Tuple, Dict

import aiohttp
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered
from pyrogram.raw.functions.messages import RequestWebView

from bot.utils import logger
from bot.exceptions import InvalidSession
from .headers import headers
from bot.config import settings


class Miner:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client

        self.speed_levels = {
            '0': 0.01,
            '1': 0.015,
            '2': 0.02,
            '3': 0.025,
            '4': 0.03,
            '5': 0.05
        }

        self.speed_upgrades = {
            '1': 0.4,
            '2': 2.0,
            '3': 4.0,
            '4': 10.0,
            '5': 30.0
        }

        self.storage_levels = {
            '0': 2,
            '1': 3,
            '2': 4,
            '3': 6,
            '4': 12,
            '5': 24
        }

        self.storage_ugprades = {
            '1': 0.4,
            '2': 1.0,
            '3': 2.0,
            '4': 8.0,
            '5': 16.0
        }

    async def get_tg_web_data(self, proxy: str | None) -> str:
        try:
            if proxy:
                proxy = Proxy.from_str(proxy)
                proxy_dict = dict(
                    scheme=proxy.protocol,
                    hostname=proxy.host,
                    port=proxy.port,
                    username=proxy.login,
                    password=proxy.password
                )
            else:
                proxy_dict = None

            self.tg_client.proxy = proxy_dict

            if not self.tg_client.is_connected:
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            web_view = await self.tg_client.invoke(RequestWebView(
                peer=await self.tg_client.resolve_peer('seed_coin_bot'),
                bot=await self.tg_client.resolve_peer('seed_coin_bot'),
                platform='android',
                from_bot_menu=False,
                url='https://seeddao.org/'
            ))

            auth_url = web_view.url
            tg_web_data = unquote(
                string=unquote(
                    string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0]))

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

            return tg_web_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error during Authorization: {error}")
            await asyncio.sleep(delay=7)

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

    async def balance(self, http_client: aiohttp.ClientSession) -> float:
        try:
            response = await http_client.get(
                url='https://elb.seeddao.org/api/v1/profile/balance',
                json={})
            response.raise_for_status()

            response_json = await response.json()
            balance = float(response_json['data']) / 1000000000
            return balance
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while daily claiming: {error}")
            await asyncio.sleep(delay=7)

    async def profile(self, http_client: aiohttp.ClientSession) -> Dict[str, Any]:
        try:
            response = await http_client.get(
                url='https://elb.seeddao.org/api/v1/profile',
                json={})
            response.raise_for_status()

            response_json = await response.json()
            profile = response_json
            return profile
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while daily claiming: {error}")
            await asyncio.sleep(delay=7)

    async def claim(self, http_client: aiohttp.ClientSession) -> Dict[str, Any]:
        try:
            response = await http_client.post(
                url='https://elb.seeddao.org/api/v1/seed/claim',
                json={})
            response.raise_for_status()

            response_json = await response.json()
            claim = response_json
            return claim
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while daily claiming: {error}")
            await asyncio.sleep(delay=7)

    async def get_daily_bonuses(self, http_client: aiohttp.ClientSession) -> Dict[str, Any]:
        try:
            response = await http_client.get(
                url='https://elb.seeddao.org/api/v1/login-bonuses',
                json={})
            response.raise_for_status()

            response_json = await response.json()
            daily_info = response_json

            return daily_info
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while daily claiming: {error}")
            await asyncio.sleep(delay=7)

    async def daily_claim(self, http_client: aiohttp.ClientSession) -> Dict[str, Any]:
        try:
            response = await http_client.post(
                url='https://elb.seeddao.org/api/v1/login-bonuses',
                json={})
            response.raise_for_status()

            response_json = await response.json()
            daily_info = response_json

            return daily_info
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while daily claiming: {error}")
            await asyncio.sleep(delay=7)

    def is_daily_claim_possible(self, daily_info: Dict[str, Any]) -> bool:
        if not daily_info:
            return True

        data = daily_info.get('data')
        if not data:
            return True

        if isinstance(data, dict):
            timestamp = dateutil.parser.parse(data['timestamp']).timestamp()
            if time.time() <= timestamp:
                return False

            if time.time() - timestamp >= 24 * 3600:
                return True
            return False

        last_timestamp = 0
        if isinstance(data, list):
            for claim in data:
                timestamp = dateutil.parser.parse(claim['timestamp']).timestamp()
                if timestamp >= last_timestamp:
                    last_timestamp = timestamp

            if time.time() - last_timestamp >= 24 * 3600:
                return True
            return False
        return False

    def is_claim_possible(self, profile: Dict[str, Any]) -> bool:
        if not profile:
            return False

        last_claim_timestamp = dateutil.parser.parse(profile['data']['last_claim']).timestamp()
        speed_level, storage_level, holy_level = self.get_storage_and_speed_levels(profile)

        if storage_level <= 0:
            storage_hours = 2
        else:
            storage_hours = self.storage_levels[str(storage_level)]

        next_claim_timestamp = last_claim_timestamp + storage_hours * 3600

        if time.time() > next_claim_timestamp:
            return True

        percent = 100 * (time.time() - last_claim_timestamp) / (storage_hours * 3600)
        if percent >= settings.CLAIM_MIN_PERCENT:
            return True

        return False

    def get_sleep_time_to_claim(self, profile: Dict[str, Any]) -> int:
        last_claim_timestamp = dateutil.parser.parse(profile['data']['last_claim']).timestamp()
        speed_level, storage_level, holy_level = self.get_storage_and_speed_levels(profile)

        if storage_level <= 0:
            storage_hours = 2
        else:
            storage_hours = self.storage_levels[str(storage_level)]

        next_claim_timestamp = last_claim_timestamp + storage_hours * 3600
        return next_claim_timestamp - time.time()

    def get_storage_and_speed_levels(self, profile: Dict[str, Any]) -> Tuple[int, int, int]:
        if not profile:
            return 0, 0, 0

        upgrades = profile['data']['upgrades']
        if not upgrades:
            return 0, 0, 0

        speed_level = 0
        storage_level = 0
        holy_level = 0
        for upgrade in upgrades:
            type = upgrade['upgrade_type']
            if type == 'mining-speed':
                level = upgrade['upgrade_level']
                if level >= speed_level:
                    speed_level = level
            elif type == 'storage-size':
                level = upgrade['upgrade_level']
                if level >= storage_level:
                    storage_level = level
            elif type == 'holy-water':
                level = upgrade['upgrade_level']
                if level >= holy_level:
                    holy_level = level

        return speed_level, storage_level, holy_level

    async def upgrade_speed(self, http_client: aiohttp.ClientSession) -> Dict[str, Any]:
        try:
            response = await http_client.post(
                url='https://elb.seeddao.org/api/v1/seed/mining-speed/upgrade',
                json={})
            response.raise_for_status()

            response_json = await response.json()
            daily_info = response_json

            return daily_info
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while daily claiming: {error}")
            await asyncio.sleep(delay=7)

    async def upgrade_speed_if_possible(self, http_client: aiohttp.ClientSession, profile: Dict[str, Any], balance: float) -> bool:
        speed_level, storage_level, holy_level = self.get_storage_and_speed_levels(profile)
        next_speed_level = speed_level + 1

        if settings.SPEED_MAX_LEVEL >= next_speed_level:
            skey = str(next_speed_level)
            if skey in self.speed_upgrades:
                price = self.speed_upgrades[skey]
                if balance >= price:
                    logger.info(f"f{self.session_name} | Speed upgrade is possible, trying to upgrade")
                    upgrade_speed_res = await self.upgrade_speed(http_client=http_client)
                    if not upgrade_speed_res:
                        return True
                    else:
                        logger.error(f"f{self.session_name} | Speed upgraded unsuccessfully with error messge <c>{upgrade_speed_res['message']}</c>")
                        return False
        return False

    async def upgrade_storage(self, http_client: aiohttp.ClientSession) -> Dict[str, Any]:
        try:
            response = await http_client.post(
                url='https://elb.seeddao.org/api/v1/seed/storage-size/upgrade',
                json={})
            response.raise_for_status()

            response_json = await response.json()
            daily_info = response_json

            return daily_info
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while daily claiming: {error}")
            await asyncio.sleep(delay=7)

    async def upgrade_storage_if_possible(self, http_client: aiohttp.ClientSession, profile: Dict[str, Any], balance: float) -> bool:
        speed_level, storage_level, holy_level = self.get_storage_and_speed_levels(profile)
        next_storage_level = storage_level + 1

        if settings.STORAGE_MAX_LEVEL >= next_storage_level:
            skey = str(next_storage_level)
            if skey in self.storage_ugprades:
                price = self.storage_ugprades[skey]
                if balance >= price:
                    logger.info(f"f{self.session_name} | Storage upgrade is possible, trying to upgrade")
                    upgrade_storage_res = await self.upgrade_storage(http_client=http_client)
                    if not upgrade_storage_res:
                        return True
                    else:
                        logger.error(f"f{self.session_name} | Storage upgraded unsuccessfully with error messge <c>{upgrade_storage_res['message']}</c>")
                        return False
        return False

    async def run(self, proxy: str | None) -> None:
        logged_in = False
        tdata_created_time = 0
        sleep_time = settings.DEFAULT_SLEEP
        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        async with (aiohttp.ClientSession(headers=headers, connector=proxy_conn) as http_client):
            if proxy:
                await self.check_proxy(http_client=http_client, proxy=proxy)

            while True:
                try:
                    if not logged_in or time.time() - tdata_created_time >= 3600:
                        tg_web_data = await self.get_tg_web_data(proxy=proxy)
                        logged_in = True

                        http_client.headers["Telegram-Data"] = tg_web_data
                        headers["Telegram-Data"] = tg_web_data

                        tdata_created_time = time.time()

                    profile = await self.profile(http_client=http_client)
                    balance = await self.balance(http_client=http_client)
                    logger.info(f"{self.session_name} | Balance is <c>{balance: .6f}</c>")

                    claim_possible = self.is_claim_possible(profile=profile)
                    if claim_possible:
                        claim_status = await self.claim(http_client=http_client)
                        if claim_status:
                            balance = await self.balance(http_client=http_client)
                            logger.success(f"{self.session_name} | Claimed successfully, new balance is <c>{balance}</c>")
                            profile = await self.profile(http_client=http_client)

                    daily_info = await self.get_daily_bonuses(http_client=http_client)
                    daily_possible = self.is_daily_claim_possible(daily_info)
                    if daily_possible:
                        logger.info(f"{self.session_name} | Daily claim is possible, claiming")
                        res = await self.daily_claim(http_client=http_client)
                        if res:
                            balance = await self.balance(http_client=http_client)
                            logger.success(f"{self.session_name} | Daily claim was possible, new balance is <c>{balance}</c>")

                    upgrade_speed_res = await self.upgrade_speed_if_possible(http_client=http_client, profile=profile, balance=balance)
                    if upgrade_speed_res:
                        profile = await self.profile(http_client=http_client)
                        balance = await self.balance(http_client=http_client)
                        logger.success(f"{self.session_name} | Speed upgraded successfully, new balance is <c>{balance}</c>")

                    upgrade_storage_res = await self.upgrade_storage_if_possible(http_client=http_client, profile=profile, balance=balance)
                    if upgrade_storage_res:
                        profile = await self.profile(http_client=http_client)
                        balance = await self.balance(http_client=http_client)
                        logger.success(f"{self.session_name} | Storage upgraded successfully, new balance is <c>{balance}</c>")

                    sleep_time = self.get_sleep_time_to_claim(profile)
                    if sleep_time <= 0:
                        sleep_time = settings.DEFAULT_SLEEP

                except InvalidSession as error:
                    raise error

                except Exception as error:
                    logger.error(f"{self.session_name} | Unknown error: {error}")
                    await asyncio.sleep(delay=7)

                else:
                    logger.info(f"{self.session_name} | Sleeping for the next claim {sleep_time}s")
                    await asyncio.sleep(delay=sleep_time)


async def run_miner(tg_client: Client, proxy: str | None):
    try:
        await Miner(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")