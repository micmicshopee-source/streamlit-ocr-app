# 产品需求文档 (PRD)
## 發票報帳小秘笈 Pro - 功能改进与反馈系统

**文档版本**: v1.0  
**创建日期**: 2026-01-26  
**产品经理**: AI Assistant  
**目标版本**: v1.3

---

## 📋 需求概述

### 需求1: 修复关键用户体验问题（P0）
### 需求2: 添加用户反馈/评论系统（新功能）

---

## 🎯 需求1: 修复关键用户体验问题

### 1.1 注册后自动登录

**问题描述**:
- 当前：用户注册成功后，需要手动切换到"登录"模式，再输入密码登录
- 影响：增加不必要的操作步骤，用户体验差

**需求**:
- 注册成功后，自动设置登录状态，直接进入主界面
- 无需用户手动切换模式

**技术实现**:
```python
# 在 register_user() 成功后
if success:
    st.session_state.authenticated = True
    st.session_state.user_email = email.strip()
    # 直接跳转，不需要提示切换模式
    st.rerun()
```

**验收标准**:
- ✅ 注册成功后直接进入主界面
- ✅ 无需手动切换登录模式

---

### 1.2 添加删除确认对话框

**问题描述**:
- 当前：点击"删除选中数据"按钮后立即删除，没有确认
- 影响：可能误删重要数据

**需求**:
- 删除前显示确认对话框
- 用户确认后才执行删除

**技术实现**:
```python
# 使用 st.dialog 或 st.confirm
if st.button("🗑️ 刪除選中數據"):
    # 检查是否有选中的数据
    if selected_count > 0:
        # 显示确认对话框
        if st.confirm(f"確定要刪除 {selected_count} 筆數據嗎？此操作無法復原。"):
            # 执行删除
```

**验收标准**:
- ✅ 删除前必须确认
- ✅ 确认对话框显示删除数量
- ✅ 取消操作不会删除数据

---

### 1.3 存储模式切换警告

**问题描述**:
- 当前：用户可以在数据库模式和内存模式之间切换，但切换时数据不会迁移
- 影响：可能导致数据丢失或数据混乱

**需求**:
- 切换模式前显示警告对话框
- 明确告知用户切换的后果
- 提供取消选项

**技术实现**:
```python
# 在存储模式选择处
if storage_mode != current_mode:
    if st.confirm("⚠️ 警告：切換存儲模式可能導致數據無法訪問。\n\n數據庫模式 → 內存模式：數據庫數據不會顯示\n內存模式 → 數據庫模式：內存數據不會保存\n\n確定要切換嗎？"):
        # 执行切换
    else:
        # 恢复原模式
```

**验收标准**:
- ✅ 切换前必须确认
- ✅ 警告信息清晰明确
- ✅ 用户可以取消操作

---

## 🎯 需求2: 用户反馈/评论系统

### 2.1 功能概述

**目标**:
- 允许用户提交反馈意见
- 所有用户都可以查看反馈
- 支持对反馈进行评论
- 支持点赞/有用标记

**用户价值**:
- 收集用户意见和建议
- 促进用户之间的交流
- 帮助产品改进

---

### 2.2 功能需求

#### 2.2.1 反馈提交
- 用户可以提交反馈（标题、内容、类型：bug/建议/其他）
- 反馈自动记录提交时间和用户邮箱
- 支持匿名反馈（可选）

#### 2.2.2 反馈列表
- 显示所有反馈（按时间倒序）
- 显示反馈标题、内容、提交者、时间、类型
- 显示评论数量和点赞数
- 支持筛选（按类型、按时间）

#### 2.2.3 评论功能
- 用户可以对反馈进行评论
- 显示评论者、评论时间、评论内容
- 支持对评论进行回复（可选，v1.0 暂不实现）

#### 2.2.4 点赞功能
- 用户可以对反馈点赞（标记为有用）
- 显示点赞数量
- 防止重复点赞（同一用户只能点赞一次）

---

### 2.3 数据库设计

**反馈表 (feedback)**:
```sql
CREATE TABLE feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    type TEXT NOT NULL,  -- 'bug', 'suggestion', 'other'
    is_anonymous INTEGER DEFAULT 0,  -- 0=显示用户, 1=匿名
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX idx_feedback_created ON feedback(created_at);
CREATE INDEX idx_feedback_type ON feedback(type);
```

**评论表 (feedback_comments)**:
```sql
CREATE TABLE feedback_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_id INTEGER NOT NULL,
    user_email TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (feedback_id) REFERENCES feedback(id) ON DELETE CASCADE
);

CREATE INDEX idx_comments_feedback ON feedback_comments(feedback_id);
```

**点赞表 (feedback_likes)**:
```sql
CREATE TABLE feedback_likes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_id INTEGER NOT NULL,
    user_email TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(feedback_id, user_email),  -- 防止重复点赞
    FOREIGN KEY (feedback_id) REFERENCES feedback(id) ON DELETE CASCADE
);

CREATE INDEX idx_likes_feedback ON feedback_likes(feedback_id);
```

---

### 2.4 UI/UX 设计

**位置**: 侧边栏或主界面底部添加"💬 反馈意见"按钮

**界面布局**:
1. **反馈列表页面**:
   - 顶部：筛选器（类型、排序）
   - 中间：反馈列表（卡片式布局）
   - 底部：提交反馈按钮

2. **反馈详情页面**:
   - 反馈内容
   - 评论列表
   - 评论输入框
   - 点赞按钮

3. **提交反馈对话框**:
   - 标题输入
   - 内容输入（多行文本）
   - 类型选择（单选）
   - 匿名选项（复选框）
   - 提交按钮

---

### 2.5 技术实现要点

1. **数据库初始化**: 在 `init_db()` 中添加反馈相关表
2. **数据隔离**: 反馈系统是公共的，所有用户都可以看到（不需要 user_email 过滤）
3. **权限控制**: 
   - 所有登录用户都可以查看和提交反馈
   - 用户可以编辑/删除自己的反馈（可选）
4. **UI组件**: 使用 Streamlit 的 dialog、expander 等组件

---

### 2.6 验收标准

- ✅ 用户可以提交反馈
- ✅ 所有用户可以看到反馈列表
- ✅ 用户可以对反馈进行评论
- ✅ 用户可以对反馈点赞
- ✅ 反馈按时间倒序显示
- ✅ 支持按类型筛选
- ✅ 防止重复点赞

---

## 📝 开发优先级

### Phase 1: 立即修复（本周）
1. ✅ 注册后自动登录
2. ✅ 添加删除确认
3. ✅ 存储模式切换警告

### Phase 2: 反馈系统（下周）
1. ✅ 数据库设计和初始化
2. ✅ 反馈提交功能
3. ✅ 反馈列表显示
4. ✅ 评论功能
5. ✅ 点赞功能

---

## 🎨 UI/UX 设计要求

### 反馈系统界面
- 使用深色主题，与系统整体风格一致
- 反馈卡片使用圆角、阴影，提升视觉层次
- 评论区域使用缩进，清晰显示层级关系
- 点赞按钮使用图标+数字，直观易用

### 交互设计
- 提交反馈使用对话框（dialog）
- 反馈列表使用可展开卡片（expander）
- 评论实时显示，无需刷新
- 操作反馈明确（成功/失败提示）

---

## 📊 数据统计需求（可选）

- 反馈总数
- 各类型反馈数量（bug/建议/其他）
- 最受欢迎的反馈（点赞数最多）
- 最近活跃的反馈（最新评论）

---

## 🔒 安全与隐私

1. **内容审核**: 考虑添加敏感词过滤（可选）
2. **用户隐私**: 匿名选项保护用户隐私
3. **数据清理**: 考虑添加反馈删除功能（管理员或作者）
4. **防刷机制**: 限制同一用户短时间内提交过多反馈（可选）

---

## 📈 后续优化（v1.4+）

1. 反馈状态管理（已处理/处理中/待处理）
2. 管理员回复功能
3. 反馈分类标签
4. 搜索功能
5. 反馈统计图表

---

**文档状态**: ✅ 待开发  
**开发负责人**: 待分配  
**预计完成时间**: 1-2周
