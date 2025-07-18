#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LogSeq to Notion 转换工具
将LogSeq导出的文档转换为可导入Notion的格式
"""

import os
import re
import uuid
import shutil
import json
import zipfile
from pathlib import Path
from urllib.parse import quote
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional

class LogSeqToNotionConverter:
    def __init__(self, logseq_export_path: str, output_path: str, source_name: str = None, generate_uuid: bool = False):
        """
        初始化转换器
        
        Args:
            logseq_export_path: LogSeq导出目录路径（可以是具体的导出目录，或包含多个导出的父目录）
            output_path: Notion格式输出根目录路径
            source_name: 指定要转换的LogSeq导出名称（如果logseq_export_path包含多个导出）
            generate_uuid: 是否生成UUID（默认为False，不生成UUID）
        """
        self.logseq_base_path = Path(logseq_export_path)
        self.output_base_path = Path(output_path)
        self.source_name = source_name
        self.generate_uuid = generate_uuid
        
        # 确定实际的LogSeq路径
        if source_name:
            self.logseq_path = self.logseq_base_path / source_name
            if not self.logseq_path.exists():
                raise ValueError(f"指定的LogSeq导出 '{source_name}' 不存在于 {logseq_export_path}")
        else:
            # 如果没有指定source_name，检查是否是直接的LogSeq导出目录
            if (self.logseq_base_path / "pages").exists() or (self.logseq_base_path / "journals").exists():
                self.logseq_path = self.logseq_base_path
                self.source_name = self.logseq_base_path.name
            else:
                # 尝试找到可用的导出
                available_exports = self.list_available_exports()
                if not available_exports:
                    raise ValueError(f"在 {logseq_export_path} 中未找到任何LogSeq导出目录\n"
                                   f"请确保目录结构正确，例如: {logseq_export_path}/my-notes/pages/")
                else:
                    raise ValueError(f"请指定要转换的LogSeq导出名称。\n"
                                   f"可用选项: {', '.join(available_exports)}\n"
                                   f"使用 -s 参数指定，例如: -s {available_exports[0]}")
        
        # 为每次转换创建带时间戳的输出目录
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_dir_name = f"{self.source_name}-{timestamp}"
        
        # 创建外层目录和内层Notion导入目录
        self.outer_output_path = self.output_base_path / output_dir_name
        self.output_path = self.outer_output_path / "notion-output"
        
        # 确保输出目录存在
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # 页面映射：LogSeq页面名 -> (Notion文件名, UUID或空字符串)
        self.page_mapping: Dict[str, Tuple[str, str]] = {}
        
        # 资源文件映射
        self.asset_mapping: Dict[str, str] = {}
        
        # 处理日志
        self.conversion_log: List[str] = []
        
    def list_available_exports(self) -> List[str]:
        """列出可用的LogSeq导出"""
        if not self.logseq_base_path.exists():
            return []
        
        exports = []
        for item in self.logseq_base_path.iterdir():
            if item.is_dir() and ((item / "pages").exists() or (item / "journals").exists()):
                exports.append(item.name)
        return exports
    
    def log(self, message: str):
        """记录转换日志"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        self.conversion_log.append(f"{datetime.now().isoformat()}: {message}")
    
    def generate_uuid(self) -> str:
        """生成32位UUID（不带连字符）"""
        return uuid.uuid4().hex
    
    def sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除不合法字符"""
        # 移除或替换不合法字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.strip('. ')
        return filename
    
    def extract_page_name(self, filepath: Path) -> str:
        """从文件路径提取页面名称"""
        return filepath.stem
    
    def create_notion_filename(self, page_name: str, page_uuid: str) -> str:
        """创建Notion格式的文件名"""
        clean_name = self.sanitize_filename(page_name)
        if self.generate_uuid:
            return f"{clean_name} {page_uuid}.md"
        else:
            return f"{clean_name}.md"
    
    def scan_pages(self):
        """扫描所有页面并建立映射关系"""
        self.log("开始扫描页面...")
        
        # 扫描pages目录
        pages_dir = self.logseq_path / "pages"
        if pages_dir.exists():
            for md_file in pages_dir.glob("*.md"):
                page_name = self.extract_page_name(md_file)
                page_uuid = self.generate_uuid() if self.generate_uuid else ""
                notion_filename = self.create_notion_filename(page_name, page_uuid)
                self.page_mapping[page_name] = (notion_filename, page_uuid)
                self.log(f"页面映射: {page_name} -> {notion_filename}")
        
        # 扫描journals目录
        journals_dir = self.logseq_path / "journals"
        if journals_dir.exists():
            for md_file in journals_dir.glob("*.md"):
                # 转换日期格式：2025_01_01 -> 2025年01月01日
                date_str = md_file.stem
                if re.match(r'\d{4}_\d{2}_\d{2}', date_str):
                    year, month, day = date_str.split('_')
                    page_name = f"{year}年{month}月{day}日"
                else:
                    page_name = date_str
                
                page_uuid = self.generate_uuid() if self.generate_uuid else ""
                notion_filename = self.create_notion_filename(page_name, page_uuid)
                self.page_mapping[date_str] = (notion_filename, page_uuid)  # 保持原文件名作为key
                self.log(f"日记映射: {date_str} -> {notion_filename}")
    
    def convert_links(self, content: str) -> str:
        """转换LogSeq链接格式为Notion格式"""
        def replace_page_link(match):
            page_name = match.group(1)
            if page_name in self.page_mapping:
                notion_filename, _ = self.page_mapping[page_name]
                # URL编码文件名
                encoded_filename = quote(notion_filename, safe='')
                return f"[{page_name}]({encoded_filename})"
            else:
                # 如果页面不存在，保持原样或创建新页面
                self.log(f"警告: 未找到页面 '{page_name}'，保持原链接格式")
                return f"[{page_name}](#{page_name})"
        
        # 转换 [[页面名]] 格式的链接
        content = re.sub(r'\[\[([^\]]+)\]\]', replace_page_link, content)
        
        # 转换 ![图片](路径) 格式的图片链接
        content = self.convert_image_links(content)
        
        return content
    
    def convert_image_links(self, content: str) -> str:
        """转换图片链接"""
        def replace_image_link(match):
            alt_text = match.group(1)
            image_path = match.group(2)
            
            # 如果是assets目录的文件
            if image_path.startswith('../assets/') or 'assets/' in image_path:
                # 提取文件名
                filename = os.path.basename(image_path)
                # 生成新的相对路径（假设图片会被放在当前页面的子目录中）
                new_path = quote(filename, safe='')
                return f"![{alt_text}]({new_path})"
            
            return match.group(0)  # 保持原样
        
        return re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_image_link, content)
    
    def convert_logseq_syntax(self, content: str) -> str:
        """转换LogSeq特有语法"""
        # 转换任务状态
        content = re.sub(r'^(\s*)-\s+DONE\s+', r'\1- [x] ', content, flags=re.MULTILINE)
        content = re.sub(r'^(\s*)-\s+TODO\s+', r'\1- [ ] ', content, flags=re.MULTILINE)
        content = re.sub(r'^(\s*)-\s+LATER\s+', r'\1- [ ] ', content, flags=re.MULTILINE)
        content = re.sub(r'^(\s*)-\s+NOW\s+', r'\1- [ ] ', content, flags=re.MULTILINE)
        
        # 移除LogSeq特有的属性语法
        content = re.sub(r'^([a-zA-Z-]+)::\s*(.*)$', r'**\1**: \2', content, flags=re.MULTILINE)
        
        # 转换块引用（简化处理，转换为引用格式）
        content = re.sub(r'\(\(\([a-f0-9-]+\)\)\)', '> [引用块]', content)
        
        # 移除查询语法（LogSeq的{{query}}）
        content = re.sub(r'\{\{[^}]+\}\}', '<!-- LogSeq查询已移除 -->', content)
        
        return content
    
    def create_page_hierarchy(self):
        """创建页面层级结构"""
        self.log("创建页面层级结构...")
        
        # 为简化处理，我们将所有页面放在同一级别
        # 你可以根据需要修改这部分来创建层级结构
        for original_name, (notion_filename, page_uuid) in self.page_mapping.items():
            self.log(f"准备转换页面: {original_name}")
    
    def copy_and_convert_assets(self):
        """复制并转换资源文件"""
        self.log("处理资源文件...")
        
        assets_dir = self.logseq_path / "assets"
        if not assets_dir.exists():
            self.log("未找到assets目录，跳过资源文件处理")
            return
        
        # 创建资源文件目录
        assets_output_dir = self.output_path / "assets"
        assets_output_dir.mkdir(exist_ok=True)
        
        for asset_file in assets_dir.rglob("*"):
            if asset_file.is_file():
                # 复制资源文件
                dest_path = assets_output_dir / asset_file.name
                shutil.copy2(asset_file, dest_path)
                self.asset_mapping[str(asset_file)] = str(dest_path)
                self.log(f"复制资源文件: {asset_file.name}")
    
    def convert_file(self, source_path: Path, target_path: Path):
        """转换单个文件"""
        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 应用各种转换
            content = self.convert_links(content)
            content = self.convert_logseq_syntax(content)
            
            # 确保目标目录存在
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入转换后的内容
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.log(f"转换完成: {source_path.name} -> {target_path.name}")
            
        except Exception as e:
            self.log(f"转换文件失败 {source_path}: {str(e)}")
    
    def convert_all_pages(self):
        """转换所有页面"""
        self.log("开始转换页面内容...")
        
        # 转换pages目录
        pages_dir = self.logseq_path / "pages"
        if pages_dir.exists():
            for md_file in pages_dir.glob("*.md"):
                page_name = self.extract_page_name(md_file)
                if page_name in self.page_mapping:
                    notion_filename, _ = self.page_mapping[page_name]
                    target_path = self.output_path / notion_filename
                    self.convert_file(md_file, target_path)
        
        # 转换journals目录
        journals_dir = self.logseq_path / "journals"
        if journals_dir.exists():
            for md_file in journals_dir.glob("*.md"):
                date_str = md_file.stem
                if date_str in self.page_mapping:
                    notion_filename, _ = self.page_mapping[date_str]
                    target_path = self.output_path / notion_filename
                    self.convert_file(md_file, target_path)
    
    def generate_conversion_report(self):
        """生成转换报告"""
        report = {
            "conversion_time": datetime.now().isoformat(),
            "total_pages": len(self.page_mapping),
            "page_mapping": self.page_mapping,
            "asset_mapping": self.asset_mapping,
            "conversion_log": self.conversion_log
        }
        
        report_path = self.output_path / "conversion_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        self.log(f"转换报告已生成: {report_path}")
    
    def create_zip_package(self):
        """将转换结果打包成ZIP文件"""
        self.log("开始创建ZIP压缩包...")
        
        # ZIP文件路径（与notion-output目录同级）
        zip_filename = f"{self.outer_output_path.name}.zip"
        zip_path = self.outer_output_path / zip_filename
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 遍历notion-output目录中的所有文件
                for file_path in self.output_path.rglob('*'):
                    if file_path.is_file():
                        # 计算相对路径（相对于notion-output目录）
                        relative_path = file_path.relative_to(self.output_path)
                        # 在ZIP中保持目录结构
                        zipf.write(file_path, relative_path)
                        
            # 计算ZIP文件大小
            zip_size = zip_path.stat().st_size
            zip_size_mb = zip_size / (1024 * 1024)
            
            self.log(f"ZIP压缩包创建完成: {zip_path}")
            self.log(f"压缩包大小: {zip_size_mb:.2f} MB")
            
            return zip_path
            
        except Exception as e:
            self.log(f"创建ZIP压缩包失败: {str(e)}")
            return None
    
    def convert(self):
        """执行完整的转换流程"""
        self.log("=" * 50)
        self.log(f"开始LogSeq到Notion的转换: {self.source_name}")
        self.log(f"输入目录: {self.logseq_path}")
        self.log(f"输出目录: {self.output_path}")
        self.log("=" * 50)
        
        try:
            # 1. 扫描并映射所有页面
            self.scan_pages()
            
            # 2. 创建页面层级结构
            self.create_page_hierarchy()
            
            # 3. 复制和转换资源文件
            self.copy_and_convert_assets()
            
            # 4. 转换所有页面内容
            self.convert_all_pages()
            
            # 5. 生成转换报告
            self.generate_conversion_report()
            
            # 6. 创建ZIP压缩包
            zip_path = self.create_zip_package()
            
            self.log("=" * 50)
            self.log("转换完成！")
            self.log(f"Notion导入目录: {self.output_path}")
            if zip_path:
                self.log(f"ZIP压缩包: {zip_path}")
            self.log(f"完整输出目录: {self.outer_output_path}")
            self.log(f"共转换 {len(self.page_mapping)} 个页面")
            self.log("=" * 50)
            
        except Exception as e:
            self.log(f"转换过程中发生错误: {str(e)}")
            raise

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='LogSeq到Notion转换工具')
    parser.add_argument('logseq_path', help='LogSeq导出根目录路径')
    parser.add_argument('output_path', help='Notion导入根目录路径')
    parser.add_argument('-s', '--source', dest='source_name', 
                        help='指定要转换的LogSeq导出名称（子目录名）')
    parser.add_argument('--list', action='store_true',
                        help='列出所有可用的LogSeq导出')
    parser.add_argument('--all', action='store_true',
                        help='转换所有可用的LogSeq导出')
    parser.add_argument('--with-uuid', action='store_true', 
                        help='生成UUID后缀（默认不生成，文件名更简洁）')
    
    args = parser.parse_args()
    
    # 列出可用导出
    if args.list:
        base_path = Path(args.logseq_path)
        if not base_path.exists():
            print(f"错误: 路径 {args.logseq_path} 不存在")
            return
        
        exports = []
        for item in base_path.iterdir():
            if item.is_dir() and ((item / "pages").exists() or (item / "journals").exists()):
                exports.append(item.name)
        
        if exports:
            print("可用的LogSeq导出:")
            for export in exports:
                print(f"  - {export}")
        else:
            print("未找到任何LogSeq导出")
        return
    
    # 批量转换所有导出
    if args.all:
        base_path = Path(args.logseq_path)
        exports = []
        for item in base_path.iterdir():
            if item.is_dir() and ((item / "pages").exists() or (item / "journals").exists()):
                exports.append(item.name)
        
        if not exports:
            print("未找到任何LogSeq导出")
            return
        
        print(f"找到 {len(exports)} 个LogSeq导出，开始批量转换...")
        for export_name in exports:
            try:
                print(f"\n{'='*50}")
                print(f"正在转换: {export_name}")
                print(f"{'='*50}")
                converter = LogSeqToNotionConverter(args.logseq_path, args.output_path, export_name, args.with_uuid)
                converter.convert()
            except Exception as e:
                print(f"转换 {export_name} 时发生错误: {str(e)}")
                continue
        
        print(f"\n{'='*50}")
        print("批量转换完成！")
        print(f"{'='*50}")
        return
    
    # 单个转换
    try:
        converter = LogSeqToNotionConverter(args.logseq_path, args.output_path, args.source_name, args.with_uuid)
        converter.convert()
    except Exception as e:
        print(f"错误: {str(e)}")
        print("\n使用 --list 参数查看可用的LogSeq导出")

if __name__ == "__main__":
    main() 