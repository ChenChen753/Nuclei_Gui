"""
安全存储模块 - 加密存储敏感信息
使用 Windows DPAPI 或 keyring 库加密存储 API Key 等敏感数据
"""
import os
import sys
import base64
import json
from typing import Optional

from core.logger import get_logger

logger = get_logger("secure_storage")


class SecureStorage:
    """
    安全存储管理器
    
    优先使用 Windows DPAPI 进行加密，如果不可用则使用 keyring 库，
    最后回退到 base64 编码（不安全，仅用于兼容）。
    """
    
    SERVICE_NAME = "NucleiGUI"
    
    def __init__(self):
        self._backend = self._detect_backend()
        logger.info("安全存储后端: " + self._backend)
    
    def _detect_backend(self) -> str:
        """检测可用的加密后端"""
        # 优先尝试 Windows DPAPI
        if sys.platform == 'win32':
            try:
                import win32crypt
                return "dpapi"
            except ImportError:
                pass
        
        # 尝试 keyring
        try:
            import keyring
            keyring.get_keyring()
            return "keyring"
        except Exception:
            pass
        
        # 回退到 base64（不安全）
        logger.warning("未找到安全存储后端，将使用 base64 编码（不安全）")
        return "base64"
    
    def store(self, key: str, value: str) -> bool:
        """
        安全存储敏感数据
        
        Args:
            key: 存储键名
            value: 要存储的值
            
        Returns:
            bool: 是否存储成功
        """
        if not value:
            return self.delete(key)
        
        try:
            if self._backend == "dpapi":
                return self._store_dpapi(key, value)
            elif self._backend == "keyring":
                return self._store_keyring(key, value)
            else:
                return self._store_base64(key, value)
        except Exception as e:
            logger.error("存储敏感数据失败 [" + key + "]: " + str(e))
            return False
    
    def retrieve(self, key: str) -> Optional[str]:
        """
        获取存储的敏感数据
        
        Args:
            key: 存储键名
            
        Returns:
            Optional[str]: 存储的值，如果不存在则返回 None
        """
        try:
            if self._backend == "dpapi":
                return self._retrieve_dpapi(key)
            elif self._backend == "keyring":
                return self._retrieve_keyring(key)
            else:
                return self._retrieve_base64(key)
        except Exception as e:
            logger.error("获取敏感数据失败 [" + key + "]: " + str(e))
            return None
    
    def delete(self, key: str) -> bool:
        """
        删除存储的敏感数据
        
        Args:
            key: 存储键名
            
        Returns:
            bool: 是否删除成功
        """
        try:
            if self._backend == "dpapi":
                return self._delete_dpapi(key)
            elif self._backend == "keyring":
                return self._delete_keyring(key)
            else:
                return self._delete_base64(key)
        except Exception as e:
            logger.error("删除敏感数据失败 [" + key + "]: " + str(e))
            return False
    
    # ============== Windows DPAPI 后端 ==============
    
    def _get_dpapi_file_path(self) -> str:
        """获取 DPAPI 加密数据存储文件路径"""
        app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        storage_dir = os.path.join(app_data, 'NucleiGUI', 'secure')
        os.makedirs(storage_dir, exist_ok=True)
        return os.path.join(storage_dir, 'credentials.dat')
    
    def _load_dpapi_data(self) -> dict:
        """加载 DPAPI 加密的数据"""
        file_path = self._get_dpapi_file_path()
        if not os.path.exists(file_path):
            return {}
        
        try:
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()
            
            import win32crypt
            decrypted_data = win32crypt.CryptUnprotectData(encrypted_data, None, None, None, 0)
            return json.loads(decrypted_data[1].decode('utf-8'))
        except Exception:
            return {}
    
    def _save_dpapi_data(self, data: dict) -> bool:
        """保存数据并使用 DPAPI 加密"""
        try:
            import win32crypt
            json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            encrypted_data = win32crypt.CryptProtectData(json_data, None, None, None, None, 0)
            
            file_path = self._get_dpapi_file_path()
            with open(file_path, 'wb') as f:
                f.write(encrypted_data)
            return True
        except Exception as e:
            logger.error("DPAPI 加密保存失败: " + str(e))
            return False
    
    def _store_dpapi(self, key: str, value: str) -> bool:
        data = self._load_dpapi_data()
        data[key] = value
        return self._save_dpapi_data(data)
    
    def _retrieve_dpapi(self, key: str) -> Optional[str]:
        data = self._load_dpapi_data()
        return data.get(key)
    
    def _delete_dpapi(self, key: str) -> bool:
        data = self._load_dpapi_data()
        if key in data:
            del data[key]
            return self._save_dpapi_data(data)
        return True
    
    # ============== Keyring 后端 ==============
    
    def _store_keyring(self, key: str, value: str) -> bool:
        import keyring
        keyring.set_password(self.SERVICE_NAME, key, value)
        return True
    
    def _retrieve_keyring(self, key: str) -> Optional[str]:
        import keyring
        return keyring.get_password(self.SERVICE_NAME, key)
    
    def _delete_keyring(self, key: str) -> bool:
        import keyring
        try:
            keyring.delete_password(self.SERVICE_NAME, key)
        except Exception:
            pass
        return True
    
    # ============== Base64 后端（不安全，仅用于兼容）==============
    
    def _get_base64_file_path(self) -> str:
        """获取 base64 数据存储文件路径"""
        app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        storage_dir = os.path.join(app_data, 'NucleiGUI')
        os.makedirs(storage_dir, exist_ok=True)
        return os.path.join(storage_dir, 'credentials.json')
    
    def _load_base64_data(self) -> dict:
        file_path = self._get_base64_file_path()
        if not os.path.exists(file_path):
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                encoded_data = json.load(f)
            
            return {k: base64.b64decode(v).decode('utf-8') for k, v in encoded_data.items()}
        except Exception:
            return {}
    
    def _save_base64_data(self, data: dict) -> bool:
        try:
            encoded_data = {k: base64.b64encode(v.encode('utf-8')).decode('utf-8') for k, v in data.items()}
            
            file_path = self._get_base64_file_path()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(encoded_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error("Base64 保存失败: " + str(e))
            return False
    
    def _store_base64(self, key: str, value: str) -> bool:
        data = self._load_base64_data()
        data[key] = value
        return self._save_base64_data(data)
    
    def _retrieve_base64(self, key: str) -> Optional[str]:
        data = self._load_base64_data()
        return data.get(key)
    
    def _delete_base64(self, key: str) -> bool:
        data = self._load_base64_data()
        if key in data:
            del data[key]
            return self._save_base64_data(data)
        return True


# 全局单例
_secure_storage = None


def get_secure_storage() -> SecureStorage:
    """获取安全存储管理器单例"""
    global _secure_storage
    if _secure_storage is None:
        _secure_storage = SecureStorage()
    return _secure_storage


def store_api_key(service: str, api_key: str) -> bool:
    """
    存储 API Key
    
    Args:
        service: 服务名称（如 'fofa', 'ai_openai' 等）
        api_key: API Key 值
        
    Returns:
        bool: 是否存储成功
    """
    return get_secure_storage().store("api_key_" + service, api_key)


def get_api_key(service: str) -> Optional[str]:
    """
    获取 API Key
    
    Args:
        service: 服务名称
        
    Returns:
        Optional[str]: API Key 值
    """
    return get_secure_storage().retrieve("api_key_" + service)


def delete_api_key(service: str) -> bool:
    """
    删除 API Key
    
    Args:
        service: 服务名称
        
    Returns:
        bool: 是否删除成功
    """
    return get_secure_storage().delete("api_key_" + service)
