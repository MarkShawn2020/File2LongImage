#!/usr/bin/env python3
"""
File2LongImage macOS Application (简化版)
不依赖 tkinterdnd2 的版本，但仍支持 macOS 特性
"""

import os
import sys
import time
import subprocess
import pdf2image
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
from pathlib import Path
from config import OUTPUT_DIR, POPPLER_PATH, LIBREOFFICE_PATH, INTERMEDIATE_DIR

# 增加 PIL 的最大图像像素限制
Image.MAX_IMAGE_PIXELS = 500000000  # 5亿像素

class File2LongImageApp:
    def __init__(self, root):
        self.root = root
        self.setup_ui()
        self.setup_macos_features()
        self.current_files = []
        self.processing = False
        
    def setup_ui(self):
        """设置用户界面"""
        self.root.title("File2LongImage")
        self.root.geometry("700x500")
        
        # 设置 macOS 风格
        if sys.platform == 'darwin':
            self.root.configure(bg='#f0f0f0')
            try:
                style = ttk.Style()
                style.theme_use('aqua')
            except:
                pass
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="文件转长图工具", 
                                font=('Helvetica', 24, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding="10")
        file_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        main_frame.rowconfigure(1, weight=1)
        file_frame.columnconfigure(0, weight=1)
        
        # 文件列表
        list_frame = ttk.Frame(file_frame)
        list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # 列表框和滚动条
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.file_listbox = tk.Listbox(list_frame, height=6, 
                                       yscrollcommand=scrollbar.set,
                                       selectmode=tk.EXTENDED)
        self.file_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.config(command=self.file_listbox.yview)
        
        # 文件操作按钮
        file_btn_frame = ttk.Frame(file_frame)
        file_btn_frame.grid(row=1, column=0, pady=5)
        
        ttk.Button(file_btn_frame, text="添加文件", 
                  command=self.select_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_btn_frame, text="删除选中", 
                  command=self.remove_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_btn_frame, text="清空列表", 
                  command=self.clear_files).pack(side=tk.LEFT, padx=2)
        
        # 设置区域
        settings_frame = ttk.LabelFrame(main_frame, text="设置", padding="10")
        settings_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # DPI 设置
        ttk.Label(settings_frame, text="图片 DPI:").grid(row=0, column=0, sticky=tk.W)
        self.dpi_var = tk.IntVar(value=300)
        self.dpi_scale = ttk.Scale(settings_frame, from_=72, to=600, 
                                   variable=self.dpi_var, orient=tk.HORIZONTAL)
        self.dpi_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=10)
        self.dpi_label = ttk.Label(settings_frame, text="300")
        self.dpi_label.grid(row=0, column=2)
        
        def update_dpi_label(value):
            self.dpi_label.config(text=str(int(float(value))))
        self.dpi_scale.config(command=update_dpi_label)
        
        settings_frame.columnconfigure(1, weight=1)
        
        # 输出格式
        ttk.Label(settings_frame, text="输出格式:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.format_var = tk.StringVar(value="PNG")
        format_frame = ttk.Frame(settings_frame)
        format_frame.grid(row=1, column=1, sticky=tk.W, padx=10)
        ttk.Radiobutton(format_frame, text="PNG", variable=self.format_var, 
                       value="PNG").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="JPG", variable=self.format_var, 
                       value="JPG").pack(side=tk.LEFT, padx=5)
        
        # JPG 质量
        self.quality_frame = ttk.Frame(settings_frame)
        self.quality_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        ttk.Label(self.quality_frame, text="JPG 质量:").pack(side=tk.LEFT)
        self.quality_var = tk.IntVar(value=85)
        self.quality_scale = ttk.Scale(self.quality_frame, from_=1, to=100,
                                      variable=self.quality_var, orient=tk.HORIZONTAL)
        self.quality_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.quality_label = ttk.Label(self.quality_frame, text="85")
        self.quality_label.pack(side=tk.LEFT)
        
        def update_quality_label(value):
            self.quality_label.config(text=str(int(float(value))))
        self.quality_scale.config(command=update_quality_label)
        
        # 格式切换时显示/隐藏质量设置
        def on_format_change(*args):
            if self.format_var.get() == "JPG":
                self.quality_frame.grid()
            else:
                self.quality_frame.grid_remove()
        self.format_var.trace('w', on_format_change)
        on_format_change()  # 初始化显示状态
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var)
        self.progress_bar.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # 状态标签
        self.status_label = ttk.Label(main_frame, text="准备就绪", foreground='#666')
        self.status_label.grid(row=4, column=0)
        
        # 转换按钮
        self.convert_btn = ttk.Button(main_frame, text="开始转换", 
                                      command=self.start_conversion,
                                      state=tk.DISABLED)
        self.convert_btn.grid(row=5, column=0, pady=10)
        
    def setup_macos_features(self):
        """设置 macOS 特定功能"""
        if sys.platform == 'darwin':
            # 设置应用菜单
            menubar = tk.Menu(self.root)
            self.root.config(menu=menubar)
            
            # 应用菜单
            app_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="File2LongImage", menu=app_menu)
            app_menu.add_command(label="关于", command=self.show_about)
            app_menu.add_separator()
            app_menu.add_command(label="偏好设置", command=self.show_preferences, 
                               accelerator="Cmd+,")
            app_menu.add_separator()
            app_menu.add_command(label="退出", command=self.root.quit, 
                               accelerator="Cmd+Q")
            
            # 文件菜单
            file_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="文件", menu=file_menu)
            file_menu.add_command(label="打开文件", command=self.select_files,
                                accelerator="Cmd+O")
            file_menu.add_command(label="清空列表", command=self.clear_files)
            file_menu.add_separator()
            file_menu.add_command(label="转换", command=self.start_conversion,
                                accelerator="Cmd+R")
            
            # 编辑菜单
            edit_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="编辑", menu=edit_menu)
            edit_menu.add_command(label="删除选中", command=self.remove_selected,
                                accelerator="Delete")
            
            # 窗口菜单
            window_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="窗口", menu=window_menu)
            window_menu.add_command(label="最小化", command=self.root.iconify,
                                  accelerator="Cmd+M")
            
            # 帮助菜单
            help_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="帮助", menu=help_menu)
            help_menu.add_command(label="使用指南", command=self.show_help)
            
            # 绑定快捷键
            self.root.bind('<Command-o>', lambda e: self.select_files())
            self.root.bind('<Command-r>', lambda e: self.start_conversion())
            self.root.bind('<Command-q>', lambda e: self.root.quit())
            self.root.bind('<Command-comma>', lambda e: self.show_preferences())
            self.root.bind('<Command-m>', lambda e: self.root.iconify())
            self.root.bind('<Delete>', lambda e: self.remove_selected())
            self.root.bind('<BackSpace>', lambda e: self.remove_selected())
    
    def select_files(self):
        """选择文件"""
        # macOS 的 Tkinter 不支持分号分隔的扩展名，需要使用空格分隔
        if sys.platform == 'darwin':
            filetypes = [
                ("所有支持的文件", "*.pdf *.doc *.docx *.ppt *.pptx *.csv *.xls *.xlsx *.odt *.rtf *.txt"),
                ("PDF 文件", "*.pdf"),
                ("Word 文档", "*.doc *.docx"),
                ("Excel 表格", "*.xls *.xlsx *.csv"),
                ("PowerPoint", "*.ppt *.pptx"),
                ("文本文件", "*.txt *.rtf"),
                ("所有文件", "*")
            ]
        else:
            filetypes = [
                ("所有支持的文件", "*.pdf;*.doc;*.docx;*.ppt;*.pptx;*.csv;*.xls;*.xlsx;*.odt;*.rtf;*.txt"),
                ("PDF 文件", "*.pdf"),
                ("Word 文档", "*.doc;*.docx"),
                ("Excel 表格", "*.xls;*.xlsx;*.csv"),
                ("PowerPoint", "*.ppt;*.pptx"),
                ("文本文件", "*.txt;*.rtf"),
                ("所有文件", "*.*")
            ]
        files = filedialog.askopenfilenames(filetypes=filetypes)
        if files:
            self.add_files(files)
    
    def add_files(self, files):
        """添加文件到列表"""
        for file in files:
            if file not in self.current_files:
                self.current_files.append(file)
                self.file_listbox.insert(tk.END, os.path.basename(file))
        
        if self.current_files:
            self.convert_btn.config(state=tk.NORMAL)
            self.status_label.config(text=f"已选择 {len(self.current_files)} 个文件")
    
    def remove_selected(self):
        """删除选中的文件"""
        selection = self.file_listbox.curselection()
        if selection:
            # 从后往前删除，避免索引变化
            for index in reversed(selection):
                self.file_listbox.delete(index)
                del self.current_files[index]
            
            if not self.current_files:
                self.convert_btn.config(state=tk.DISABLED)
                self.status_label.config(text="准备就绪")
            else:
                self.status_label.config(text=f"已选择 {len(self.current_files)} 个文件")
    
    def clear_files(self):
        """清空文件列表"""
        self.current_files = []
        self.file_listbox.delete(0, tk.END)
        self.convert_btn.config(state=tk.DISABLED)
        self.status_label.config(text="准备就绪")
    
    def start_conversion(self):
        """开始转换"""
        if not self.current_files or self.processing:
            return
        
        # 在新线程中执行转换
        thread = threading.Thread(target=self.convert_files)
        thread.daemon = True
        thread.start()
    
    def convert_files(self):
        """转换文件（在后台线程中运行）"""
        self.processing = True
        self.root.after(0, lambda: self.convert_btn.config(state=tk.DISABLED))
        
        # 创建输出目录
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(INTERMEDIATE_DIR, exist_ok=True)
        
        total_files = len(self.current_files)
        success_count = 0
        failed_files = []
        
        for idx, file_path in enumerate(self.current_files):
            try:
                # 更新状态
                self.root.after(0, lambda i=idx, f=file_path: 
                              self.status_label.config(
                                  text=f"正在转换 ({i+1}/{total_files}): {os.path.basename(f)}"))
                
                # 转换文件
                dpi = self.dpi_var.get()
                output_format = self.format_var.get()
                quality = self.quality_var.get() if output_format == "JPG" else 85
                
                output_path = self.convert_single_file(file_path, OUTPUT_DIR, 
                                                       dpi, output_format, quality)
                if output_path:
                    success_count += 1
                else:
                    failed_files.append(os.path.basename(file_path))
                
                # 更新进度
                progress = (idx + 1) / total_files * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                
            except Exception as e:
                failed_files.append(f"{os.path.basename(file_path)}: {str(e)}")
        
        # 转换完成
        self.processing = False
        self.root.after(0, self.conversion_complete, success_count, failed_files)
    
    def convert_single_file(self, file_path, output_dir, dpi, output_format, quality):
        """转换单个文件"""
        images = []
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        
        if file_path.lower().endswith('.pdf'):
            images = pdf2image.convert_from_path(file_path, poppler_path=POPPLER_PATH, dpi=dpi)
        elif file_path.lower().endswith((".doc", ".docx", ".ppt", ".pptx", ".csv", 
                                        ".xls", ".xlsx", ".odt", ".rtf", ".txt")):
            if LIBREOFFICE_PATH is None:
                raise ValueError("LibreOffice 未安装")
            
            # 转换为 PDF
            pdf_path = os.path.join(INTERMEDIATE_DIR, f"{base_name}.pdf")
            conversion_cmd = f'{LIBREOFFICE_PATH} --headless --convert-to pdf "{file_path}" --outdir "{INTERMEDIATE_DIR}"'
            subprocess.run(conversion_cmd, shell=True, capture_output=True)
            
            if os.path.exists(pdf_path):
                images = pdf2image.convert_from_path(pdf_path, poppler_path=POPPLER_PATH, dpi=dpi)
                os.remove(pdf_path)  # 清理临时 PDF
            else:
                raise ValueError("文件转换失败")
        else:
            raise ValueError("不支持的文件格式")
        
        if images:
            # 合并图像
            output_path = os.path.join(output_dir, f"{base_name}.{output_format.lower()}")
            return self.merge_images(images, output_path, output_format, quality)
        
        return None
    
    def merge_images(self, images, output_path, output_format, quality):
        """合并图像"""
        widths, heights = zip(*(i.size for i in images))
        total_height = sum(heights)
        max_width = max(widths)
        
        merged_image = Image.new('RGB', (max_width, total_height))
        y_offset = 0
        
        for img in images:
            merged_image.paste(img, (0, y_offset))
            y_offset += img.height
        
        # 保存图像
        if output_format == "JPG":
            merged_image = merged_image.convert("RGB")
            merged_image.save(output_path, format="JPEG", quality=quality, optimize=True)
        else:
            merged_image.save(output_path, format="PNG", optimize=True)
        
        return output_path
    
    def conversion_complete(self, success_count, failed_files):
        """转换完成后的处理"""
        self.convert_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)
        
        if failed_files:
            message = f"转换完成！\n成功: {success_count} 个文件\n失败: {len(failed_files)} 个文件\n\n失败文件:\n" + "\n".join(failed_files)
            messagebox.showwarning("转换完成", message)
        else:
            message = f"所有 {success_count} 个文件转换成功！"
            messagebox.showinfo("转换完成", message)
            
            # 打开输出文件夹
            if sys.platform == 'darwin':
                subprocess.run(['open', OUTPUT_DIR])
            elif sys.platform == 'win32':
                os.startfile(OUTPUT_DIR)
        
        self.status_label.config(text="转换完成")
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """File2LongImage v1.0
        
文件转长图工具
将 PDF、Word、Excel、PPT 等文档
转换为高质量长图

© 2024 File2LongImage
基于 Python, Tkinter, pdf2image"""
        messagebox.showinfo("关于 File2LongImage", about_text)
    
    def show_preferences(self):
        """显示偏好设置窗口"""
        pref_window = tk.Toplevel(self.root)
        pref_window.title("偏好设置")
        pref_window.geometry("400x300")
        
        # 设置内容
        ttk.Label(pref_window, text="默认设置", font=('Helvetica', 16, 'bold')).pack(pady=10)
        
        frame = ttk.Frame(pref_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="默认 DPI:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Label(frame, text=str(self.dpi_var.get())).grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(frame, text="默认格式:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Label(frame, text=self.format_var.get()).grid(row=1, column=1, sticky=tk.W)
        
        ttk.Label(frame, text="输出目录:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Label(frame, text=OUTPUT_DIR).grid(row=2, column=1, sticky=tk.W)
        
        ttk.Button(pref_window, text="关闭", 
                  command=pref_window.destroy).pack(pady=10)
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """使用指南：

1. 点击"添加文件"或拖放文件到列表
2. 设置转换参数：
   - DPI：图片清晰度（72-600）
   - 格式：PNG（无损）或 JPG（有损）
   - 质量：JPG 压缩质量（1-100）
3. 点击"开始转换"
4. 转换完成后自动打开输出文件夹

支持的文件格式：
PDF, Word (doc/docx), Excel (xls/xlsx),
PowerPoint (ppt/pptx), 文本文件等

快捷键：
Cmd+O - 打开文件
Cmd+R - 开始转换
Delete - 删除选中文件
Cmd+Q - 退出程序"""
        messagebox.showinfo("使用指南", help_text)

def main():
    root = tk.Tk()
    app = File2LongImageApp(root)
    
    # 设置应用图标（如果存在）
    icon_path = "assets/icon.icns"
    if os.path.exists(icon_path):
        try:
            root.iconbitmap(icon_path)
        except:
            pass
    
    # 居中窗口
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    root.mainloop()

if __name__ == "__main__":
    main()