# LogSeq to Notion 转换工具

将LogSeq导出的笔记转换为可以导入Notion的格式，支持多笔记集管理，最大程度保持原有信息结构。

## 🚀 快速开始

### 1. 准备目录结构

#### 📁 标准目录结构
```
项目根目录/
├── logseq-export/              # 存放所有LogSeq导出
│   ├── project-a/              # 第一个笔记集
│   │   ├── pages/
│   │   ├── journals/
│   │   └── assets/
│   ├── personal-notes/         # 第二个笔记集
│   │   ├── pages/
│   │   ├── journals/
│   │   └── assets/
│   └── research-log/           # 第三个笔记集
│       ├── pages/
│       └── journals/
├── notion-import/              # 自动生成的转换结果
├── logseq_to_notion_converter.py
├── quick_convert.py
└── README.md
```

### 2. 准备LogSeq导出文件
从LogSeq中导出你的笔记：
- 在LogSeq中选择 `Settings` → `Export` → `Export public pages`
- 将导出的文件解压到 `logseq-export/你的笔记集名称/` 目录下

### 3. 运行转换工具

#### 方法一：快速转换（推荐）

**基本用法：**
```bash
# 使用默认子目录名称
python quick_convert.py

# 指定要转换的子目录
python quick_convert.py project-a

# 指定子目录并生成UUID
python quick_convert.py project-a --with-uuid

# 自定义路径
python quick_convert.py project-a --logseq-path my-logseq --output-path my-output
```

**参数说明：**
- `source_name`: 要转换的LogSeq导出子目录名称（可选，有默认值）
- `--logseq-path`: LogSeq导出根目录路径（默认: logseq-export）
- `--output-path`: Notion导入根目录路径（默认: notion-import）
- `--with-uuid`: 生成UUID后缀（默认不生成）

#### 方法二：命令行转换

**查看可用的LogSeq导出：**
```bash
python logseq_to_notion_converter.py logseq-export notion-import --list
```

**转换指定的导出：**
```bash
# 转换单个笔记集
python logseq_to_notion_converter.py logseq-export notion-import -s project-a

# 转换单个笔记集并生成UUID
python logseq_to_notion_converter.py logseq-export notion-import -s project-a --with-uuid
```

**批量转换所有导出：**
```bash
# 转换所有笔记集
python logseq_to_notion_converter.py logseq-export notion-import --all

# 转换所有笔记集并生成UUID
python logseq_to_notion_converter.py logseq-export notion-import --all --with-uuid
```

### 4. 导入到Notion

#### 📂 输出结构
转换完成后，每个笔记集会在 `notion-import/` 下生成带时间戳的子目录：
```
notion-import/
└── project-a-20250718-143022/
    ├── notion-import/          # 📁 Notion导入目录
    │   ├── 页面1.md
    │   ├── assets/
    │   └── conversion_report.json
    └── project-a-20250718-143022.zip  # 📦 ZIP压缩包
```

#### 🎯 导入方式

**方式一：使用ZIP文件（推荐）**
1. 下载或复制 `项目名-时间戳.zip` 文件
2. 解压ZIP文件到本地
3. 在Notion中选择 `Import` → `Markdown & CSV`
4. 选择解压后的文件夹进行导入

**方式二：直接使用目录**
1. 进入 `notion-import/` 子目录
2. 在Notion中选择 `Import` → `Markdown & CSV`
3. 选择该目录进行导入

💡 **推荐使用ZIP文件**：压缩包保证了文件完整性，便于传输和分享。

## 📋 转换功能

### 🎁 新增功能
- **自动ZIP打包**: 每次转换完成后自动生成ZIP压缩包
- **双重输出格式**: 同时提供目录和ZIP文件两种格式
- **嵌套目录结构**: 外层时间戳目录 → notion-import子目录 → Notion文件

### ✅ 支持的转换

| LogSeq格式 | Notion格式 | 说明 |
|------------|------------|------|
| `[[页面链接]]` | `[页面链接](文件名.md)` | 页面间链接 |
| `- DONE 任务` | `- [x] 任务` | 已完成任务 |
| `- TODO 任务` | `- [ ] 任务` | 待办任务 |
| `![图片](路径)` | `![图片](新路径)` | 图片引用 |
| `property:: value` | `**property**: value` | 页面属性 |
| `#标签` | `#标签` | 标签保持不变 |

### 🔄 文件结构转换

**LogSeq结构:**
```
logseq-export/
├── project-a/                   # 第一个笔记集
│   ├── pages/
│   │   ├── 页面1.md
│   │   └── 页面2.md
│   ├── journals/
│   │   ├── 2025_01_01.md
│   │   └── 2025_01_02.md
│   └── assets/
│       └── 图片.jpg
└── personal-notes/              # 第二个笔记集
    ├── pages/
    │   └── 笔记.md
    └── journals/
        └── 2025_01_03.md
```

**Notion结构:**
```
# 默认格式（无UUID，文件名简洁）
notion-import/
├── project-a-20250718-143022/           # 第一个笔记集转换结果
│   ├── notion-import/                   # Notion导入目录
│   │   ├── 页面1.md
│   │   ├── 页面2.md
│   │   ├── 2025年01月01日.md
│   │   ├── 2025年01月02日.md
│   │   ├── assets/
│   │   │   └── 图片.jpg
│   │   └── conversion_report.json
│   └── project-a-20250718-143022.zip   # 自动生成的ZIP包
└── personal-notes-20250718-143156/      # 第二个笔记集转换结果
    ├── notion-import/
    │   ├── 笔记.md
    │   ├── 2025年01月03日.md
    │   └── conversion_report.json
    └── personal-notes-20250718-143156.zip

# 带UUID格式（--with-uuid参数）
notion-import/
├── project-a-20250718-143022/
│   ├── notion-import/
│   │   ├── 页面1 a1b2c3d4.md
│   │   ├── 页面2 e5f6g7h8.md
│   │   ├── 2025年01月01日 i9j0k1l2.md
│   │   ├── 2025年01月02日 m3n4o5p6.md
│   │   └── conversion_report.json
│   └── project-a-20250718-143022.zip
└── personal-notes-20250718-143156/
    ├── notion-import/
    │   ├── 笔记 x9y8z7w6.md
    │   ├── 2025年01月03日 v5u4t3s2.md
    │   └── conversion_report.json
    └── personal-notes-20250718-143156.zip
```

## ⚠️ 注意事项

### 部分支持的功能
- **块引用** `(((block-id)))` → 转换为 `> [引用块]`
- **查询语法** `{{query}}` → 转换为 `<!-- LogSeq查询已移除 -->`
- **命名空间** `ns/page` → 保持原文件名

### 建议处理方式
1. **重要的查询** - 在转换前手动记录
2. **复杂的块引用** - 考虑转换为直接链接
3. **特殊属性** - 转换后检查是否需要手动调整

## 🔧 自定义配置

### UUID生成选项

**默认模式（推荐）**：
- 文件名简洁易读：`页面名.md`
- 更好的可读性和管理性
- 如果存在同名页面可能会有冲突

**UUID模式（`--with-uuid`）**：
- 文件名包含唯一标识符：`页面名 a1b2c3d4.md`
- 确保文件名唯一，避免冲突
- 文件名较长，可读性稍差

### 代码自定义

你可以修改 `logseq_to_notion_converter.py` 中的以下方法来自定义转换：

- `convert_logseq_syntax()` - 修改语法转换规则
- `create_page_hierarchy()` - 自定义页面层级结构
- `convert_links()` - 调整链接转换逻辑

## 📊 转换报告

转换完成后会生成 `conversion_report.json`，包含：
- 转换的页面映射关系
- 资源文件处理情况
- 详细的转换日志
- 潜在问题和警告

## 🐛 故障排除

### 常见问题

**Q: 链接无法正确转换**
A: 检查页面名称是否包含特殊字符，工具会自动清理文件名

**Q: 图片无法显示**
A: 确保图片在assets目录中，并检查转换报告中的资源映射

**Q: 中文页面名称问题**
A: 工具支持UTF-8编码，确保文件系统支持中文文件名

### 调试模式
转换过程中的所有日志都会显示在控制台，如遇问题可查看详细日志。

## 📝 示例转换结果

**LogSeq原文:**
```markdown
# 我的笔记

这是一个[[重要页面]]的链接。

- TODO 需要完成的任务
- DONE 已完成的任务

property:: 这是一个属性

![图片描述](../assets/image.jpg)
```

**Notion转换后（默认模式）:**
```markdown
# 我的笔记

这是一个[重要页面](重要页面.md)的链接。

- [ ] 需要完成的任务
- [x] 已完成的任务

**property**: 这是一个属性

![图片描述](image.jpg)
```

**Notion转换后（UUID模式）:**
```markdown
# 我的笔记

这是一个[重要页面](重要页面%20a1b2c3d4.md)的链接。

- [ ] 需要完成的任务
- [x] 已完成的任务

**property**: 这是一个属性

![图片描述](image.jpg)
```

## 📁 目录管理特性

### 🗂️ 多笔记集支持
- **集中管理**: 所有LogSeq导出统一放在 `logseq-export/` 下
- **隔离转换**: 每个笔记集转换后有独立的输出目录
- **时间戳标识**: 自动为每次转换生成时间戳，避免覆盖历史结果
- **批量处理**: 支持一键转换所有笔记集
- **自动打包**: 每次转换自动生成ZIP压缩包，便于分享和备份

### 🕐 版本管理
转换结果目录命名格式：`笔记集名称-YYYYMMDD-HHMMSS`

例如：
- `my-notes-20250718-143022/` - 2025年7月18日14:30:22的转换结果
  - `notion-import/` - Notion导入目录
  - `my-notes-20250718-143022.zip` - 压缩包

这样可以：
- 保留历史转换记录
- 对比不同时间的转换结果  
- 避免意外覆盖重要文件
- 方便文件传输和备份

## 🛠️ 高级使用

### 迁移工作流建议

1. **初次设置**:
   ```bash
   # 创建目录结构
   mkdir logseq-export notion-import
   
   # 将LogSeq导出放置到对应目录
   # logseq-export/project-name/
   ```

2. **单次转换**:
   ```bash
   # 查看可用导出
   python logseq_to_notion_converter.py logseq-export notion-import --list
   
   # 转换指定项目
   python logseq_to_notion_converter.py logseq-export notion-import -s project-name
   ```

3. **批量迁移**:
   ```bash
   # 转换所有项目
   python logseq_to_notion_converter.py logseq-export notion-import --all
   ```

4. **Notion导入**:
   - 在Notion中为每个项目创建独立的工作区或页面
   - 可以使用ZIP文件或直接使用notion-import目录导入
   - 推荐使用ZIP文件：解压后导入，保持文件结构完整

## 🤝 贡献

欢迎提交问题和改进建议！主要改进方向：
- 更智能的层级结构识别
- 更完整的LogSeq语法支持
- 增强的批量处理功能
- 错误恢复和断点续传机制 