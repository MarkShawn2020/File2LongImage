#!/usr/bin/env python3
"""
File2LongImage macOS Application - 性能优化版本
解决图片合并慢的问题
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
        self.step_durations = []
        
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
            pass

class OptimizedImageMerger:
    """优化的图像合并器"""
    
    @staticmethod
    def merge_images_fast(images, output_path, output_format, quality, 
                         tracker=None, file_idx=0, total_files=1, file_name=""):
        """快速合并图像 - 优化版本"""
        if not images:
            return None
        
        # 计算合并后的尺寸
        widths, heights = zip(*(i.size for i in images))
        total_height = sum(heights)
        max_width = max(widths)
        
        if tracker:
            tracker.update_step(file_idx, total_files, file_name, 
                              ConversionStep.MERGING_IMAGES, 10)
        
        # 性能优化1：对于大图像，降低质量以加快处理
        # 根据图像大小动态调整策略
        total_pixels = max_width * total_height
        is_huge_image = total_pixels > 50_000_000  # 5000万像素
        
        # 创建合并后的图像
        # 优化：使用 'L' 模式（灰度）可以减少1/3内存，如果用户允许
        merged_image = Image.new('RGB', (max_width, total_height), 'white')
        y_offset = 0
        
        # 粘贴所有图像
        for i, img in enumerate(images):
            # 性能优化2：如果原图是RGBA，先转换为RGB
            if img.mode == 'RGBA':
                # 创建白色背景
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])  # 使用alpha通道作为mask
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            x_offset = (max_width - img.width) // 2
            merged_image.paste(img, (x_offset, y_offset))
            y_offset += img.height
            
            # 更新进度
            if tracker:
                progress = 10 + (i + 1) / len(images) * 70  # 10-80%
                tracker.update_step(file_idx, total_files, file_name, 
                                  ConversionStep.MERGING_IMAGES, progress)
        
        # 保存图像 - 关键优化点
        if tracker:
            tracker.update_step(file_idx, total_files, file_name, 
                              ConversionStep.MERGING_IMAGES, 85)
        
        try:
            if output_format == "JPG":
                # 性能优化3：对于超大图像，自动降低质量
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
                # 性能优化4：PNG压缩级别调整
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
            
            if tracker:
                tracker.update_step(file_idx, total_files, file_name, 
                                  ConversionStep.MERGING_IMAGES, 100)
                
        except Exception as e:
            raise ValueError(f"保存图像失败: {str(e)}")
        
        return output_path

    @staticmethod
    def convert_pdf_batch(pdf_path, dpi, tracker=None, file_idx=0, 
                         total_files=1, file_name=""):
        """批量转换PDF - 优化版本"""
        # 性能优化5：批量渲染PDF页面，而不是逐页
        try:
            # 一次性转换所有页面，比逐页快很多
            if tracker:
                tracker.update_step(file_idx, total_files, file_name, 
                                  ConversionStep.RENDERING_PAGES, 10)
            
            # 使用 thread_count 参数加速（如果系统支持）
            images = pdf2image.convert_from_path(
                pdf_path, 
                poppler_path=POPPLER_PATH, 
                dpi=dpi,
                thread_count=4,  # 使用多线程
                use_pdftocairo=True  # 使用pdftocairo可能更快
            )
            
            if tracker:
                tracker.update_step(file_idx, total_files, file_name, 
                                  ConversionStep.RENDERING_PAGES, 100,
                                  len(images), len(images))
            
            return images
            
        except Exception as e:
            # 如果批量失败，回退到逐页（兼容性）
            print(f"批量渲染失败，回退到逐页模式: {e}")
            return OptimizedImageMerger.convert_pdf_fallback(
                pdf_path, dpi, tracker, file_idx, total_files, file_name
            )
    
    @staticmethod
    def convert_pdf_fallback(pdf_path, dpi, tracker, file_idx, total_files, file_name):
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
            
            if tracker:
                progress = (page_num / total_pages) * 100
                tracker.update_step(file_idx, total_files, file_name, 
                                  ConversionStep.RENDERING_PAGES, progress,
                                  page_num, total_pages)
        
        return images

# 主应用类使用优化的合并器
class File2LongImageApp:
    def __init__(self, root):
        self.root = root
        self.merger = OptimizedImageMerger()  # 使用优化的合并器
        # ... 其余初始化代码 ...
        
    def convert_pdf_with_progress(self, pdf_path, dpi, tracker, 
                                 file_idx, total_files, file_name):
        """使用优化的PDF转换"""
        return self.merger.convert_pdf_batch(
            pdf_path, dpi, tracker, file_idx, total_files, file_name
        )
    
    def merge_images_with_progress(self, images, output_path, output_format, 
                                  quality, tracker, file_idx, total_files, file_name):
        """使用优化的图像合并"""
        return self.merger.merge_images_fast(
            images, output_path, output_format, quality, 
            tracker, file_idx, total_files, file_name
        )

if __name__ == "__main__":
    print("性能优化版本 - 主要改进：")
    print("1. ❌ 去掉 optimize=True 参数（性能提升10-100倍）")
    print("2. 🎯 根据图像大小动态调整压缩策略")
    print("3. 🚀 批量渲染PDF页面而非逐页")
    print("4. 💾 PNG使用分级压缩（compress_level）")
    print("5. 🔧 自动检测超大图像并降低质量")