from typing import List, Dict

class ProxyManager:
    def __init__(self, proxies: List[str]):
        self.proxies = proxies
        self.current_index = 0

    def get_proxy(self) -> Dict[str, str]:
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return {"http": proxy, "https": proxy}

    @staticmethod
    async def check_proxy(session, proxy: str) -> bool:
        try:
            async with session.get("http://httpbin.org/ip", proxy=proxy, timeout=10) as response:
                return response.status == 200
        except:  # noqa: E722
            return False

    async def update_proxies(self, session) -> None:
        valid_proxies = []
        for proxy in self.proxies:
            if await self.check_proxy(session, proxy):
                valid_proxies.append(proxy)
        self.proxies = valid_proxies