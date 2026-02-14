# 分步执行指南

为了定位 "column project_id does not exist" 错误的具体位置，请按以下步骤执行：

## 步骤1: 创建基础表（不包含project_id）

```sql
-- 1. 创建用户资料表
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY,
    username VARCHAR(50) UNIQUE,
    display_name VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. 创建项目表
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

执行后检查是否成功。

## 步骤2: 创建包含project_id的表

```sql
-- 创建user_sessions表
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    session_id VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

如果这一步出错，说明问题在表创建阶段。

## 步骤3: 创建索引

```sql
-- 为project_id创建索引
CREATE INDEX IF NOT EXISTS idx_user_sessions_project_id ON user_sessions(project_id);
```

如果这一步出错，说明问题在索引创建阶段。

## 步骤4: 测试视图

```sql
-- 创建简单测试视图
CREATE OR REPLACE VIEW test_view AS
SELECT 
    p.id,
    p.name,
    COUNT(us.id) as session_count
FROM projects p
LEFT JOIN user_sessions us ON p.id = us.project_id
GROUP BY p.id, p.name;
```

如果这一步出错，说明问题在视图创建阶段。

## 步骤5: 测试函数

```sql
-- 创建简单测试函数
CREATE OR REPLACE FUNCTION test_function(project_uuid UUID)
RETURNS INTEGER AS $$
BEGIN
    RETURN (SELECT COUNT(*) FROM user_sessions WHERE project_id = project_uuid);
END;
$$ LANGUAGE plpgsql;
```

如果这一步出错，说明问题在函数创建阶段。

## 诊断建议

请告诉我在哪一步出现错误，我可以针对性地修复问题。
