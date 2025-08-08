from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.common.exceptions import NoAlertPresentException
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import StaleElementReferenceException

class getForm:
    def __init__(self, url):
        # options = Options()
        # options.add_argument("--headless")
        # self.driver = webdriver.Firefox(options=options)
        self.driver = webdriver.Firefox()
        self.driver.get(url)

    def run(self):
        self.intercept()
        symbol = self.input()
        form = self.get_result()
        self.driver.quit()
        if form == 0:
            return form, 0
        return form, symbol

    def intercept(self):
        script = """
        window.interceptedRequests = [];
        window.originalFetch = window.fetch;

        // 拦截XMLHttpRequest
        (function() {
            var open = XMLHttpRequest.prototype.open;
            var send = XMLHttpRequest.prototype.send;

            XMLHttpRequest.prototype.open = function(method, url) {
                this._method = method;
                this._url = url;
                return open.apply(this, arguments);
            };

            XMLHttpRequest.prototype.send = function(body) {
                var requestData = {
                    method: this._method,
                    url: this._url,
                    params: body,
                    type: 'XMLHttpRequest'
                };
                window.interceptedRequests.push(requestData);
                console.log("Intercepted XMLHttpRequest:", requestData);
                return send.apply(this, arguments);
            };
        })();

        // 拦截fetch API
        window.fetch = function(url, options = {}) {
            var requestData = {
                method: options.method || 'GET',
                url: url,
                params: options.body || null,
                type: 'fetch'
            };
            window.interceptedRequests.push(requestData);
            console.log("Intercepted fetch:", requestData);
            return window.originalFetch.apply(this, arguments);
        };

        // 拦截表单提交
        document.addEventListener('submit', function(e) {
            var form = e.target;
            var formData = new FormData(form);
            var params = {};
            for (var pair of formData.entries()) {
                params[pair[0]] = pair[1];
            }
            var requestData = {
                method: form.method || 'POST',
                url: form.action || window.location.href,
                params: JSON.stringify(params),
                type: 'form'
            };
            window.interceptedRequests.push(requestData);
            console.log("Intercepted form submit:", requestData);
        });
        """
        self.driver.execute_script(script)

    def input(self):
        try:
            username_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//input["
                    "contains(@placeholder, '账') or "
                    "contains(@placeholder, '帐') or "
                    "contains(@placeholder, '户') or "
                    "contains(@placeholder, 'ser') or "
                    "contains(@placeholder, 'ame') or "
                    "contains(@placeholder, '号') or "
                    "contains(@placeholder, 'mail') or "
                    "contains(@placeholder, 'email') or "
                    "contains(@placeholder, '邮箱') or "
                    "contains(@placeholder, '邮件') or "
                    "@name='username' or "
                    "@name='email' or "
                    "@id='email' or "
                    "@type='email']"

                )))
            username_input.send_keys("yyhxxw@gmail.com")
        except Exception:
            print(f"[ERROR] 找不到用户名/邮箱输入框")
            return 0
        try:
            password_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//input["
                    "contains(@placeholder, '密') or "
                    "contains(@placeholder, 'pass') or "
                    "contains(@placeholder, 'word') or "
                    
                    "@type='password']"
                )))

            password_input.send_keys("xxw123456")
        except Exception:
            print(f"[ERROR] 找不到密码输入框")
            return 0

        try:
            verification_code = self.driver.find_element(
                By.XPATH,
                "//input["
                "contains(@placeholder, '验证码')]"
            )
            print("[INFO] 检测到验证码")
            verification_code.send_keys("0000")
            return 0
        except:
            pass

        # 尝试多种策略查找登录按钮
        login_button = None
        
        # 策略1: 通用按钮查找（包含Log in文本的所有元素）
        try:
            login_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//*[contains(normalize-space(text()), 'Log in') or "
                    "contains(normalize-space(.), 'Log in') or "
                    "contains(normalize-space(text()), 'LOGIN') or "
                    "contains(normalize-space(text()), 'Login')]"
                ))
            )
            print("[INFO] 找到登录按钮 - 策略1")
        except:
            pass
        
        # 策略2: 标准按钮和输入元素
        if not login_button:
            try:
                login_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//button[contains(text(), 'Log in') or contains(text(), 'LOGIN') or contains(text(), 'Login')] | "
                        "//input[@type='submit' and (contains(@value, 'Log in') or contains(@value, 'LOGIN') or contains(@value, 'Login'))] | "
                        "//input[@type='button' and (contains(@value, 'Log in') or contains(@value, 'LOGIN') or contains(@value, 'Login'))]"
                    ))
                )
                print("[INFO] 找到登录按钮 - 策略2")
            except:
                pass
        
        # 策略3: 带role属性的元素
        if not login_button:
            try:
                login_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//*[@role='button' and (contains(text(), 'Log in') or contains(text(), 'LOGIN') or contains(text(), 'Login'))]"
                    ))
                )
                print("[INFO] 找到登录按钮 - 策略3")
            except:
                pass
        
        # 策略4: 查找所有可能的提交按钮
        if not login_button:
            try:
                login_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//button[@type='submit'] | //input[@type='submit'] | //*[@role='button']"
                    ))
                )
                print("[INFO] 找到提交按钮 - 策略4")
            except:
                pass
        
        if login_button:
            try:
                login_button.click()
                print("[INFO] 成功点击登录按钮")
                time.sleep(3)  # 增加等待时间确保请求发送
            except Exception as e:
                print(f"[ERROR] 点击按钮失败: {e}")
                return 0
        else:
            # 调试信息：打印页面中所有可能的按钮
            print("[DEBUG] 未找到登录按钮，页面中的按钮元素：")
            try:
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for i, btn in enumerate(buttons):
                    try:
                        text = btn.text.strip()
                        print(f"  Button {i+1}: '{text}'")
                    except:
                        print(f"  Button {i+1}: [无法获取文本]")
                
                inputs = self.driver.find_elements(By.XPATH, "//input[@type='submit' or @type='button']")
                for i, inp in enumerate(inputs):
                    try:
                        value = inp.get_attribute("value") or ""
                        print(f"  Input {i+1}: value='{value}'")
                    except:
                        print(f"  Input {i+1}: [无法获取属性]")
            except Exception as e:
                print(f"[DEBUG] 获取调试信息失败: {e}")
            
            print(f"[ERROR] 未检测到登陆按钮")
            return 0
        try:
            self.driver.switch_to.alert.dismiss()
        except NoAlertPresentException:
            pass

    def get_result(self):
        # 等待更长时间确保请求被发送
        time.sleep(2)
        
        intercepted_requests = self.driver.execute_script("return window.interceptedRequests;")

        if intercepted_requests:
            print(f"[INFO] 共拦截到 {len(intercepted_requests)} 个请求")
            
            # 显示所有拦截的请求
            for i, req in enumerate(intercepted_requests):
                print(f"\n请求 {i+1}:")
                print(f"  类型: {req.get('type', 'unknown')}")
                print(f"  方法: {req.get('method', 'unknown')}")
                print(f"  路径: {req.get('url', 'unknown')}")
                print(f"  参数: {req.get('params', 'None')}")
            
            # 智能选择登录请求
            login_request = self.find_login_request(intercepted_requests)
            
            if login_request:
                print("\n=== 最终返回的请求数据 ===")
                print(f"请求方法: {login_request.get('method', 'unknown')}")
                print(f"请求路径: {login_request.get('url', 'unknown')}")
                print(f"请求参数: {login_request.get('params', 'None')}\n")
                return login_request
            else:
                print("[ERROR] 未找到有效的登录请求")
                return 0
        else:
            print("[ERROR] 未拦截到表单提交")
            print("[DEBUG] 检查页面是否使用了不同的提交方式...")
            
            # 检查页面是否有表单元素
            try:
                forms = self.driver.find_elements(By.TAG_NAME, "form")
                print(f"[DEBUG] 页面中发现 {len(forms)} 个表单元素")
                for i, form in enumerate(forms):
                    action = form.get_attribute("action") or "当前页面"
                    method = form.get_attribute("method") or "GET"
                    print(f"  表单 {i+1}: action='{action}', method='{method}'")
            except Exception as e:
                print(f"[DEBUG] 检查表单元素失败: {e}")
            
            return 0
    
    def find_login_request(self, requests_list):
        """智能选择真正的登录请求"""
        import re
        import json
        
        # 登录相关的关键字
        login_keywords = ['login', 'auth', 'signin', 'sign-in', 'authenticate', 'session']
        param_keywords = ['email', 'username', 'user', 'password', 'pwd', 'pass', 'passwd']
        
        # 候选请求列表
        candidates = []
        
        for req in requests_list:
            method = req.get('method', '').upper()
            url = req.get('url', '').lower()
            params = req.get('params')
            
            # 只考虑POST请求
            if method != 'POST':
                continue
                
            # 检查URL是否包含登录关键字
            url_score = 0
            for keyword in login_keywords:
                if keyword in url:
                    url_score += 10
                    break
            
            # 检查参数是否包含用户名密码
            param_score = 0
            if params and params != 'None':
                try:
                    # 尝试解析JSON参数
                    if isinstance(params, str):
                        if params.startswith('{'):
                            param_dict = json.loads(params)
                        else:
                            # 可能是form数据，转为字符串检查
                            param_dict = {'content': params.lower()}
                    else:
                        param_dict = params
                    
                    # 检查参数中的关键字
                    param_content = str(param_dict).lower()
                    for keyword in param_keywords:
                        if keyword in param_content:
                            param_score += 5
                    
                    # 额外检查是否包含邮箱格式
                    if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', param_content):
                        param_score += 15
                        
                except (json.JSONDecodeError, TypeError):
                    # 如果无法解析，就直接在字符串中查找
                    param_content = str(params).lower()
                    for keyword in param_keywords:
                        if keyword in param_content:
                            param_score += 5
            
            total_score = url_score + param_score
            
            # 只有得分大于0的请求才被认为是候选
            if total_score > 0:
                candidates.append((req, total_score))
                print(f"[DEBUG] 候选登录请求: {url}, 得分: {total_score}")
        
        if candidates:
            # 按得分排序，返回得分最高的
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_candidate = candidates[0][0]
            print(f"[INFO] 选择最佳登录请求: {best_candidate.get('url')}, 得分: {candidates[0][1]}")
            return best_candidate
        
        # 如果没有找到候选，尝试返回第一个POST请求
        for req in requests_list:
            if req.get('method', '').upper() == 'POST' and req.get('params') and req.get('params') != 'None':
                print("[INFO] 未找到明确的登录请求，返回第一个包含参数的POST请求")
                return req
        
        return None