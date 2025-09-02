#!/usr/bin/env python3
"""
专业级错误日志系统
提供详细的、可复制的、结构化的错误信息
"""

import os
import sys
import traceback
import platform
import datetime
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import subprocess
import hashlib

@dataclass
class SystemInfo:
    """系统信息数据类"""
    os_name: str
    os_version: str
    python_version: str
    cpu_count: int
    memory_total: Optional[str]
    disk_free: Optional[str]
    poppler_version: Optional[str]
    libreoffice_version: Optional[str]
    pil_version: str
    pdf2image_version: str

@dataclass
class ErrorLog:
    """错误日志数据类"""
    # 基本信息
    timestamp: str
    log_id: str
    
    # 文件信息
    file_name: str
    file_path: str
    file_size: Optional[int]
    file_hash: Optional[str]
    
    # 错误信息
    error_type: str
    error_message: str
    error_step: str
    traceback: str
    
    # 转换参数
    conversion_params: Dict[str, Any]
    
    # 系统信息
    system_info: SystemInfo
    
    # 执行信息
    elapsed_time: Optional[float]
    memory_usage: Optional[str]

class ErrorLogger:
    """错误日志记录器"""
    
    @staticmethod
    def get_system_info() -> SystemInfo:
        """获取系统信息"""
        # 基本系统信息
        os_name = platform.system()
        os_version = platform.version()
        python_version = sys.version
        cpu_count = os.cpu_count() or 0
        
        # 内存信息（macOS）
        memory_total = None
        try:
            if sys.platform == 'darwin':
                result = subprocess.run(['sysctl', 'hw.memsize'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    mem_bytes = int(result.stdout.split(':')[1].strip())
                    memory_total = f"{mem_bytes / (1024**3):.1f} GB"
        except:
            pass
        
        # 磁盘空间
        disk_free = None
        try:
            statvfs = os.statvfs('/')
            free_bytes = statvfs.f_frsize * statvfs.f_avail
            disk_free = f"{free_bytes / (1024**3):.1f} GB"
        except:
            pass
        
        # Poppler版本
        poppler_version = None
        try:
            result = subprocess.run(['pdftoppm', '-v'], 
                                  capture_output=True, text=True, stderr=subprocess.STDOUT)
            if result.returncode == 0:
                poppler_version = result.stdout.split('\n')[0]
        except:
            pass
        
        # LibreOffice版本
        libreoffice_version = None
        try:
            result = subprocess.run(['soffice', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                libreoffice_version = result.stdout.split('\n')[0]
        except:
            pass
        
        # Python库版本
        pil_version = "Unknown"
        pdf2image_version = "Unknown"
        try:
            import PIL
            pil_version = PIL.__version__
        except:
            pass
        
        try:
            import pdf2image
            pdf2image_version = pdf2image.__version__
        except:
            pass
        
        return SystemInfo(
            os_name=os_name,
            os_version=os_version,
            python_version=python_version,
            cpu_count=cpu_count,
            memory_total=memory_total,
            disk_free=disk_free,
            poppler_version=poppler_version,
            libreoffice_version=libreoffice_version,
            pil_version=pil_version,
            pdf2image_version=pdf2image_version
        )
    
    @staticmethod
    def get_file_hash(file_path: str, chunk_size: int = 8192) -> Optional[str]:
        """计算文件MD5哈希（前1MB）"""
        try:
            md5 = hashlib.md5()
            with open(file_path, 'rb') as f:
                # 只读取前1MB以提高性能
                data = f.read(1024 * 1024)
                md5.update(data)
            return md5.hexdigest()[:16]  # 返回前16位
        except:
            return None
    
    @staticmethod
    def get_memory_usage() -> Optional[str]:
        """获取当前进程内存使用"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            return f"{mem_info.rss / (1024**2):.1f} MB"
        except:
            return None
    
    @classmethod
    def create_error_log(cls, 
                        file_path: str,
                        file_name: str,
                        error: Exception,
                        error_step: str,
                        conversion_params: Dict[str, Any],
                        elapsed_time: Optional[float] = None) -> ErrorLog:
        """创建详细的错误日志"""
        
        # 生成唯一ID
        timestamp = datetime.datetime.now()
        log_id = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"
        
        # 文件信息
        file_size = None
        file_hash = None
        try:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                file_hash = cls.get_file_hash(file_path)
        except:
            pass
        
        # 获取完整的异常信息
        tb_str = ''.join(traceback.format_exception(
            type(error), error, error.__traceback__
        ))
        
        return ErrorLog(
            timestamp=timestamp.isoformat(),
            log_id=log_id,
            file_name=file_name,
            file_path=file_path,
            file_size=file_size,
            file_hash=file_hash,
            error_type=type(error).__name__,
            error_message=str(error),
            error_step=error_step,
            traceback=tb_str,
            conversion_params=conversion_params,
            system_info=cls.get_system_info(),
            elapsed_time=elapsed_time,
            memory_usage=cls.get_memory_usage()
        )
    
    @staticmethod
    def format_log_for_display(log: ErrorLog) -> str:
        """格式化日志用于显示"""
        output = []
        output.append("=" * 70)
        output.append(f"错误报告 - {log.timestamp}")
        output.append(f"日志ID: {log.log_id}")
        output.append("=" * 70)
        
        # 文件信息
        output.append("\n【文件信息】")
        output.append(f"文件名: {log.file_name}")
        output.append(f"路径: {log.file_path}")
        if log.file_size:
            size_mb = log.file_size / (1024 * 1024)
            output.append(f"大小: {size_mb:.1f} MB ({log.file_size:,} bytes)")
        if log.file_hash:
            output.append(f"哈希: {log.file_hash}")
        
        # 错误信息
        output.append("\n【错误信息】")
        output.append(f"类型: {log.error_type}")
        output.append(f"步骤: {log.error_step}")
        output.append(f"消息: {log.error_message}")
        
        # 转换参数
        output.append("\n【转换参数】")
        for key, value in log.conversion_params.items():
            output.append(f"{key}: {value}")
        
        # 执行信息
        output.append("\n【执行信息】")
        if log.elapsed_time:
            output.append(f"耗时: {log.elapsed_time:.1f} 秒")
        if log.memory_usage:
            output.append(f"内存使用: {log.memory_usage}")
        
        # 系统信息
        output.append("\n【系统环境】")
        output.append(f"操作系统: {log.system_info.os_name} {log.system_info.os_version[:50]}...")
        output.append(f"Python: {log.system_info.python_version.split()[0]}")
        output.append(f"CPU核心: {log.system_info.cpu_count}")
        if log.system_info.memory_total:
            output.append(f"总内存: {log.system_info.memory_total}")
        if log.system_info.disk_free:
            output.append(f"磁盘剩余: {log.system_info.disk_free}")
        
        # 依赖版本
        output.append("\n【依赖版本】")
        output.append(f"PIL/Pillow: {log.system_info.pil_version}")
        output.append(f"pdf2image: {log.system_info.pdf2image_version}")
        if log.system_info.poppler_version:
            output.append(f"Poppler: {log.system_info.poppler_version}")
        if log.system_info.libreoffice_version:
            output.append(f"LibreOffice: {log.system_info.libreoffice_version}")
        
        # 详细追踪
        output.append("\n【调用栈追踪】")
        output.append(log.traceback)
        
        output.append("=" * 70)
        output.append("报告结束")
        output.append("=" * 70)
        
        return '\n'.join(output)
    
    @staticmethod
    def format_log_for_clipboard(log: ErrorLog) -> str:
        """格式化日志用于剪贴板（Markdown格式）"""
        output = []
        output.append("## 错误报告")
        output.append(f"**时间**: {log.timestamp}")
        output.append(f"**ID**: `{log.log_id}`")
        output.append("")
        
        output.append("### 文件信息")
        output.append(f"- **文件**: `{log.file_name}`")
        output.append(f"- **路径**: `{log.file_path}`")
        if log.file_size:
            output.append(f"- **大小**: {log.file_size / (1024*1024):.1f} MB")
        output.append("")
        
        output.append("### 错误详情")
        output.append(f"- **类型**: `{log.error_type}`")
        output.append(f"- **步骤**: {log.error_step}")
        output.append(f"- **消息**: {log.error_message}")
        output.append("")
        
        output.append("### 系统环境")
        output.append(f"- **OS**: {log.system_info.os_name}")
        output.append(f"- **Python**: {log.system_info.python_version.split()[0]}")
        output.append(f"- **Pillow**: {log.system_info.pil_version}")
        output.append(f"- **pdf2image**: {log.system_info.pdf2image_version}")
        output.append("")
        
        output.append("### 调用栈")
        output.append("```python")
        output.append(log.traceback)
        output.append("```")
        
        return '\n'.join(output)
    
    @staticmethod
    def save_to_file(log: ErrorLog, directory: str = "logs") -> str:
        """保存日志到文件"""
        os.makedirs(directory, exist_ok=True)
        
        # 生成文件名
        filename = f"error_{log.log_id}.log"
        filepath = os.path.join(directory, filename)
        
        # 保存文本版本
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(ErrorLogger.format_log_for_display(log))
        
        # 保存JSON版本（便于程序分析）
        json_filepath = filepath.replace('.log', '.json')
        with open(json_filepath, 'w', encoding='utf-8') as f:
            # 转换为可序列化的字典
            log_dict = asdict(log)
            json.dump(log_dict, f, indent=2, ensure_ascii=False)
        
        return filepath

# 使用示例
if __name__ == "__main__":
    print("错误日志系统演示")
    print("=" * 70)
    
    # 模拟错误
    try:
        # 故意触发错误
        1 / 0
    except Exception as e:
        # 创建错误日志
        log = ErrorLogger.create_error_log(
            file_path="/Users/test/document.pdf",
            file_name="document.pdf",
            error=e,
            error_step="渲染页面",
            conversion_params={
                "dpi": 200,
                "format": "PNG",
                "quality": 85
            },
            elapsed_time=3.5
        )
        
        # 显示格式化的日志
        print(ErrorLogger.format_log_for_display(log))
        
        # 保存到文件
        filepath = ErrorLogger.save_to_file(log)
        print(f"\n日志已保存到: {filepath}")