# -*- coding: utf-8 -*-
"""
Django 管理命令：生成数据源插件文档
"""

from django.core.management.base import BaseCommand
from django.core.management.color import color_style
from core.plugins.manager import get_plugin_manager
from core.plugins.documentation import DocumentationGenerator
from pathlib import Path
import json


class Command(BaseCommand):
    help = '生成数据源插件的文档'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            type=str,
            default='markdown',
            choices=['markdown', 'json', 'both'],
            help='输出格式（markdown, json, both）',
        )
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='输出文件路径（如果不指定，输出到控制台）',
        )
        parser.add_argument(
            '--source',
            type=str,
            default=None,
            help='生成特定数据源的文档',
        )
    
    def handle(self, *args, **options):
        style = color_style()
        manager = get_plugin_manager()
        
        self.stdout.write(style.HTTP_INFO("🔍 正在扫描已注册的数据源插件..."))
        
        plugins = manager.get_all_plugins()
        
        if not plugins:
            self.stdout.write(style.ERROR("❌ 未找到任何已注册的插件"))
            return
        
        self.stdout.write(style.SUCCESS(f"✅ 找到 {len(plugins)} 个插件"))
        for name, plugin in plugins.items():
            self.stdout.write(f"   • {plugin.display_name} ({name})")
        
        self.stdout.write("")
        
        if options['source']:
            # 生成特定数据源的文档
            plugin = manager.get_plugin(options['source'])
            if not plugin:
                self.stdout.write(style.ERROR(f"❌ 数据源 '{options['source']}' 不存在"))
                return
            
            doc = DocumentationGenerator.generate_plugin_doc(plugin)
            output_format = 'markdown'
        else:
            # 生成所有数据源的文档
            output_format = options['format']
            doc = DocumentationGenerator.generate_all_plugins_doc(manager)
        
        if output_format == 'both' or output_format == 'json':
            doc_json = DocumentationGenerator.generate_capabilities_json(manager)
            json_doc = json.dumps(doc_json, indent=2, ensure_ascii=False)
        else:
            json_doc = None
        
        # 输出或保存
        output_path = options['output']
        
        if output_format == 'markdown' or output_format == 'both':
            if output_path:
                output_file = Path(output_path) if output_format == 'markdown' else Path(f"{output_path}.md")
                output_file.write_text(doc, encoding='utf-8')
                self.stdout.write(style.SUCCESS(f"✅ Markdown 文档已保存到: {output_file}"))
            else:
                self.stdout.write("")
                self.stdout.write(style.HTTP_INFO("📄 Markdown 文档:"))
                self.stdout.write("=" * 80)
                self.stdout.write(doc)
                self.stdout.write("=" * 80)
        
        if output_format == 'json' or output_format == 'both':
            if output_path:
                output_file = Path(output_path) if output_format == 'json' else Path(f"{output_path}.json")
                output_file.write_text(json_doc, encoding='utf-8')
                self.stdout.write(style.SUCCESS(f"✅ JSON 文档已保存到: {output_file}"))
            else:
                self.stdout.write("")
                self.stdout.write(style.HTTP_INFO("📋 JSON 格式:"))
                self.stdout.write("=" * 80)
                self.stdout.write(json_doc)
                self.stdout.write("=" * 80)
        
        self.stdout.write("")
        self.stdout.write(style.SUCCESS("✅ 文档生成完成"))
