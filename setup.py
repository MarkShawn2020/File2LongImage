"""
py2app build script for File2LongImage

Usage:
    python setup.py py2app
"""

from setuptools import setup
import sys
import os

# 确保在 macOS 上运行
if sys.platform != 'darwin':
    print("This setup script is for macOS only!")
    sys.exit(1)

APP = ['mac_app.py']
DATA_FILES = [
    ('', ['config.py']),
    ('assets', ['assets/demo.png']),
]

OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'assets/icon.icns',
    'plist': {
        'CFBundleName': 'File2LongImage',
        'CFBundleDisplayName': 'File2LongImage',
        'CFBundleIdentifier': 'com.file2longimage.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
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
                'CFBundleTypeExtensions': ['txt', 'rtf'],
            }
        ],
        'UTExportedTypeDeclarations': [],
        'NSAppleEventsUsageDescription': 'File2LongImage needs to control other applications to convert documents.',
        'NSDesktopFolderUsageDescription': 'File2LongImage needs access to save converted images.',
        'NSDocumentsFolderUsageDescription': 'File2LongImage needs access to read and save documents.',
        'NSDownloadsFolderUsageDescription': 'File2LongImage needs access to read files from Downloads.',
    },
    'packages': [
        'PIL', 
        'pdf2image',
        'tkinter',
        'subprocess',
        'hashlib',
        'threading',
        'pathlib',
    ],
    'includes': [
        'config',
    ],
    'excludes': [
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'pytest',
        'setuptools',
        'pip',
    ],
    'resources': [
        'output',
        '.intermediate',
    ],
    'frameworks': [],
    'dylib_excludes': [],
    'strip': True,
    'optimize': 2,
}

# 尝试包含 Poppler 二进制文件
poppler_path = '/opt/homebrew/bin'
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

setup(
    name='File2LongImage',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    install_requires=[
        'Pillow>=10.0.0,<11.0.0',
        'pdf2image==1.16.3',
        'tkinterdnd2',
    ],
)