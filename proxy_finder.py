#!/usr/bin/env python3
"""
Proxy finder and checker utility
Fetches proxy lists from various sources and tests them
"""

import requests
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random

class ProxyFinder:
    def __init__(self):
        self.sources = [
            {
                'name': 'free-proxy-list.net',
                'url': 'https://free-proxy-list.net/',
                'parser': self.parse_free_proxy_list
            },
            {
                'name': 'proxy-list.download HTTP',
                'url': 'https://www.proxy-list.download/api/v1/get?type=http',
                'parser': self.parse_proxy_list_download
            },
            {
                'name': 'proxy-list.download HTTPS',
                'url': 'https://www.proxy-list.download/api/v1/get?type=https',
                'parser': self.parse_proxy_list_download
            },
            {
                'name': 'proxyscrape HTTP',
                'url': 'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all',
                'parser': self.parse_proxyscrape
            }
        ]

        # Well-known public proxies for testing (may not work)
        self.test_proxies = [
            'http://httpbin.org/ip',  # Not a proxy, for testing
        ]

    def parse_free_proxy_list(self, content):
        """Parse free-proxy-list.net format"""
        proxies = []
        # This would require HTML parsing, simplified version
        return proxies

    def parse_proxy_list_download(self, content):
        """Parse proxy-list.download format"""
        try:
            data = json.loads(content)
            return [f"{proxy['ip']}:{proxy['port']}" for proxy in data]
        except:
            # Fallback: treat as plain text list
            return [line.strip() for line in content.split('\n') if ':' in line]

    def parse_proxyscrape(self, content):
        """Parse proxyscrape format"""
        return [line.strip() for line in content.split('\n') if ':' in line and line.strip()]

    def fetch_proxy_list(self, source, timeout=15):
        """Fetch proxy list from a source"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(source['url'], headers=headers, timeout=timeout)

            if response.status_code == 200:
                proxies = source['parser'](response.text)
                print(f"✓ {source['name']}: Found {len(proxies)} proxies")
                return proxies
            else:
                print(f"✗ {source['name']}: HTTP {response.status_code}")
                return []

        except requests.exceptions.RequestException as e:
            print(f"✗ {source['name']}: {str(e)}")
            return []
        except Exception as e:
            print(f"✗ {source['name']}: Parse error - {str(e)}")
            return []

    def check_proxy(self, proxy, test_url='http://httpbin.org/ip', timeout=10):
        """Check if a proxy is working"""
        try:
            proxy_dict = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }

            start_time = time.time()
            response = requests.get(
                test_url,
                proxies=proxy_dict,
                timeout=timeout,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            response_time = time.time() - start_time

            if response.status_code == 200:
                try:
                    data = response.json()
                    real_ip = data.get('origin', 'unknown')
                    return {
                        'proxy': proxy,
                        'status': 'working',
                        'response_time': round(response_time, 2),
                        'real_ip': real_ip,
                        'protocol': 'http'
                    }
                except:
                    return {
                        'proxy': proxy,
                        'status': 'working',
                        'response_time': round(response_time, 2),
                        'protocol': 'http'
                    }
            else:
                return {
                    'proxy': proxy,
                    'status': 'failed',
                    'error': f'HTTP {response.status_code}'
                }

        except Exception as e:
            return {
                'proxy': proxy,
                'status': 'failed',
                'error': str(e)
            }

    def find_working_proxies(self, max_proxies_per_source=50, max_workers=20):
        """Find working proxies from all sources"""
        all_proxies = []

        print("Fetching proxy lists from sources...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_source = {
                executor.submit(self.fetch_proxy_list, source): source
                for source in self.sources
            }

            for future in as_completed(future_to_source):
                proxies = future.result()
                if proxies:
                    # Limit proxies per source to avoid overwhelming
                    limited_proxies = proxies[:max_proxies_per_source]
                    all_proxies.extend(limited_proxies)

        # Remove duplicates
        all_proxies = list(set(all_proxies))
        print(f"\nCollected {len(all_proxies)} unique proxies")

        if not all_proxies:
            print("No proxies found from sources. Using test proxies...")
            # Add some well-known test proxies
            test_proxies = [
                '8.8.8.8:80',     # Google DNS (unlikely to work as proxy)
                '1.1.1.1:80',     # Cloudflare DNS
                '208.67.222.222:80',  # OpenDNS
                '208.67.220.220:80'   # OpenDNS
            ]
            all_proxies.extend(test_proxies)

        print(f"Testing {len(all_proxies)} proxies...")

        working_proxies = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_proxy = {
                executor.submit(self.check_proxy, proxy): proxy
                for proxy in all_proxies
            }

            for future in as_completed(future_to_proxy):
                result = future.result()
                if result['status'] == 'working':
                    working_proxies.append(result)
                    print(f"✓ {result['proxy']} - {result['response_time']}s - IP: {result.get('real_ip', 'N/A')}")
                else:
                    print(f"✗ {result['proxy']} - {result['error']}")

        print(f"\nFound {len(working_proxies)} working proxies")
        return working_proxies

def main():
    finder = ProxyFinder()
    working_proxies = finder.find_working_proxies()

    # Save results
    with open('working_proxies.json', 'w') as f:
        json.dump(working_proxies, f, indent=2)

    # Save simple list for easy use
    with open('working_proxies.txt', 'w') as f:
        for proxy in working_proxies:
            f.write(f"{proxy['proxy']}\n")

    print(f"\nResults saved to working_proxies.json and working_proxies.txt")

if __name__ == "__main__":
    main()
