import time
import threading
import tkinter as tk
from tkinter import scrolledtext
from tkinter import messagebox
from playwright.sync_api import sync_playwright

# ==========================================
# 【全局默认设置】
# 既然不写配置表了，我们需要一个通用的"暗号"来找消息
# 这里填你之前找到的那个通用选择器
DEFAULT_SELECTOR = ".lastNewMsg" 
# ==========================================

class App:
    def __init__(self, root):
        self.root = root
        root.title("全自动客服监控精灵 (自动扫描版)")
        root.geometry("700x500")
        
        # 1. 第一步：启动浏览器的按钮
        self.btn_launch = tk.Button(root, text="第一步：打开专用浏览器", command=self.launch_browser_thread, bg="#FF9500", fg="black", font=("Arial", 12))
        self.btn_launch.pack(pady=10, fill=tk.X, padx=20)

        # 2. 第二步：开始接管的按钮
        self.btn_scan = tk.Button(root, text="第二步：我已经登录好了，开始接管！", command=self.start_scan, bg="#007AFF", fg="white", font=("Arial", 14, "bold"))
        self.btn_scan.pack(pady=5, fill=tk.X, padx=20)
        self.btn_scan.config(state="disabled") # 一开始先禁用，等浏览器开了再启用
        
        # 消息显示区
        self.text_area = scrolledtext.ScrolledText(root, width=80, height=20, font=("Arial", 12))
        self.text_area.pack(padx=10, pady=10)
        
        # 状态变量
        self.playwright = None
        self.browser = None
        self.context = None
        self.monitored_pages = [] # 用来存目前正在监控的页面
        self.is_running = False

    def log(self, msg):
        current_time = time.strftime("%H:%M:%S")
        self.text_area.insert(tk.END, f"[{current_time}] {msg}\n")
        self.text_area.see(tk.END)

    def launch_browser_thread(self):
        """在一个新线程里启动浏览器，防止界面卡死"""
        threading.Thread(target=self._launch_browser_core, daemon=True).start()

    def _launch_browser_core(self):
        try:
            self.playwright = sync_playwright().start()
            # headless=False 必须是 False，否则你看不到浏览器
            self.browser = self.playwright.chromium.launch(headless=False)
            
            # 创建一个上下文（你可以理解为一个浏览器窗口）
            self.context = self.browser.new_context()
            
            # 先开一个空白页
            page = self.context.new_page()
            page.goto("about:blank")
            
            self.log(">>> 浏览器已启动！ <<<")
            self.log("请在弹出的浏览器中：")
            self.log("1. 点击 + 号新建标签页")
            self.log("2. 打开你的客服后台网址")
            self.log("3. 完成登录并停留在消息页面")
            self.log("4. 搞定后，点击软件上的【第二步】按钮")
            
            # 启用第二步的按钮
            self.btn_scan.config(state="normal", bg="#007AFF")
            self.btn_launch.config(state="disabled", text="浏览器运行中...")
            
        except Exception as e:
            self.log(f"启动失败: {e}")

    def start_scan(self):
        """点击按钮后，扫描当前浏览器里所有的标签页"""
        if not self.context:
            return
            
        # 获取当前所有打开的标签页
        all_pages = self.context.pages
        
        count = 0
        for page in all_pages:
            # 跳过空白页
            if page.url == "about:blank":
                continue
                
            # 获取网页标题作为名字
            title = page.title()
            if not title:
                title = "未知页面"
            
            self.log(f"已捕获页面: {title}")
            
            # 把这个页面加入监控列表
            self.monitored_pages.append({
                "page": page,
                "title": title,
                "last_msg": ""
            })
            count += 1
            
        if count == 0:
            messagebox.showwarning("提示", "你好像还没打开任何网页？请先在浏览器里打开后台！")
            return
            
        self.log(f"--------------------------------")
        self.log(f"成功接管了 {count} 个后台页面！开始监控...")
        self.log(f"--------------------------------")
        
        self.is_running = True
        self.btn_scan.config(state="disabled", text="正在监控中...")
        
        # 启动监控循环线程
        threading.Thread(target=self.monitoring_loop, daemon=True).start()

    def monitoring_loop(self):
        """死循环，不停地轮询所有页面"""
        while self.is_running:
            for item in self.monitored_pages:
                try:
                    page = item['page']
                    # 使用默认的暗号选择器
                    elements = page.locator(DEFAULT_SELECTOR).all()
                    
                    if elements:
                        # 获取文字（根据你的反馈，有时候是第一个，有时候是最后一个，这里默认取第一个）
                        # 如果抓不到，就把 [0] 改成 [-1]
                        new_text = elements[0].text_content()
                        
                        if new_text and new_text.strip() != "" and new_text != item['last_msg']:
                            # 只有新消息才显示
                            self.log(f"🔔 【{item['title']}】: {new_text.strip()}")
                            item['last_msg'] = new_text
                            
                except Exception as e:
                    # 页面可能被关闭了或者刷新中，跳过
                    pass
            
            # 休息2秒，给CPU喘口气
            time.sleep(2)

    def on_closing(self):
        """关闭软件时清理资源"""
        self.is_running = False
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()