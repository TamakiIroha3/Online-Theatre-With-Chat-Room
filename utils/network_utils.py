# utils/network_utils.py - 网络工具
import socket
import ipaddress
import netifaces
import platform
from typing import List, Tuple, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

class NetworkUtils:
    """网络工具类"""
    
    @staticmethod
    def get_all_ip_addresses() -> List[Tuple[str, str]]:
        """
        获取所有网络接口的IP地址
        返回: [(ip_address, interface_name), ...]
        """
        ip_list = []
        
        try:
            # 获取所有网络接口
            interfaces = netifaces.interfaces()
            
            for interface in interfaces:
                try:
                    addrs = netifaces.ifaddresses(interface)
                    
                    # 获取IPv4地址
                    if netifaces.AF_INET in addrs:
                        for addr_info in addrs[netifaces.AF_INET]:
                            ip = addr_info.get('addr')
                            if ip and not ip.startswith('127.'):
                                ip_list.append((ip, f"{interface} (IPv4)"))
                    
                    # 获取IPv6地址
                    if netifaces.AF_INET6 in addrs:
                        for addr_info in addrs[netifaces.AF_INET6]:
                            ip = addr_info.get('addr', '').split('%')[0]  # 去掉范围标识符
                            if ip and NetworkUtils.is_valid_ipv6(ip):
                                # 过滤本地链路地址
                                if not ip.startswith('fe80:'):
                                    ip_list.append((ip, f"{interface} (IPv6)"))
                
                except Exception as e:
                    logger.debug(f"获取接口 {interface} 地址失败: {e}")
        
        except Exception as e:
            logger.error(f"获取网络接口失败: {e}")
        
        return ip_list
    
    @staticmethod
    def get_public_ipv6() -> Optional[str]:
        """获取公网IPv6地址"""
        try:
            # 尝试连接到IPv6 DNS服务器来获取本机IPv6
            s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            s.connect(("2001:4860:4860::8888", 80))  # Google DNS IPv6
            ip = s.getsockname()[0]
            s.close()
            
            # 验证是否为公网地址
            addr = ipaddress.IPv6Address(ip)
            if not addr.is_private and not addr.is_link_local:
                return ip
        except Exception as e:
            logger.debug(f"获取公网IPv6失败: {e}")
        
        return None
    
    @staticmethod
    def get_local_ip(prefer_ipv6=True) -> str:
        """
        获取本机IP地址
        Args:
            prefer_ipv6: 是否优先返回IPv6地址
        """
        # 尝试获取公网IPv6
        if prefer_ipv6:
            ipv6 = NetworkUtils.get_public_ipv6()
            if ipv6:
                return ipv6
        
        # 获取所有IP地址
        all_ips = NetworkUtils.get_all_ip_addresses()
        
        # 分类IP地址
        ipv6_addrs = []
        ipv4_addrs = []
        
        for ip, interface in all_ips:
            if ':' in ip:  # IPv6
                ipv6_addrs.append(ip)
            else:  # IPv4
                ipv4_addrs.append(ip)
        
        # 根据偏好返回
        if prefer_ipv6 and ipv6_addrs:
            return ipv6_addrs[0]
        elif ipv4_addrs:
            return ipv4_addrs[0]
        elif ipv6_addrs:
            return ipv6_addrs[0]
        else:
            return "127.0.0.1"
    
    @staticmethod
    def is_valid_ipv6(ip: str) -> bool:
        """验证IPv6地址是否有效"""
        try:
            # 去掉可能的范围标识符
            ip = ip.split('%')[0]
            ipaddress.IPv6Address(ip)
            return True
        except (ipaddress.AddressValueError, ValueError):
            return False
    
    @staticmethod
    def is_valid_ipv4(ip: str) -> bool:
        """验证IPv4地址是否有效"""
        try:
            ipaddress.IPv4Address(ip)
            return True
        except (ipaddress.AddressValueError, ValueError):
            return False
    
    @staticmethod
    def is_valid_ip(ip: str) -> bool:
        """验证IP地址是否有效（IPv4或IPv6）"""
        return NetworkUtils.is_valid_ipv4(ip) or NetworkUtils.is_valid_ipv6(ip)
    
    @staticmethod
    def format_ipv6_for_url(ip: str) -> str:
        """
        格式化IPv6地址用于URL
        IPv6地址在URL中需要用方括号包围
        """
        if NetworkUtils.is_valid_ipv6(ip):
            # 去掉可能的方括号，然后重新添加
            ip = ip.strip('[]')
            return f"[{ip}]"
        return ip
    
    @staticmethod
    def parse_address(address: str) -> Tuple[str, Optional[int]]:
        """
        解析地址字符串，分离IP和端口
        支持IPv4、IPv6格式
        Examples:
            "192.168.1.1:8080" -> ("192.168.1.1", 8080)
            "[::1]:8080" -> ("::1", 8080)
            "example.com:80" -> ("example.com", 80)
        """
        # IPv6格式 [ip]:port
        if address.startswith('['):
            try:
                ip_end = address.index(']')
                ip = address[1:ip_end]
                if ip_end + 1 < len(address) and address[ip_end + 1] == ':':
                    port = int(address[ip_end + 2:])
                    return ip, port
                return ip, None
            except (ValueError, IndexError):
                pass
        
        # IPv4格式或域名 ip:port
        if ':' in address:
            parts = address.rsplit(':', 1)
            if len(parts) == 2:
                try:
                    port = int(parts[1])
                    return parts[0], port
                except ValueError:
                    pass
        
        return address, None
    
    @staticmethod
    def find_available_port(start_port: int, max_attempts: int = 100) -> Optional[int]:
        """
        从指定端口开始查找可用端口
        Args:
            start_port: 起始端口
            max_attempts: 最大尝试次数
        Returns:
            可用端口号，如果没找到返回None
        """
        for i in range(max_attempts):
            port = start_port + i
            if NetworkUtils.is_port_available(port):
                return port
        return None
    
    @staticmethod
    def is_port_available(port: int, host: str = '') -> bool:
        """
        检查端口是否可用
        Args:
            port: 端口号
            host: 主机地址，默认为所有接口
        """
        # 同时检查IPv4和IPv6
        for family in [socket.AF_INET, socket.AF_INET6]:
            try:
                with socket.socket(family, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    if family == socket.AF_INET6:
                        # IPv6特定设置
                        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                        bind_addr = (host if host else '::', port)
                    else:
                        bind_addr = (host if host else '0.0.0.0', port)
                    
                    s.bind(bind_addr)
                    s.listen(1)
            except (OSError, socket.error):
                return False
        
        return True
    
    @staticmethod
    def resolve_hostname(hostname: str, prefer_ipv6: bool = True) -> Optional[str]:
        """
        解析主机名到IP地址
        Args:
            hostname: 主机名
            prefer_ipv6: 是否优先返回IPv6地址
        """
        try:
            # 获取所有地址信息
            addr_info = socket.getaddrinfo(hostname, None)
            
            ipv6_addrs = []
            ipv4_addrs = []
            
            for info in addr_info:
                family, _, _, _, addr = info
                if family == socket.AF_INET6:
                    ipv6_addrs.append(addr[0])
                elif family == socket.AF_INET:
                    ipv4_addrs.append(addr[0])
            
            # 根据偏好返回
            if prefer_ipv6 and ipv6_addrs:
                return ipv6_addrs[0]
            elif ipv4_addrs:
                return ipv4_addrs[0]
            elif ipv6_addrs:
                return ipv6_addrs[0]
        
        except socket.gaierror as e:
            logger.error(f"解析主机名 {hostname} 失败: {e}")
        
        return None
    
    @staticmethod
    def create_socket(host: str, port: int, ipv6_first: bool = True) -> Optional[socket.socket]:
        """
        创建socket连接，自动处理IPv4/IPv6
        Args:
            host: 主机地址
            port: 端口
            ipv6_first: 是否优先尝试IPv6
        """
        families = [socket.AF_INET6, socket.AF_INET] if ipv6_first else [socket.AF_INET, socket.AF_INET6]
        
        for family in families:
            try:
                sock = socket.socket(family, socket.SOCK_STREAM)
                sock.settimeout(10)  # 10秒超时
                
                if family == socket.AF_INET6:
                    # 处理IPv6地址格式
                    if NetworkUtils.is_valid_ipv6(host):
                        connect_addr = (host, port, 0, 0)
                    else:
                        # 尝试解析为IPv6
                        resolved = NetworkUtils.resolve_hostname(host, prefer_ipv6=True)
                        if resolved and NetworkUtils.is_valid_ipv6(resolved):
                            connect_addr = (resolved, port, 0, 0)
                        else:
                            sock.close()
                            continue
                else:
                    # IPv4地址
                    if NetworkUtils.is_valid_ipv4(host):
                        connect_addr = (host, port)
                    else:
                        # 尝试解析为IPv4
                        resolved = NetworkUtils.resolve_hostname(host, prefer_ipv6=False)
                        if resolved and NetworkUtils.is_valid_ipv4(resolved):
                            connect_addr = (resolved, port)
                        else:
                            sock.close()
                            continue
                
                sock.connect(connect_addr)
                return sock
            
            except (socket.error, OSError) as e:
                logger.debug(f"使用 {family} 连接到 {host}:{port} 失败: {e}")
                continue
        
        return None