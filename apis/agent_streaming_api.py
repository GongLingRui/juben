"""
智能体流式API
提供智能体协作的流式展示功能
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from utils.storage_manager import JubenStorageManager
from utils.logger import JubenLogger
from agents.base_juben_agent import BaseJubenAgent
from agents.juben_orchestrator import JubenOrchestrator

# 创建路由器
router = APIRouter(prefix="/juben/agents", tags=["智能体流式API"])

# 全局变量
active_sessions: Dict[str, Dict] = {}
websocket_connections: Dict[str, List[WebSocket]] = {}
storage_manager = JubenStorageManager()
logger = JubenLogger("agent_streaming_api")

# 数据模型
class StartSessionRequest(BaseModel):
    projectId: str
    agents: List[str]
    title: str

class SendMessageRequest(BaseModel):
    sessionId: str
    message: str
    targetAgent: Optional[str] = None

class AgentStreamEvent(BaseModel):
    type: str
    data: Dict
    timestamp: str

class AgentMessage(BaseModel):
    id: str
    agentId: str
    agentName: str
    agentType: str
    content: str
    contentType: str  # thought, action, result, error, complete
    timestamp: str
    metadata: Optional[Dict] = None
    isStreaming: bool = False
    isComplete: bool = False

class AgentSession(BaseModel):
    id: str
    sessionId: str
    projectId: str
    title: str
    status: str  # idle, running, completed, error
    agents: List[str]
    messages: List[AgentMessage]
    startTime: str
    endTime: Optional[str] = None
    totalTokens: int = 0
    totalCost: float = 0.0

# 智能体配置
AGENT_CONFIGS = {
    'planner': {
        'name': '短剧策划智能体',
        'description': '负责短剧的整体策划和创意构思',
        'class': 'PlannerAgent'
    },
    'creator': {
        'name': '短剧创作智能体',
        'description': '负责具体的剧本创作和内容生成',
        'class': 'CreatorAgent'
    },
    'evaluation': {
        'name': '剧本评估智能体',
        'description': '负责剧本质量评估和改进建议',
        'class': 'EvaluationAgent'
    },
    'story-analysis': {
        'name': '故事五元素分析',
        'description': '分析故事的五元素结构',
        'class': 'StoryAnalysisAgent'
    },
    'character-profile-generator': {
        'name': '角色档案生成器',
        'description': '生成详细的角色档案和背景故事',
        'class': 'CharacterProfileGeneratorAgent'
    },
    'plot-points-workflow': {
        'name': '大情节点工作流',
        'description': '生成大情节点和详细情节点',
        'class': 'PlotPointsWorkflowAgent'
    },
    'drama-workflow': {
        'name': '戏剧工作流',
        'description': '完整的戏剧创作工作流',
        'class': 'DramaWorkflowAgent'
    }
}

async def broadcast_to_session(session_id: str, event: AgentStreamEvent):
    """向会话的所有WebSocket连接广播事件"""
    if session_id in websocket_connections:
        message = f"data: {event.json()}\n\n"
        disconnected = []
        
        for websocket in websocket_connections[session_id]:
            try:
                await websocket.send_text(message)
            except:
                disconnected.append(websocket)
        
        # 清理断开的连接
        for ws in disconnected:
            websocket_connections[session_id].remove(ws)

async def create_agent_message(
    agent_id: str,
    content: str,
    content_type: str,
    metadata: Optional[Dict] = None,
    is_streaming: bool = False
) -> AgentMessage:
    """创建智能体消息"""
    agent_config = AGENT_CONFIGS.get(agent_id, {
        'name': agent_id,
        'description': '未知智能体'
    })
    
    return AgentMessage(
        id=str(uuid.uuid4()),
        agentId=agent_id,
        agentName=agent_config['name'],
        agentType=agent_id,
        content=content,
        contentType=content_type,
        timestamp=datetime.now().isoformat(),
        metadata=metadata or {},
        isStreaming=is_streaming,
        isComplete=content_type == 'complete'
    )

async def simulate_agent_thinking(agent_id: str, session_id: str, duration: int = 2000):
    """模拟智能体思考过程"""
    # 发送思考开始事件
    thinking_message = await create_agent_message(
        agent_id, 
        "正在分析任务需求...", 
        "thought", 
        {"duration": duration}
    )
    
    await broadcast_to_session(session_id, AgentStreamEvent(
        type="message",
        data=thinking_message.dict(),
        timestamp=datetime.now().isoformat()
    ))
    
    # 模拟思考过程
    await asyncio.sleep(1)
    
    # 发送思考进展
    progress_message = await create_agent_message(
        agent_id,
        "正在制定执行计划...",
        "thought",
        {"progress": 50}
    )
    
    await broadcast_to_session(session_id, AgentStreamEvent(
        type="message",
        data=progress_message.dict(),
        timestamp=datetime.now().isoformat()
    ))
    
    await asyncio.sleep(1)
    
    # 发送思考完成
    complete_message = await create_agent_message(
        agent_id,
        "分析完成，开始执行任务...",
        "thought",
        {"progress": 100}
    )
    
    await broadcast_to_session(session_id, AgentStreamEvent(
        type="message",
        data=complete_message.dict(),
        timestamp=datetime.now().isoformat()
    ))

async def simulate_agent_execution(agent_id: str, session_id: str, task: str):
    """模拟智能体执行任务"""
    # 发送执行开始事件
    action_message = await create_agent_message(
        agent_id,
        f"开始执行任务: {task}",
        "action",
        {"task": task, "startTime": datetime.now().isoformat()}
    )
    
    await broadcast_to_session(session_id, AgentStreamEvent(
        type="message",
        data=action_message.dict(),
        timestamp=datetime.now().isoformat()
    ))
    
    # 模拟执行过程
    await asyncio.sleep(2)
    
    # 发送执行结果
    result_message = await create_agent_message(
        agent_id,
        f"任务执行完成: {task}\n\n这里是智能体 {AGENT_CONFIGS[agent_id]['name']} 的执行结果。",
        "result",
        {
            "task": task,
            "endTime": datetime.now().isoformat(),
            "tokensUsed": 150,
            "duration": 2000,
            "toolsUsed": ["analysis_tool", "generation_tool"],
            "confidence": 0.85
        }
    )
    
    await broadcast_to_session(session_id, AgentStreamEvent(
        type="message",
        data=result_message.dict(),
        timestamp=datetime.now().isoformat()
    ))
    
    # 发送完成消息
    complete_message = await create_agent_message(
        agent_id,
        "任务已完成，等待下一步指示。",
        "complete",
        {"completedAt": datetime.now().isoformat()}
    )
    
    await broadcast_to_session(session_id, AgentStreamEvent(
        type="message",
        data=complete_message.dict(),
        timestamp=datetime.now().isoformat()
    ))

async def run_agent_workflow(session_id: str, agents: List[str], task: str):
    """运行智能体协作工作流"""
    session = active_sessions.get(session_id)
    if not session:
        return
    
    try:
        # 更新会话状态
        session['status'] = 'running'
        await broadcast_to_session(session_id, AgentStreamEvent(
            type="session_update",
            data={"status": "running"},
            timestamp=datetime.now().isoformat()
        ))
        
        # 按顺序执行智能体任务
        for agent_id in agents:
            if agent_id in AGENT_CONFIGS:
                # 思考阶段
                await simulate_agent_thinking(agent_id, session_id)
                
                # 执行阶段
                await simulate_agent_execution(agent_id, session_id, f"智能体 {agent_id} 的任务")
                
                # 更新智能体状态
                await broadcast_to_session(session_id, AgentStreamEvent(
                    type="agent_status",
                    data={"agentId": agent_id, "status": "completed"},
                    timestamp=datetime.now().isoformat()
                ))
        
        # 会话完成
        session['status'] = 'completed'
        session['endTime'] = datetime.now().isoformat()
        
        await broadcast_to_session(session_id, AgentStreamEvent(
            type="complete",
            data={"endTime": session['endTime']},
            timestamp=datetime.now().isoformat()
        ))
        
    except Exception as e:
        logger.error(f"Agent workflow error: {e}")
        session['status'] = 'error'
        
        await broadcast_to_session(session_id, AgentStreamEvent(
            type="error",
            data={"message": str(e)},
            timestamp=datetime.now().isoformat()
        ))

@router.post("/start-session")
async def start_session(request: StartSessionRequest, background_tasks: BackgroundTasks):
    """启动智能体会话"""
    try:
        session_id = str(uuid.uuid4())
        
        # 创建会话
        session = {
            'id': session_id,
            'sessionId': session_id,
            'projectId': request.projectId,
            'title': request.title,
            'status': 'idle',
            'agents': request.agents,
            'messages': [],
            'startTime': datetime.now().isoformat(),
            'endTime': None,
            'totalTokens': 0,
            'totalCost': 0.0
        }
        
        active_sessions[session_id] = session
        
        # 发送会话开始事件
        await broadcast_to_session(session_id, AgentStreamEvent(
            type="session_start",
            data=session,
            timestamp=datetime.now().isoformat()
        ))
        
        # 启动后台工作流
        background_tasks.add_task(
            run_agent_workflow, 
            session_id, 
            request.agents, 
            f"协作任务: {request.title}"
        )
        
        return session
        
    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop-session/{session_id}")
async def stop_session(session_id: str):
    """停止智能体会话"""
    try:
        if session_id in active_sessions:
            session = active_sessions[session_id]
            session['status'] = 'completed'
            session['endTime'] = datetime.now().isoformat()
            
            await broadcast_to_session(session_id, AgentStreamEvent(
                type="complete",
                data={"endTime": session['endTime']},
                timestamp=datetime.now().isoformat()
            ))
            
            # 清理WebSocket连接
            if session_id in websocket_connections:
                for websocket in websocket_connections[session_id]:
                    await websocket.close()
                del websocket_connections[session_id]
            
            # 移除会话
            del active_sessions[session_id]
            
        return {"message": "Session stopped successfully"}
        
    except Exception as e:
        logger.error(f"Failed to stop session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send-message")
async def send_message(request: SendMessageRequest):
    """发送消息到智能体"""
    try:
        session_id = request.sessionId
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # 创建用户消息
        user_message = await create_agent_message(
            "user",
            request.message,
            "user_message",
            {"targetAgent": request.targetAgent}
        )
        
        await broadcast_to_session(session_id, AgentStreamEvent(
            type="message",
            data=user_message.dict(),
            timestamp=datetime.now().isoformat()
        ))
        
        # 如果指定了目标智能体，触发该智能体响应
        if request.targetAgent and request.targetAgent in AGENT_CONFIGS:
            # 模拟智能体响应
            await simulate_agent_thinking(request.targetAgent, session_id)
            await simulate_agent_execution(request.targetAgent, session_id, f"响应用户消息: {request.message}")
        
        return {"message": "Message sent successfully"}
        
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    """获取会话历史"""
    try:
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = active_sessions[session_id]
        return session['messages']
        
    except Exception as e:
        logger.error(f"Failed to get session history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/stream/agents/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket端点用于流式通信"""
    await websocket.accept()
    
    # 添加到连接列表
    if session_id not in websocket_connections:
        websocket_connections[session_id] = []
    websocket_connections[session_id].append(websocket)
    
    try:
        # 如果会话存在，发送当前状态
        if session_id in active_sessions:
            session = active_sessions[session_id]
            await websocket.send_text(f"data: {json.dumps({
                'type': 'session_update',
                'data': session,
                'timestamp': datetime.now().isoformat()
            })}\n\n")
        
        # 保持连接
        while True:
            try:
                # 等待客户端消息（心跳检测）
                data = await websocket.receive_text()
                # 可以在这里处理客户端发送的消息
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # 清理连接
        if session_id in websocket_connections:
            if websocket in websocket_connections[session_id]:
                websocket_connections[session_id].remove(websocket)

@router.get("/sessions")
async def list_sessions():
    """获取所有活跃会话"""
    return {
        "sessions": list(active_sessions.values()),
        "total": len(active_sessions)
    }

@router.get("/agents")
async def list_available_agents():
    """获取可用的智能体列表"""
    return {
        "agents": [
            {
                "id": agent_id,
                "name": config["name"],
                "description": config["description"],
                "class": config["class"]
            }
            for agent_id, config in AGENT_CONFIGS.items()
        ]
    }
