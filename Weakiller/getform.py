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
                    params: body
                };
                window.interceptedRequests.push(requestData);
                console.log("Intercepted Request:", requestData);
                return send.apply(this, arguments);
            };
        })();
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
                    
                    "@name='username']"

                )))
            username_input.send_keys("testuser")
        except Exception:
            print(f"[ERROR] 找不到账号输入框")
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

            password_input.send_keys("Testpass@123")
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

        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button["
                    "contains(., '登') or "
                    "contains(., '交') or "
                    "span[contains(., '登')] or "
                    "span[contains(., 'ogin')] or "
                    "span[span[contains(., '登')]]"
                    "] | "

                    "//a[contains(text(), '登')] | "

                    "//input[contains(@value, '登')]"

                ))
            ).click()
            time.sleep(2)
        except:
            print(f"[ERROR] 未检测到登陆按钮")
            return 0
        try:
            self.driver.switch_to.alert.dismiss()
        except NoAlertPresentException:
            pass

    def get_result(self):
        intercepted_requests = self.driver.execute_script("return window.interceptedRequests;")

        if intercepted_requests:
            req = intercepted_requests[0]
            print("获取到提交表单:")
            print(f"请求方法: {req['method']}")
            print(f"请求路径: {req['url']}")
            print(f"请求参数: {req['params']}\n")

            return req
        print("[ERROR] 未拦截到表单提交")
        return 0
