import argparse
import openpyxl
import getform
import send
import sys

author_info = r'''
 _    _            _    _ _ _           
| |  | |          | |  (_) | |          
| |  | | ___  __ _| | ___| | | ___ _ __ 
| |/\| |/ _ \/ _` | |/ / | | |/ _ \ '__|
\  /\  /  __/ (_| |   <| | | |  __/ |   
 \/  \/ \___|\__,_|_|\_\_|_|_|\___|_|   
'''


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


def process_urls(urls):
    for url in urls:
        if not url.startswith("http"):
            url = "http://" + url
        print(f"\n正在处理: {url}")
        form = getform.getForm(url)
        result, symbol = form.run()
        if symbol == 0 or result is None or result["params"] is None:
            print("跳过无效URL。")
            continue
        sender = send.send(url, result)
        sender.run()


if __name__ == '__main__':
    print(author_info)

    parser = argparse.ArgumentParser(description='WakeTool - 表单处理工具')
    parser.add_argument('-u', '--url', help='处理单个 URL')
    parser.add_argument('-t', '--file', help='从 txt 文件读取 URL 列表')
    parser.add_argument('-e', '--excel', help='从 Excel 文件读取 URL 列表')

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
        sys.exit(0)

    print(f"\n共获取 {len(urls)} 个 URL，开始处理...\n")
    process_urls(urls)

