import os
import pdf2image
import streamlit as st
from PIL import Image
import time
import subprocess
import sys
from config import OUTPUT_DIR, POPPLER_PATH, LIBREOFFICE_PATH

st.set_page_config(page_title="文件转长图工具", page_icon="🖼️")

def merge_images(images, output_path):
    st.write("开始合并图像...")
    progress_bar = st.progress(0)
    status_text = st.empty()
    start_time = time.time()

    widths, heights = zip(*(i.size for i in images))
    total_height = sum(heights)
    max_width = max(widths)

    merged_image = Image.new('RGB', (max_width, total_height))
    y_offset = 0

    total_images = len(images)
    for idx, img in enumerate(images):
        merged_image.paste(img, (0, y_offset))
        y_offset += img.height

        # 更新进度
        progress = (idx + 1) / total_images
        progress_bar.progress(progress)
        elapsed_time = time.time() - start_time
        estimated_total_time = elapsed_time / progress
        remaining_time = estimated_total_time - elapsed_time
        status_text.text(f"正在合并图像：{idx + 1}/{total_images}，预计剩余时间：{int(remaining_time)}秒")

    merged_image.save(output_path)
    status_text.text("图像合并完成！")
    progress_bar.progress(1.0)

def convert_to_image(file_path, output_dir, dpi):
    st.write("开始转换文件...")
    progress_bar = st.progress(0)
    status_text = st.empty()
    start_time = time.time()

    images = []
    base_name = os.path.splitext(os.path.basename(file_path))[0]

    if file_path.lower().endswith('.pdf'):
        images = pdf2image.convert_from_path(file_path, poppler_path=POPPLER_PATH, dpi=dpi)
        progress_bar.progress(0.3)
    elif file_path.lower().endswith((".doc", ".docx", ".ppt", ".pptx", ".csv", ".xls", ".xlsx", ".odt", ".rtf", ".txt", ".psd", ".cdr", ".wps", ".svg")):
        pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
        if sys.platform.startswith('win'):
            conversion_cmd = f'"{LIBREOFFICE_PATH}" --headless --convert-to pdf "{file_path}" --outdir "{output_dir}"'
        else:
            conversion_cmd = f'{LIBREOFFICE_PATH} --headless --convert-to pdf "{file_path}" --outdir "{output_dir}"'
        subprocess.run(conversion_cmd, shell=True)

        if not os.path.exists(pdf_path):
            raise ValueError("文件转换为 PDF 失败")
        else:
            status_text.text(f"文件转换为 PDF 成功，正在转换为图像: {pdf_path}")
            progress_bar.progress(0.6)

        images = pdf2image.convert_from_path(pdf_path, poppler_path=POPPLER_PATH, dpi=dpi)
        progress_bar.progress(0.9)
    else:
        raise ValueError("不支持的文件格式")

    if images:
        merged_output_path = os.path.join(output_dir, f"{base_name}.png")
        merge_images(images, merged_output_path)
        progress_bar.progress(1.0)
        status_text.text("文件转换完成！")

st.title("文件转长图工具")
dpi = st.slider("设置图片 PPI", min_value=72, max_value=600, value=300)

uploaded_file = st.file_uploader("上传文件", type=["pdf", "doc", "docx", "ppt", "pptx", "csv", "xls", "xlsx", "odt", "rtf", "txt", "psd", "cdr", "wps", "svg"])

if uploaded_file is not None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(uploaded_file.name, "wb") as f:
        f.write(uploaded_file.getbuffer())
    convert_to_image(uploaded_file.name, OUTPUT_DIR, dpi)
    st.image(os.path.join(OUTPUT_DIR, f"{os.path.splitext(uploaded_file.name)[0]}.png"), caption='转换后的长图')