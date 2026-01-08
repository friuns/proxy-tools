#!/usr/bin/env python3
"""
Simple proxy checker utility
Usage: python3 proxy_checker.py <proxy_list_file>
"""

import sys
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def check_proxy(proxy, timeout=10):
    """
    Check if a proxy is working by making a request through it
    """
    proxy_dict = {
        'http': f'http://{proxy}',
        'https': f'http://{proxy}'
    }

    try:
        # Test with a simple HTTP request
        response = requests.get(
            'http://httpbin.org/ip',
            proxies=proxy_dict,
            timeout=timeout,
            headers={'User-Agent': 'Mozilla/5.0'}
        )

        if response.status_code == 200:
            data = response.json()
            real_ip = data.get('origin', 'unknown')
            return {
                'proxy': proxy,
                'status': 'working',
                'response_time': response.elapsed.total_seconds(),
                'real_ip': real_ip
            }
        else:
            return {
                'proxy': proxy,
                'status': 'failed',
                'error': f'HTTP {response.status_code}'
            }

    except requests.exceptions.RequestException as e:
        return {
            'proxy': proxy,
            'status': 'failed',
            'error': str(e)
        }
    except Exception as e:
        return {
            'proxy': proxy,
            'status': 'failed',
            'error': f'Unexpected error: {str(e)}'
        }

def check_proxies_from_file(filename, max_workers=10):
    """
    Check all proxies from a file (one proxy per line, format: ip:port)
    """
    try:
        with open(filename, 'r') as f:
            proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
        return []

    print(f"Loaded {len(proxies)} proxies from {filename}")
    print(f"Checking proxies with {max_workers} concurrent threads...")

    results = []
    working_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_proxy = {executor.submit(check_proxy, proxy): proxy for proxy in proxies}

        for future in as_completed(future_to_proxy):
            result = future.result()
            results.append(result)

            if result['status'] == 'working':
                working_count += 1
                print(f"✓ {result['proxy']} - {result['response_time']:.2f}s - Real IP: {result['real_ip']}")
            else:
                print(f"✗ {result['proxy']} - {result['error']}")

    print(f"\nSummary: {working_count}/{len(proxies)} proxies are working")
    return results

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 proxy_checker.py <proxy_list_file>")
        print("File should contain one proxy per line in format: ip:port")
        sys.exit(1)

    filename = sys.argv[1]
    results = check_proxies_from_file(filename)

    # Save results to JSON file
    output_file = f"{filename.rsplit('.', 1)[0]}_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {output_file}")

if __name__ == "__main__":
    main()
