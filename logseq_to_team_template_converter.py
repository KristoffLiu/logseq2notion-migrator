#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LogSeq to Team Template 转换工具
将LogSeq导出的文档转换为Notion Team Template格式
所有内容统一存储在一个数据库中，支持多种视图
"""

import os
import re
import uuid
import shutil
import json
import zipfile
import csv
from pathlib import Path
from urllib.parse import quote
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional

class LogSeqToTeamTemplateConverter:
    def __init__(self, source_name: str, team_name: str = "LogSeq导入团队", with_uuid: bool = False):
        """
        初始化转换器
        
        Args:
            source_name: LogSeq导出子目录名称（在logseq-export目录下）
            team_name: 团队模板名称
            with_uuid: 是否使用UUID（默认为False）
        """
        # 默认使用固定的根目录
        self.logseq_base_path = Path("logseq-export")
        self.output_base_path = Path("notion-import")
        self.source_name = source_name
        self.team_name = team_name
        self.with_uuid = with_uuid
        
        # 确定实际的LogSeq路径
        self.logseq_path = self.logseq_base_path / source_name
        if not self.logseq_path.exists():
            raise ValueError(f"指定的LogSeq导出 '{source_name}' 不存在于 logseq-export 目录")
        
        # 检查是否有pages或journals目录
        if not ((self.logseq_path / "pages").exists() or (self.logseq_path / "journals").exists()):
            raise ValueError(f"{source_name} 不是有效的LogSeq导出目录（缺少pages或journals目录）")
        
        # 为每次转换创建带时间戳的输出目录
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_dir_name = f"{self.source_name}-team-{timestamp}"
        
        # 创建输出目录结构 - 参考team-template结构
        self.outer_output_path = self.output_base_path / output_dir_name
        self.output_path = self.outer_output_path / "notion-import"
        
        # 根据配置决定是否使用UUID
        if self.with_uuid:
            self.main_page_uuid = uuid.uuid4().hex
            self.database_uuid = uuid.uuid4().hex
            self.main_page_name = f"{self.team_name} {self.main_page_uuid}"
            self.database_name = f"{self.team_name}聚合数据库 {self.database_uuid}"
        else:
            self.main_page_uuid = ""
            self.database_uuid = ""
            self.main_page_name = self.team_name
            self.database_name = f"{self.team_name}聚合数据库"
        
        # 目录结构：主页面目录包含数据库目录
        self.main_page_dir = self.output_path / self.main_page_name
        self.database_dir = self.main_page_dir / self.database_name
        
        # 确保输出目录存在
        self.database_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据库条目列表
        self.database_entries = []
        
        # 页面映射：LogSeq页面名 -> (Notion文件名, UUID)
        self.page_mapping: Dict[str, Tuple[str, str]] = {}
        
        # 资源文件映射
        self.asset_mapping: Dict[str, str] = {}
        
        # 处理日志
        self.conversion_log: List[str] = []
        
    @staticmethod
    def list_available_exports() -> List[str]:
        """列出可用的LogSeq导出"""
        logseq_base = Path("logseq-export")
        if not logseq_base.exists():
            return []
        
        exports = []
        for item in logseq_base.iterdir():
            if item.is_dir() and ((item / "pages").exists() or (item / "journals").exists()):
                exports.append(item.name)
        return exports
    
    def log(self, message: str):
        """记录转换日志"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        self.conversion_log.append(f"{datetime.now().isoformat()}: {message}")
    
    def sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除不合法字符"""
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.strip('. ')
        return filename
    
    def extract_page_name(self, filepath: Path) -> str:
        """从文件路径提取页面名称"""
        return filepath.stem
    
    def create_notion_filename(self, page_name: str, page_uuid: str) -> str:
        """创建Notion格式的文件名"""
        clean_name = self.sanitize_filename(page_name)
        if self.with_uuid:
            return f"{clean_name} {page_uuid}.md"
        else:
            return f"{clean_name}.md"
    
    def determine_page_type(self, filepath: Path, page_name: str) -> str:
        """确定页面类型"""
        # 如果是journals目录下的文件，标记为日志
        if "journals" in filepath.parts:
            return "日志"
        
        # 检查文件名模式
        if re.match(r'\d{4}年\d{2}月\d{2}日', page_name) or re.match(r'\d{4}_\d{2}_\d{2}', page_name):
            return "日志"
        
        # 其他都标记为文章
        return "文章"
    
    def convert_date_format(self, date_str: str) -> Tuple[str, str]:
        """转换日期格式"""
        # 处理 YYYY_MM_DD 格式
        if re.match(r'\d{4}_\d{2}_\d{2}', date_str):
            year, month, day = date_str.split('_')
            chinese_date = f"{year}年{month}月{day}日"
            iso_date = f"{month}/{day}/{year}"
            return chinese_date, iso_date
        
        # 处理其他日期格式
        if re.match(r'\d{4}年\d{2}月\d{2}日', date_str):
            # 已经是中文格式
            match = re.match(r'(\d{4})年(\d{2})月(\d{2})日', date_str)
            if match:
                year, month, day = match.groups()
                iso_date = f"{month}/{day}/{year}"
                return date_str, iso_date
        
        # 默认返回原始值
        return date_str, ""
    
    def extract_summary(self, content: str, max_length: int = 150) -> str:
        """从内容中提取摘要"""
        # 移除markdown格式
        content = re.sub(r'#+ ', '', content)  # 移除标题
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # 移除粗体
        content = re.sub(r'\*(.*?)\*', r'\1', content)  # 移除斜体
        content = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', content)  # 移除链接，保留文本
        content = re.sub(r'!\[.*?\]\(.*?\)', '', content)  # 移除图片
        content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)  # 移除代码块
        content = re.sub(r'`.*?`', '', content)  # 移除行内代码
        
        # 清理空白和换行
        content = ' '.join(content.split())
        
        # 截取摘要
        if len(content) > max_length:
            content = content[:max_length] + "..."
        
        return content.strip()
    
    def convert_links(self, content: str) -> str:
        """转换LogSeq链接格式为Notion格式"""
        def replace_page_link(match):
            page_name = match.group(1)
            if page_name in self.page_mapping:
                notion_filename, page_uuid = self.page_mapping[page_name]
                # 创建Notion格式的链接
                encoded_filename = quote(notion_filename[:-3])  # 移除.md扩展名
                if self.with_uuid and page_uuid:
                    return f"[{page_name}]({encoded_filename}%20{page_uuid}.md)"
                else:
                    return f"[{page_name}]({encoded_filename}.md)"
            else:
                return f"[{page_name}]"
        
        # 转换 [[页面]] 格式的链接
        content = re.sub(r'\[\[([^\]]+)\]\]', replace_page_link, content)
        
        return content
    
    def process_assets(self):
        """处理资源文件"""
        assets_dir = self.logseq_path / "assets"
        if not assets_dir.exists():
            self.log("assets目录不存在，跳过资源文件处理")
            return
        
        self.log("处理资源文件...")
        self.log(f"assets源目录: {assets_dir}")
        self.log(f"database目录: {self.database_dir}")
        
        # 创建assets目录
        notion_assets_dir = self.database_dir / "assets"
        try:
            notion_assets_dir.mkdir(parents=True, exist_ok=True)
            self.log(f"创建assets目录成功: {notion_assets_dir}")
        except Exception as e:
            self.log(f"创建assets目录失败: {e}")
            return
        
        for asset_file in assets_dir.rglob("*"):
            if asset_file.is_file():
                try:
                    # 复制资源文件
                    relative_path = asset_file.relative_to(assets_dir)
                    target_path = notion_assets_dir / relative_path
                    
                    self.log(f"准备复制: {asset_file} -> {target_path}")
                    
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(asset_file, target_path)
                    
                    # 建立映射
                    self.asset_mapping[str(relative_path)] = str(target_path.relative_to(self.output_path))
                    self.log(f"资源文件复制成功: {relative_path}")
                except Exception as e:
                    self.log(f"复制资源文件失败 {asset_file}: {e}")
                    continue
    
    def scan_and_convert_pages(self):
        """扫描并转换所有页面"""
        self.log("开始扫描和转换页面...")
        
        # 处理pages目录
        pages_dir = self.logseq_path / "pages"
        if pages_dir.exists():
            for md_file in pages_dir.glob("*.md"):
                self.process_page_file(md_file)
        
        # 处理journals目录
        journals_dir = self.logseq_path / "journals"
        if journals_dir.exists():
            for md_file in journals_dir.glob("*.md"):
                self.process_page_file(md_file)
    
    def process_page_file(self, md_file: Path):
        """处理单个页面文件"""
        page_name = self.extract_page_name(md_file)
        
        # 跳过contents.md，因为它的内容已经集成到主页面中
        if page_name == "contents":
            self.log(f"跳过contents.md，其内容已集成到主页面")
            return
        
        page_uuid = uuid.uuid4().hex if self.with_uuid else ""
        
        # 确定页面类型
        page_type = self.determine_page_type(md_file, page_name)
        
        # 处理日期格式（如果是日志）
        display_name = page_name
        start_date = ""
        
        if page_type == "日志":
            display_name, start_date = self.convert_date_format(page_name)
        
        # 读取内容
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.log(f"读取文件失败 {md_file}: {str(e)}")
            return
        
        # 创建页面映射
        notion_filename = self.create_notion_filename(display_name, page_uuid)
        self.page_mapping[page_name] = (notion_filename, page_uuid)
        
        # 提取摘要
        summary = self.extract_summary(content)
        
        # 创建数据库条目
        entry = {
            "名字": display_name,
            "开始日期": start_date,
            "页面类型": page_type,
            "结束日期": "",
            "相关成员": "",
            "Created by": "LogSeq导入",
            "内容标签": "",
            "摘要": summary,
            "状态": "Not started",
            "进度": ""
        }
        
        self.database_entries.append(entry)
        
        # 创建Notion格式的页面文件
        self.create_notion_page(notion_filename, page_uuid, display_name, page_type, start_date, content, summary)
        
        self.log(f"转换页面: {page_name} -> {display_name} ({page_type})")
    
    def create_notion_page(self, filename: str, page_uuid: str, page_name: str, page_type: str, start_date: str, content: str, summary: str):
        """创建Notion格式的页面文件"""
        notion_content = f"# {page_name}\n\n"
        
        # 添加属性
        notion_content += f"Created by: LogSeq导入\n"
        if start_date:
            notion_content += f"开始日期: {start_date}\n"
        notion_content += f"状态: Not started\n"
        notion_content += f"页面类型: {page_type}\n"
        if summary:
            notion_content += f"摘要: {summary}\n"
        
        notion_content += "\n---\n\n"
        
        # 转换链接格式
        converted_content = self.convert_links(content)
        notion_content += converted_content
        
        # 写入文件
        page_path = self.database_dir / filename
        try:
            with open(page_path, 'w', encoding='utf-8') as f:
                f.write(notion_content)
        except Exception as e:
            self.log(f"写入页面文件失败 {filename}: {str(e)}")
    
    def create_database_csv(self):
        """创建数据库CSV文件"""
        self.log("创建数据库CSV文件...")
        
        csv_path = self.main_page_dir / f"{self.database_name}.csv"
        
        # CSV表头
        headers = ["名字", "开始日期", "页面类型", "结束日期", "相关成员", "Created by", "内容标签", "摘要", "状态", "进度"]
        
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(self.database_entries)
            
            self.log(f"数据库CSV创建完成: {len(self.database_entries)} 条记录")
        except Exception as e:
            self.log(f"创建数据库CSV失败: {str(e)}")
    
    def read_contents_file(self) -> str:
        """读取contents.md文件内容"""
        contents_path = self.logseq_path / "pages" / "contents.md"
        if contents_path.exists():
            try:
                with open(contents_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 转换链接格式
                    return self.convert_links(content)
            except Exception as e:
                self.log(f"读取contents.md失败: {e}")
                return ""
        return ""
    
    def create_main_page(self):
        """创建主页面 - 完全参考team-template结构"""
        self.log("创建主页面...")
        
        # 读取contents.md内容
        contents_content = self.read_contents_file()
        
        # 编码数据库名称用于链接
        encoded_db_name = quote(self.database_name)
        
        # 构建主页面内容，contents内容在前面
        main_content = f"""# {self.team_name}

{contents_content}

---

<aside>
💡

模板版本：LogSeq导入-v1.0
导入时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

</aside>

---

<aside>
💡

请勿向非协作人员展示任何文档，
除非该文档的保密等级属于公开或内部公开。

</aside>

<aside>
⚠️ 保密等级：请修改

</aside>

<aside>
🏠

## 部门

项目组所在部门

</aside>

<aside>
👥

## 协作人员

@相关人员

</aside>

<aside>
ℹ️

## 信息

</aside>

<aside>
📅

创建时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

最后修改时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

</aside>

<aside>
<img src="https://www.notion.so/icons/table_orange.svg" alt="https://www.notion.so/icons/table_orange.svg" width="40px" />

## 数据库

[{self.team_name}聚合数据库]({encoded_db_name}.csv)

</aside>

今日聚合页面展示了当天的所有动态。

# 今日聚合

[今日聚合]({encoded_db_name}_today.csv)

这是一个基本的项目管理可视化

全局视角展示了周期内的动态。

# 全局视角

[全局视角]({encoded_db_name}_global.csv)

# 项目管理

[项目管理]({encoded_db_name}_projects.csv)

这是一个针对任务的可视化

# 任务管理

[任务管理]({encoded_db_name}_tasks.csv)

# 会议日志

[会议日志]({encoded_db_name}_meetings.csv)

# Wiki

[Wiki]({encoded_db_name}_wiki.csv)

---

## 导入统计

- 总记录数：{len(self.database_entries)}
- 日志条目：{len([e for e in self.database_entries if e['页面类型'] == '日志'])}
- 文章条目：{len([e for e in self.database_entries if e['页面类型'] == '文章'])}
- 导入源：{self.source_name}
"""
        
        # 写入主页面文件
        main_page_path = self.output_path / f"{self.main_page_name}.md"
        try:
            with open(main_page_path, 'w', encoding='utf-8') as f:
                f.write(main_content)
            self.log("主页面创建完成")
        except Exception as e:
            self.log(f"创建主页面失败: {str(e)}")
    
    def create_view_csvs(self):
        """创建各种视图的CSV文件 - 按照team-template结构"""
        self.log("创建视图CSV文件...")
        
        headers = ["名字", "开始日期", "页面类型", "结束日期", "相关成员", "Created by", "内容标签", "摘要", "状态", "进度"]
        
        # 今日聚合视图
        today_entries = self.database_entries
        self.write_csv(f"{self.database_name}_today.csv", headers, today_entries)
        
        # 全局视角
        global_entries = self.database_entries
        self.write_csv(f"{self.database_name}_global.csv", headers, global_entries)
        
        # 项目管理视图（目前所有条目都当作项目处理）
        project_entries = self.database_entries
        self.write_csv(f"{self.database_name}_projects.csv", headers, project_entries)
        
        # 任务管理视图
        task_entries = self.database_entries
        self.write_csv(f"{self.database_name}_tasks.csv", headers, task_entries)
        
        # 会议日志视图
        meeting_entries = self.database_entries
        self.write_csv(f"{self.database_name}_meetings.csv", headers, meeting_entries)
        
        # Wiki视图
        wiki_entries = self.database_entries
        self.write_csv(f"{self.database_name}_wiki.csv", headers, wiki_entries)
        
        self.log("所有视图CSV创建完成")
    
    def write_csv(self, filename: str, headers: List[str], entries: List[Dict]):
        """写入CSV文件"""
        csv_path = self.main_page_dir / filename
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(entries)
        except Exception as e:
            self.log(f"写入CSV文件失败 {filename}: {str(e)}")
    
    def create_conversion_report(self):
        """创建转换报告"""
        report = {
            "conversion_time": datetime.now().isoformat(),
            "source_name": self.source_name,
            "team_name": self.team_name,
            "total_entries": len(self.database_entries),
            "journal_entries": len([e for e in self.database_entries if e['页面类型'] == '日志']),
            "article_entries": len([e for e in self.database_entries if e['页面类型'] == '文章']),
            "main_page_name": self.main_page_name,
            "database_name": self.database_name,
            "conversion_log": self.conversion_log
        }
        
        report_path = self.output_path / "conversion_report.json"
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            self.log("转换报告创建完成")
        except Exception as e:
            self.log(f"创建转换报告失败: {str(e)}")
    
    def create_zip_archive(self):
        """创建ZIP压缩包"""
        self.log("创建ZIP压缩包...")
        
        zip_path = self.outer_output_path / f"{self.source_name}-team-template.zip"
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in self.output_path.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(self.output_path)
                        zipf.write(file_path, arcname)
            
            self.log(f"ZIP压缩包创建完成: {zip_path}")
        except Exception as e:
            self.log(f"创建ZIP压缩包失败: {str(e)}")
    
    def convert(self):
        """执行转换"""
        self.log("="*50)
        self.log(f"开始转换LogSeq到Team Template格式")
        self.log(f"源目录: {self.logseq_path}")
        self.log(f"输出目录: {self.output_path}")
        self.log(f"团队名称: {self.team_name}")
        self.log("="*50)
        
        try:
            # 处理资源文件
            self.process_assets()
            
            # 扫描和转换页面
            self.scan_and_convert_pages()
            
            # 创建数据库CSV
            self.create_database_csv()
            
            # 创建主页面
            self.create_main_page()
            
            # 创建视图CSV
            self.create_view_csvs()
            
            # 创建转换报告
            self.create_conversion_report()
            
            # 创建ZIP压缩包
            self.create_zip_archive()
            
            self.log("="*50)
            self.log("转换完成！")
            self.log(f"输出目录: {self.outer_output_path}")
            self.log(f"总条目数: {len(self.database_entries)}")
            self.log(f"日志条目: {len([e for e in self.database_entries if e['页面类型'] == '日志'])}")
            self.log(f"文章条目: {len([e for e in self.database_entries if e['页面类型'] == '文章'])}")
            self.log("="*50)
            
        except Exception as e:
            self.log(f"转换过程中发生错误: {str(e)}")
            raise

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="将LogSeq导出转换为Notion Team Template格式")
    parser.add_argument("source_name", help="LogSeq导出子目录名称（在logseq-export目录下）")
    parser.add_argument("-t", "--team-name", default="LogSeq导入团队", help="团队模板名称")
    parser.add_argument("--with-uuid", action="store_true", help="使用UUID（默认不使用）")
    parser.add_argument("--list", action="store_true", help="列出可用的LogSeq导出")
    
    args = parser.parse_args()
    
    # 列出可用的导出
    if args.list:
        exports = LogSeqToTeamTemplateConverter.list_available_exports()
        
        print("可用的LogSeq导出:")
        if exports:
            for export in exports:
                print(f"  - {export}")
        else:
            print("未找到任何LogSeq导出")
        return
    
    # 执行转换
    try:
        converter = LogSeqToTeamTemplateConverter(args.source_name, args.team_name, args.with_uuid)
        converter.convert()
    except Exception as e:
        print(f"错误: {str(e)}")
        print("\n使用 --list 参数查看可用的LogSeq导出")

if __name__ == "__main__":
    main() 