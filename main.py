import time
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
from playwright.sync_api import sync_playwright

# ==========================================
# 【全局配置】
# 这里填你之前抓取到的"消息元素"选择器
# 如果不同网站的规则不一样，这里默认填最常用的那个
DEFAULT_SELECTOR = ".lastNewMsg" 
# ==========================================

class App:
    def __init__(self, root):
        self.root = root
        root.title("客服消息聚合助手 (Edge版)")
        root.geometry("700x550")
        
        # --- 界面布局 ---
        
        # 顶部说明
        lbl_instruction = tk.Label(root, text="操作流程：\n1. 点击下方橙色按钮打开浏览器\n2. 在打开的 Edge 中新建标签页，登录各个客服后台\n3. 登录完成后，点击下方蓝色按钮开始接管", 
                                   bg="#f0f0f0", justify=tk.LEFT, padx=10, pady=10)
        lbl_instruction.pack(fill=tk.X)

        # 1. 启动按钮
        self.btn_launch = tk.Button(root, text="第一步：启动 Edge 浏览器", command=self.launch_browser_thread, 
                                    bg="#FF9500", fg="black", font=("Arial", 12, "bold"), height=2)
        self.btn_launch.pack(pady=10, fill=tk.X, padx=20)

        # 2. 接管按钮
        self.btn_scan = tk.Button(root, text="第二步：已登录完成，开始监控！", command=self.start_scan, 
                                  bg="#007AFF", fg="white", font=("Arial", 14, "bold"), height=2)
        self.btn_scan.pack(pady=5, fill=tk.X, padx=20)
        self.btn_scan.config(state="disabled") # 初始禁用
        
        # 消息显示区
        self.text_area = scrolledtext.ScrolledText(root, width=80, height=20, font=("Arial", 12))
        self.text_area.pack(padx=10, pady=10)
        
        # 底部状态栏
        self.lbl_status = tk.Label(root, text="准备就绪", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.lbl_status.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 内部变量
        self.playwright = None
        self.browser = None
        self.context = None
        self.monitored_pages = [] 
        self.is_running = False

    def log(self, msg):
        """记录日志到界面"""
        current_time = time.strftime("%H:%M:%S")
        self.text_area.insert(tk.END, f"[{current_time}] {msg}\n")
        self.text_area.see(tk.END)
        self.lbl_status.config(text=msg)

    def launch_browser_thread(self):
        """在后台线程启动浏览器"""
        threading.Thread(target=self._launch_browser_core, daemon=True).start()

    def _launch_browser_core(self):
        try:
            self.log("正在启动 Playwright 引擎...")
            self.playwright = sync_playwright().start()
            
            # =====================================================
            # 【关键】 channel="msedge" 调用系统自带的 Edge
            # =====================================================
            try:
                self.log("正在寻找系统 Edge 浏览器...")
                # headless=False 必须为 False，否则无法人工登录
                self.browser = self.playwright.chromium.launch(channel="msedge", headless=False)
            except Exception:
                messagebox.showerror("错误", "启动失败！\n请检查电脑是否安装了 Microsoft Edge 浏览器。")
                self.log("❌ 启动失败：未找到 Edge。")
                return

            # 创建上下文（浏览器实例）
            self.context = self.browser.new_context()
            
            # 打开一个空白页作为起始
            page = self.context.new_page()
            page.goto("about:blank")
            
            self.log(">>> Edge 浏览器已启动！请进行登录操作 <<<")
            
            # 界面状态切换
            self.btn_scan.config(state="normal", bg="#007AFF")
            self.btn_launch.config(state="disabled", text="Edge 运行中...")
            
        except Exception as e:
            self.log(f"启动发生未知错误: {e}")
            messagebox.showerror("错误", f"详情: {e}")

    def start_scan(self):
        """扫描当前浏览器打开的所有标签页"""
        if not self.context:
            return
            
        # 获取所有标签页
        all_pages = self.context.pages
        
        # 清空旧的监控列表
        self.monitored_pages = []
        count = 0
        
        for page in all_pages:
            # 跳过空白页
            if page.url == "about:blank":
                continue
                
            title = page.title()
            if not title: title = "未知页面"
            
            # 加入监控名单
            self.monitored_pages.append({
                "page": page,
                "title": title,
                "last_msg": ""
            })
            self.log(f"已捕获页面: {title}")
            count += 1
            
        if count == 0:
            messagebox.showwarning("提示", "未检测到有效的网页！\n请先在 Edge 中新建标签页并打开客服后台。")
            return
            
        self.log(f"--------------------------------")
        self.log(f"成功接管 {count} 个页面！开始实时监控...")
        self.log(f"--------------------------------")
        
        self.is_running = True
        self.btn_scan.config(state="disabled", text="正在监控中 (关闭软件停止)")
        
        # 启动轮询线程
        threading.Thread(target=self.monitoring_loop, daemon=True).start()

    def monitoring_loop(self):
        """核心循环：不断检查新消息"""
        while self.is_running:
            for item in self.monitored_pages:
                try:
                    page = item['page']
                    # 查找消息元素
                    elements = page.locator(DEFAULT_SELECTOR).all()
                    
                    if elements:
                        # 尝试获取第一条或最后一条（根据你的反馈，如果是最新消息在最上面用[0]，在最下面用[-1]）
                        # 这里默认取第一个
                        new_text = elements[0].text_content()
                        
                        # 只有当：1.有字 2.不为空白 3.和上次不一样 时，才报警
                        if new_text and new_text.strip() != "" and new_text != item['last_msg']:
                            full_msg = f"🔔 【{item['title']}】新消息: {new_text.strip()}"
                            self.log(full_msg)
                            item['last_msg'] = new_text
                            
                except Exception:
                    # 页面可能被关闭了，跳过不报错
                    pass
            
            # 每 3 秒检查一次
            time.sleep(3)

    def on_closing(self):
        """关闭窗口时的清理"""
        if messagebox.askokcancel("退出", "确定要关闭助手吗？\n这将同时关闭 Edge 浏览器。"):
            self.is_running = False
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    # 绑定关闭事件
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()