import requests

url = "https://public-api.birdeye.so/defi/txs/token/seek_by_time?offset=0&limit=10&tx_type=swap&token_address=4rToHJLjcdDjtuXupVqCXgMWBaJcxLtQ6dZVMZAsCUsq"
headers = {
    "accept": "application/json",
    "x-chain": "solana",
    "X-API-KEY": "c11020fe7a6d4fea8f3c118b3565ac39"
}
resp = requests.get(url, headers=headers)
print(resp.status_code)
print(resp.text)
