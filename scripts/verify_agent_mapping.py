#!/usr/bin/env python3
"""
Agent映射验证脚本
=================

验证前端Agent配置与后端API路由的一致性
确保点击某个Agent时调用的是正确的Agent，不会误调其他Agent
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import re
from typing import Dict, List, Tuple


def extract_frontend_agents() -> List[Dict]:
    """从前端agents.ts提取Agent配置"""
    agents_file = Path(__file__).parent.parent / "frontend/src/config/agents.ts"

    with open(agents_file, 'r', encoding='utf-8') as f:
        content = f.read()

    agents = []

    # 逐行解析，找到每个agent的配置
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 检查是否是agent配置的开始
        if line.startswith('{'):
            agent_config = {}
            j = i

            # 向下查找配置项，直到遇到 }
            while j < len(lines):
                current_line = lines[j].strip()

                # 提取id
                if 'id:' in current_line:
                    match = re.search(r'id:\s*["\']([^"\']+)["\']', current_line)
                    if match:
                        agent_config['id'] = match.group(1)

                # 提取name
                elif 'name:' in current_line and 'displayName' not in current_line:
                    match = re.search(r'name:\s*["\']([^"\']+)["\']', current_line)
                    if match:
                        agent_config['name'] = match.group(1)

                # 提取displayName
                elif 'displayName:' in current_line:
                    match = re.search(r'displayName:\s*["\']([^"\']+)["\']', current_line)
                    if match:
                        agent_config['display_name'] = match.group(1)

                # 提取apiEndpoint
                elif 'apiEndpoint:' in current_line:
                    match = re.search(r'apiEndpoint:\s*["\']([^"\']+)["\']', current_line)
                    if match:
                        agent_config['api_endpoint'] = match.group(1)

                # 检查是否到达agent配置的结束
                if current_line.startswith('}') and 'id' in agent_config and 'api_endpoint' in agent_config:
                    # 确保有必需的字段
                    if 'display_name' not in agent_config:
                        agent_config['display_name'] = agent_config.get('name', '')
                    agents.append(agent_config)
                    i = j
                    break

                j += 1

        i += 1

    return agents


def extract_backend_endpoints() -> Dict[str, str]:
    """从后端api_routes.py提取端点到Agent的映射"""
    routes_file = Path(__file__).parent.parent / "apis/core/api_routes.py"

    with open(routes_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找所有路由定义和对应的agent
    endpoint_to_agent = {}

    # 模式: 匹配 @router.post 后跟 agent = get_xxx_agent()
    # 使用更简单的模式，避免复杂的正则表达式
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]

        # 检查是否是路由定义
        if '@router.post' in line or '@router.get' in line:
            # 提取端点路径
            match = re.search(r'@router\.(?:post|get)\(["\']([^"\']+)["\']', line)
            if match:
                endpoint = match.group(1)

                # 向下查找是否有agent调用
                for j in range(i, min(i + 50, len(lines))):
                    if 'agent = get_' in lines[j] and '_agent()' in lines[j]:
                        agent_match = re.search(r'agent = (get_\w+_agent)\(\)', lines[j])
                        if agent_match:
                            endpoint_to_agent[endpoint] = agent_match.group(1)
                            break
        i += 1

    return endpoint_to_agent


def extract_backend_agent_list() -> List[Dict]:
    """从后端AGENTS_LIST_CONFIG提取配置"""
    routes_file = Path(__file__).parent.parent / "apis/core/api_routes.py"

    with open(routes_file, 'r', encoding='utf-8') as f:
        content = f.read()

    agents = []

    # 找到AGENTS_LIST_CONFIG的开始和结束
    start_idx = content.find('AGENTS_LIST_CONFIG = [')
    if start_idx == -1:
        return []

    # 从开始位置查找对应的结束括号
    bracket_count = 0
    in_config = False
    end_idx = start_idx

    for i in range(start_idx, len(content)):
        if content[i] == '[':
            bracket_count += 1
            in_config = True
        elif content[i] == ']':
            bracket_count -= 1
            if bracket_count == 0 and in_config:
                end_idx = i
                break

    config_content = content[start_idx:end_idx + 1]

    # 逐行解析
    lines = config_content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 检查是否是agent配置的开始
        if line.startswith('{'):
            agent_config = {}
            j = i

            # 向下查找配置项，直到遇到 }
            while j < len(lines):
                current_line = lines[j].strip()

                # 提取id
                if '"id":' in current_line:
                    match = re.search(r'"id":\s*"([^"]+)"', current_line)
                    if match:
                        agent_config['id'] = match.group(1)

                # 提取name
                elif '"name":' in current_line:
                    match = re.search(r'"name":\s*"([^"]+)"', current_line)
                    if match:
                        agent_config['name'] = match.group(1)

                # 提取api_endpoint
                elif '"api_endpoint":' in current_line:
                    match = re.search(r'"api_endpoint":\s*"([^"]+)"', current_line)
                    if match:
                        agent_config['api_endpoint'] = match.group(1)

                # 检查是否到达agent配置的结束
                if current_line.startswith('}') and 'id' in agent_config and 'api_endpoint' in agent_config:
                    agents.append(agent_config)
                    i = j
                    break

                j += 1

        i += 1

    return agents


def verify_mapping():
    """验证Agent映射一致性"""
    print("=" * 80)
    print("Agent映射验证报告")
    print("=" * 80)

    # 提取数据
    frontend_agents = extract_frontend_agents()
    backend_config = extract_backend_agent_list()
    backend_endpoints = extract_backend_endpoints()

    # 构建查找字典
    frontend_by_id = {a["id"]: a for a in frontend_agents}
    backend_by_id = {a["id"]: a for a in backend_config}

    print(f"\n📊 统计信息:")
    print(f"  前端Agent数量: {len(frontend_agents)}")
    print(f"  后端配置数量: {len(backend_config)}")
    print(f"  后端端点数量: {len(backend_endpoints)}")

    # 1. 检查前端有的但后端配置没有的
    print(f"\n🔍 检查1: 前端Agent在后端配置中是否存在")
    missing_in_backend = []
    for fa in frontend_agents:
        if fa["id"] not in backend_by_id:
            missing_in_backend.append(fa)

    if missing_in_backend:
        print(f"  ❌ 发现{len(missing_in_backend)}个前端Agent在后端配置中缺失:")
        for agent in missing_in_backend:
            print(f"     - {agent['id']} ({agent['display_name']}) -> {agent['api_endpoint']}")
    else:
        print(f"  ✅ 所有前端Agent都在后端配置中存在")

    # 2. 检查后端配置有的但前端没有的
    print(f"\n🔍 检查2: 后端配置在前端Agent中是否存在")
    missing_in_frontend = []
    for ba in backend_config:
        if ba["id"] not in frontend_by_id:
            missing_in_frontend.append(ba)

    if missing_in_frontend:
        print(f"  ⚠️  发现{len(missing_in_frontend)}个后端Agent在前端配置中缺失:")
        for agent in missing_in_frontend:
            print(f"     - {agent['id']} ({agent['name']}) -> {agent['api_endpoint']}")
    else:
        print(f"  ✅ 所有后端Agent都在前端配置中存在")

    # 3. 检查API端点一致性
    print(f"\n🔍 检查3: 前后端API端点是否一致")
    endpoint_mismatches = []
    for fa in frontend_agents:
        ba = backend_by_id.get(fa["id"])
        if ba:
            # 标准化端点路径进行比较
            frontend_ep = fa["api_endpoint"].strip().strip('/')
            backend_ep = ba["api_endpoint"].strip().strip('/')

            if frontend_ep != backend_ep:
                endpoint_mismatches.append({
                    "id": fa["id"],
                    "name": fa["display_name"],
                    "frontend": fa["api_endpoint"],
                    "backend": ba["api_endpoint"]
                })

    if endpoint_mismatches:
        print(f"  ❌ 发现{len(endpoint_mismatches)}个端点不匹配:")
        for mm in endpoint_mismatches:
            print(f"     - {mm['id']} ({mm['name']})")
            print(f"       前端: {mm['frontend']}")
            print(f"       后端: {mm['backend']}")
    else:
        print(f"  ✅ 所有前后端API端点一致")

    # 4. 检查后端端点是否有对应的路由
    print(f"\n🔍 检查4: 后端API端点是否有对应的路由实现")
    missing_routes = []
    for ba in backend_config:
        endpoint = ba["api_endpoint"].strip().strip('/')
        if endpoint not in backend_endpoints:
            missing_routes.append({
                "id": ba["id"],
                "name": ba["name"],
                "endpoint": ba["api_endpoint"]
            })

    if missing_routes:
        print(f"  ❌ 发现{len(missing_routes)}个端点缺少路由实现:")
        for mr in missing_routes:
            print(f"     - {mr['id']} ({mr['name']}) -> {mr['endpoint']}")
    else:
        print(f"  ✅ 所有后端API端点都有路由实现")

    # 5. 详细Agent映射表
    print(f"\n📋 详细Agent映射表:")
    print("-" * 80)
    print(f"{'Agent ID':<35} {'前端端点':<40} {'后端端点':<40} {'状态':<10}")
    print("-" * 80)

    for fa in frontend_agents:
        ba = backend_by_id.get(fa["id"])
        if ba:
            has_route = fa["api_endpoint"].strip().strip('/') in backend_endpoints
            status = "✅" if has_route else "⚠️"
            print(f"{fa['id']:<35} {fa['api_endpoint']:<40} {ba['api_endpoint']:<40} {status:<10}")

    # 总结
    print("\n" + "=" * 80)
    print("总结")
    print("=" * 80)

    issues = len(missing_in_backend) + len(missing_in_frontend) + len(endpoint_mismatches) + len(missing_routes)

    if issues == 0:
        print("✅ 所有检查通过！前后端Agent映射完全一致。")
        return 0
    else:
        print(f"❌ 发现{issues}个问题需要修复:")
        if missing_in_backend:
            print(f"   - {len(missing_in_backend)}个前端Agent在后端缺失")
        if missing_in_frontend:
            print(f"   - {len(missing_in_frontend)}个后端Agent在前端缺失")
        if endpoint_mismatches:
            print(f"   - {len(endpoint_mismatches)}个端点不匹配")
        if missing_routes:
            print(f"   - {len(missing_routes)}个端点缺少路由")
        return 1


if __name__ == "__main__":
    exit_code = verify_mapping()
    sys.exit(exit_code)
