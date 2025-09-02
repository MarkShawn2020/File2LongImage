#!/usr/bin/env python3
"""
File2LongImage macOS Application - 并行处理版本
支持多文件并行转换，每个文件独立控制
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
from concurrent.futures import ThreadPoolExecutor, Future
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum
from config import OUTPUT_DIR, POPPLER_PATH, LIBREOFFICE_PATH, INTERMEDIATE_DIR
import uuid
from error_logger import ErrorLogger, ErrorLog

# 增加 PIL 的最大图像像素限制
Image.MAX_IMAGE_PIXELS = 500000000

class FileStatus(Enum):
    """文件状态枚举"""
    PENDING = "等待中"
    PROCESSING = "转换中"
    PAUSED = "已暂停"
    COMPLETED = "已完成"
    FAILED = "失败"
    CANCELLED = "已取消"

class ConversionStep(Enum):
    """转换步骤枚举"""
    DETECTING = "检测文件"
    CONVERTING_TO_PDF = "转换PDF"
    LOADING_PDF = "加载PDF"
    RENDERING_PAGES = "渲染页面"
    MERGING_IMAGES = "合并图片"
    SAVING_OUTPUT = "保存文件"
    COMPLETED = "完成"

@dataclass
class FileTask:
    """文件任务数据类"""
    task_id: str
    file_path: str
    file_name: str
    status: FileStatus = FileStatus.PENDING
    progress: float = 0.0
    current_step: str = ""
    error_message: str = ""
    error_log: Optional[ErrorLog] = None  # 详细错误日志
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    output_path: Optional[str] = None
    future: Optional[Future] = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    pause_event: threading.Event = field(default_factory=threading.Event)
    
    def __post_init__(self):
        self.pause_event.set()  # 默认不暂停

class ParallelFile2LongImageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File2LongImage - 并行转换版")
        self.root.geometry("900x700")
        
        # macOS 特定设置
        if sys.platform == 'darwin':
            self.root.configure(bg='#f0f0f0')
            try:
                style = ttk.Style()
                style.theme_use('aqua')
            except:
                pass
        
        # 核心数据结构
        self.tasks: Dict[str, FileTask] = {}  # task_id -> FileTask
        self.executor = ThreadPoolExecutor(max_workers=3)  # 并发执行器
        self.max_workers = 3  # 最大并发数
        self.update_queue = queue.Queue()  # UI更新队列
        
        self.setup_ui()
        self.setup_menu()
        self.start_ui_updater()
    
    def setup_ui(self):
        """设置用户界面"""
        # 主容器
        main_container = ttk.Frame(self.root, padding="10")
        main_container.pack(fill='both', expand=True)
        
        # 标题
        title_label = ttk.Label(main_container, text="文件转长图 - 并行处理", 
                               font=('Helvetica', 20, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # 顶部控制栏
        control_frame = ttk.Frame(main_container)
        control_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Button(control_frame, text="➕ 添加文件", 
                  command=self.add_files).pack(side='left', padx=2)
        ttk.Button(control_frame, text="▶️ 全部开始", 
                  command=self.start_all).pack(side='left', padx=2)
        ttk.Button(control_frame, text="⏸ 全部暂停", 
                  command=self.pause_all).pack(side='left', padx=2)
        ttk.Button(control_frame, text="✖️ 全部取消", 
                  command=self.cancel_all).pack(side='left', padx=2)
        ttk.Button(control_frame, text="🗑 清空完成", 
                  command=self.clear_completed).pack(side='left', padx=2)
        
        # 并发控制
        ttk.Label(control_frame, text="并发数:").pack(side='left', padx=(20, 5))
        self.workers_var = tk.IntVar(value=3)
        workers_spin = ttk.Spinbox(control_frame, from_=1, to=5, width=5,
                                   textvariable=self.workers_var,
                                   command=self.update_max_workers)
        workers_spin.pack(side='left')
        
        # 文件列表（TreeView）
        list_frame = ttk.LabelFrame(main_container, text="文件队列", padding="10")
        list_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # 创建TreeView
        columns = ('状态', '进度', '步骤', '信息', '用时')
        self.file_tree = ttk.Treeview(list_frame, columns=columns, height=10)
        
        # 配置列
        self.file_tree.heading('#0', text='文件名')
        self.file_tree.heading('状态', text='状态')
        self.file_tree.heading('进度', text='进度')
        self.file_tree.heading('步骤', text='当前步骤')
        self.file_tree.heading('信息', text='信息')  # 动态信息：处理中显示速度，完成后显示大小
        self.file_tree.heading('用时', text='用时')
        
        # 设置列宽
        self.file_tree.column('#0', width=250)
        self.file_tree.column('状态', width=80)
        self.file_tree.column('进度', width=100)
        self.file_tree.column('步骤', width=100)
        self.file_tree.column('信息', width=80)
        self.file_tree.column('用时', width=80)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', 
                                 command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.file_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # 右键菜单
        self.create_context_menu()
        
        # 设置面板
        settings_frame = ttk.LabelFrame(main_container, text="转换设置", padding="10")
        settings_frame.pack(fill='x', pady=(0, 10))
        
        # DPI设置
        dpi_frame = ttk.Frame(settings_frame)
        dpi_frame.pack(fill='x', pady=5)
        ttk.Label(dpi_frame, text="DPI:").pack(side='left', padx=(0, 10))
        self.dpi_var = tk.IntVar(value=200)
        dpi_scale = ttk.Scale(dpi_frame, from_=72, to=600, 
                             variable=self.dpi_var, orient='horizontal')
        dpi_scale.pack(side='left', fill='x', expand=True)
        dpi_label = ttk.Label(dpi_frame, text="200")
        dpi_label.pack(side='left', padx=(10, 0))
        self.dpi_var.trace('w', lambda *args: dpi_label.config(text=str(self.dpi_var.get())))
        
        # 输出格式
        format_frame = ttk.Frame(settings_frame)
        format_frame.pack(fill='x', pady=5)
        ttk.Label(format_frame, text="格式:").pack(side='left', padx=(0, 10))
        self.format_var = tk.StringVar(value="PNG")
        ttk.Radiobutton(format_frame, text="PNG", variable=self.format_var, 
                       value="PNG").pack(side='left', padx=10)
        ttk.Radiobutton(format_frame, text="JPG", variable=self.format_var, 
                       value="JPG").pack(side='left', padx=10)
        
        # JPG质量
        self.quality_frame = ttk.Frame(settings_frame)
        ttk.Label(self.quality_frame, text="JPG质量:").pack(side='left', padx=(0, 10))
        self.quality_var = tk.IntVar(value=85)
        quality_scale = ttk.Scale(self.quality_frame, from_=1, to=100, 
                                 variable=self.quality_var, orient='horizontal')
        quality_scale.pack(side='left', fill='x', expand=True)
        quality_label = ttk.Label(self.quality_frame, text="85")
        quality_label.pack(side='left', padx=(10, 0))
        self.quality_var.trace('w', lambda *args: quality_label.config(text=str(self.quality_var.get())))
        
        self.format_var.trace('w', self.on_format_change)
        
        # 状态栏
        status_frame = ttk.Frame(main_container)
        status_frame.pack(fill='x', side='bottom')
        self.status_label = ttk.Label(status_frame, text="就绪", relief='sunken')
        self.status_label.pack(fill='x')
    
    def create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="▶️ 开始", command=self.start_selected)
        self.context_menu.add_command(label="⏸ 暂停", command=self.pause_selected)
        self.context_menu.add_command(label="✖️ 取消", command=self.cancel_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📄 打开文件", command=self.open_output)
        self.context_menu.add_command(label="📁 在Finder中显示", command=self.reveal_in_finder)
        self.context_menu.add_command(label="📂 打开输出文件夹", command=self.open_output_folder)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑 删除任务", command=self.remove_selected)
        
        self.file_tree.bind("<Button-3>", self.show_context_menu)  # macOS
        self.file_tree.bind("<Button-2>", self.show_context_menu)  # Windows/Linux
        self.file_tree.bind("<Double-Button-1>", self.on_double_click)  # 双击事件
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        # 选中点击的项
        item = self.file_tree.identify_row(event.y)
        if item:
            self.file_tree.selection_set(item)
            
            # 动态更新菜单项
            task = self.tasks.get(item)
            if task:
                # 清除旧菜单
                self.context_menu.delete(0, tk.END)
                
                # 根据状态添加菜单项
                if task.status == FileStatus.PENDING:
                    self.context_menu.add_command(label="▶️ 开始", command=self.start_selected)
                elif task.status == FileStatus.PROCESSING:
                    self.context_menu.add_command(label="⏸ 暂停", command=self.pause_selected)
                    self.context_menu.add_command(label="✖️ 取消", command=self.cancel_selected)
                elif task.status == FileStatus.PAUSED:
                    self.context_menu.add_command(label="▶️ 继续", command=self.start_selected)
                    self.context_menu.add_command(label="✖️ 取消", command=self.cancel_selected)
                elif task.status == FileStatus.FAILED:
                    self.context_menu.add_command(label="🔍 查看错误详情", command=self.show_error_detail)
                    self.context_menu.add_command(label="🔄 重试", command=self.retry_selected)
                
                self.context_menu.add_separator()
                
                # 文件操作
                if task.status == FileStatus.COMPLETED and task.output_path:
                    self.context_menu.add_command(label="📄 打开文件", command=self.open_output)
                    self.context_menu.add_command(label="📁 在Finder中显示", command=self.reveal_in_finder)
                
                self.context_menu.add_command(label="📂 打开输出文件夹", command=self.open_output_folder)
                
                # 任务管理
                self.context_menu.add_separator()
                if task.status != FileStatus.PROCESSING:
                    self.context_menu.add_command(label="🗑 删除任务", command=self.remove_selected)
            
            self.context_menu.post(event.x_root, event.y_root)
    
    def setup_menu(self):
        """设置菜单栏"""
        if sys.platform == 'darwin':
            menubar = tk.Menu(self.root)
            self.root.config(menu=menubar)
            
            # 应用菜单
            app_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="File2LongImage", menu=app_menu)
            app_menu.add_command(label="关于", command=self.show_about)
            app_menu.add_separator()
            app_menu.add_command(label="退出", command=self.quit_app, accelerator="Cmd+Q")
            
            # 文件菜单
            file_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="文件", menu=file_menu)
            file_menu.add_command(label="添加文件...", command=self.add_files, accelerator="Cmd+O")
            
            # 绑定快捷键
            self.root.bind('<Command-o>', lambda e: self.add_files())
            self.root.bind('<Command-q>', lambda e: self.quit_app())
    
    def add_files(self):
        """添加文件到队列"""
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
            for file_path in files:
                # 检查是否已存在
                if not any(task.file_path == file_path for task in self.tasks.values()):
                    task_id = str(uuid.uuid4())[:8]
                    task = FileTask(
                        task_id=task_id,
                        file_path=file_path,
                        file_name=os.path.basename(file_path)
                    )
                    self.tasks[task_id] = task
                    
                    # 添加到TreeView
                    self.file_tree.insert('', 'end', iid=task_id, 
                                         text=task.file_name,
                                         values=(task.status.value, '0%', '', '', ''))
            
            self.update_status(f"已添加 {len(files)} 个文件")
    
    def start_all(self):
        """开始所有待处理的文件"""
        for task_id, task in self.tasks.items():
            if task.status == FileStatus.PENDING:
                self.start_task(task_id)
    
    def start_selected(self):
        """开始选中的文件"""
        selected = self.file_tree.selection()
        for task_id in selected:
            if task_id in self.tasks:
                self.start_task(task_id)
    
    def start_task(self, task_id: str):
        """开始单个任务"""
        task = self.tasks.get(task_id)
        if not task or task.status not in [FileStatus.PENDING, FileStatus.PAUSED]:
            return
        
        # 提交到线程池
        task.status = FileStatus.PROCESSING
        task.start_time = time.time()
        task.pause_event.set()  # 确保不暂停
        task.cancel_event.clear()  # 清除取消标志
        
        # 提交转换任务
        future = self.executor.submit(self.convert_file_worker, task)
        task.future = future
        
        # 更新UI
        self.update_task_display(task_id)
    
    def convert_file_worker(self, task: FileTask):
        """工作线程：转换文件"""
        try:
            # 获取参数
            dpi = self.dpi_var.get()
            output_format = self.format_var.get()
            quality = self.quality_var.get() if output_format == "JPG" else 85
            
            # 检查取消
            if task.cancel_event.is_set():
                task.status = FileStatus.CANCELLED
                return
            
            # 步骤1：检测文件
            self.update_task_progress(task, ConversionStep.DETECTING, 10)
            
            # 检查文件是否存在
            if not os.path.exists(task.file_path):
                raise FileNotFoundError(f"文件不存在: {task.file_path}")
            
            # 检查暂停
            task.pause_event.wait()
            
            images = []
            base_name = os.path.splitext(task.file_name)[0]
            
            # PDF直接处理
            if task.file_path.lower().endswith('.pdf'):
                self.update_task_progress(task, ConversionStep.RENDERING_PAGES, 20)
                images = self.convert_pdf_parallel(task, dpi)
                if not images:
                    raise ValueError(f"PDF转换失败: 无法从PDF提取图像")
                
            # Office文件
            elif task.file_path.lower().endswith((".doc", ".docx", ".ppt", ".pptx", 
                                                  ".csv", ".xls", ".xlsx", ".odt", 
                                                  ".rtf", ".txt")):
                if LIBREOFFICE_PATH is None:
                    raise ValueError("LibreOffice 未安装，无法转换Office文件")
                
                # 转换为PDF
                self.update_task_progress(task, ConversionStep.CONVERTING_TO_PDF, 20)
                pdf_path = self.convert_to_pdf(task)
                
                if not pdf_path:
                    raise ValueError(f"Office转换PDF失败: LibreOffice无法处理此文件")
                
                if not os.path.exists(pdf_path):
                    raise FileNotFoundError(f"PDF生成失败: 临时PDF文件不存在 ({pdf_path})")
                
                # PDF文件大小检查
                pdf_size = os.path.getsize(pdf_path)
                if pdf_size == 0:
                    raise ValueError(f"PDF生成失败: 生成的PDF文件为空")
                
                print(f"PDF生成成功: {pdf_path} ({pdf_size} bytes)")
                
                self.update_task_progress(task, ConversionStep.RENDERING_PAGES, 50)
                images = self.convert_pdf_parallel(task, dpi, pdf_path)
                
                if not images:
                    # 尝试保留PDF以便调试
                    debug_pdf = os.path.join(OUTPUT_DIR, f"{base_name}_debug.pdf")
                    try:
                        import shutil
                        shutil.copy(pdf_path, debug_pdf)
                        print(f"调试: PDF已保存到 {debug_pdf}")
                    except:
                        pass
                    raise ValueError(f"PDF渲染失败: 无法从临时PDF提取图像\nPDF路径: {pdf_path}\nPDF大小: {pdf_size} bytes")
                
                # 清理临时PDF
                try:
                    os.remove(pdf_path)
                except Exception as e:
                    print(f"警告: 无法删除临时PDF: {e}")
            else:
                raise ValueError(f"不支持的文件格式: {os.path.splitext(task.file_path)[1]}")
            
            # 检查取消
            if task.cancel_event.is_set():
                task.status = FileStatus.CANCELLED
                return
            
            # 合并图像
            if images:
                print(f"开始合并 {len(images)} 张图像")
                self.update_task_progress(task, ConversionStep.MERGING_IMAGES, 70)
                output_path = os.path.join(OUTPUT_DIR, f"{base_name}.{output_format.lower()}")
                task.output_path = self.merge_images_fast(images, output_path, 
                                                          output_format, quality, task)
                
                if not task.output_path:
                    raise ValueError("图像合并失败")
                
                # 完成
                task.status = FileStatus.COMPLETED
                task.end_time = time.time()
                task.progress = 100
                self.update_task_progress(task, ConversionStep.COMPLETED, 100)
                print(f"转换成功: {task.output_path}")
            else:
                raise ValueError("无法生成图像: images列表为空")
                
        except Exception as e:
            task.status = FileStatus.FAILED
            task.error_message = str(e)
            task.end_time = time.time()
            
            # 创建详细错误日志
            elapsed = task.end_time - task.start_time if task.start_time else None
            task.error_log = ErrorLogger.create_error_log(
                file_path=task.file_path,
                file_name=task.file_name,
                error=e,
                error_step=task.current_step or "Unknown",
                conversion_params={
                    "dpi": self.dpi_var.get(),
                    "format": self.format_var.get(),
                    "quality": self.quality_var.get() if self.format_var.get() == "JPG" else None
                },
                elapsed_time=elapsed
            )
            
            # 保存日志到文件
            try:
                log_file = ErrorLogger.save_to_file(task.error_log)
                print(f"错误日志已保存: {log_file}")
            except:
                pass
        
        finally:
            # 更新最终状态
            self.update_queue.put(('update', task.task_id))
    
    def convert_pdf_parallel(self, task: FileTask, dpi: int, pdf_path: str = None) -> List:
        """并行转换PDF"""
        if pdf_path is None:
            pdf_path = task.file_path
        
        print(f"开始转换PDF: {pdf_path}")
        print(f"DPI: {dpi}, Poppler路径: {POPPLER_PATH}")
        
        try:
            # 首先检查PDF是否有效
            from pdf2image import pdfinfo_from_path
            try:
                info = pdfinfo_from_path(pdf_path, poppler_path=POPPLER_PATH)
                print(f"PDF信息: 页数={info.get('Pages', 0)}, 加密={info.get('Encrypted', False)}")
                
                if info.get('Encrypted', False):
                    raise ValueError("PDF文件已加密，无法处理")
                
                if info.get('Pages', 0) == 0:
                    raise ValueError("PDF文件没有页面")
                    
            except Exception as e:
                print(f"PDF信息获取失败: {e}")
                # 继续尝试转换
            
            # 批量转换
            images = pdf2image.convert_from_path(
                pdf_path,
                poppler_path=POPPLER_PATH,
                dpi=dpi,
                thread_count=2,  # 子线程内使用2个线程
                fmt='png',  # 明确指定输出格式
                use_pdftocairo=False  # 使用pdftoppm而非pdftocairo
            )
            
            print(f"PDF转换成功: 生成了 {len(images)} 张图像")
            return images
            
        except Exception as e:
            print(f"PDF转换失败: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def convert_to_pdf(self, task: FileTask) -> Optional[str]:
        """转换Office文件为PDF"""
        # 确保中间目录存在
        os.makedirs(INTERMEDIATE_DIR, exist_ok=True)
        
        base_name = os.path.splitext(task.file_name)[0]
        # 处理文件名中的特殊字符 - 更全面的替换
        import re
        # 替换所有非字母数字和中文的字符为下划线
        safe_base_name = re.sub(r'[^a-zA-Z0-9一-鿿._-]', '_', base_name)
        # 移除多个连续的下划线
        safe_base_name = re.sub(r'_+', '_', safe_base_name)
        # 移除开头和结尾的下划线
        safe_base_name = safe_base_name.strip('_')
        pdf_path = os.path.join(INTERMEDIATE_DIR, f"{safe_base_name}.pdf")
        
        # 如果目标PDF已存在，先删除
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except:
                pass
        
        # 构建命令 - 使用列表形式避免shell解析问题
        conversion_cmd = [
            LIBREOFFICE_PATH,
            '--headless',
            '--convert-to', 'pdf',
            task.file_path,
            '--outdir', INTERMEDIATE_DIR
        ]
        
        print(f"执行LibreOffice转换: {' '.join(conversion_cmd)}")
        # 不使用shell=True，避免特殊字符问题
        result = subprocess.run(conversion_cmd, capture_output=True, text=True)
        
        # 输出调试信息
        if result.stdout:
            print(f"LibreOffice stdout: {result.stdout}")
        if result.stderr:
            print(f"LibreOffice stderr: {result.stderr}")
        
        # LibreOffice可能使用原始文件名生成PDF
        original_pdf_path = os.path.join(INTERMEDIATE_DIR, f"{os.path.splitext(task.file_name)[0]}.pdf")
        
        # 检查两个可能的路径
        if os.path.exists(pdf_path):
            print(f"PDF生成成功(安全名): {pdf_path}")
            return pdf_path
        elif os.path.exists(original_pdf_path):
            print(f"PDF生成成功(原始名): {original_pdf_path}")
            # 重命名为安全名
            try:
                os.rename(original_pdf_path, pdf_path)
                return pdf_path
            except:
                return original_pdf_path
        else:
            print(f"PDF生成失败: 找不到输出文件")
            print(f"检查路径: {pdf_path}")
            print(f"检查路径: {original_pdf_path}")
            # 列出中间目录内容，查找任何PDF文件
            try:
                files = os.listdir(INTERMEDIATE_DIR)
                print(f"{INTERMEDIATE_DIR} 目录内容: {files}")
                # 查找任何PDF文件
                pdf_files = [f for f in files if f.lower().endswith('.pdf')]
                if pdf_files:
                    print(f"找到PDF文件: {pdf_files}")
                    # 使用找到的第一个PDF
                    found_pdf = os.path.join(INTERMEDIATE_DIR, pdf_files[0])
                    print(f"使用找到的PDF: {found_pdf}")
                    return found_pdf
            except Exception as e:
                print(f"列出目录失败: {e}")
            return None
    
    def merge_images_fast(self, images, output_path, output_format, quality, task):
        """快速合并图像"""
        if not images:
            return None
        
        # 计算尺寸
        widths, heights = zip(*(i.size for i in images))
        total_height = sum(heights)
        max_width = max(widths)
        
        # 创建合并图像
        merged_image = Image.new('RGB', (max_width, total_height), 'white')
        y_offset = 0
        
        for i, img in enumerate(images):
            # 检查取消
            if task.cancel_event.is_set():
                return None
            
            x_offset = (max_width - img.width) // 2
            merged_image.paste(img, (x_offset, y_offset))
            y_offset += img.height
            
            # 更新进度
            progress = 70 + (i + 1) / len(images) * 20
            self.update_task_progress(task, ConversionStep.MERGING_IMAGES, progress)
        
        # 保存（使用优化参数）
        self.update_task_progress(task, ConversionStep.SAVING_OUTPUT, 95)
        
        total_pixels = max_width * total_height
        if output_format == "JPG":
            merged_image = merged_image.convert("RGB")
            if total_pixels > 10_000_000:
                merged_image.save(output_path, format="JPEG", quality=quality, optimize=False)
            else:
                merged_image.save(output_path, format="JPEG", quality=quality, optimize=True)
        else:  # PNG
            if total_pixels > 50_000_000:
                merged_image.save(output_path, format="PNG", compress_level=1, optimize=False)
            else:
                merged_image.save(output_path, format="PNG", compress_level=6, optimize=True)
        
        return output_path
    
    def update_task_progress(self, task: FileTask, step: ConversionStep, progress: float):
        """更新任务进度"""
        task.current_step = step.value
        task.progress = progress
        self.update_queue.put(('progress', task.task_id))
    
    def update_task_display(self, task_id: str):
        """更新任务显示"""
        task = self.tasks.get(task_id)
        if not task:
            return
        
        # 计算用时
        elapsed = "-"
        elapsed_sec = 0
        if task.start_time:
            if task.end_time:
                elapsed_sec = task.end_time - task.start_time
            else:
                elapsed_sec = time.time() - task.start_time
            
            # 格式化时间显示
            if elapsed_sec < 60:
                elapsed = f"{elapsed_sec:.1f}秒"
            elif elapsed_sec < 3600:
                minutes = int(elapsed_sec // 60)
                seconds = int(elapsed_sec % 60)
                elapsed = f"{minutes}分{seconds}秒"
            else:
                hours = int(elapsed_sec // 3600)
                minutes = int((elapsed_sec % 3600) // 60)
                elapsed = f"{hours}时{minutes}分"
        
        # 动态信息栏：根据状态显示不同内容
        info_text = "-"
        if task.status == FileStatus.PROCESSING:
            # 处理中：显示速度
            if task.progress > 0 and elapsed_sec > 0:
                info_text = f"{task.progress/elapsed_sec:.1f}%/秒"
        elif task.status == FileStatus.COMPLETED:
            # 完成后：显示输出文件大小
            if task.output_path and os.path.exists(task.output_path):
                file_size = os.path.getsize(task.output_path)
                if file_size < 1024:
                    info_text = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    info_text = f"{file_size/1024:.1f} KB"
                elif file_size < 1024 * 1024 * 1024:
                    info_text = f"{file_size/(1024*1024):.1f} MB"
                else:
                    info_text = f"{file_size/(1024*1024*1024):.2f} GB"
        elif task.status == FileStatus.FAILED:
            # 失败：显示简短错误或提示
            if task.error_message:
                # 截取错误信息的前20个字符
                short_error = task.error_message[:20]
                if len(task.error_message) > 20:
                    short_error += "..."
                info_text = short_error
            else:
                info_text = "双击查看"
        elif task.status == FileStatus.PAUSED:
            # 暂停：显示暂停提示
            info_text = "已暂停"
        elif task.status == FileStatus.CANCELLED:
            # 取消：显示取消提示
            info_text = "已取消"
        
        # 进度条文本
        progress_text = f"{task.progress:.0f}%"
        if task.progress > 0 and task.progress < 100:
            bar_length = 10
            filled = int(bar_length * task.progress / 100)
            progress_text = '█' * filled + '░' * (bar_length - filled) + f" {task.progress:.0f}%"
        
        # 更新TreeView
        self.file_tree.item(task_id, values=(
            task.status.value,
            progress_text,
            task.current_step,
            info_text,  # 动态信息
            elapsed
        ))
        
        # 根据状态设置颜色
        if task.status == FileStatus.COMPLETED:
            self.file_tree.item(task_id, tags=('completed',))
        elif task.status == FileStatus.FAILED:
            self.file_tree.item(task_id, tags=('failed',))
        elif task.status == FileStatus.PROCESSING:
            self.file_tree.item(task_id, tags=('processing',))
        
        # 配置标签颜色
        self.file_tree.tag_configure('completed', foreground='green')
        self.file_tree.tag_configure('failed', foreground='red')
        self.file_tree.tag_configure('processing', foreground='blue')
    
    def pause_selected(self):
        """暂停选中的任务"""
        selected = self.file_tree.selection()
        for task_id in selected:
            task = self.tasks.get(task_id)
            if task and task.status == FileStatus.PROCESSING:
                task.pause_event.clear()
                task.status = FileStatus.PAUSED
                self.update_task_display(task_id)
    
    def pause_all(self):
        """暂停所有任务"""
        for task_id, task in self.tasks.items():
            if task.status == FileStatus.PROCESSING:
                task.pause_event.clear()
                task.status = FileStatus.PAUSED
                self.update_task_display(task_id)
    
    def cancel_selected(self):
        """取消选中的任务"""
        selected = self.file_tree.selection()
        for task_id in selected:
            task = self.tasks.get(task_id)
            if task and task.status in [FileStatus.PROCESSING, FileStatus.PAUSED]:
                task.cancel_event.set()
                task.pause_event.set()  # 解除暂停以便退出
                if task.future:
                    task.future.cancel()
                task.status = FileStatus.CANCELLED
                self.update_task_display(task_id)
    
    def cancel_all(self):
        """取消所有任务"""
        for task_id, task in self.tasks.items():
            if task.status in [FileStatus.PROCESSING, FileStatus.PAUSED]:
                task.cancel_event.set()
                task.pause_event.set()
                if task.future:
                    task.future.cancel()
                task.status = FileStatus.CANCELLED
                self.update_task_display(task_id)
    
    def remove_selected(self):
        """删除选中的任务"""
        selected = self.file_tree.selection()
        for task_id in selected:
            task = self.tasks.get(task_id)
            if task and task.status not in [FileStatus.PROCESSING]:
                self.file_tree.delete(task_id)
                del self.tasks[task_id]
    
    def clear_completed(self):
        """清空已完成的任务"""
        to_remove = []
        for task_id, task in self.tasks.items():
            if task.status in [FileStatus.COMPLETED, FileStatus.FAILED, FileStatus.CANCELLED]:
                to_remove.append(task_id)
        
        for task_id in to_remove:
            self.file_tree.delete(task_id)
            del self.tasks[task_id]
    
    def open_output(self):
        """打开输出文件"""
        selected = self.file_tree.selection()
        if selected:
            task = self.tasks.get(selected[0])
            if task and task.output_path and os.path.exists(task.output_path):
                if sys.platform == 'darwin':
                    subprocess.run(['open', task.output_path])
                elif sys.platform == 'win32':
                    os.startfile(task.output_path)
                else:  # Linux
                    subprocess.run(['xdg-open', task.output_path])
    
    def reveal_in_finder(self):
        """在Finder中显示文件"""
        selected = self.file_tree.selection()
        if selected:
            task = self.tasks.get(selected[0])
            if task and task.output_path and os.path.exists(task.output_path):
                if sys.platform == 'darwin':
                    # macOS: 使用 open -R 在Finder中显示并选中文件
                    subprocess.run(['open', '-R', task.output_path])
                elif sys.platform == 'win32':
                    # Windows: 使用 explorer /select
                    subprocess.run(['explorer', '/select,', task.output_path])
                else:  # Linux
                    # Linux: 打开包含文件的目录
                    parent_dir = os.path.dirname(task.output_path)
                    subprocess.run(['xdg-open', parent_dir])
            else:
                # 如果输出文件不存在，显示原始文件
                if task and task.file_path and os.path.exists(task.file_path):
                    if sys.platform == 'darwin':
                        subprocess.run(['open', '-R', task.file_path])
                    elif sys.platform == 'win32':
                        subprocess.run(['explorer', '/select,', task.file_path])
                    else:
                        parent_dir = os.path.dirname(task.file_path)
                        subprocess.run(['xdg-open', parent_dir])
    
    def open_output_folder(self):
        """打开输出文件夹"""
        if os.path.exists(OUTPUT_DIR):
            if sys.platform == 'darwin':
                subprocess.run(['open', OUTPUT_DIR])
            elif sys.platform == 'win32':
                os.startfile(OUTPUT_DIR)
            else:  # Linux
                subprocess.run(['xdg-open', OUTPUT_DIR])
    
    def update_max_workers(self):
        """更新最大并发数"""
        new_max = self.workers_var.get()
        if new_max != self.max_workers:
            # 关闭旧的执行器
            self.executor.shutdown(wait=False)
            # 创建新的执行器
            self.executor = ThreadPoolExecutor(max_workers=new_max)
            self.max_workers = new_max
            self.update_status(f"并发数已更新为 {new_max}")
    
    def on_format_change(self, *args):
        """格式选择变化时的处理"""
        if self.format_var.get() == "JPG":
            self.quality_frame.pack(fill='x', pady=5)
        else:
            self.quality_frame.pack_forget()
    
    def start_ui_updater(self):
        """启动UI更新器"""
        def updater():
            try:
                while True:
                    action, task_id = self.update_queue.get_nowait()
                    self.update_task_display(task_id)
            except queue.Empty:
                pass
            finally:
                self.root.after(100, updater)
        
        updater()
    
    def update_status(self, message):
        """更新状态栏"""
        self.status_label.config(text=message)
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """File2LongImage v3.0 并行版
        
多文件并行转换
独立进度控制
高性能处理

© 2024 File2LongImage"""
        messagebox.showinfo("关于", about_text)
    
    def on_double_click(self, event):
        """处理双击事件"""
        item = self.file_tree.identify_row(event.y)
        if item:
            task = self.tasks.get(item)
            if task:
                if task.status == FileStatus.FAILED:
                    # 失败的任务显示错误详情
                    self.show_error_detail_for_task(task)
                elif task.status == FileStatus.COMPLETED and task.output_path:
                    # 完成的任务打开文件
                    self.open_output()
                elif task.status == FileStatus.PENDING:
                    # 待处理的任务开始转换
                    self.start_task(item)
    
    def show_error_detail(self):
        """显示选中任务的错误详情"""
        selected = self.file_tree.selection()
        if selected:
            task = self.tasks.get(selected[0])
            if task and task.status == FileStatus.FAILED:
                self.show_error_detail_for_task(task)
    
    def show_error_detail_for_task(self, task: 'FileTask'):
        """显示任务的错误详情窗口"""
        # 创建错误详情窗口
        error_window = tk.Toplevel(self.root)
        error_window.title("错误详情")
        error_window.geometry("600x400")
        
        # 主框架
        main_frame = ttk.Frame(error_window, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="❌ 转换失败", 
                               font=('Helvetica', 16, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # 文件信息
        info_frame = ttk.LabelFrame(main_frame, text="文件信息", padding="10")
        info_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(info_frame, text=f"文件名: {task.file_name}").pack(anchor='w')
        ttk.Label(info_frame, text=f"路径: {task.file_path}").pack(anchor='w')
        ttk.Label(info_frame, text=f"失败步骤: {task.current_step}").pack(anchor='w')
        
        if task.start_time and task.end_time:
            duration = task.end_time - task.start_time
            ttk.Label(info_frame, text=f"耗时: {duration:.1f} 秒").pack(anchor='w')
        
        # 错误信息
        error_frame = ttk.LabelFrame(main_frame, text="错误信息", padding="10")
        error_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # 错误文本框（可滚动、可复制）
        text_frame = ttk.Frame(error_frame)
        text_frame.pack(fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side='right', fill='y')
        
        error_text = tk.Text(text_frame, wrap='word', height=15, 
                           yscrollcommand=scrollbar.set, font=('Courier', 10))
        error_text.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=error_text.yview)
        
        # 插入详细错误日志
        if task.error_log:
            # 使用详细日志
            log_content = ErrorLogger.format_log_for_display(task.error_log)
            error_text.insert('1.0', log_content)
        else:
            # 备用：仅显示简单错误信息
            error_msg = task.error_message or "未知错误"
            error_text.insert('1.0', error_msg)
            
            # 分析错误并提供建议
            suggestions = self.analyze_error(error_msg)
            if suggestions:
                error_text.insert('end', '\n\n💡 可能的解决方案:\n')
                for suggestion in suggestions:
                    error_text.insert('end', f'• {suggestion}\n')
        
        # 设置文本框样式
        error_text.tag_configure('header', font=('Helvetica', 11, 'bold'))
        error_text.tag_configure('error', foreground='red')
        error_text.config(state='disabled')  # 设为只读
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x')
        
        # 复制错误信息按钮
        def copy_error():
            self.root.clipboard_clear()
            if task.error_log:
                # 复制Markdown格式（方便GitHub Issue）
                clipboard_content = ErrorLogger.format_log_for_clipboard(task.error_log)
            else:
                clipboard_content = f"文件: {task.file_name}\n错误: {task.error_message}"
            self.root.clipboard_append(clipboard_content)
            messagebox.showinfo("复制成功", "详细日志已复制到剪贴板\n可直接粘贴到GitHub Issue或邮件中")
        
        ttk.Button(button_frame, text="📋 复制详细日志", 
                  command=copy_error).pack(side='left', padx=5)
        
        # 打开日志文件按钮
        def open_log_file():
            if task.error_log:
                log_file = f"logs/error_{task.error_log.log_id}.log"
                if os.path.exists(log_file):
                    if sys.platform == 'darwin':
                        subprocess.run(['open', log_file])
                    elif sys.platform == 'win32':
                        os.startfile(log_file)
                    else:
                        subprocess.run(['xdg-open', log_file])
        
        if task.error_log:
            ttk.Button(button_frame, text="📄 打开日志文件", 
                      command=open_log_file).pack(side='left', padx=5)
        
        # 重试按钮
        def retry():
            error_window.destroy()
            # 重置任务状态
            task.status = FileStatus.PENDING
            task.progress = 0
            task.error_message = ""
            task.current_step = ""
            task.start_time = None
            task.end_time = None
            self.update_task_display(task.task_id)
            # 重新开始
            self.start_task(task.task_id)
        
        ttk.Button(button_frame, text="🔄 重试转换", 
                  command=retry).pack(side='left', padx=5)
        
        # 关闭按钮
        ttk.Button(button_frame, text="关闭", 
                  command=error_window.destroy).pack(side='right', padx=5)
        
        # 使窗口居中
        error_window.transient(self.root)
        error_window.grab_set()
    
    def analyze_error(self, error_msg: str) -> list:
        """分析错误信息并提供解决建议"""
        suggestions = []
        error_lower = error_msg.lower()
        
        if "libreoffice" in error_lower:
            suggestions.append("安装 LibreOffice: brew install --cask libreoffice")
            suggestions.append("确保 LibreOffice 路径正确配置")
        elif "poppler" in error_lower:
            suggestions.append("安装 Poppler: brew install poppler")
            suggestions.append("检查 Poppler 路径配置")
        elif "permission" in error_lower or "权限" in error_msg:
            suggestions.append("检查文件读取权限")
            suggestions.append("确保输出目录有写入权限")
        elif "memory" in error_lower or "内存" in error_msg:
            suggestions.append("降低 DPI 设置")
            suggestions.append("关闭其他应用释放内存")
            suggestions.append("分批处理大文件")
        elif "timeout" in error_lower or "超时" in error_msg:
            suggestions.append("增加超时时间设置")
            suggestions.append("检查网络连接（如果涉及网络资源）")
        elif "corrupt" in error_lower or "损坏" in error_msg:
            suggestions.append("文件可能已损坏，尝试修复或使用其他工具打开")
            suggestions.append("检查文件是否完整下载")
        elif "not found" in error_lower or "找不到" in error_msg:
            suggestions.append("确认文件路径正确")
            suggestions.append("检查文件是否被移动或删除")
        else:
            suggestions.append("检查文件格式是否支持")
            suggestions.append("尝试降低转换质量或DPI")
            suggestions.append("查看系统日志获取更多信息")
        
        return suggestions
    
    def retry_selected(self):
        """重试选中的失败任务"""
        selected = self.file_tree.selection()
        for task_id in selected:
            task = self.tasks.get(task_id)
            if task and task.status == FileStatus.FAILED:
                # 重置任务状态
                task.status = FileStatus.PENDING
                task.progress = 0
                task.error_message = ""
                task.current_step = ""
                task.start_time = None
                task.end_time = None
                self.update_task_display(task_id)
                # 重新开始
                self.start_task(task_id)
    
    def quit_app(self):
        """退出应用"""
        # 取消所有任务
        self.cancel_all()
        # 关闭执行器
        self.executor.shutdown(wait=False)
        # 退出
        self.root.quit()

def main():
    """主函数"""
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(INTERMEDIATE_DIR, exist_ok=True)
    
    # 启动应用
    root = tk.Tk()
    app = ParallelFile2LongImageApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()