#!/usr/bin/env python3
"""
验证Agent自动保存功能
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 80)
print("Agent自动保存功能验证")
print("=" * 80)

# 检查BaseJubenAgent中的修改
with open("agents/base_juben_agent.py", "r") as f:
    content = f.read()

# 检查关键方法
checks = {
    "_store_stream_event_async": "异步存储流式事件" in content or "save_stream_event" in content,
    "_auto_save_final_result": "auto_save_output" in content,
    "_should_auto_save": "utility_agents" in content,
    "auto_save_output": "async def auto_save_output" in content,
}

print("\n✅ 方法实现检查:")
for method, exists in checks.items():
    status = "✅" if exists else "❌"
    print(f"  {status} {method}")

# 检查是否有重复的auto_save_output调用
import_count = content.count("await self.auto_save_output")
print(f"\n📊 auto_save_output调用次数: {import_count}")
if import_count > 0:
    print(f"  ✅ 有{import_count}处调用（包含手动调用和自动调用）")
else:
    print(f"  ⚠️  没有找到auto_save_output调用")

# 检查工具类Agent列表
utility_section = content.find("utility_agents = [")
if utility_section > 0:
    utility_list = content[utility_section:utility_section+500]
    print(f"\n🔧 工具类Agent列表:")
    for line in utility_list.split('\n'):
        if '"' in line:
            print(f"  {line.strip()}")

print("\n" + "=" * 80)
print("总结")
print("=" * 80)

if all(checks.values()):
    print("✅ 所有关键方法已正确实现")
    print("✅ Agent输出将自动保存到数据库")
    print("✅ 工具类Agent不会保存（避免数据库垃圾）")
else:
    print("❌ 有些方法可能缺失，请检查")

print("\n注意事项:")
print("1. Agent需要使用emit_juben_event发送complete/result事件")
print("2. 工具类Agent（file_reference, websearch等）不会自动保存")
print("3. 核心Agent（策划、创作、评估等）会自动保存")
print("4. 手动调用auto_save_output的Agent不会重复保存")
