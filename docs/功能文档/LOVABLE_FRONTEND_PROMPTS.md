# 剧本创作Agent - Lovable 前端界面 Prompt 集合

> 项目：竖屏短剧策划助手 (Juben)
> 生成工具：Lovable.dev
> 设计风格：专业、现代、AI驱动

---

## 使用说明

### Lovable Prompting 最佳实践（基于官方文档）

1. **Plan before you prompt** - 先规划再提示
2. **Build by component** - 按组件逐步构建
3. **Use real content** - 使用真实内容，不用lorem ipsum
4. **Apply design buzzwords** - 使用设计术语定义风格
5. **Speak atomic** - 使用原子化UI术语（按钮、卡片、模态框等）
6. **Use prompt patterns** - 使用结构化的布局模式

### 设计风格定义

```
整体风格：专业、现代、AI驱动
色彩方案：深色主题，紫蓝渐变（AI感）
字体：Inter (英文) + 思源黑体 (中文)
氛围：Premium, Cinematic, Tech-forward
```

---

## 1. 登录/注册页面

### Prompt

```
Create a login and signup page for a professional AI script writing platform called "剧本策划助手" (Juben Script Planner).

Design Requirements:
- Style: Premium, cinematic, tech-forward with dark theme
- Use a gradient background with purple (#8B5CF6) to blue (#3B82F6) tones
- Add subtle animated particles or floating orbs in the background for AI feel
- Glassmorphism effect for the main card

Layout Structure:
- Center-aligned card with glassmorphism effect
- Left side: Brand section with logo, tagline, and feature highlights
- Right side: Auth form with tabs for "登录" (Login) and "注册" (Sign Up)

Login Form Fields:
1. Email input field with icon prefix
2. Password input field with show/hide toggle
3. "Remember me" checkbox
4. "Forgot password?" link
5. Primary CTA button: "立即登录" (Login Now) - full width, gradient background
6. Social login buttons: WeChat and Google (optional)

Signup Form Fields:
1. Name input field
2. Email input field
3. Password input field with strength indicator
4. Confirm password input field
5. Terms agreement checkbox
6. Primary CTA button: "创建账户" (Create Account)

Additional Elements:
- Bottom text: "还没有账户？立即注册" with link
- Trust badges at bottom: "企业级安全" | "数据加密" | "隐私保护"

Use Inter font for English, Source Han Sans for Chinese. Add smooth hover effects on buttons and inputs. Mobile responsive with stacked layout on small screens.
```

### 组件化构建Prompt

```
Create a glassmorphism card component for the login form with:
- Translucent white background (rgba(255,255,255,0.1))
- Blur effect (backdrop-filter: blur(20px))
- Rounded corners (24px)
- Subtle white border (1px solid rgba(255,255,255,0.2))
- Soft shadow (0 8px 32px rgba(0,0,0,0.3))

Add floating particle animation in the background:
- 5-7 circular orbs with gradient fills
- Slow floating animation (6-8s duration)
- Random positions and sizes (40-120px)
- Opacity: 0.3-0.6
```

---

## 2. 主仪表板 (Dashboard)

### Prompt

```
Create a main dashboard page for an AI script planning platform.

Design Style:
- Dark theme with purple-blue gradient accents
- Sidebar navigation (collapsed on mobile)
- Card-based content layout
- Clean, minimal, data-focused aesthetic

Layout Structure:
1. Left Sidebar (280px wide, collapsible):
   - Logo area with "剧本策划助手" branding
   - Navigation menu with icons:
     * 仪表板
     * 策划助手
     * 创作中心
     * 评估分析
     * 知识库
     * 项目管理
     * 设置
   - User profile section at bottom with avatar

2. Top Header (fixed height 64px):
   - Search bar with placeholder "搜索项目、剧本..."
   - Notification bell with badge count
   - Quick action button: "新建项目" (primary CTA)
   - User avatar with dropdown menu

3. Main Content Area:
   Welcome section:
   - Greeting: "你好，[用户名]！今天想创作什么？"
   - Quick stats row (4 cards):
     * 进行中的项目: 12
     * 已完成的剧本: 48
     * 本月创作时长: 36小时
     * AI助手使用次数: 156

Recent Projects section:
- Grid of project cards (3 columns on desktop, 1 on mobile)
- Each card shows: thumbnail, title, progress bar, last edited time, tags
- Hover effect: card lifts with shadow, shows action buttons

AI Assistants quick access:
- Row of 4 assistant cards with icons:
  1. 策划专家 - 黄色主题
  2. 创作助手 - 紫色主题
  3. 评估分析师 - 蓝色主题
  4. 知识库搜索 - 绿色主题

Activity Feed section:
- List of recent activities with timestamps
- Icons for different activity types (created, edited, shared, etc.)
```

### 组件化构建Prompt

```
Create a project card component with:
- Rounded corners (16px)
- Dark background (#1E1E2E)
- Hover lift effect (transform: translateY(-4px))
- Progress bar with gradient fill
- Action buttons on hover: Edit, Share, Delete
- Tag badges for project types (短剧, 网剧, 电影)

Create a stat card component:
- Glassmorphism effect
- Icon in circle (gradient background)
- Large number display
- Label text in muted color
- Subtle glow effect on hover
```

---

## 3. 策划助手对话界面

### Prompt

```
Create an AI chat interface for script planning assistance.

Design Style:
- Chat-focused layout similar to Claude/ChatGPT
- Clean, distraction-free
- Dark theme with purple accents
- Smooth streaming text animation

Layout Structure:
1. Left Sidebar (260px, collapsible):
   - Back button to dashboard
   - Assistant info card:
     * Avatar with gradient border
     * Name: "策划专家"
     * Tagline: "基于爆款引擎理论的专业策划"
     * Status indicator (online)
   - Conversation history list
   - "新建对话" button

2. Main Chat Area:
   Top Bar:
   - Title: "剧本策划助手"
   - Model selector dropdown: "GLM-4.5 (推荐)" | "GPT-4o" | "Llama 3.3"
   - Settings button

   Messages Container (scrollable):
   - AI Welcome message with rich formatting:
     "你好！我是你的专业剧本策划助手，基于爆款引擎理论为你服务。

     我可以帮你：
     📊 分析市场趋势和热门题材
     💡 设计故事概念和核心冲突
     🎭 规划角色人设和关系网络
     📝 构建三幕式结构和情节点

     让我们开始创作吧！你有什么想法想聊？"

   - Message bubbles:
     * User messages: right-aligned, gradient background
     * AI messages: left-aligned, dark glassmorphism card
     * Typing indicator with animated dots
     * Timestamp on each message
     * Copy button on AI messages

3. Input Area (fixed at bottom):
   - Textarea with placeholder "描述你想创作的剧本..." (auto-expand)
   - Attachment buttons: File, Image, URL
   - Knowledge base toggle: "启用知识库检索"
   - Web search toggle: "启用网络搜索"
   - Send button (right-aligned, prominent)

4. Right Panel (320px, optional/toggleable):
   - Context panel showing:
     * Session notes created during conversation
     * Reference materials cited
     * Related suggestions
     * Export options (Markdown, PDF, DOCX)

Interactive Features:
- Streaming text response animation
- Message reactions (👍 ❤️ 🤔)
- Branch conversation support
- Markdown rendering with syntax highlighting
- Code block copy button
```

### 组件化构建Prompt

```
Create a chat message bubble component:
- User message:
  * Gradient background (purple to blue)
  * White text
  * Rounded corners (18px, sharp on bottom-right)
  * Max width: 70%

- AI message:
  * Dark glassmorphism card
  * Light text (#E5E7EB)
  * Rounded corners (18px, sharp on bottom-left)
  * Subtle border (1px solid rgba(139, 92, 246, 0.3))
  * Copy button in top-right corner (appears on hover)

Create a streaming text animation component:
- Cursor blink effect at end of text
- Smooth character-by-character reveal
- Fade-in effect for complete paragraphs
```

---

## 4. 剧本编辑器界面

### Prompt

```
Create a professional script editor interface for writing drama scripts.

Design Style:
- Writer-focused, distraction-free
- Monospace font for script content
- Traditional screenplay formatting
- Dark theme with easy-on-eyes colors

Layout Structure:
1. Top Toolbar (fixed, 48px height):
   - Back button with project title
   - Save status indicator (saved/saving/unsaved)
   - Undo/Redo buttons
   - Export dropdown: PDF | DOCX | TXT | FDX
   - Share button
   - AI Assistant toggle button

2. Left Sidebar (optional, 280px):
   - Scene navigator (tree view):
     * Act 1: 开端
       - Scene 1: 咖啡厅 - 日
       - Scene 2: 街道 - 夜
     * Act 2: 发展
       - Scene 3: 公寓 - 夜
   - Character list with avatars:
     * 主角头像 + 姓名
     * 配角头像 + 姓名
   - Quick notes section

3. Main Editor Area:
   - Script content in screenplay format:
     * Scene headings (Sluglines): INT. LOCATION - DAY
     * Action descriptions
     * Character names (centered)
     * Dialogue (centered under character)
     * Parentheticals
     * Transitions (CUT TO:, DISSOLVE TO:)

   - Formatting toolbar (floating or fixed):
     * Scene heading
     * Action
     * Character
     * Dialogue
     * Parenthetical
     * Transition

   - Line numbers (toggleable)
   - Page break indicators
   - Estimated runtime display

4. Right Panel (AI Assistant, 320px):
   - Tabbed interface:

     Tab 1: AI助手
     - Quick actions:
       * 续写对话
       * 生成场景描述
       * 优化台词
       * 检查格式
     - Prompt input area
     - AI response display

     Tab 2: 评估
     - Overall score with circular progress
     - Dimension scores:
       * 情绪价值: 8.5/10
       * 冲突强度: 7.8/10
       * 人物塑造: 9.2/10
     - Improvement suggestions

     Tab 3: 参考
     - Knowledge base snippets
     - Similar scenes from database
     - Character consistency notes

Keyboard Shortcuts panel (toggleable):
- Tab: Indent dialogue
- Enter: New element
- Ctrl/Cmd + K: Insert character
- Ctrl/Cmd + S: Save
- Ctrl/Cmd + /: Comment
```

### 组件化构建Prompt

```
Create a screenplay-formatted text component:
- Monospace font (Courier Prime or similar)
- Scene heading: Bold, uppercase, #FF6B6B color
- Action: Regular, #E5E7EB color, left-aligned
- Character name: Bold, uppercase, centered, #4ECDC4 color
- Dialogue: Regular, centered, #E5E7EB color
- Parenthetical: Italic, #95A5A6 color

Create a scene card component for the navigator:
- Compact card (200px width)
- Scene number badge
- Location name (truncated)
- Time of day indicator (Day/Night)
- Duration estimate
- Character count
- Edit and delete buttons on hover
```

---

## 5. 评估分析界面

### Prompt

```
Create a comprehensive script evaluation and analysis dashboard.

Design Style:
- Data-driven, analytical
- Professional, report-style
- Visualizations and charts
- Dark theme with color-coded metrics

Layout Structure:
1. Top Bar:
   - Breadcrumb: 评估 > 项目名称
   - Evaluation date
   - Export report button (PDF)
   - Share button
   - Start new evaluation button

2. Overview Section (top):
   - Large circular progress indicator:
     * Overall score: 8.7/10
     * Color-coded: Green (8-10), Yellow (6-7.9), Red (<6)
     * Label: "强烈关注" (Strongly Recommended)
   - Quick stats row:
     * 评估轮次: 第3次
     * 评估时间: 2025-01-15 14:32
     * 评估模型: GLM-4.5
     * 字数统计: 45,678字

3. Dimensions Grid (6 cards in 2x3 layout):
   Each dimension card shows:
   - Icon and dimension name
   - Score with circular progress
   - Score bar (colored based on score)
   - Trend indicator (↑↓ compared to last evaluation)
   - Brief comment snippet

   Dimensions:
   1. 故事概念 - 8.5/10
   2. 故事设计 - 8.2/10
   3. 主题立意 - 7.8/10
   4. 故事情境 - 9.0/10
   5. 人物设定 - 8.8/10
   6. 人物关系 - 8.4/10
   7. 情节桥段 - 8.6/10
   8. 商业价值 - 9.2/10

4. Detailed Analysis Section (tabbed):

   Tab 1: 评分详情
   - Radar chart showing all dimensions
   - Historical comparison (line chart)
   - Score distribution histogram
   - Dimension correlation matrix

   Tab 2: 优势分析
   - List of strengths with icons:
     * ✓ "黄金三秒钩子设计出色"
     * ✓ "人物人设鲜明，有记忆点"
     * ✓ "商业化卡点设置精准"
   - Evidence snippets from script
   - Similar successful case references

   Tab 3: 改进建议
   - List of improvement areas:
     * ! "第二幕节奏稍显拖沓"
     * ! "配角动机不够清晰"
     * ! "结尾可以更震撼"
   - Specific suggestions with examples
   - Before/After comparison
   - AI-generated revision suggestions

   Tab 4: 评估历史
   - Timeline of all evaluations
   - Score evolution chart
   - Major version changes highlighted
   - Comments and notes for each version

5. Action Panel (bottom or side):
   - "接受建议并修改" button
   - "开始新的评估" button
   - "导出完整报告" button
   - "对比不同版本" button

Interactive Features:
- Click on dimension card to see detailed breakdown
- Hover over score to see explanation
- Filter evaluations by date range
- Compare two evaluations side-by-side
```

### 组件化构建Prompt

```
Create a dimension score card component:
- Dark card background (#1E1E2E)
- Rounded corners (12px)
- Icon in colored circle (40px)
- Dimension name in bold
- Large score number with one decimal
- Circular progress bar (stroke-dasharray animation)
- Mini bar chart showing historical trend
- Expandable: click to see detailed analysis

Create a radar chart component:
- 8-axis radar chart
- Semi-transparent fill (rgba(139, 92, 246, 0.2))
- Colored stroke (#8B5CF6)
- Data points as circles
- Labels for each dimension
- Comparison overlay for previous evaluation
- Tooltip on hover showing exact values
```

---

## 6. 创作工作流编辑器

### Prompt

```
Create a visual workflow editor for script creation pipelines.

Design Style:
- Node-based editor (like Node-RED or ComfyUI)
- Professional, technical aesthetic
- Dark theme with colorful node types
- Canvas-based, zoomable interface

Layout Structure:
1. Top Toolbar:
   - Workflow name with edit button
   - Save workflow button
   - Run workflow button (with play icon)
   - Stop button
   - Export/Import workflow
   - Template dropdown
   - Zoom controls (- 100% +)
   - Fit to screen button

2. Left Sidebar (Node Palette, 240px):
   - Search input: "搜索节点..."
   - Collapsible node categories:

     输入节点:
     - 故事大纲 (Story Outline)
     - 角色设定 (Character Setup)
     - 创意概念 (Concept)

     处理节点:
     - 大情节点生成
     - 详细情节点 (Detailed Plot Points)
     - 对话创作 (Dialogue Writer)
     - 场景描述 (Scene Description)
     - 角色关系分析 (Relationship Analyzer)

     分析节点:
     - 故事评估 (Story Evaluation)
     - 商业价值分析 (Commercial Analysis)
     - 市场趋势分析 (Market Trends)
     - IP价值评估 (IP Value)

     输出节点:
     - 导出剧本 (Export Script)
     - 生成报告 (Generate Report)
     - 保存到项目 (Save to Project)

     工具节点:
     - 知识库检索 (Knowledge Search)
     - 网络搜索 (Web Search)
     - 文本合并 (Text Merge)
     - 条件分支 (Conditional)
     - 循环 (Loop)

3. Main Canvas Area:
   - Infinite canvas with grid background
   - Nodes as cards with:
     * Header with icon and title
     * Input ports on left (circles)
     * Output ports on right (circles)
     * Status indicator (idle, running, completed, error)
     * Mini settings button
     * Delete button (appears on hover)

   - Connections (Bezier curves):
     * Animated gradient when active
     * Data flow arrows
     * Connection points snap to ports

   - Node types with color coding:
     * Input: Green (#10B981)
     * Process: Blue (#3B82F6)
     * Analysis: Purple (#8B5CF6)
     * Output: Orange (#F59E0B)
     * Tool: Gray (#6B7280)

   - Canvas controls:
     * Pan (middle mouse or space+drag)
     * Zoom (scroll wheel)
     * Multi-select (shift+click)
     * Delete selected (delete key)
     * Duplicate (ctrl+d)
     * Undo/Redo (ctrl+z/ctrl+shift+z)

4. Right Panel (Node Settings, 300px):
   - Shows when a node is selected
   - Node configuration form:
     * Name input field
     * Description textarea
     * Parameters (varies by node type)
     * Model selector
     * Temperature slider (for AI nodes)
     * Advanced settings toggle

   - Execution info:
     * Status indicator
     * Progress bar
     * Execution time
     * Input/output preview
     * Error messages (if any)

5. Bottom Panel (Execution Log, 200px height, collapsible):
   - Timeline of executed nodes
   - Each execution shows:
     * Node name
     * Start time
     * Duration
     * Status icon
     * Expandable to see details

Interactive Features:
- Drag nodes from palette to canvas
- Connect nodes by dragging from output to input port
- Double-click node to open settings
- Right-click for context menu (duplicate, delete, lock, etc.)
- Group selection with rectangle
- Mini-map for navigation
- Auto-layout button
- Validate workflow button
```

### 组件化构建Prompt

```
Create a workflow node card component:
- Rounded corners (8px)
- Gradient header (based on node type)
- White node icon (24px) in header
- Title text (bold, truncate)
- Status dot in corner (color: gray/yellow/green/red)
- Body: parameter preview (2-3 lines, truncated)
- Input ports (left side):
  * 5 circular ports vertically aligned
  * Hover effect: expand to show label
- Output ports (right side):
  * 3 circular ports vertically aligned
  * Hover effect: expand to show label
- Shadow: 0 4px 12px rgba(0,0,0,0.3)
- Hover: lift + increased shadow

Create a connection line component:
- Bezier curve (cubic-bezier)
- Gradient stroke (purple to blue)
- Animated dash array when active (flow effect)
- Arrow at end
- Highlight on hover
- Glow effect for active connections
```

---

## 7. 知识库管理界面

### Prompt

```
Create a knowledge base management interface for script resources.

Design Style:
- Content-focused, searchable
- Card-based grid layout
- Organized, clutter-free
- Warm accent colors

Layout Structure:
1. Top Bar:
   - Title: "知识库"
   - Search bar (large, prominent): "搜索桥段、情节、模板..."
   - Filter dropdown: 全部 | 剧本桥段 | 高能情节 | 创作模板 | 人物设定
   - Sort dropdown: 最新 | 最热 | 相关度
   - View toggle: Grid | List
   - Upload button (primary CTA)
   - Import button

2. Left Sidebar (Filters, 240px):
   - Category tree:
     * 剧本桥段 (2,345)
       - 开场钩子 (456)
       - 冲突爆发 (789)
       - 情绪高潮 (567)
       - 结尾反转 (533)
     * 高能情节 (1,234)
       - 打脸爽点 (345)
       - 身份曝光 (456)
       - 误会解除 (433)
     * 创作模板 (987)
       - 三幕式结构 (234)
       - 人物小传 (321)
       - 场景大纲 (432)

   - Tag cloud:
     * #战神归来 (234)
     * #豪门恩怨 (189)
     * #甜宠 (345)
     * #复仇 (278)
     * #穿越 (156)

   - Source filter:
     * Checkbox: 平台数据
     * Checkbox: 用户上传
     * Checkbox: AI生成

3. Main Content Area:
   - Stats bar:
     * 总条目: 4,566
     * 本月新增: 234
     * 热门标签: 战神归来

   - Content grid (3 columns):
     Each card shows:
     - Thumbnail or icon
     - Title (truncate to 2 lines)
     - Category badge
     - Tags (max 3 visible, +N more)
     - Preview text (3 lines, ellipsis)
     - Metadata row:
       * View count
       * Use count
       * Upload date
     - Action buttons on hover:
       * View
       * Edit
       * Add to project
       * Delete

   - Selected item detail panel (slide-in from right):
     - Full content display
     - Rich formatting
     - Related items
     - Usage history
     - Edit button
     - Delete button

4. Upload Modal (triggered by upload button):
   - Drag-drop zone with dashed border
   - File input button
   - Paste text option
   - Form fields:
     * Title (required)
     * Category (dropdown)
     * Tags (multi-select)
     * Content (textarea with rich text editor)
   - Submit button

5. Batch Actions Bar (appears when items selected):
   - "已选择 N 项"
   - Add to project button
   - Export button
   - Delete button
   - Clear selection button

Interactive Features:
- Real-time search with debouncing
- Multi-select with checkboxes
- Bulk actions
- Drag to reorder
- Infinite scroll or pagination
- Quick preview on hover
```

### 组件化构建Prompt

```
Create a knowledge base card component:
- White/off-white background (dark mode: #252535)
- Rounded corners (12px)
- Subtle border
- Category badge at top-left (colored by category)
- Icon or thumbnail (80x80px, rounded)
- Title: bold, truncate to 2 lines
- Tags: small pills, max 3 visible
- Preview text: muted color, 3 lines
- Metadata row: small icons with numbers
- Hover effect: slight lift + shadow
- Action buttons: fade in on hover

Create a tag pill component:
- Small, rounded-full
- Background color (by tag category)
- Light text
- Close button on hover
- Click to select (shows checkmark)
```

---

## 8. 项目管理界面

### Prompt

```
Create a project management interface for organizing script projects.

Design Style:
- Organized, table-based
- Professional, business-like
- Clean, data-dense
- Status-color-coded

Layout Structure:
1. Top Bar:
   - Title: "项目管理"
   - Search bar: "搜索项目..."
   - View toggle: List | Kanban | Calendar
   - Filter button
   - Sort dropdown
   - "新建项目" button (primary CTA)

2. Filter Panel (expandable below top bar):
   - Status checkboxes:
     * 进行中 (In Progress)
     * 已完成 (Completed)
     * 已暂停 (Paused)
     * 已归档 (Archived)
   - Type checkboxes:
     * 竖屏短剧
     * 网络剧
     * 电影
     * 微短剧
   - Date range picker
   - Assignee dropdown
   - Clear all filters button

3. Main Content Area (List View):
   - Data table with columns:
     1. Project name (with thumbnail)
     2. Type badge
     3. Progress bar (visual + percentage)
     4. Status badge
     5. Assignee (avatar)
     6. Last edited (relative time)
     7. Actions button (kebab menu)

   - Table features:
     * Sort by column (click header)
     * Filter in column
     * Select rows (checkboxes)
     * Pagination
     * Infinite scroll option

4. Main Content Area (Kanban View):
   - Columns (drag-drop):
     * 💡 构思阶段
     * 📝 策划中
     * ✍️ 创作中
     * 📊 评估中
     * ✅ 已完成

   - Cards in columns:
     * Project title
     * Thumbnail
     * Tags
     * Assignee avatars
     * Due date badge
     * Progress indicator
     * Drag handle
     * Hover actions

5. Main Content Area (Calendar View):
   - Month calendar grid
   - Projects shown as events (bars spanning days)
   - Color-coded by project type
   - Milestone markers
   - Drag to reschedule

6. Project Detail Panel (slide-in from right, 400px):
   - Project header:
     * Thumbnail
     * Title
     * Type badge
     * Status badge (editable)
     * Actions: Edit, Delete, Archive

   - Progress section:
     * Overall progress bar
     * Stage breakdown (策划 | 创作 | 评估)
     * Completion percentage

   - Team section:
     * Assignee list with avatars
     * Add member button
     * Role indicators

   - Timeline section:
     * Vertical timeline
     * Milestone markers
     * Activity feed

   - Files section:
     * File list with icons
     * Upload button
     * Folder structure

   - Notes section:
     * Note cards
     * Add note button

Interactive Features:
- Drag-drop in Kanban view
- Multi-project selection
- Bulk actions (archive, delete, assign)
- Quick edit from table
- Context menu (right-click)
```

### 组件化构建Prompt

```
Create a project table row component:
- Border-bottom separator
- Hover background change
- Checkbox (left)
- Thumbnail + Name (first column)
- Type badge (small pill)
- Progress bar (full width of column)
- Status badge (colored)
- Avatar circle for assignee
- Relative time text
- Kebab menu button (right, appears on hover)

Create a Kanban card component:
- White/off-white background
- Rounded corners (8px)
- Subtle shadow
- Project thumbnail (top, full width)
- Title (bold, truncate)
- Tags row (small pills)
- Avatar row (overlap)
- Due date badge (bottom right, colored by urgency)
- Drag handle (left, 6 dots icon)
- Hover: lift + shadow increase
```

---

## 9. 设置页面

### Prompt

```
Create a comprehensive settings page for user preferences and configuration.

Design Style:
- Clean, organized
- Section-based layout
- Form controls
- Dark theme

Layout Structure:
1. Top Bar:
   - Title: "设置"
   - Breadcrumb: 首页 > 设置
   - Save button (top right)

2. Left Navigation (vertical tabs, 200px):
   - 个人资料
   - 账户安全
   - API密钥
   - 模型设置
   - 通知偏好
   - 界面主题
   - 导出数据
   - 团队管理

3. Main Content Area:

Section: 个人资料
- Avatar upload with preview (circular, 120px)
- Form fields:
  * Display name (input)
  * Username (input, read-only)
  * Email (input, verified badge)
  * Bio (textarea)
  * Location (input)
  * Website (input)
- Save button

Section: 账户安全
- Password change form:
  * Current password (password input)
  * New password (password input with strength indicator)
  * Confirm password (password input)
- Two-factor authentication:
  * Status: Enabled/Disabled
  * Setup button
  * QR code display
- Active sessions:
  * List of devices/locations
  - Current session indicator
  - Revoke button for each
- Account deletion:
  * Danger zone (red background)
  - Delete account button

Section: API密钥
- API key list (masked):
  * Key name
  * Created date
  * Last used
  * Actions: Copy, Revoke
- Create new key button
- Form:
  * Key name (input)
  * Permissions (checkboxes)
  * Expiration (date picker)
  * Create button

Section: 模型设置
- Model provider selection:
  * Radio cards for each provider:
    - Logo/icon
    - Provider name
    - Description
    - Recommended badge
- Model configuration:
  * Model dropdown (per provider)
  * Temperature slider (0-2, step 0.1)
  * Max tokens slider
  * Top P slider
- Advanced settings (collapsible):
  * System prompt (textarea)
  * Stop sequences (input tags)
  * Presence penalty slider
  * Frequency penalty slider

Section: 通知偏好
- Notification channels (toggles):
  * Email notifications
  * Push notifications
  * SMS notifications
  * Webhook notifications
- Notification types (checkboxes):
  * Project updates
  * AI responses complete
  * Team invitations
  * Weekly summary
  * Billing alerts
- Quiet hours:
  * Enable toggle
  * Start time (time picker)
  - End time (time picker)
  - Timezone dropdown

Section: 界面主题
- Theme selection:
  * Radio cards with preview:
    - 深色主题 (Dark) - selected
    - 浅色主题 (Light)
    - 跟随系统 (System)
- Accent color selection:
  * Color swatches (circles)
  * Purple (default)
  * Blue
  * Green
  * Orange
  * Pink
- Font size:
  * Radio buttons: Small | Medium | Large
- Language:
  * Dropdown: 简体中文 | English
- Dense mode toggle

Section: 导出数据
- Export options:
  * All projects (checkbox)
  * Chat history (checkbox)
  * Knowledge base (checkbox)
  * Settings (checkbox)
- Export formats:
  * JSON
  * CSV
  * PDF report
- Export button
- "Request data deletion" button (danger)

Section: 团队管理 (Pro feature)
- Team members list:
  - Avatar + Name
  - Role badge (Owner/Admin/Member)
  - Email
  - Last active
  - Actions: Change role, Remove
- Invite member button:
  - Email input
  - Role dropdown
  - Send invite button
- Pending invites:
  - Email
  - Role
  - Sent date
  - Cancel button
- Billing section:
  - Plan badge
  * Renew date
  * Upgrade button
```

### 组件化构建Prompt

```
Create a settings section component:
- Section header (h3) with separator
- Form group spacing (24px)
- Label above each input
- Input validation (red border + error message)
- Save button at bottom of each section
- Loading state during save

Create a toggle switch component:
- Rounded track (pill shape, 44px long, 24px high)
- Circle thumb (20px diameter)
- Off state: gray track
- On state: purple track with purple glow
- Smooth transition animation (200ms)
- Label text to right of switch

Create a radio card component:
- Bordered card (200px wide, 120px high)
- Radio input (hidden)
- Label area (clickable)
- Icon/preview image (top)
- Title (bold)
- Description (small, muted)
- Selected state: purple border + checkmark badge
- Hover: border + shadow
```

---

## 10. 移动端响应式适配

### Prompt

```
Create mobile-responsive adaptations for all pages.

General Mobile Principles:
- Hamburger menu for navigation
- Stacked layouts instead of grids
- Larger touch targets (44px minimum)
- Simplified information density
- Bottom navigation bar for main app

Mobile Navigation:
- Bottom tab bar (fixed):
  * Home icon
  * Projects icon
  * Create FAB (center, prominent)
  * Assistant icon
  * Profile icon
- Slide-in drawer menu
- Back gesture/button

Mobile Dashboard:
- Single column layout
- Scrollable horizontal cards for stats
- Vertical list for projects
- Quick access buttons at top
- Pull to refresh
- Infinite scroll

Mobile Chat:
- Full-screen chat interface
- Input area fixed at bottom
- Swipe gestures for message actions
- Quick action buttons above keyboard
- Image/attachment preview full-screen
- Voice input button

Mobile Editor:
- Full-screen writing mode
- Toolbar above keyboard
- Swipe to change scene/character
- Portrait-optimized formatting
- Auto-save indicator
- Word count in corner
```

---

## 通用设计系统

### Color Palette

```
Primary Colors:
- Primary: #8B5CF6 (Purple 500)
- Primary Light: #A78BFA (Purple 400)
- Primary Dark: #7C3AED (Purple 600)
- Secondary: #3B82F6 (Blue 500)

Accent Colors:
- Success: #10B981 (Green 500)
- Warning: #F59E0B (Amber 500)
- Error: #EF4444 (Red 500)
- Info: #06B6D4 (Cyan 500)

Neutral Colors (Dark Theme):
- Background: #0F0F1A (Darkest)
- Surface: #1E1E2E (Dark)
- Surface Light: #2A2A3C (Medium)
- Border: #3A3A4C (Light)
- Text Primary: #F5F5F7 (Lightest)
- Text Secondary: #A5A5B5 (Muted)
- Text Tertiary: #6B6B7B (Placeholder)
```

### Typography

```
Font Families:
- English: Inter, system-ui, sans-serif
- Chinese: Source Han Sans CN, Noto Sans SC, sans-serif
- Monospace: JetBrains Mono, Fira Code, monospace

Font Sizes:
- Display 1: 48px (H1, page titles)
- Display 2: 36px (H2, section titles)
- Display 3: 24px (H3, card titles)
- Body Large: 18px (important text)
- Body: 16px (default)
- Body Small: 14px (secondary)
- Caption: 12px (metadata)

Font Weights:
- Regular: 400
- Medium: 500
- Semibold: 600
- Bold: 700
```

### Spacing Scale

```
- 4px: xs (tight spacing)
- 8px: sm (compact)
- 12px: md (normal)
- 16px: lg (comfortable)
- 24px: xl (spacious)
- 32px: 2xl (sections)
- 48px: 3xl (containers)
```

### Border Radius

```
- 4px: sm (small elements)
- 8px: md (cards, buttons)
- 12px: lg (larger cards)
- 16px: xl (modals)
- 24px: 2xl (hero cards)
- 9999px: full (pills, badges)
```

### Shadows

```
- sm: 0 1px 2px rgba(0,0,0,0.2)
- md: 0 4px 6px rgba(0,0,0,0.3)
- lg: 0 10px 15px rgba(0,0,0,0.3)
- xl: 0 20px 25px rgba(0,0,0,0.3)
- glow: 0 0 20px rgba(139, 92, 246, 0.3)
```

---

## Lovable Prompting 技巧总结

### 关键设计术语 (Design Buzzwords)

在prompt中使用这些术语可以更好地控制输出风格：

| 术语 | 含义 | 适用场景 |
|------|------|----------|
| Premium | 高端品质 | 登录页、仪表板 |
| Cinematic | 电影感 | 编辑器、评估页 |
| Minimal | 极简主义 | 聊天界面 |
| Clean | 干净整洁 | 表单、设置 |
| Tech-forward | 科技前沿 | AI功能界面 |
| Professional | 专业商务 | 项目管理 |
| Expressive | 富有表现力 | 创作工具 |
| Calm | 平静舒适 | 知识库浏览 |
| Dark mode | 深色模式 | 全局主题 |
| Glassmorphism | 毛玻璃效果 | 卡片、面板 |

### 原子UI术语 (Atomic UI Terms)

精确描述UI元素：

```
- Button (按钮): Primary, Secondary, Ghost, Text
- Card (卡片): Basic, Elevated, Outlined
- Input (输入框): Text, Password, Email, Number
- Badge (徽章): Status, Category, Notification
- Avatar (头像): With status, Grouped
- Modal (模态框): Centered, Full-screen, Slide-over
- Dropdown (下拉菜单): Single select, Multi select
- Toggle (开关): Simple, With label
- Slider (滑块): Single value, Range
- Progress (进度条): Linear, Circular
- Tooltip (提示框): Hover, Click, Follow cursor
- Toast (通知提示): Success, Error, Warning, Info
```

### 布局模式 (Layout Patterns)

```
Header - Content - Footer模式:
"顶部是固定的导航栏，中间是可滚动的内容区，底部是操作栏"

Sidebar - Main模式:
"左侧是固定宽度的侧边栏导航，右侧是主内容区，全屏高度"

Centered Card模式:
"居中的卡片容器，最大宽度600px，上下留白，居中对齐"

Dashboard Grid模式:
"仪表板风格的网格布局，响应式列数，卡片间距24px"

Split View模式:
"左右分屏布局，左侧是列表，右侧是详情，可调整比例"

Nested Navigation模式:
"顶部主导航 > 左侧次级导航 > 内容区域，面包屑导航"
```

### 交互状态 (Interaction States)

```
Hover: 鼠标悬停状态
"鼠标悬停时卡片上浮4px，阴影增强"

Active: 激活状态
"点击时按钮缩小并渐变颜色"

Focus: 聚焦状态
"输入框获得焦点时显示紫色边框和发光效果"

Loading: 加载状态
"显示旋转的加载图标，文字变为'处理中...'"

Error: 错误状态
"输入框显示红色边框，下方显示错误提示文字"

Disabled: 禁用状态
"按钮变为灰色，不透明度50%，不可点击"

Empty: 空状态
"显示空状态插图和提示文字'暂无数据'"
```

---

## Sources

本prompt集合基于以下Lovable官方文档和资源：

- [The Lovable Prompting Bible](https://lovable.dev/blog/2025-01-16-lovable-prompting-handbook)
- [Prompt better in Lovable - Official Documentation](https://docs.lovable.dev/prompting/prompting-one)
- [Lovable Video Library - Tutorials & Guides](https://lovable.dev/videos)
- [Guides for Building Apps and Websites with AI](https://lovable.dev/guides)
- [Write Perfect Lovable Prompts: Zero to App in 2025 - YouTube](https://www.youtube.com/watch?v=Im2OxYhGPGg)
- [Vibe Coding on Lovable AI for Absolute Beginners - YouTube](https://www.youtube.com/watch?v=Rx9V3Ltiklw)
