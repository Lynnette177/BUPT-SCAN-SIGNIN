from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timedelta
import os
import requests
from werkzeug.utils import secure_filename
from pyzbar.pyzbar import decode
import json
from PIL import Image
import numpy as np
import cv2
import tongyirenzheng

#os.chdir('/app')


UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.static_folder = 'uploads'

# 存储用户上传的图片信息
uploaded_images = []


usage_count_file = 'usage_count.txt'


# 读取功能使用次数
def read_usage_count():
    try:
        with open(usage_count_file, 'r') as file:
            return int(file.read())
    except FileNotFoundError:
        return 0


# 保存功能使用次数
def save_usage_count(count):
    with open(usage_count_file, 'w') as file:
        file.write(str(count))


def sign_in(userinfo,classinfo,sid):
    try:
        usage_count = read_usage_count()  # 读取功能使用次数
        usage_count += 1  # 每次访问主页，增加计数
        save_usage_count(usage_count)  # 保存功能使用次数
    except:
        pass
    current_time = datetime.now()
    current_time += timedelta(minutes=1)
    # 格式化为所需的字符串格式
    formatted_time = current_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]  # 去除毫秒的后三位

    url = 'https://apiucloud.bupt.edu.cn/ykt-site/attendancedetailinfo/sign'
    headers = {
        'Host': 'apiucloud.bupt.edu.cn',
        'Accept': '*/*',
        'Authorization': userinfo[1],
        'Sec-Fetch-Site': 'same-site',
        'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
        'Sec-Fetch-Mode': 'cors',
        'Content-Type': 'application/json',
        'Origin': 'https://appucloud.bupt.edu.cn',
        'Blade-Auth': userinfo[2],
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.48(0x1800302c) NetType/WIFI Language/zh_CN',
        'Referer': 'https://appucloud.bupt.edu.cn/',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
    }

    data = {
        "attendanceDetailInfo": {
            "attendanceId": classinfo.get('attendanceDetailInfo', {}).get('attendanceId'),
            "siteId": classinfo.get('attendanceDetailInfo', {}).get('siteId'),
            "userId": userinfo[3],
            "classLessonId": classinfo.get('attendanceDetailInfo', {}).get('classLessonId'),
        },
        "qrCodeCreateTime": formatted_time
    }
    print(headers)
    print(data)
    response = requests.post(url, json=data, headers=headers)

    print(response.status_code)
    print(response.text)
    if response.json().get('msg') is not None:
        return response.json().get('msg')
    os.remove('Accounts/'+sid+'.txt')
    return response.json().get('message') + '  已经删除过期数据。请重新登录。'

def check_file_in_folder(title):
    files = os.listdir('uploads')
    if (title + '.txt') in files:
        return True
    else:
        return False


# 检查图片是否是二维码
def is_qr_code(image_path):
    pil_image = Image.open(image_path)
    # 将PIL图像转换为NumPy数组
    image_np = np.array(pil_image)
    # 将NumPy数组传递给OpenCV
    image = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
    # 转换为灰度图
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # 解码图片中的二维码
    decocdeQR = decode(gray_image)
    if not decocdeQR:
        return 0
    else:
        qrvalue = ''
        for obj in decocdeQR:
            # 提取二维码的位置和数据
            x, y, w, h = obj.rect
            # 提取二维码的图像
            qr_code = gray_image[y:y + h, x:x + w]
            # 对二维码图像进行二值化处理
            _, qr_code_bin = cv2.threshold(qr_code, 128, 255, cv2.THRESH_BINARY)
            # 打印二维码数据
            qrvalue = obj.data.decode('utf-8')
        print(qrvalue)
        try:
            parts = qrvalue.split('|')
            info_part = parts[1]

            # 解析信息部分为字典
            info_dict = {}
            for item in info_part.split('&'):
                key, value = item.split('=')
                info_dict[key] = value

            # 创建 JSON 结构
            result_json = {
                "qrCodeCreateTime": info_dict["createTime"],
                "attendanceDetailInfo": {
                    "siteId": info_dict["siteId"],
                    "attendanceId": info_dict["id"],
                    "userId": "",  # 在原始字符串中没有提到该字段，这里使用 get 方法避免 KeyError
                    "classLessonId": info_dict["classLessonId"]
                }
            }
            print(result_json)
            with open((image_path[:image_path.rfind('.')] + '.txt'), 'w') as txt_file:
                json.dump(result_json, txt_file, indent=2)
        except:
            print("不是合法二维码")
            return 2
    return 1


def get_txt_files():
    # 获取文件夹中的所有txt文件名
    txt_files = [file[:-4] for file in os.listdir('Accounts') if file.endswith('.txt')]
    return txt_files


@app.route('/user_info/<title>', methods=['GET', 'POST'])
def user_info(title):
    if not check_file_in_folder(title):
        return "不存在这个课程"
    txt_files = get_txt_files()  # 获取所有txt文件名
    with open('uploads/' + title + '.txt', 'r') as file:
        loaded_data = json.load(file)
    if request.method == 'POST' and 'login' in request.form:
        # 处理用户信息并发送给服务器的API
        username = request.form['username']
        password = request.form['password']
        save_password = request.form.get('save_password')  # 获取保存密码复选框的值
        print(title,username,password)
        try:
            result = tongyirenzheng.get_co_and_sa(username,password)
        except:
            return render_template('user_info.html',
                                   error_message='登录失败。请检查用户名密码。', txt_files=txt_files)
        try:
            smsg = sign_in(result, loaded_data,username)
        except Exception as e:
            print(e)
            smsg = "未知原因签到失败"
        smsg = str(username) + ':' + smsg
        smsglist = [smsg]
        if save_password:
            with open('Accounts/' + username + '.txt', 'w') as file:
                # 将列表中的每个元素写入文件，并在每个元素后添加换行符
                for item in result:
                    file.write(item + '\n')
            txt_files = get_txt_files()  # 获取所有txt文件名
            return render_template('user_info.html', result=smsglist, error_message='Cookie已保存到服务器。过期后将删除。', txt_files=txt_files)
        # 调用API发送用户信息及标题
        return render_template('user_info.html', result=smsglist, txt_files=txt_files)
    elif request.method == 'POST' and 'signin' in request.form:
        selected_ids = request.form.getlist('selected_ids')
        # 对每个学号进行操作：
        smsglist = []
        for student_id in selected_ids:
            with open('Accounts/' + student_id + '.txt', 'r') as file:
                # 逐行读取文件内容并放入列表中
                acc_cookie = file.readlines()
                # 去除每行末尾的换行符
            acc_cookie = [line.strip() for line in acc_cookie]
            try:
                smsg = sign_in(acc_cookie, loaded_data,student_id)
            except Exception as e:
                print(e)
                smsg = '未知原因签到失败'
            smsg = str(student_id) + ':' + smsg
            smsglist.append(smsg)
        print(smsglist)
        txt_files = get_txt_files()  # 获取所有txt文件名
        return render_template('user_info.html', result=smsglist, txt_files=txt_files)
    return render_template('user_info.html', title=title, txt_files=txt_files)


# 主页
@app.route('/')
def index():
    try:
        usage_count = read_usage_count()
    except:
        usage_count = 0
    upload_folder = app.config['UPLOAD_FOLDER']
    image_files = os.listdir(upload_folder)
    images = []
    images_exd = []
    now = datetime.now()

    # 创建包含文件名和创建时间的元组列表
    file_time_tuples = []
    for image_file in image_files:
        if image_file[-3:] == 'txt':
            continue
        try:
            creation_time = os.path.getctime(os.path.join(upload_folder, image_file))
            file_time_tuples.append((image_file, creation_time))
        except OSError:
            # 如果无法获取文件创建时间，跳过该文件
            continue

    # 按照创建时间对文件列表进行排序
    sorted_file_time_tuples = sorted(file_time_tuples, key=lambda x: x[1], reverse=True)
    current_time = float(datetime.now().timestamp())
    # 根据排序后的文件列表生成图片信息字典
    for image_file, creation_time in sorted_file_time_tuples:
        try:
            t_difference = current_time - creation_time
            # 如果文件创建时间超过 24 小时（86400 秒），则删除文件
            if t_difference > 86400:
                os.remove('uploads/' + image_file)
                os.remove('uploads/' + image_file[:image_file.rfind('.')] + '.txt')
                continue
        except:
            pass
        try:
            title, expiry_time_str = image_file.split('--')
            expiry_time = datetime.strptime(expiry_time_str.split('.')[0], '%Y-%m-%d-%H-%M-%S')
            expired = expiry_time < now
            if expired:
                images_exd.append({'filename': image_file, 'title': title,
                               'creation_time': datetime.fromtimestamp(creation_time).strftime('%Y-%m-%d %H:%M:%S'),
                               'expiry_time': expiry_time.strftime('%Y-%m-%d-%H-%M-%S'), 'expired': expired})
            else:
                images.append({'filename':image_file,'title': title, 'creation_time': datetime.fromtimestamp(creation_time).strftime('%Y-%m-%d %H:%M:%S'), 'expiry_time': expiry_time.strftime('%Y-%m-%d-%H-%M-%S'), 'expired': expired})
        except ValueError:
            # 如果无法解析过期时间，跳过该文件
            continue
    images+=(images_exd)
    return render_template('index.html', images=images,usage_count=usage_count)


# 上传图片
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        title = request.form['title']
        expiry_minutes = int(request.form['expiry_time'])
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            expiry_time = datetime.now() + timedelta(minutes=expiry_minutes)
            new_filename = f"{title}--{expiry_time.strftime('%Y-%m-%d-%H-%M-%S')}.{filename.split('.')[-1]}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
            qrresult = is_qr_code(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
            if qrresult  == 0:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
                return render_template('upload.html', error_message="上传的图片没有二维码，或者识别不到，尝试拍的清楚一些吧")
            elif qrresult == 2:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
                return render_template('upload.html',
                                       error_message="上传的图片不是签到的二维码")
            return redirect(url_for('index'))
    return render_template('upload.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=False)
