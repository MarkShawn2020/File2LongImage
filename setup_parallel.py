"""
py2app build script for File2LongImage (Parallel Version)

Usage:
    python setup_parallel.py py2app
"""

from setuptools import setup
import sys
import os

# 确保在 macOS 上运行
if sys.platform != 'darwin':
    print("This setup script is for macOS only!")
    sys.exit(1)

APP = ['mac_app_parallel.py']
DATA_FILES = [
    ('', ['config.py', 'error_logger.py']),
    ('assets', ['assets/demo.png', 'assets/demo-parallel.png']),
]

# 创建必要的目录
os.makedirs('output', exist_ok=True)
os.makedirs('.intermediate', exist_ok=True)
os.makedirs('logs', exist_ok=True)

OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'assets/icon.icns' if os.path.exists('assets/icon.icns') else None,
    'plist': {
        'CFBundleName': 'File2LongImage',
        'CFBundleDisplayName': 'File2LongImage - 并行版',
        'CFBundleIdentifier': 'com.file2longimage.parallel',
        'CFBundleVersion': '2.0.0',
        'CFBundleShortVersionString': '2.0.0',
        'NSHumanReadableCopyright': '© 2024 File2LongImage',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.14.0',
        'NSRequiresAquaSystemAppearance': False,  # 支持暗色模式
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'PDF Document',
                'CFBundleTypeRole': 'Viewer',
                'LSItemContentTypes': ['com.adobe.pdf'],
                'CFBundleTypeExtensions': ['pdf'],
            },
            {
                'CFBundleTypeName': 'Microsoft Word Document',
                'CFBundleTypeRole': 'Viewer',
                'CFBundleTypeExtensions': ['doc', 'docx'],
            },
            {
                'CFBundleTypeName': 'Microsoft Excel Document',
                'CFBundleTypeRole': 'Viewer',
                'CFBundleTypeExtensions': ['xls', 'xlsx', 'csv'],
            },
            {
                'CFBundleTypeName': 'Microsoft PowerPoint Document',
                'CFBundleTypeRole': 'Viewer',
                'CFBundleTypeExtensions': ['ppt', 'pptx'],
            },
            {
                'CFBundleTypeName': 'Text Document',
                'CFBundleTypeRole': 'Viewer',
                'CFBundleTypeExtensions': ['txt', 'rtf', 'odt'],
            }
        ],
        'NSAppleEventsUsageDescription': 'File2LongImage needs to control other applications to convert documents.',
        'NSDesktopFolderUsageDescription': 'File2LongImage needs access to save converted images.',
        'NSDocumentsFolderUsageDescription': 'File2LongImage needs access to read and save documents.',
        'NSDownloadsFolderUsageDescription': 'File2LongImage needs access to read files from Downloads.',
    },
    'packages': [
        'PIL', 
        'pdf2image',
        'tkinter',
        'concurrent.futures',
        'dataclasses',
        'enum',
        'uuid',
    ],
    'includes': [
        'config',
        'error_logger',
        'subprocess',
        'hashlib',
        'threading',
        'pathlib',
        'queue',
        'time',
        'webbrowser',
        'traceback',
        'json',
        'platform',
        'psutil',
        'shutil',
        'tempfile',
    ],
    'excludes': [
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'pytest',
        'setuptools',
        'pip',
        'IPython',
        'jupyter',
    ],
    'resources': [
        'output',
        '.intermediate',
        'logs',
    ],
    'frameworks': [],
    'dylib_excludes': [],
    'strip': True,
    'optimize': 1,  # 降低优化级别以便调试
}

# 尝试包含 Poppler 二进制文件
poppler_paths = ['/opt/homebrew/bin', '/usr/local/bin']
for poppler_path in poppler_paths:
    if os.path.exists(poppler_path):
        poppler_binaries = [
            'pdfinfo',
            'pdftocairo', 
            'pdftotext',
            'pdftoppm',
        ]
        for binary in poppler_binaries:
            binary_path = os.path.join(poppler_path, binary)
            if os.path.exists(binary_path):
                DATA_FILES.append(('poppler', [binary_path]))
        break

setup(
    name='File2LongImage',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    install_requires=[
        'Pillow>=10.0.0,<11.0.0',
        'pdf2image==1.16.3',
        'psutil>=5.9.0',
    ],
)