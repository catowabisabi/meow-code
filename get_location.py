"""
獲取本機 IP 地址並查詢地理位置
"""

import requests
import json


def get_current_ip():
    """獲取當前公網 IP 地址"""
    try:
        response = requests.get("https://ipinfo.io/json", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"獲取 IP 失敗: {e}")
        return None


def main():
    print("正在獲取 IP 和位置信息...\n")
    
    info = get_current_ip()
    
    if info:
        print("=" * 50)
        print("📍 你的位置信息")
        print("=" * 50)
        print(f"  IP 地址:    {info.get('ip', 'N/A')}")
        print(f"  主機名:      {info.get('hostname', 'N/A')}")
        print(f"  城市:        {info.get('city', 'N/A')}")
        print(f"  省份/地區:   {info.get('region', 'N/A')}")
        print(f"  國家:        {info.get('country', 'N/A')}")
        print(f"  坐標:        {info.get('loc', 'N/A')}")
        print(f"  郵編:        {info.get('postal', 'N/A')}")
        print(f"  時區:        {info.get('timezone', 'N/A')}")
        print(f"  運營商:      {info.get('org', 'N/A')}")
        print("=" * 50)
        
        # 解析坐標
        if info.get('loc'):
            lat, lon = info['loc'].split(',')
            print(f"\n🗺️  Google Maps 鏈接: https://www.google.com/maps?q={lat},{lon}")


if __name__ == "__main__":
    main()