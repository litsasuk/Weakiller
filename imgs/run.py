import argparse
import openpyxl
import getform
import send
import sys
from urllib.parse import urlparse, urljoin

author_info = r'''
 _    _            _    _ _ _           
| |  | |          | |  (_) | |          
| |  | | ___  __ _| | ___| | | ___ _ __ 
| |/\| |/ _ \/ _` | |/ / | | |/ _ \ '__|
\  /\  /  __/ (_| |   <| | | |  __/ |   
 \/  \/ \___|\__,_|_|\_\_|_|_|\___|_|   
'''


def detect_login_and_target_urls(url):
    """检测URL类型并返回登录页面URL和目标页面URL"""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    
    # 已知的登录页面路径模式
    login_patterns = ['/login', '/auth', '/signin', '/sign-in']
    
    # 检查是否已经是登录页面
    is_login_page = any(pattern in parsed_url.path.lower() for pattern in login_patterns)
    
    if is_login_page:
        # 如果已经是登录页面，返回原URL作为登录页面，目标页面为None
        return url, None
    
    # 不是登录页面，需要推断登录页面
    base_url = f"{parsed_url.scheme}://{domain}"
    
    # 针对特定网站的登录页面推断
    if 'toolpath.com' in domain:
        login_url = urljoin(base_url, '/login')
        return login_url, url
    elif 'github.com' in domain:
        login_url = urljoin(base_url, '/login')
        return login_url, url
    elif 'gitlab.com' in domain:
        login_url = urljoin(base_url, '/users/sign_in')
        return login_url, url
    else:
        # 默认尝试常见的登录路径
        for pattern in login_patterns:
            login_url = urljoin(base_url, pattern)
            return login_url, url
    
    # 如果无法推断，返回原URL
    return url, None


def extract_page_name_from_url(url):
    """从URL提取页面名称用于文件命名"""
    if not url:
        return "unknown_page"
    
    parsed_url = urlparse(url)
    path = parsed_url.path.strip('/')
    
    if not path:
        return "home"
    
    # 将路径转换为有效的文件名
    # 移除或替换不适合文件名的字符
    page_name = path.replace('/', '_').replace('\\', '_').replace(':', '_')
    page_name = ''.join(c for c in page_name if c.isalnum() or c in '_-.')
    
    # 限制长度
    if len(page_name) > 50:
        page_name = page_name[:50]
    
    return page_name if page_name else "page"


def read_urls_from_txt(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"[ERROR] 无法读取文件: {file_path} - {e}")
        sys.exit(1)


def read_urls_from_excel(file_path):
    try:
        wb = openpyxl.load_workbook(file_path)
        sheet = wb.active
        return [row[0].strip() for row in sheet.iter_rows(values_only=True) if row[0]]
    except Exception as e:
        print(f"[ERROR] 无法读取 Excel 文件: {file_path} - {e}")
        sys.exit(1)


def process_urls(urls, target_page=None):
    for url in urls:
        if not url.startswith("http"):
            url = "http://" + url
        
        print(f"\n正在处理URL: {url}")
        
        # 检测登录页面和目标页面
        login_url, detected_target = detect_login_and_target_urls(url)
        
        # 确定最终的目标页面
        final_target_page = target_page or detected_target
        
        if detected_target:
            print(f"[INFO] 检测到目标页面: {detected_target}")
            print(f"[INFO] 推断的登录页面: {login_url}")
        elif target_page:
            print(f"[INFO] 使用命令行指定的目标页面: {target_page}")
        
        # 提取页面名称用于文件保存
        page_name = extract_page_name_from_url(final_target_page)
        print(f"[INFO] 页面文件名: {page_name}")
        
        # 使用登录页面URL进行表单提取
        print(f"[INFO] 开始处理登录页面: {login_url}")
        form = getform.getForm(login_url)
        result, symbol = form.run()
        if symbol == 0 or result is None or result["params"] is None:
            print("跳过无效URL。")
            continue
        
        # 创建sender时传递目标页面和页面名称
        sender = send.send(login_url, result, final_target_page, page_name)
        sender.run()


if __name__ == '__main__':
    print(author_info)

    parser = argparse.ArgumentParser(description='WakeTool - 表单处理工具')
    parser.add_argument('-u', '--url', help='处理单个 URL')
    parser.add_argument('-t', '--file', help='从 txt 文件读取 URL 列表')
    parser.add_argument('-e', '--excel', help='从 Excel 文件读取 URL 列表')
    parser.add_argument('--target', help='登录成功后要访问的目标页面URL')

    args = parser.parse_args()

    if args.url:
        urls = [args.url.strip()]
    elif args.file:
        urls = read_urls_from_txt(args.file)
    elif args.excel:
        urls = read_urls_from_excel(args.excel)
    else:
        print("请使用 -u / -f / -e 指定输入方式，例如：")
        print("  python run.py -u http://example.com")
        print("  python run.py -t url_list.txt")
        print("  python run.py -e urls.xlsx")
        print("  python run.py -u http://example.com --target https://target.com/page")
        sys.exit(0)

    print(f"\n共获取 {len(urls)} 个 URL，开始处理...\n")
    if args.target:
        print(f"[INFO] 指定目标页面: {args.target}")
    process_urls(urls, args.target)

