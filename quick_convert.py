#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LogSeq到Notion快速转换工具
转换指定的LogSeq导出子目录
"""

import argparse
from logseq_to_notion_converter import LogSeqToNotionConverter
from pathlib import Path

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='LogSeq到Notion快速转换工具')
    parser.add_argument('source_name', nargs='?', default='big_tech_250718_01',
                        help='要转换的LogSeq导出子目录名称')
    parser.add_argument('--logseq-path', default='logseq-export',
                        help='LogSeq导出根目录路径 (默认: logseq-export)')
    parser.add_argument('--output-path', default='notion-import',
                        help='Notion导入根目录路径 (默认: notion-import)')
    parser.add_argument('--with-uuid', action='store_true',
                        help='生成UUID后缀（默认不生成，文件名更简洁）')
    
    args = parser.parse_args()
    
    # 配置参数
    logseq_export_path = args.logseq_path
    notion_output_path = args.output_path
    source_name = args.source_name
    generate_uuid = args.with_uuid
    
    print("🚀 LogSeq到Notion快速转换工具")
    print(f"📁 LogSeq导出根目录: {logseq_export_path}")
    print(f"📁 指定转换目录: {source_name}")
    print(f"📁 Notion导入根目录: {notion_output_path}")
    print(f"🔧 生成UUID: {'是' if generate_uuid else '否（文件名更简洁）'}")
    print("=" * 60)
    
    try:
        # 创建转换器并执行转换
        converter = LogSeqToNotionConverter(
            logseq_export_path, 
            notion_output_path, 
            source_name, 
            generate_uuid
        )
        
        print(f"🔄 开始转换: {source_name}")
        print("-" * 50)
        
        converter.convert()
        
        print(f"\n✅ 转换完成！")
        print(f"📦 Notion导入目录: {converter.output_path}")
        print(f"📁 完整输出目录: {converter.outer_output_path}")
        print("💡 现在你可以使用ZIP文件或直接使用目录导入到Notion中了")
        
    except Exception as e:
        print(f"\n❌ 转换失败: {str(e)}")
        print(f"\n💡 请检查:")
        print(f"   1. 目录 {logseq_export_path}/{source_name}/ 是否存在")
        print(f"   2. 该目录下是否包含 pages/ 或 journals/ 子目录")
        print(f"   3. 可以运行以下命令查看可用的导出:")
        print(f"      python logseq_to_notion_converter.py {logseq_export_path} {notion_output_path} --list")

if __name__ == "__main__":
    main() 