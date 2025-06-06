import os
import io
import re
import logging
from typing import Optional
from enum import Enum

from fastapi import FastAPI, HTTPException, Form, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.requests import Request
import markdown
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
from reportlab.lib.units import inch, cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrientationEnum(str, Enum):
    portrait = "portrait"
    landscape = "landscape" 
    auto = "auto"


app = FastAPI(title="Markdown Table to PDF Converter", version="1.0.0")

# 创建必要的目录
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 模板引擎
templates = Jinja2Templates(directory="templates")

# 注册中文字体
def register_chinese_fonts():
    """注册中文字体，确保中文正确显示"""
    try:
        # 尝试多种中文字体路径
        font_paths = [
            # macOS 字体路径 - 更全面的字体列表
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/STHeiti Light.ttc',
            '/System/Library/Fonts/STHeiti Medium.ttc', 
            '/System/Library/Fonts/Helvetica.ttc',
            '/Library/Fonts/Arial Unicode MS.ttf',
            '/System/Library/Fonts/Hiragino Sans GB.ttc',
            # Windows 字体路径
            'C:\\Windows\\Fonts\\simhei.ttf',
            'C:\\Windows\\Fonts\\simsun.ttc',
            'C:\\Windows\\Fonts\\msyh.ttc',
            'C:\\Windows\\Fonts\\msyhbd.ttf',
            # Linux 字体路径
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        ]
        
        font_registered = False
        base_font_name = None
        bold_font_name = None
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    print(f"尝试注册字体: {font_path}")
                    if font_path.endswith('.ttc'):
                        # TTC字体集合文件，尝试注册不同的子字体
                        for subfont_index in range(3):  # 尝试前3个子字体
                            try:
                                font_name = f'ChineseFont{subfont_index}'
                                pdfmetrics.registerFont(TTFont(font_name, font_path, subfontIndex=subfont_index))
                                
                                # 尝试找到粗体字体，先尝试不同索引
                                bold_registered = False
                                for bold_index in range(3):
                                    try:
                                        bold_font_name = f'{font_name}-Bold'
                                        pdfmetrics.registerFont(TTFont(bold_font_name, font_path, subfontIndex=bold_index))
                                        bold_registered = True
                                        break
                                    except:
                                        continue
                                
                                # 如果找不到独立粗体，使用同一字体作为粗体
                                if not bold_registered:
                                    bold_font_name = font_name
                                
                                print(f"成功注册字体: {font_path} (子字体 {subfont_index})")
                                font_registered = True
                                base_font_name = font_name
                                break
                            except Exception as e:
                                print(f"子字体 {subfont_index} 注册失败: {e}")
                                continue
                    else:
                        font_name = 'ChineseFont'
                        pdfmetrics.registerFont(TTFont(font_name, font_path))
                        # 注册Bold版本 - 使用相同字体文件
                        bold_font_name = f'{font_name}-Bold'
                        try:
                            pdfmetrics.registerFont(TTFont(bold_font_name, font_path))
                        except:
                            bold_font_name = font_name  # 如果注册失败，使用相同字体
                        print(f"成功注册字体: {font_path}")
                        font_registered = True
                        base_font_name = font_name
                    
                    if font_registered:
                        break
                        
                except Exception as e:
                    print(f"字体注册失败 {font_path}: {e}")
                    continue
        
        # 如果所有字体都失败，尝试使用reportlab的内置Unicode字体
        if not font_registered:
            print("所有系统字体注册失败，尝试内置字体")
            try:
                # 尝试使用内置的字体
                from reportlab.pdfbase.cidfonts import UnicodeCIDFont
                pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
                print("成功注册内置中文字体: STSong-Light")
                return 'STSong-Light', 'STSong-Light'
            except:
                print("内置中文字体也注册失败，使用Helvetica")
                return 'Helvetica', 'Helvetica-Bold'
                
        return base_font_name or 'Helvetica', bold_font_name or 'Helvetica-Bold'
    except Exception as e:
        print(f"字体注册异常: {e}")
        return 'Helvetica', 'Helvetica-Bold'

# 初始化字体
FONT_NAME, BOLD_FONT_NAME = register_chinese_fonts()
print(f"最终使用的字体: {FONT_NAME}, 粗体字体: {BOLD_FONT_NAME}")


def wrap_text_in_cell(text, max_width, font_name, font_size):
    """
    将文本包装成Paragraph对象以支持自动换行
    """
    if not text:
        return Paragraph("", ParagraphStyle(
            'cell_style',
            fontName=font_name,
            fontSize=font_size,
            alignment=TA_CENTER,
            wordWrap='LTR',
            leading=font_size * 1.1  # 减少行间距
        ))
    
    style = ParagraphStyle(
        'cell_style',
        fontName=font_name,
        fontSize=font_size,
        alignment=TA_CENTER,
        wordWrap='LTR',
        leading=font_size * 1.2,  # 适度的行间距
        leftIndent=2,
        rightIndent=2,
        spaceAfter=0,
        spaceBefore=0
    )
    
    return Paragraph(str(text), style)


def parse_markdown_table(md_content: str):
    """解析Markdown表格内容，确保UTF-8编码"""
    # 确保内容是UTF-8编码
    if isinstance(md_content, bytes):
        md_content = md_content.decode('utf-8')
    
    # 转换Markdown为HTML
    html = markdown.markdown(md_content, extensions=['tables'])
    soup = BeautifulSoup(html, 'html.parser')
    
    # 查找表格
    tables = soup.find_all('table')
    if not tables:
        # 如果没有标准表格，尝试手动解析Markdown表格
        return parse_markdown_table_manual(md_content)
    
    table_data = []
    for table in tables:
        rows = table.find_all('tr')
        table_rows = []
        for row in rows:
            cells = row.find_all(['th', 'td'])
            row_data = [cell.get_text(strip=True) for cell in cells]
            if row_data:  # 只添加非空行
                table_rows.append(row_data)
        if table_rows:
            table_data.extend(table_rows)
    
    return table_data


def parse_markdown_table_manual(md_content: str):
    """手动解析Markdown表格格式，确保UTF-8处理"""
    # 确保UTF-8编码
    if isinstance(md_content, bytes):
        md_content = md_content.decode('utf-8')
        
    lines = md_content.strip().split('\n')
    table_data = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 跳过分隔符行 (|---|---|)
        if re.match(r'^\|[\s\-\|:]*\|?$', line):
            continue
            
        # 解析表格行
        if line.startswith('|') and line.endswith('|'):
            cells = [cell.strip() for cell in line[1:-1].split('|')]
            if cells:
                table_data.append(cells)
        elif '|' in line:
            cells = [cell.strip() for cell in line.split('|')]
            if cells:
                table_data.append(cells)
    
    return table_data


def determine_orientation(table_data, orientation: str = "auto"):
    """确定PDF方向，优先考虑内容适配"""
    if orientation in ["portrait", "landscape"]:
        return orientation
    
    if not table_data:
        return "portrait"
    
    # 计算表格的复杂度来决定方向
    max_cols = max(len(row) for row in table_data) if table_data else 0
    total_content_length = sum(
        sum(len(str(cell)) for cell in row) for row in table_data
    ) if table_data else 0
    avg_content_per_cell = total_content_length / (len(table_data) * max_cols) if len(table_data) > 0 and max_cols > 0 else 0
    
    # 更智能的方向判断：考虑列数、平均内容长度和总内容量
    if max_cols > 4 or avg_content_per_cell > 20 or total_content_length > 500:
        return "landscape"
    else:
        return "portrait"


def calculate_text_width(text, font_name, font_size):
    """计算文本的实际显示宽度，考虑中英文混合"""
    if not text:
        return 0
    
    text_str = str(text)
    width = 0
    
    for char in text_str:
        if ord(char) > 127:  # 中文字符
            width += font_size * 0.9  # 中文字符宽度
        else:  # 英文字符和标点
            width += font_size * 0.5  # 英文字符宽度
    
    return width


def create_table_styles(font_size):
    """创建表格样式，根据字体大小调整样式"""
    # 根据字体大小调整内边距
    padding = max(3, font_size // 2)
    
    return TableStyle([
        # 字体设置
        ('FONTNAME', (0, 0), (-1, 0), BOLD_FONT_NAME),  # 表头：使用粗体字体
        ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),      # 正文：使用普通字体
        ('FONTSIZE', (0, 0), (-1, -1), font_size),      # 动态字体大小
        
        # 对齐方式
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),         # 垂直居中
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),          # 水平居中
        
        # 边框和网格
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # 细边框
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black), # 表头下细线
        
        # 背景色
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # 表头背景
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),     # 正文背景
        
        # 紧凑的内边距
        ('LEFTPADDING', (0, 0), (-1, -1), padding),
        ('RIGHTPADDING', (0, 0), (-1, -1), padding),
        ('TOPPADDING', (0, 0), (-1, -1), padding),
        ('BOTTOMPADDING', (0, 0), (-1, -1), padding),
    ])


def calculate_optimal_table_size(data, available_width, available_height):
    """优化的表格尺寸计算，确保内容尽量在一页中显示"""
    if not data or len(data) < 1:
        return None, None, 1.0, 10
    
    num_cols = len(data[0])
    num_rows = len(data)
    
    # 动态字体大小策略：根据表格复杂度调整
    total_content = sum(len(str(cell)) for row in data for cell in row)
    
    # 根据内容量和表格大小决定字体大小
    if total_content > 1000 or num_rows > 8 or num_cols > 5:
        base_font_size = 8  # 内容多时使用小字体
    elif total_content > 500 or num_rows > 5:
        base_font_size = 9  # 中等内容使用中等字体
    else:
        base_font_size = 10  # 内容少时使用标准字体
    
    # 计算每列的内容宽度和可能的行数
    col_widths = []
    max_lines_per_col = []
    
    for col_idx in range(num_cols):
        max_width = 0
        max_lines = 1
        
        for row in data:
            if col_idx < len(row):
                cell_content = str(row[col_idx])
                text_width = calculate_text_width(cell_content, FONT_NAME, base_font_size)
                max_width = max(max_width, text_width)
                
                # 更精确的换行预估：根据字符数和列宽预估
                char_count = len(cell_content)
                if char_count > 20:  # 长文本预估换行
                    estimated_lines = max(1, char_count // 20)
                    max_lines = max(max_lines, min(estimated_lines, 4))  # 限制最大行数
        
        col_widths.append(max_width)
        max_lines_per_col.append(max_lines)
    
    # 计算基础表格尺寸
    min_col_width = 50  # 降低最小列宽
    padding_per_col = 8  # 减少内边距
    
    # 初始列宽分配
    total_content_width = sum(col_widths)
    border_width = num_cols  # 减少边框占用
    base_table_width = total_content_width + padding_per_col * num_cols + border_width
    
    # 动态行高计算
    max_lines_overall = max(max_lines_per_col) if max_lines_per_col else 1
    base_row_height = max(0.8 * cm, base_font_size * max_lines_overall * 1.3 + 10)
    estimated_table_height = num_rows * base_row_height
    
    # 优化的缩放策略：目标是尽量填满页面
    width_scale = available_width / base_table_width if base_table_width > 0 else 1.0
    height_scale = available_height / estimated_table_height if estimated_table_height > 0 else 1.0
    
    # 更激进的缩放策略，优先保证一页显示
    scale_factor = min(width_scale, height_scale)
    
    # 如果缩放比例太小，尝试减小字体大小
    if scale_factor < 0.6:
        # 重新计算，使用更小的字体
        adjusted_font_size = max(6, int(base_font_size * scale_factor * 1.2))
        
        # 重新计算列宽
        adjusted_col_widths = []
        for col_idx in range(num_cols):
            max_width = 0
            for row in data:
                if col_idx < len(row):
                    cell_content = str(row[col_idx])
                    text_width = calculate_text_width(cell_content, FONT_NAME, adjusted_font_size)
                    max_width = max(max_width, text_width)
            adjusted_col_widths.append(max_width)
        
        # 重新计算基础宽度
        total_content_width = sum(adjusted_col_widths)
        base_table_width = total_content_width + padding_per_col * num_cols + border_width
        
        # 重新计算行高
        base_row_height = max(0.7 * cm, adjusted_font_size * max_lines_overall * 1.3 + 8)
        estimated_table_height = num_rows * base_row_height
        
        # 重新计算缩放
        width_scale = available_width / base_table_width if base_table_width > 0 else 1.0
        height_scale = available_height / estimated_table_height if estimated_table_height > 0 else 1.0
        scale_factor = min(width_scale, height_scale)
        
        col_widths = adjusted_col_widths
        base_font_size = adjusted_font_size
    
    # 智能列宽分配
    if scale_factor < 1.0:
        # 需要压缩时的列宽分配
        total_weight = sum(col_widths) if sum(col_widths) > 0 else 1
        final_col_widths = []
        
        for w in col_widths:
            min_width = max(min_col_width, available_width * 0.06)  # 最小列宽6%
            proportional_width = (w / total_weight) * available_width * 0.98
            final_width = max(min_width, proportional_width)
            final_col_widths.append(final_width)
        
        # 确保总宽度不超出
        total_final_width = sum(final_col_widths)
        if total_final_width > available_width:
            adjustment_factor = available_width * 0.98 / total_final_width
            final_col_widths = [w * adjustment_factor for w in final_col_widths]
    else:
        # 不需要压缩时，适当扩展
        extra_space = available_width - base_table_width
        space_per_col = extra_space / num_cols if num_cols > 0 else 0
        final_col_widths = [w + padding_per_col + max(0, space_per_col) for w in col_widths]
    
    # 最终行高
    final_row_height = max(base_row_height * min(scale_factor, 1.0), 0.6 * cm)
    
    return final_col_widths, final_row_height, scale_factor, base_font_size


def create_pdf(table_data, orientation: str = "portrait"):
    """创建PDF文档，优化布局确保内容在一页中并居中显示"""
    buffer = io.BytesIO()
    
    # 设置页面尺寸
    if orientation == "landscape":
        pagesize = landscape(A4)
    else:
        pagesize = A4
    
    # 减少页面边距，为表格留出更多空间
    margin_left = margin_right = 1.0 * cm  # 减少左右边距
    margin_top = margin_bottom = 1.2 * cm  # 减少上下边距
    
    # 计算可用空间
    available_width = pagesize[0] - margin_left - margin_right
    available_height = pagesize[1] - margin_top - margin_bottom
    
    # 创建文档，设置PDF元数据确保预览器正常显示
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=pagesize, 
        topMargin=margin_top, 
        bottomMargin=margin_bottom,
        leftMargin=margin_left, 
        rightMargin=margin_right,
        title="表格转换PDF",
        author="Markdown表格转换工具",
        subject="表格数据",
        creator="mdt2pdf"
    )
    
    story = []
    
    if table_data:
        # 计算最优表格尺寸（现在返回字体大小）
        col_widths, row_height, scale_factor, font_size = calculate_optimal_table_size(
            table_data, available_width, available_height
        )
        
        # 转换表格数据为Paragraph对象以支持换行
        processed_data = []
        
        for row_idx, row in enumerate(table_data):
            processed_row = []
            for col_idx, cell in enumerate(row):
                # 表头使用粗体
                font_name = BOLD_FONT_NAME if row_idx == 0 else FONT_NAME
                wrapped_cell = wrap_text_in_cell(
                    cell, 
                    col_widths[col_idx] if col_idx < len(col_widths) else 100, 
                    font_name, 
                    font_size
                )
                processed_row.append(wrapped_cell)
            processed_data.append(processed_row)
        
        # 创建表格
        table = Table(
            processed_data,
            colWidths=col_widths,
            repeatRows=1  # 重复表头行
        )
        
        # 设置表格样式（传入字体大小）
        table_style = create_table_styles(font_size)
        table.setStyle(table_style)
        
        # 计算表格实际宽度和高度
        actual_table_width = sum(col_widths)
        estimated_table_height = len(table_data) * row_height
        
        # 添加垂直居中的空白间隔
        if estimated_table_height < available_height:
            top_spacer_height = (available_height - estimated_table_height) / 2
            story.append(Spacer(1, max(0, top_spacer_height)))
        
        # 创建居中的表格容器
        centered_table = KeepTogether([table])
        
        # 如果表格宽度小于可用宽度，通过调整页边距来居中
        if actual_table_width < available_width:
            # 重新计算边距以实现水平居中
            horizontal_margin = (pagesize[0] - actual_table_width) / 2
            
            # 重新创建文档以应用新的边距
            doc = SimpleDocTemplate(
                buffer, 
                pagesize=pagesize, 
                topMargin=margin_top, 
                bottomMargin=margin_bottom,
                leftMargin=horizontal_margin, 
                rightMargin=horizontal_margin,
                title="表格转换PDF",
                author="Markdown表格转换工具", 
                subject="表格数据",
                creator="mdt2pdf"
            )
            
            # 重新计算可用高度（宽度已经匹配表格宽度）
            available_height_centered = pagesize[1] - margin_top - margin_bottom
            
            # 重新添加垂直居中间隔
            story = []  # 清空之前的story
            if estimated_table_height < available_height_centered:
                top_spacer_height = (available_height_centered - estimated_table_height) / 2
                story.append(Spacer(1, max(0, top_spacer_height)))
        
        story.append(centered_table)
        
        logger.info(f"PDF生成成功，缩放比例: {scale_factor:.2f}, 字体大小: {font_size}, 列宽: {[f'{w:.1f}' for w in col_widths]}, 表格宽度: {actual_table_width:.1f}")
        
    else:
        # 如果没有表格数据，添加居中的提示文本
        style = ParagraphStyle(
            'default',
            fontName=FONT_NAME,
            fontSize=14,
            alignment=1,  # 居中对齐
            textColor=colors.black
        )
        
        # 添加垂直居中的间隔
        story.append(Spacer(1, available_height / 2 - 1 * cm))
        story.append(Paragraph("没有找到有效的表格数据", style))
    
    # 构建PDF，设置文档属性确保预览器正常显示
    try:
        doc.build(story)
        
        # 在buffer中添加一些PDF查看器兼容性设置
        buffer.seek(0)
        pdf_content = buffer.read()
        buffer.seek(0)
        buffer.truncate()
        
        # 重新写入内容，确保PDF查看器工具栏正常显示
        buffer.write(pdf_content)
        buffer.seek(0)
        
    except Exception as e:
        logger.error(f"PDF生成失败: {e}")
        # 如果居中布局失败，使用原始布局
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=pagesize, 
            topMargin=margin_top, 
            bottomMargin=margin_bottom,
            leftMargin=margin_left, 
            rightMargin=margin_right
        )
        
        story = []
        if table_data:
            col_widths, row_height, scale_factor, font_size = calculate_optimal_table_size(
                table_data, available_width, available_height
            )
            
            processed_data = []
            for row_idx, row in enumerate(table_data):
                processed_row = []
                for col_idx, cell in enumerate(row):
                    font_name = BOLD_FONT_NAME if row_idx == 0 else FONT_NAME
                    wrapped_cell = wrap_text_in_cell(
                        cell, 
                        col_widths[col_idx] if col_idx < len(col_widths) else 100, 
                        font_name, 
                        font_size
                    )
                    processed_row.append(wrapped_cell)
                processed_data.append(processed_row)
            
            table = Table(processed_data, colWidths=col_widths, repeatRows=1)
            table_style = create_table_styles(font_size)
            table.setStyle(table_style)
            story.append(KeepTogether([table]))
        
        doc.build(story)
        buffer.seek(0)
    
    return buffer


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页面"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/convert")
async def convert_markdown_to_pdf(
    markdown_content: str = Form(...),
    orientation: OrientationEnum = Form(OrientationEnum.auto)
):
    """转换Markdown表格为PDF"""
    try:
        print(f"接收到的内容: {markdown_content[:100]}...")  # 调试信息
        
        # 解析Markdown表格
        table_data = parse_markdown_table(markdown_content)
        print(f"解析得到的表格数据: {table_data}")  # 调试信息
        
        if not table_data:
            raise HTTPException(status_code=400, detail="未找到有效的表格数据")
        
        # 确定方向
        final_orientation = determine_orientation(table_data, orientation.value)
        print(f"确定的页面方向: {final_orientation}")  # 调试信息
        
        # 生成PDF
        pdf_buffer = create_pdf(table_data, final_orientation)
        
        # 返回PDF文件，设置正确的响应头确保预览器工具栏显示
        return StreamingResponse(
            io.BytesIO(pdf_buffer.read()),
            media_type="application/pdf",
            headers={
                "Content-Disposition": "inline; filename=table.pdf",  # 使用inline而不是attachment
                "Content-Type": "application/pdf",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
        )
        
    except Exception as e:
        print(f"PDF生成错误: {e}")  # 调试信息
        raise HTTPException(status_code=500, detail=f"PDF生成失败: {str(e)}")


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "font": FONT_NAME, "bold_font": BOLD_FONT_NAME}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
