from platform import system_alias
import sys
import re
import json
import datetime
import time
from pathlib import Path
from copy import deepcopy
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QListWidget, QListWidgetItem, QMessageBox, QProgressBar
from PyQt5.QtGui import QFont, QColor, QTextCursor
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from PyQt5.QtCore import QThread, pyqtSignal


user_data_dir = Path('./aadx_user_data')

def create_driver(headless=True):
    chrome_options = Options()
    # if headless:
    #     # chrome_options.add_argument('--headless')
    #     pass
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36'
    chrome_options.add_argument(f'user-agent={user_agent}')
    chrome_options.add_argument(f'user-data-dir={str(user_data_dir.resolve())}')
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-webgl")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.implicitly_wait(2)
    return driver

class HitThread(QThread):
    update_progress = pyqtSignal(int)
    users_updated = pyqtSignal(object)
    update_console = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, users, driver):
        super().__init__()
        self.users = users
        self.driver = driver
        self.is_running = True

    def stop(self):
        self.is_running = False 
        
    def run(self):
        for i, user in enumerate(self.users):
            if not self.is_running:
                break
            if user['hit'] == 1:
                self.progress_bar.setValue(i + 1)
                continue
            try:
                self.driver.get(f"https://aadx.io/share?name={user['name']}")
                time.sleep(2)
                button = self.driver.find_element(By.CSS_SELECTOR, '#root > div > div > div.p-chest-boxs > button')
                button.click()
                text_element = self.driver.find_element(By.CSS_SELECTOR, 'body > div.p-chest-modal-portal > div > div > section > div.p-chest-modal-text').text
                if text_element in ['你今日已经助力过相同用户', 'You have hammered this user today.', '你和你的朋友获得了一次助力', 'You and your friend both get 1 help.']:
                    user['hit'] = 1
                else:
                    user['hit'] = -1
                self.update_console.emit(f'{user["name"]}: {text_element}\n')
            except Exception as e:
                user['hit'] = -1
                self.update_console.emit(f'{user["name"]}: Failed, will retry at next time\n')
            self.update_progress.emit(i)
        users_copy = deepcopy(self.users)
        self.users_updated.emit(users_copy)
        self.finished.emit()

class UserHitsApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_users()
        self.update_user_list()

    def init_ui(self):
        self.setGeometry(300, 300, 800, 600)
        self.setWindowTitle('AVAX Hits')

        layout = QHBoxLayout(self)

        # Left side components
        self.text_edit = QTextEdit(self)
        self.parse_button = QPushButton('Parse Links', self)
        self.parse_button.clicked.connect(self.parse_links)
        self.login_button = QPushButton('Login', self)
        self.login_button.clicked.connect(self.login)
    
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.text_edit)
        left_layout.addWidget(self.parse_button)
        left_layout.addWidget(self.login_button)

        # Right side components
        self.user_list = QListWidget(self)
        self.hit_button = QPushButton('Hit', self)
        self.hit_button.clicked.connect(self.hit_users)
        self.console_box = QTextEdit(self)
        self.console_box.setReadOnly(True)  # 设置为只读，使其充当控制台输出
        font = QFont('Consolas')
        font.setStyleHint(QFont.Monospace)  # 强制使用等宽字体
        self.console_box.setFont(font)
        self.console_box.setStyleSheet("""
            QTextEdit {
                background-color: black;
                color: #07da63;
            }
        """)
        self.console_box.append('[INFO]\n')
        self.progress_bar = QProgressBar(self)
        
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.user_list)
        right_layout.addWidget(self.hit_button)
        right_layout.addWidget(self.progress_bar)
        right_layout.addWidget(self.console_box)

        layout.addLayout(left_layout)
        layout.addLayout(right_layout)
        self.setLayout(layout)

        self.driver = None
        self.driver_headless_state = -1
        self.color_mapping = {
            -1: QColor('red'),
            0: QColor('orange'),
            1: QColor('green')
        }

    def enable_head(self):
        self.driver.quit()
        self.driver = create_driver(headless=False)
        self.driver_headless_state = 0

    def disable_head(self):
        self.driver.quit()
        self.driver = create_driver(headless=True)
        self.driver_headless_state = 1
        
    def load_users(self):
        try:
            with open('users.json', 'r') as file:
                self.users = json.load(file)
                for user in self.users:
                    user.setdefault('last_hit', None)
        except FileNotFoundError:
            self.users = []

    def save_users(self):
        with open('users.json', 'w') as file:
            json.dump(self.users, file)

    def parse_links(self):
        text = self.text_edit.toPlainText()
        links = re.findall(r'https?://\S+', text)
        for link in links:
            match = re.search(r'name=([^&]+)', link)
            if match:
                name = match.group(1)
                if not any(user['name'] == name for user in self.users):
                    self.users.append({'name': name, 'hit': -1})
        self.save_users()
        self.update_user_list()
        
    def update_user_list(self, index=None):
        if index is not None and 0 <= index < len(self.users):
            # Update only the item at the specified index
            user = self.users[index]
            item = self.user_list.item(index)
            if item:
                item.setText(user['name'])
                item.setForeground(self.color_mapping[user['hit']])
        else:
            # If no index is provided, update the entire list
            self.user_list.clear()
            for user in self.users:
                item = QListWidgetItem(user['name'])
                item.setForeground(self.color_mapping[user['hit']])
                self.user_list.addItem(item)

    def hit_users(self):
        self.parse_button.setEnabled(False)
        self.login_button.setEnabled(False)
        self.hit_button.setEnabled(False)
        if self.driver is None:
            self.driver = create_driver(headless = True)
            self.driver_headless_state = 1
        if self.driver is not None and self.driver_headless_state == 0:
            self.disable_head()
        self.progress_bar.setMaximum(len(self.users))
        self.progress_bar.setValue(0)

        current_time = datetime.datetime.now()
        for user in self.users:
            last_hit_time = user.get('last_hit')
            if last_hit_time:
                last_hit_time = datetime.datetime.fromisoformat(last_hit_time)
                if (current_time - last_hit_time).total_seconds() < 86400:
                    user['hit'] = 1
                    continue
            user['hit'] = 0 
            
        self.save_users()
            
        self.hit_thread = HitThread(self.users, self.driver)
        self.hit_thread.update_progress.connect(self.update_hit_progress)
        self.hit_thread.update_console.connect(self.append_text_to_console)
        self.hit_thread.users_updated.connect(self.update_users_from_thread)
        self.hit_thread.finished.connect(self.on_hit_finished)
        self.hit_thread.start()
    
    def update_hit_progress(self, i):
        self.update_user_list(i)
        self.progress_bar.setValue(i + 1)
    
    def append_text_to_console(self, text):
        # 将文本追加到 console_box 中
        self.console_box.moveCursor(QTextCursor.End)
        self.console_box.insertPlainText(text)
        self.console_box.moveCursor(QTextCursor.End)
    
    def on_hit_finished(self):
        # 重新启用按钮
        self.parse_button.setEnabled(True)
        self.login_button.setEnabled(True)
        self.hit_button.setEnabled(True)
        # 更新用户列表
        self.update_user_list()
        self.save_users()

    def update_users_from_thread(self, users):
        self.users = users
        self.update_user_list()
    
    def login(self):
        if self.driver is None:
            self.driver = create_driver(headless = False)
            self.driver_headless_state = 0
        if self.driver is not None and self.driver_headless_state == 1:
            self.enable_head()
        self.driver.get('https://aadx.io/share?name=spike2091')
        
    def closeEvent(self, event):
        if hasattr(self, 'hit_thread') and self.hit_thread.isRunning():
            self.hit_thread.stop()
            self.hit_thread.wait()
        if self.driver is not None:
            self.driver.quit()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = UserHitsApp()
    ex.show()
    sys.exit(app.exec_())
