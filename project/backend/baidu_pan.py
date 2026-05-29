"""
百度网盘 API 集成
支持：获取用户信息、文件列表、获取文件下载链接
OAuth 文档：https://pan.baidu.com/union/doc/3ksg0s9r7
"""
import os
import sys
import json
import time
import hashlib
import requests

from config import BAIDU_APP_ID, BAIDU_APP_KEY, BAIDU_SECRET_KEY, BAIDU_SIGN_KEY

# 百度网盘 API 基础地址
BASE_URL = "https://pan.baidu.com"
OAUTH_URL = "https://openapi.baidu.com"

# Token 缓存文件
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', '.baidu_token.json')


class BaiduPanClient:
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self._load_token()

    def _load_token(self):
        """从缓存文件加载 token"""
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'r') as f:
                    data = json.load(f)
                if data.get('expires_at', 0) > time.time():
                    self.access_token = data.get('access_token')
                    self.refresh_token = data.get('refresh_token')
                    print(f"[BaiduPan] Token 已加载，有效期至 {time.strftime('%Y-%m-%d %H:%M', time.localtime(data['expires_at']))}")
                    return
                else:
                    print("[BaiduPan] Token 已过期，需要重新授权")
            except Exception as e:
                print(f"[BaiduPan] Token 加载失败: {e}")

    def _save_token(self, data: dict):
        """保存 token 到缓存文件"""
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        token_data = {
            'access_token': data.get('access_token', ''),
            'refresh_token': data.get('refresh_token', ''),
            'expires_at': time.time() + data.get('expires_in', 0) - 300,  # 提前5分钟过期
            'updated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data, f, indent=2)
        self.access_token = token_data['access_token']
        self.refresh_token = token_data['refresh_token']
        print(f"[BaiduPan] Token 已保存")

    def get_auth_url(self) -> str:
        """获取 OAuth 授权链接（用户需要在浏览器中打开此链接授权）"""
        return (
            f"{OAUTH_URL}/oauth/2.0/authorize?"
            f"response_type=code&client_id={BAIDU_APP_KEY}"
            f"&redirect_uri=oob&scope=basic,netdisk"
            f"&display=popup"
        )

    def exchange_code(self, code: str) -> dict:
        """用授权码换取 access_token"""
        resp = requests.get(f"{OAUTH_URL}/oauth/2.0/token", params={
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': BAIDU_APP_KEY,
            'client_secret': BAIDU_SECRET_KEY,
            'redirect_uri': 'oob',
        })
        data = resp.json()
        if 'access_token' in data:
            self._save_token(data)
            return {"success": True, "msg": "授权成功", "expires_in": data.get('expires_in')}
        return {"success": False, "msg": data.get('error_description', '授权失败'), "raw": data}

    def refresh_access_token(self) -> bool:
        """刷新 access_token"""
        if not self.refresh_token:
            return False
        try:
            resp = requests.get(f"{OAUTH_URL}/oauth/2.0/token", params={
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': BAIDU_APP_KEY,
                'client_secret': BAIDU_SECRET_KEY,
            })
            data = resp.json()
            if 'access_token' in data:
                self._save_token(data)
                return True
        except Exception as e:
            print(f"[BaiduPan] Token 刷新失败: {e}")
        return False

    def _api_get(self, url: str, params: dict = None) -> dict:
        """通用 GET 请求"""
        if not self.access_token:
            return {"error": "未授权", "msg": "请先完成百度网盘 OAuth 授权"}
        if params is None:
            params = {}
        params['access_token'] = self.access_token
        try:
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()
            # token 过期自动刷新
            if data.get('errno') in (-6, -62):  # token 无效或过期
                if self.refresh_access_token():
                    params['access_token'] = self.access_token
                    resp = requests.get(url, params=params, timeout=15)
                    data = resp.json()
            return data
        except Exception as e:
            return {"error": str(e)}

    def get_user_info(self) -> dict:
        """获取用户信息"""
        return self._api_get(f"{BASE_URL}/rest/2.0/xpan/nas", {"method": "uinfo"})

    def list_files(self, path: str = "/", order: str = "time", limit: int = 100) -> dict:
        """获取文件列表"""
        return self._api_get(f"{BASE_URL}/rest/2.0/xpan/file", {
            "method": "list",
            "dir": path,
            "order": order,
            "limit": limit,
        })

    def get_file_meta(self, fsids: list) -> dict:
        """获取文件元信息（含下载链接）"""
        return self._api_get(f"{BASE_URL}/rest/2.0/xpan/multimedia", {
            "method": "filemetas",
            "fsids": json.dumps(fsids),
            "dlink": 1,
        })

    def get_download_link(self, fsid: int) -> str:
        """获取单个文件的下载链接"""
        data = self.get_file_meta([fsid])
        if data.get('list'):
            dlink = data['list'][0].get('dlink', '')
            # 需要附加 access_token
            return f"{dlink}&access_token={self.access_token}"
        return ""

    def search_files(self, keyword: str, limit: int = 100) -> dict:
        """搜索文件"""
        return self._api_get(f"{BASE_URL}/rest/2.0/xpan/file", {
            "method": "search",
            "key": keyword,
            "limit": limit,
        })

    def get_quota(self) -> dict:
        """获取网盘容量信息"""
        return self._api_get(f"{BASE_URL}/api/quota", {"checkfree": 1, "checkexpire": 1})

    def get_status(self) -> dict:
        """获取授权状态"""
        if not self.access_token:
            return {"authorized": False, "msg": "未授权", "auth_url": self.get_auth_url()}
        info = self.get_user_info()
        if info.get('errno', 0) == 0:
            return {"authorized": True, "user": info.get('baidu_name', '未知'), "uk": info.get('uk')}
        return {"authorized": False, "msg": "Token 失效", "auth_url": self.get_auth_url()}


# 全局单例
_client = None

def get_client() -> BaiduPanClient:
    global _client
    if _client is None:
        _client = BaiduPanClient()
    return _client
