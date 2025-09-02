#!/usr/bin/env python3
"""
File2LongImage macOS Application
原生 macOS 应用程序，支持菜单栏集成等特性
"""

import os
import sys
import time
import subprocess
import pdf2image
from pdf2image import pdfinfo_from_path
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import queue
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from enum import Enum
from config import OUTPUT_DIR, POPPLER_PATH, LIBREOFFICE_PATH, INTERMEDIATE_DIR

# 增加 PIL 的最大图像像素限制
Image.MAX_IMAGE_PIXELS = 500000000  # 5亿像素

class ConversionStep(Enum):
    """转换步骤枚举"""
    DETECTING = "检测文件类型"
    CONVERTING_TO_PDF = "转换为PDF"
    LOADING_PDF = "加载PDF文档"
    RENDERING_PAGES = "渲染页面"
    MERGING_IMAGES = "合并图片"
    SAVING_OUTPUT = "保存输出"
    COMPLETED = "完成"
    ERROR = "错误"

@dataclass
class ProgressUpdate:
    """进度更新数据类"""
    file_index: int
    total_files: int
    file_name: str
    step: ConversionStep
    step_progress: float = 0.0  # 0-100
    current_page: int = 0
    total_pages: int = 0
    elapsed_time: float = 0.0
    estimated_remaining: Optional[float] = None
    error_message: Optional[str] = None

class ProgressTracker:
    """进度跟踪器"""
    def __init__(self, update_queue: queue.Queue):
        self.queue = update_queue
        self.start_times = {}
        self.step_durations = []  # 用于估算剩余时间
        
    def start_file(self, file_index: int, total_files: int, file_name: str):
        """开始处理文件"""
        self.current_file_start = time.time()
        self.send_update(ProgressUpdate(
            file_index=file_index,
            total_files=total_files,
            file_name=file_name,
            step=ConversionStep.DETECTING,
            elapsed_time=0
        ))
    
    def update_step(self, file_index: int, total_files: int, file_name: str, 
                   step: ConversionStep, progress: float = 0, 
                   current_page: int = 0, total_pages: int = 0):
        """更新步骤进度"""
        elapsed = time.time() - self.current_file_start
        
        # 估算剩余时间
        estimated = None
        if progress > 0 and progress < 100:
            rate = elapsed / (progress / 100)
            estimated = rate - elapsed
        
        self.send_update(ProgressUpdate(
            file_index=file_index,
            total_files=total_files,
            file_name=file_name,
            step=step,
            step_progress=progress,
            current_page=current_page,
            total_pages=total_pages,
            elapsed_time=elapsed,
            estimated_remaining=estimated
        ))
    
    def send_update(self, update: ProgressUpdate):
        """发送更新到UI线程"""
        try:
            self.queue.put_nowait(update)
        except queue.Full:
            pass  # 忽略队列满的情况

class File2LongImageApp:
    def __init__(self, root):
        self.root = root
        self.setup_ui()
        self.setup_macos_features()
        self.current_files = []
        self.processing = False
        self.progress_queue = queue.Queue(maxsize=100)
        self.current_progress_state = None  # 保存当前进度状态
        self.file_start_time = None  # 记录当前文件开始时间
        self.start_progress_monitor()
        self.start_time_updater()  # 启动时间更新器
        
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
        self.dpi_var = tk.IntVar(value=200)
        self.dpi_scale = ttk.Scale(settings_frame, from_=72, to=600, 
                                   variable=self.dpi_var, orient=tk.HORIZONTAL)
        self.dpi_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=10)
        self.dpi_label = ttk.Label(settings_frame, text="200")
        self.dpi_label.grid(row=0, column=2)
        
        def update_dpi_label(value):
            self.dpi_label.config(text=str(int(float(value))))
        self.dpi_scale.config(command=update_dpi_label)
        
        settings_frame.columnconfigure(1, weight=1)
        
        # 输出格式 - 只提供 PNG 和 JPG
        ttk.Label(settings_frame, text="输出格式:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.format_var = tk.StringVar(value="PNG")
        format_frame = ttk.Frame(settings_frame)
        format_frame.grid(row=1, column=1, sticky=tk.W, padx=10)
        ttk.Radiobutton(format_frame, text="PNG (推荐)", variable=self.format_var, 
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
        
        # 进度显示区域
        self.setup_progress_panel(main_frame)
        
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
    
    def setup_progress_panel(self, parent):
        """设置进度显示面板"""
        # 进度容器
        progress_container = ttk.Frame(parent)
        progress_container.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=10)
        progress_container.columnconfigure(0, weight=1)
        
        # 总体进度
        overall_frame = ttk.LabelFrame(progress_container, text="总体进度", padding="10")
        overall_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)
        overall_frame.columnconfigure(0, weight=1)
        
        self.overall_label = ttk.Label(overall_frame, text="准备就绪")
        self.overall_label.grid(row=0, column=0, sticky=tk.W)
        
        self.overall_progress_var = tk.DoubleVar()
        self.overall_progress = ttk.Progressbar(overall_frame, 
                                               variable=self.overall_progress_var,
                                               mode='determinate')
        self.overall_progress.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # 当前文件进度
        file_frame = ttk.LabelFrame(progress_container, text="当前文件", padding="10")
        file_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2)
        file_frame.columnconfigure(0, weight=1)
        
        self.file_name_label = ttk.Label(file_frame, text="", font=('Helvetica', 11, 'bold'))
        self.file_name_label.grid(row=0, column=0, sticky=tk.W)
        
        self.step_label = ttk.Label(file_frame, text="")
        self.step_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        
        self.step_progress_var = tk.DoubleVar()
        self.step_progress = ttk.Progressbar(file_frame, 
                                            variable=self.step_progress_var,
                                            mode='determinate')
        self.step_progress.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # 详细信息网格
        detail_frame = ttk.Frame(file_frame)
        detail_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # 页面进度
        ttk.Label(detail_frame, text="页面进度:").grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.page_progress_label = ttk.Label(detail_frame, text="-")
        self.page_progress_label.grid(row=0, column=1, sticky='w', padx=(0, 20))
        
        # 已用时间
        ttk.Label(detail_frame, text="已用时间:").grid(row=0, column=2, sticky='w', padx=(0, 10))
        self.elapsed_time_label = ttk.Label(detail_frame, text="-")
        self.elapsed_time_label.grid(row=0, column=3, sticky='w', padx=(0, 20))
        
        # 处理速度
        ttk.Label(detail_frame, text="处理速度:").grid(row=0, column=4, sticky='w', padx=(0, 10))
        self.processing_speed_label = ttk.Label(detail_frame, text="-")
        self.processing_speed_label.grid(row=0, column=5, sticky='w')
    
    def start_progress_monitor(self):
        """启动进度监控"""
        def monitor():
            try:
                while True:
                    update = self.progress_queue.get_nowait()
                    self.current_progress_state = update  # 保存当前状态
                    if update.step == ConversionStep.DETECTING:
                        self.file_start_time = time.time()  # 记录文件开始时间
                    self.update_progress_display(update)
            except queue.Empty:
                pass
            finally:
                self.root.after(50, monitor)  # 每50ms检查一次
        
        monitor()
    
    def start_time_updater(self):
        """启动时间更新器 - 实时更新已用时间"""
        def update_time():
            # 只在处理中且有文件开始时间时更新
            if self.processing and self.file_start_time and self.current_progress_state:
                elapsed = time.time() - self.file_start_time
                self.elapsed_time_label.config(text=self.format_time(elapsed))
                
                # 如果有页面信息，更新处理速度
                if (hasattr(self, 'current_progress_state') and 
                    self.current_progress_state.current_page > 0):
                    speed = self.current_progress_state.current_page / elapsed
                    self.processing_speed_label.config(text=f"{speed:.1f} 页/秒")
            
            # 每100ms更新一次时间（10次/秒，流畅且不占用太多资源）
            self.root.after(100, update_time)
        
        update_time()
    
    def update_progress_display(self, update: ProgressUpdate):
        """更新进度显示"""
        # 更新总体进度
        overall_percent = ((update.file_index + update.step_progress/100) / update.total_files) * 100
        self.overall_progress_var.set(overall_percent)
        self.overall_label.config(text=f"文件 {update.file_index + 1}/{update.total_files} ({overall_percent:.1f}%)")
        
        # 更新文件信息
        self.file_name_label.config(text=update.file_name)
        self.step_label.config(text=f"步骤: {update.step.value}")
        self.step_progress_var.set(update.step_progress)
        
        # 更新详细信息
        if update.total_pages > 0:
            self.page_progress_label.config(
                text=f"{update.current_page}/{update.total_pages} 页"
            )
            if update.current_page > 0 and update.elapsed_time > 0:
                speed = update.current_page / update.elapsed_time
                self.processing_speed_label.config(text=f"{speed:.1f} 页/秒")
        else:
            self.page_progress_label.config(text="-")
        
        # 更新时间信息
        self.elapsed_time_label.config(text=self.format_time(update.elapsed_time))
        
        # 错误处理
        if update.step == ConversionStep.ERROR:
            messagebox.showerror("转换错误", update.error_message)
    
    def format_time(self, seconds: float) -> str:
        """格式化时间显示"""
        if seconds < 60:
            return f"{seconds:.1f} 秒"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}:{secs:02d}"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}:{minutes:02d}:{int(seconds % 60):02d}"
    
    def reset_progress_display(self):
        """重置进度显示"""
        self.overall_progress_var.set(0)
        self.overall_label.config(text="准备就绪")
        self.file_name_label.config(text="")
        self.step_label.config(text="")
        self.step_progress_var.set(0)
        self.page_progress_label.config(text="-")
        self.elapsed_time_label.config(text="-")
        self.processing_speed_label.config(text="-")
        self.current_progress_state = None
        self.file_start_time = None
    
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
        
        # 重置进度显示
        self.root.after(0, self.reset_progress_display)
        
        # 创建输出目录
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(INTERMEDIATE_DIR, exist_ok=True)
        
        tracker = ProgressTracker(self.progress_queue)
        total_files = len(self.current_files)
        success_count = 0
        failed_files = []
        
        for idx, file_path in enumerate(self.current_files):
            try:
                file_name = os.path.basename(file_path)
                tracker.start_file(idx, total_files, file_name)
                
                # 更新状态
                self.root.after(0, lambda i=idx, f=file_path, t=total_files: 
                    self.status_label.config(
                        text=f"正在转换 ({i+1}/{t}): {os.path.basename(f)}"
                    )
                )
                
                # 获取转换参数
                dpi = self.dpi_var.get()
                output_format = self.format_var.get()
                quality = self.quality_var.get() if output_format == "JPG" else 85
                
                # 执行转换
                output_path = self.convert_single_file_with_progress(
                    file_path, OUTPUT_DIR, dpi, output_format, quality, 
                    tracker, idx, total_files
                )
                
                if output_path:
                    success_count += 1
                    tracker.update_step(idx, total_files, file_name, 
                                      ConversionStep.COMPLETED, 100)
                else:
                    failed_files.append(file_name)
                    
            except Exception as e:
                failed_files.append(f"{os.path.basename(file_path)}: {str(e)}")
                tracker.send_update(ProgressUpdate(
                    file_index=idx,
                    total_files=total_files,
                    file_name=os.path.basename(file_path),
                    step=ConversionStep.ERROR,
                    error_message=str(e)
                ))
        
        # 转换完成
        self.processing = False
        self.root.after(0, self.conversion_complete, success_count, failed_files)
    
    def convert_single_file_with_progress(self, file_path, output_dir, dpi, 
                                         output_format, quality, tracker, 
                                         file_idx, total_files):
        """带进度跟踪的单文件转换"""
        images = []
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        file_name = os.path.basename(file_path)
        
        # 步骤1: 检测文件类型
        tracker.update_step(file_idx, total_files, file_name, 
                          ConversionStep.DETECTING, 100)
        time.sleep(0.1)  # 短暂延迟让用户看到状态
        
        # 步骤2: 转换为PDF（如果需要）
        if file_path.lower().endswith('.pdf'):
            # 步骤3: 加载PDF
            tracker.update_step(file_idx, total_files, file_name, 
                              ConversionStep.LOADING_PDF, 50)
            
            # 步骤4: 渲染页面
            tracker.update_step(file_idx, total_files, file_name, 
                              ConversionStep.RENDERING_PAGES, 0)
            
            # 使用自定义回调来跟踪页面渲染进度
            images = self.convert_pdf_with_progress(
                file_path, dpi, tracker, file_idx, total_files, file_name
            )
            
        elif file_path.lower().endswith((".doc", ".docx", ".ppt", ".pptx", ".csv", 
                                        ".xls", ".xlsx", ".odt", ".rtf", ".txt")):
            if LIBREOFFICE_PATH is None:
                raise ValueError("LibreOffice 未安装，无法转换 Office 文件")
            
            # 步骤2: 转换为PDF
            tracker.update_step(file_idx, total_files, file_name, 
                              ConversionStep.CONVERTING_TO_PDF, 0)
            
            pdf_path = os.path.join(INTERMEDIATE_DIR, f"{base_name}.pdf")
            conversion_cmd = f'{LIBREOFFICE_PATH} --headless --convert-to pdf "{file_path}" --outdir "{INTERMEDIATE_DIR}"'
            
            # 异步执行转换并监控进度
            process = subprocess.Popen(conversion_cmd, shell=True, 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE)
            
            # 模拟进度（LibreOffice 不提供进度信息）
            start_time = time.time()
            while process.poll() is None:
                elapsed = time.time() - start_time
                # 假设最多30秒，显示进度
                progress = min(elapsed / 30 * 100, 95)
                tracker.update_step(file_idx, total_files, file_name, 
                                  ConversionStep.CONVERTING_TO_PDF, progress)
                time.sleep(0.5)
            
            if process.returncode == 0 and os.path.exists(pdf_path):
                tracker.update_step(file_idx, total_files, file_name, 
                                  ConversionStep.CONVERTING_TO_PDF, 100)
                
                # 步骤3: 加载PDF
                tracker.update_step(file_idx, total_files, file_name, 
                                  ConversionStep.LOADING_PDF, 50)
                
                # 步骤4: 渲染页面
                images = self.convert_pdf_with_progress(
                    pdf_path, dpi, tracker, file_idx, total_files, file_name
                )
                
                try:
                    os.remove(pdf_path)
                except:
                    pass
            else:
                stdout, stderr = process.communicate()
                raise ValueError(f"文件转换失败: {stderr.decode() if stderr else '未知错误'}")
        else:
            raise ValueError(f"不支持的文件格式: {os.path.splitext(file_path)[1]}")
        
        if images:
            # 步骤5: 合并图像
            tracker.update_step(file_idx, total_files, file_name, 
                              ConversionStep.MERGING_IMAGES, 0)
            
            output_path = os.path.join(output_dir, f"{base_name}.{output_format.lower()}")
            result = self.merge_images_with_progress(
                images, output_path, output_format, quality, 
                tracker, file_idx, total_files, file_name
            )
            
            # 步骤6: 保存输出
            tracker.update_step(file_idx, total_files, file_name, 
                              ConversionStep.SAVING_OUTPUT, 100)
            
            return result
        
        return None
    
    def convert_pdf_with_progress(self, pdf_path, dpi, tracker, 
                                 file_idx, total_files, file_name):
        """带进度跟踪的PDF转换 - 优化版本"""
        try:
            # 性能优化：一次性转换所有页面，比逐页快很多
            tracker.update_step(file_idx, total_files, file_name, 
                              ConversionStep.RENDERING_PAGES, 10)
            
            # 使用 thread_count 参数加速（如果系统支持）
            images = pdf2image.convert_from_path(
                pdf_path, 
                poppler_path=POPPLER_PATH, 
                dpi=dpi,
                thread_count=4  # 使用多线程
            )
            
            # 更新完成进度
            tracker.update_step(file_idx, total_files, file_name, 
                              ConversionStep.RENDERING_PAGES, 100,
                              len(images), len(images))
            
            return images
            
        except Exception as e:
            # 如果批量失败，回退到逐页（兼容性）
            print(f"批量渲染失败，回退到逐页模式: {e}")
            return self.convert_pdf_with_progress_fallback(
                pdf_path, dpi, tracker, file_idx, total_files, file_name
            )
    
    def convert_pdf_with_progress_fallback(self, pdf_path, dpi, tracker, 
                                          file_idx, total_files, file_name):
        """逐页转换PDF - 兼容模式"""
        info = pdfinfo_from_path(pdf_path, poppler_path=POPPLER_PATH)
        total_pages = info['Pages']
        
        images = []
        for page_num in range(1, total_pages + 1):
            page_images = pdf2image.convert_from_path(
                pdf_path, 
                poppler_path=POPPLER_PATH, 
                dpi=dpi,
                first_page=page_num,
                last_page=page_num
            )
            images.extend(page_images)
            
            progress = (page_num / total_pages) * 100
            tracker.update_step(file_idx, total_files, file_name, 
                              ConversionStep.RENDERING_PAGES, progress,
                              page_num, total_pages)
        
        return images
    
    def merge_images_with_progress(self, images, output_path, output_format, 
                                  quality, tracker, file_idx, total_files, file_name):
        """带进度跟踪的图像合并"""
        if not images:
            return None
        
        # 计算合并后的尺寸
        widths, heights = zip(*(i.size for i in images))
        total_height = sum(heights)
        max_width = max(widths)
        
        tracker.update_step(file_idx, total_files, file_name, 
                          ConversionStep.MERGING_IMAGES, 20)
        
        # 创建合并后的图像
        merged_image = Image.new('RGB', (max_width, total_height), 'white')
        y_offset = 0
        
        # 粘贴所有图像
        for i, img in enumerate(images):
            x_offset = (max_width - img.width) // 2
            merged_image.paste(img, (x_offset, y_offset))
            y_offset += img.height
            
            # 更新进度
            progress = 20 + (i + 1) / len(images) * 60  # 20-80%
            tracker.update_step(file_idx, total_files, file_name, 
                              ConversionStep.MERGING_IMAGES, progress)
        
        # 保存图像
        tracker.update_step(file_idx, total_files, file_name, 
                          ConversionStep.MERGING_IMAGES, 90)
        
        # 根据图像大小动态调整策略
        total_pixels = max_width * total_height
        is_huge_image = total_pixels > 50_000_000  # 5000万像素
        
        try:
            if output_format == "JPG":
                merged_image = merged_image.convert("RGB")
                
                # 性能优化：对于超大图像，自动降低质量
                if is_huge_image and quality > 75:
                    quality = 75
                    print(f"提示：检测到超大图像，自动降低JPG质量至{quality}以提升性能")
                
                # 关键优化：去掉 optimize=True，或仅对小图像使用
                if total_pixels < 10_000_000:  # 小于1000万像素才优化
                    merged_image.save(output_path, format="JPEG", 
                                    quality=quality, optimize=True)
                else:
                    # 大图像不使用optimize，速度提升10-100倍！
                    merged_image.save(output_path, format="JPEG", 
                                    quality=quality, optimize=False)
            else:  # PNG
                # 性能优化：PNG压缩级别调整
                # compress_level: 0(无压缩,最快) - 9(最大压缩,最慢)
                if is_huge_image:
                    # 超大图像使用低压缩级别
                    merged_image.save(output_path, format="PNG", 
                                    compress_level=1, optimize=False)
                    print("提示：使用快速PNG压缩以提升性能")
                elif total_pixels < 10_000_000:
                    # 小图像可以使用优化
                    merged_image.save(output_path, format="PNG", 
                                    compress_level=6, optimize=True)
                else:
                    # 中等图像平衡质量和速度
                    merged_image.save(output_path, format="PNG", 
                                    compress_level=3, optimize=False)
            
            tracker.update_step(file_idx, total_files, file_name, 
                              ConversionStep.MERGING_IMAGES, 100)
        except Exception as e:
            raise ValueError(f"保存图像失败: {str(e)}")
        
        return output_path
    
    def conversion_complete(self, success_count, failed_files):
        """转换完成后的处理"""
        self.convert_btn.config(state=tk.NORMAL)
        self.reset_progress_display()
        
        if failed_files:
            message = f"转换完成！\n成功: {success_count} 个文件\n失败: {len(failed_files)} 个文件\n\n失败文件:\n" + "\n".join(failed_files[:10])
            if len(failed_files) > 10:
                message += f"\n... 还有 {len(failed_files) - 10} 个文件"
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
        
        if sys.platform == 'darwin':
            pref_window.configure(bg='#f0f0f0')
        
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
        
        ttk.Label(frame, text="Poppler 路径:").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Label(frame, text=POPPLER_PATH or "系统默认").grid(row=3, column=1, sticky=tk.W)
        
        ttk.Button(pref_window, text="关闭", 
                  command=pref_window.destroy).pack(pady=10)
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """使用指南：

1. 点击"添加文件"选择要转换的文件
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
            if sys.platform == 'darwin':
                # macOS 使用 iconbitmap 的方式略有不同
                root.iconbitmap(icon_path)
        except:
            pass  # 忽略图标设置失败
    
    # 居中窗口
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    # 设置最小窗口大小
    root.minsize(600, 400)
    
    root.mainloop()

if __name__ == "__main__":
    main()