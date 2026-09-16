# modules/strike_manager.py
class StrikeMgr:
    def __init__(self):
        self.ip_strikes = {}
        self.BANNED_IPS = set()

    def is_banned(self, ip: str) -> bool:
        return ip in self.BANNED_IPS

    def ban_ip(self, ip: str):
        self.BANNED_IPS.add(ip)

    def add_strike(self, ip: str) -> int:
        strikes = self.ip_strikes.get(ip, 0) + 1
        self.ip_strikes[ip] = strikes
        return strikes

    def get_banned_summary(self):
        return {
            "total_banned": len(self.BANNED_IPS),
            "banned_ips_list": list(self.BANNED_IPS),
            "active_strikes": self.ip_strikes
        }

strike_mgr = StrikeMgr()