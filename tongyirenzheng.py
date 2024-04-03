import requests
import re
cookies = None

def post_api(tid, auth, ticket1):
    url = 'https://apiucloud.bupt.edu.cn/ykt-basics/oauth/token'
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Authorization': auth,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://ucloud.bupt.edu.cn',
        'Referer': 'https://ucloud.bupt.edu.cn/',
        'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Microsoft Edge";v="122"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'Tenant-Id': tid,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0'
    }

    data = {
        'ticket': ticket1,
        'grant_type': 'third'
    }

    response = requests.post(url, headers=headers, data=data)
    #print(response.status_code)
    #print(response.json())  # 如果返回的是 JSON 数据，可以使用 json() 方法来解析
    blade = response.json()['access_token']
    userid = response.json()['user_id']
    return [blade,userid]

def extract_values(html_content):
    # 定义正则表达式模式
    # 使用正则表达式找到匹配项
    execution_value = re.search(r'<input\s+name="execution"\s+value="([^"]+)"', html_content)

    if execution_value:
        execution_value = execution_value.group(1)
        #print(execution_value)
    else:
        print("未找到execution的值")
    return execution_value

def get_and_print(url):
    global cookies
    try:
        response = requests.get(url, allow_redirects=False)
        print("Initial URL:", response.url)
        while response.status_code == 302:  # 302状态码表示重定向
            redirected_url = response.headers['Location']
            print("Redirected to:", redirected_url)
            response = requests.get(redirected_url, allow_redirects=False)
        if response.status_code == 200:
            cookies = response.cookies
            return extract_values(response.text)
        else:
            print("Failed to retrieve content. Status code:", response.status_code)
    except requests.exceptions.RequestException as e:
        print("Error:", e)

def get_login_cookies (username, password,exe):
    url = "https://auth.bupt.edu.cn/authserver/login?service=http://ucloud.bupt.edu.cn"  # 替换为实际的登录URL
    data = {
        'username': username,
        'password': password,
        'submit': '登录',
        'type': 'username_password',
        'execution': exe,
        '_eventId': 'submit',
    }
    try:
        response = requests.post(url, data=data,allow_redirects=False,cookies=cookies)
        redirected_url = response.headers['Location']
        print("重定向地址ticket:", redirected_url)
        ticket_pattern = r"ticket=(\S+)"
        match = re.search(ticket_pattern, redirected_url)
        ticket = match.group(1)
 #       print(ticket)
        response = requests.post(redirected_url, allow_redirects=False, cookies=response.cookies)
        redirected_url = response.headers['Location']
        response = requests.get(redirected_url, allow_redirects=False, cookies=response.cookies)
        js_links = re.findall(r'<script src="([^"]+\.js)"></script>', response.content.decode('utf-8'))
        js_content = None
        # 下载并打印index.js的内容
        for link in js_links:
            if 'index' in link:
                js_content = requests.get('https://ucloud.bupt.edu.cn/'+link).content
        pattern = r'headers:\s*{\s*Authorization:\s*"([^"]+)",\s*"Tenant-Id":\s*"([^"]+)"\s*}'
        match = re.search(pattern, str(js_content))
        auth_token = match.group(1)  # 获取 Authorization 字段的值
        tenant_id = match.group(2)  # 获取 Tenant-Id 字段的值
        print("Authorization:", auth_token)
        print("Tenant-Id:", tenant_id)
        blade_userid = post_api(tenant_id, auth_token, ticket)
        results = [tenant_id,auth_token,blade_userid[0],blade_userid[1]]
        print(results)
        return results
    except requests.exceptions.RequestException as e:
        print("Error:", e)

def get_co_and_sa(Account,Password):
    url1 = "https://auth.bupt.edu.cn/authserver/login?service=http://ucloud.bupt.edu.cn"
    exe = get_and_print(url1)
    return get_login_cookies(Account, Password,exe)
