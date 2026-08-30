import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector

SOURCE_URL = "https://raw.githubusercontent.com/iplocate/free-proxy-list/refs/heads/main/all-proxies.txt"
CHECK_URL = "http://httpbin.org/ip"
OUTPUT_FILE = "valid_proxies.txt"
TIMEOUT_SECONDS = 5
MAX_CONCURRENT_TASKS = 200


async def check_proxy(session: aiohttp.ClientSession, proxy_str: str, semaphore: asyncio.Semaphore) -> str | None:
    async with semaphore:
        # Приведение к формату url (если протокол не указан по умолчанию http)
        if not proxy_str.startswith(("http://", "https://", "socks4://", "socks5://")):
            proxy_url = f"http://{proxy_str}"
        else:
            proxy_url = proxy_str

        try:
            connector = ProxyConnector.from_url(proxy_url)
            async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)) as proxy_session:
                async with proxy_session.get(CHECK_URL) as response:
                    if response.status == 200:
                        return proxy_str
        except Exception:
            return None


async def main():
    print("Загрузка исходного списка прокси...")
    async with aiohttp.ClientSession() as session:
        async with session.get(SOURCE_URL) as response:
            if response.status != 200:
                print(f"Ошибка загрузки источника: HTTP {response.status}")
                return
            content = await response.text()

    raw_proxies = [line.strip() for line in content.splitlines() if line.strip()]
    print(f"Всего получено прокси: {len(raw_proxies)}")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    tasks = [check_proxy(session, p, semaphore) for p in raw_proxies]

    results = await asyncio.gather(*tasks)
    valid_proxies = [p for p in results if p is not None]

    print(f"Найдено рабочих прокси: {len(valid_proxies)}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for p in valid_proxies:
            f.write(f"{p}\n")


if __name__ == "__main__":
    asyncio.run(main())