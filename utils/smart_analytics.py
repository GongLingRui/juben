"""
智能分析系统 -  
提供智能分析、数据挖掘、预测分析和可视化
"""
import asyncio
import json
import time
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Union, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import threading
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.metrics import accuracy_score, mean_squared_error
from sklearn.preprocessing import StandardScaler

from .logger import JubenLogger
from .connection_pool_manager import get_connection_pool_manager


class AnalysisType(Enum):
    """分析类型"""
    DESCRIPTIVE = "descriptive"      # 描述性分析
    DIAGNOSTIC = "diagnostic"        # 诊断性分析
    PREDICTIVE = "predictive"        # 预测性分析
    PRESCRIPTIVE = "prescriptive"    # 规范性分析


class DataType(Enum):
    """数据类型"""
    NUMERICAL = "numerical"
    CATEGORICAL = "categorical"
    TEXT = "text"
    TIME_SERIES = "time_series"
    IMAGE = "image"
    AUDIO = "audio"


class VisualizationType(Enum):
    """可视化类型"""
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    SCATTER_PLOT = "scatter_plot"
    HEATMAP = "heatmap"
    HISTOGRAM = "histogram"
    BOX_PLOT = "box_plot"
    DENSITY_PLOT = "density_plot"


@dataclass
class DataPoint:
    """数据点"""
    timestamp: datetime
    value: Any
    category: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    """分析结果"""
    analysis_id: str
    analysis_type: AnalysisType
    data_source: str
    start_time: datetime
    end_time: datetime
    duration: float
    results: Dict[str, Any]
    insights: List[str]
    recommendations: List[str]
    confidence: float
    visualization_path: Optional[str] = None


@dataclass
class PredictionResult:
    """预测结果"""
    prediction_id: str
    model_name: str
    input_data: Dict[str, Any]
    prediction: Any
    confidence: float
    timestamp: datetime
    accuracy: Optional[float] = None


class SmartAnalytics:
    """智能分析系统"""
    
    def __init__(self):
        self.logger = JubenLogger("smart_analytics")
        
        # 分析配置
        self.analysis_enabled = True
        self.auto_analysis = False
        self.analysis_interval = 3600  # 1小时
        self.max_data_points = 100000
        self.retention_days = 30
        
        # 数据存储
        self.data_points: List[DataPoint] = []
        self.analysis_results: List[AnalysisResult] = []
        self.prediction_results: List[PredictionResult] = []
        
        # 分析模型
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.feature_importance: Dict[str, List[float]] = {}
        
        # 分析任务
        self.analysis_tasks: List[asyncio.Task] = []
        self.analysis_queue: List[Dict[str, Any]] = []
        
        # 可视化
        self.visualization_enabled = True
        self.chart_style = 'seaborn'
        self.color_palette = 'viridis'
        self.output_path = 'analytics_output'
        
        # 分析回调
        self.analysis_callbacks: List[Callable] = []
        self.prediction_callbacks: List[Callable] = []
        
        # 分析统计
        self.analytics_stats: Dict[str, Any] = {}
        
        self.logger.info("📊 智能分析系统初始化完成")
    
    async def initialize(self):
        """初始化分析系统"""
        try:
            # 创建输出目录
            Path(self.output_path).mkdir(parents=True, exist_ok=True)
            
            # 启动分析任务
            if self.analysis_enabled:
                await self._start_analysis_tasks()
            
            # 初始化可视化
            if self.visualization_enabled:
                await self._initialize_visualization()
            
            self.logger.info("✅ 智能分析系统初始化完成")
            
        except Exception as e:
            self.logger.error(f"❌ 初始化分析系统失败: {e}")
    
    async def _start_analysis_tasks(self):
        """启动分析任务"""
        try:
            # 启动数据分析任务
            task = asyncio.create_task(self._data_analysis_task())
            self.analysis_tasks.append(task)
            
            # 启动预测分析任务
            task = asyncio.create_task(self._prediction_analysis_task())
            self.analysis_tasks.append(task)
            
            # 启动可视化任务
            task = asyncio.create_task(self._visualization_task())
            self.analysis_tasks.append(task)
            
            self.logger.info("✅ 分析任务已启动")
            
        except Exception as e:
            self.logger.error(f"❌ 启动分析任务失败: {e}")
    
    async def _initialize_visualization(self):
        """初始化可视化"""
        try:
            # 设置matplotlib样式
            plt.style.use(self.chart_style)
            
            # 设置seaborn样式
            sns.set_style("whitegrid")
            sns.set_palette(self.color_palette)
            
            self.logger.info("✅ 可视化已初始化")
            
        except Exception as e:
            self.logger.error(f"❌ 初始化可视化失败: {e}")
    
    async def _data_analysis_task(self):
        """数据分析任务"""
        try:
            while True:
                await asyncio.sleep(self.analysis_interval)
                
                # 执行数据分析
                await self._perform_data_analysis()
                
        except asyncio.CancelledError:
            self.logger.info("📊 数据分析任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 数据分析任务失败: {e}")
    
    async def _prediction_analysis_task(self):
        """预测分析任务"""
        try:
            while True:
                await asyncio.sleep(self.analysis_interval * 2)  # 每2小时执行一次
                
                # 执行预测分析
                await self._perform_prediction_analysis()
                
        except asyncio.CancelledError:
            self.logger.info("🔮 预测分析任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 预测分析任务失败: {e}")
    
    async def _visualization_task(self):
        """可视化任务"""
        try:
            while True:
                await asyncio.sleep(self.analysis_interval * 3)  # 每3小时执行一次
                
                # 生成可视化图表
                await self._generate_visualizations()
                
        except asyncio.CancelledError:
            self.logger.info("📈 可视化任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 可视化任务失败: {e}")
    
    async def _perform_data_analysis(self):
        """执行数据分析"""
        try:
            if not self.data_points:
                return
            
            # 创建DataFrame
            df = self._create_dataframe()
            
            # 描述性分析
            descriptive_results = await self._descriptive_analysis(df)
            
            # 诊断性分析
            diagnostic_results = await self._diagnostic_analysis(df)
            
            # 创建分析结果
            analysis_result = AnalysisResult(
                analysis_id=f"analysis_{int(time.time())}",
                analysis_type=AnalysisType.DESCRIPTIVE,
                data_source="internal",
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration=0.0,
                results={
                    'descriptive': descriptive_results,
                    'diagnostic': diagnostic_results
                },
                insights=[],
                recommendations=[],
                confidence=0.8
            )
            
            self.analysis_results.append(analysis_result)
            
            # 触发分析回调
            await self._trigger_analysis_callbacks(analysis_result)
            
        except Exception as e:
            self.logger.error(f"❌ 执行数据分析失败: {e}")
    
    async def _perform_prediction_analysis(self):
        """执行预测分析"""
        try:
            if len(self.data_points) < 100:  # 需要足够的数据点
                return
            
            # 创建DataFrame
            df = self._create_dataframe()
            
            # 时间序列预测
            time_series_results = await self._time_series_prediction(df)
            
            # 分类预测
            classification_results = await self._classification_prediction(df)
            
            # 回归预测
            regression_results = await self._regression_prediction(df)
            
            # 创建预测结果
            for model_name, prediction in time_series_results.items():
                prediction_result = PredictionResult(
                    prediction_id=f"prediction_{int(time.time())}_{model_name}",
                    model_name=model_name,
                    input_data={},
                    prediction=prediction,
                    confidence=0.8,
                    timestamp=datetime.now()
                )
                
                self.prediction_results.append(prediction_result)
                
                # 触发预测回调
                await self._trigger_prediction_callbacks(prediction_result)
            
        except Exception as e:
            self.logger.error(f"❌ 执行预测分析失败: {e}")
    
    async def _generate_visualizations(self):
        """生成可视化图表"""
        try:
            if not self.data_points:
                return
            
            # 创建DataFrame
            df = self._create_dataframe()
            
            # 生成各种图表
            await self._create_line_chart(df)
            await self._create_bar_chart(df)
            await self._create_histogram(df)
            await self._create_scatter_plot(df)
            await self._create_heatmap(df)
            
        except Exception as e:
            self.logger.error(f"❌ 生成可视化图表失败: {e}")
    
    def _create_dataframe(self) -> pd.DataFrame:
        """创建DataFrame"""
        try:
            data = []
            for point in self.data_points:
                data.append({
                    'timestamp': point.timestamp,
                    'value': point.value,
                    'category': point.category,
                    **point.metadata
                })
            
            df = pd.DataFrame(data)
            
            # 转换时间戳
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ 创建DataFrame失败: {e}")
            return pd.DataFrame()
    
    async def _descriptive_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """描述性分析"""
        try:
            results = {}
            
            # 基本统计
            if 'value' in df.columns and pd.api.types.is_numeric_dtype(df['value']):
                results['basic_stats'] = {
                    'count': df['value'].count(),
                    'mean': df['value'].mean(),
                    'std': df['value'].std(),
                    'min': df['value'].min(),
                    'max': df['value'].max(),
                    'median': df['value'].median()
                }
            
            # 分布分析
            if 'value' in df.columns:
                results['distribution'] = {
                    'skewness': df['value'].skew() if pd.api.types.is_numeric_dtype(df['value']) else None,
                    'kurtosis': df['value'].kurtosis() if pd.api.types.is_numeric_dtype(df['value']) else None
                }
            
            # 时间序列分析
            if 'timestamp' in df.columns:
                results['time_series'] = {
                    'start_time': df['timestamp'].min(),
                    'end_time': df['timestamp'].max(),
                    'duration': (df['timestamp'].max() - df['timestamp'].min()).total_seconds(),
                    'frequency': len(df) / ((df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600)  # 每小时
                }
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 描述性分析失败: {e}")
            return {}
    
    async def _diagnostic_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """诊断性分析"""
        try:
            results = {}
            
            # 异常值检测
            if 'value' in df.columns and pd.api.types.is_numeric_dtype(df['value']):
                Q1 = df['value'].quantile(0.25)
                Q3 = df['value'].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outliers = df[(df['value'] < lower_bound) | (df['value'] > upper_bound)]
                results['outliers'] = {
                    'count': len(outliers),
                    'percentage': len(outliers) / len(df) * 100,
                    'values': outliers['value'].tolist()
                }
            
            # 趋势分析
            if 'timestamp' in df.columns and 'value' in df.columns:
                df_sorted = df.sort_values('timestamp')
                if len(df_sorted) > 1:
                    # 计算趋势
                    x = np.arange(len(df_sorted))
                    y = df_sorted['value'].values
                    
                    if pd.api.types.is_numeric_dtype(df_sorted['value']):
                        slope = np.polyfit(x, y, 1)[0]
                        results['trend'] = {
                            'slope': slope,
                            'direction': 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable'
                        }
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 诊断性分析失败: {e}")
            return {}
    
    async def _time_series_prediction(self, df: pd.DataFrame) -> Dict[str, Any]:
        """时间序列预测"""
        try:
            results = {}
            
            if 'timestamp' in df.columns and 'value' in df.columns:
                # 准备数据
                df_sorted = df.sort_values('timestamp')
                df_sorted['time_index'] = range(len(df_sorted))
                
                if len(df_sorted) > 10:  # 需要足够的数据点
                    # 简单的线性回归预测
                    X = df_sorted['time_index'].values.reshape(-1, 1)
                    y = df_sorted['value'].values
                    
                    if pd.api.types.is_numeric_dtype(df_sorted['value']):
                        model = LinearRegression()
                        model.fit(X, y)
                        
                        # 预测未来5个点
                        future_indices = np.arange(len(df_sorted), len(df_sorted) + 5).reshape(-1, 1)
                        predictions = model.predict(future_indices)
                        
                        results['linear_regression'] = {
                            'predictions': predictions.tolist(),
                            'r2_score': model.score(X, y)
                        }
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 时间序列预测失败: {e}")
            return {}
    
    async def _classification_prediction(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分类预测"""
        try:
            results = {}
            
            if 'category' in df.columns and 'value' in df.columns:
                # 准备数据
                df_clean = df.dropna()
                
                if len(df_clean) > 20:  # 需要足够的数据点
                    # 特征工程
                    features = []
                    for col in df_clean.columns:
                        if col not in ['category', 'timestamp']:
                            if pd.api.types.is_numeric_dtype(df_clean[col]):
                                features.append(col)
                    
                    if features:
                        X = df_clean[features].values
                        y = df_clean['category'].values
                        
                        # 训练随机森林分类器
                        model = RandomForestClassifier(n_estimators=100, random_state=42)
                        model.fit(X, y)
                        
                        # 预测
                        predictions = model.predict(X)
                        accuracy = accuracy_score(y, predictions)
                        
                        results['random_forest'] = {
                            'accuracy': accuracy,
                            'feature_importance': model.feature_importances_.tolist(),
                            'predictions': predictions.tolist()
                        }
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 分类预测失败: {e}")
            return {}
    
    async def _regression_prediction(self, df: pd.DataFrame) -> Dict[str, Any]:
        """回归预测"""
        try:
            results = {}
            
            if 'value' in df.columns:
                # 准备数据
                df_clean = df.dropna()
                
                if len(df_clean) > 10:  # 需要足够的数据点
                    # 特征工程
                    features = []
                    for col in df_clean.columns:
                        if col not in ['value', 'timestamp']:
                            if pd.api.types.is_numeric_dtype(df_clean[col]):
                                features.append(col)
                    
                    if features:
                        X = df_clean[features].values
                        y = df_clean['value'].values
                        
                        # 训练线性回归模型
                        model = LinearRegression()
                        model.fit(X, y)
                        
                        # 预测
                        predictions = model.predict(X)
                        mse = mean_squared_error(y, predictions)
                        
                        results['linear_regression'] = {
                            'mse': mse,
                            'r2_score': model.score(X, y),
                            'predictions': predictions.tolist()
                        }
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 回归预测失败: {e}")
            return {}
    
    async def _create_line_chart(self, df: pd.DataFrame):
        """创建折线图"""
        try:
            if 'timestamp' in df.columns and 'value' in df.columns:
                plt.figure(figsize=(12, 6))
                plt.plot(df['timestamp'], df['value'])
                plt.title('数据趋势图')
                plt.xlabel('时间')
                plt.ylabel('值')
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                chart_path = Path(self.output_path) / f'line_chart_{int(time.time())}.png'
                plt.savefig(chart_path)
                plt.close()
                
                self.logger.info(f"✅ 折线图已生成: {chart_path}")
            
        except Exception as e:
            self.logger.error(f"❌ 创建折线图失败: {e}")
    
    async def _create_bar_chart(self, df: pd.DataFrame):
        """创建柱状图"""
        try:
            if 'category' in df.columns and 'value' in df.columns:
                plt.figure(figsize=(10, 6))
                df_grouped = df.groupby('category')['value'].mean()
                df_grouped.plot(kind='bar')
                plt.title('分类平均值')
                plt.xlabel('分类')
                plt.ylabel('平均值')
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                chart_path = Path(self.output_path) / f'bar_chart_{int(time.time())}.png'
                plt.savefig(chart_path)
                plt.close()
                
                self.logger.info(f"✅ 柱状图已生成: {chart_path}")
            
        except Exception as e:
            self.logger.error(f"❌ 创建柱状图失败: {e}")
    
    async def _create_histogram(self, df: pd.DataFrame):
        """创建直方图"""
        try:
            if 'value' in df.columns and pd.api.types.is_numeric_dtype(df['value']):
                plt.figure(figsize=(10, 6))
                plt.hist(df['value'], bins=30, alpha=0.7)
                plt.title('数据分布直方图')
                plt.xlabel('值')
                plt.ylabel('频次')
                plt.tight_layout()
                
                chart_path = Path(self.output_path) / f'histogram_{int(time.time())}.png'
                plt.savefig(chart_path)
                plt.close()
                
                self.logger.info(f"✅ 直方图已生成: {chart_path}")
            
        except Exception as e:
            self.logger.error(f"❌ 创建直方图失败: {e}")
    
    async def _create_scatter_plot(self, df: pd.DataFrame):
        """创建散点图"""
        try:
            if 'timestamp' in df.columns and 'value' in df.columns:
                plt.figure(figsize=(10, 6))
                plt.scatter(df['timestamp'], df['value'], alpha=0.6)
                plt.title('数据散点图')
                plt.xlabel('时间')
                plt.ylabel('值')
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                chart_path = Path(self.output_path) / f'scatter_plot_{int(time.time())}.png'
                plt.savefig(chart_path)
                plt.close()
                
                self.logger.info(f"✅ 散点图已生成: {chart_path}")
            
        except Exception as e:
            self.logger.error(f"❌ 创建散点图失败: {e}")
    
    async def _create_heatmap(self, df: pd.DataFrame):
        """创建热力图"""
        try:
            if len(df.columns) > 2:
                # 选择数值列
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                
                if len(numeric_cols) > 1:
                    plt.figure(figsize=(10, 8))
                    correlation_matrix = df[numeric_cols].corr()
                    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0)
                    plt.title('相关性热力图')
                    plt.tight_layout()
                    
                    chart_path = Path(self.output_path) / f'heatmap_{int(time.time())}.png'
                    plt.savefig(chart_path)
                    plt.close()
                    
                    self.logger.info(f"✅ 热力图已生成: {chart_path}")
            
        except Exception as e:
            self.logger.error(f"❌ 创建热力图失败: {e}")
    
    async def _trigger_analysis_callbacks(self, analysis_result: AnalysisResult):
        """触发分析回调"""
        try:
            for callback in self.analysis_callbacks:
                try:
                    await callback(analysis_result)
                except Exception as e:
                    self.logger.error(f"❌ 分析回调执行失败: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ 触发分析回调失败: {e}")
    
    async def _trigger_prediction_callbacks(self, prediction_result: PredictionResult):
        """触发预测回调"""
        try:
            for callback in self.prediction_callbacks:
                try:
                    await callback(prediction_result)
                except Exception as e:
                    self.logger.error(f"❌ 预测回调执行失败: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ 触发预测回调失败: {e}")
    
    def add_data_point(self, value: Any, category: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """添加数据点"""
        try:
            data_point = DataPoint(
                timestamp=datetime.now(),
                value=value,
                category=category,
                metadata=metadata or {}
            )
            
            self.data_points.append(data_point)
            
            # 限制数据点数量
            if len(self.data_points) > self.max_data_points:
                self.data_points = self.data_points[-self.max_data_points:]
            
        except Exception as e:
            self.logger.error(f"❌ 添加数据点失败: {e}")
    
    def add_analysis_callback(self, callback: Callable):
        """添加分析回调"""
        try:
            self.analysis_callbacks.append(callback)
            self.logger.info("✅ 分析回调已添加")
            
        except Exception as e:
            self.logger.error(f"❌ 添加分析回调失败: {e}")
    
    def add_prediction_callback(self, callback: Callable):
        """添加预测回调"""
        try:
            self.prediction_callbacks.append(callback)
            self.logger.info("✅ 预测回调已添加")
            
        except Exception as e:
            self.logger.error(f"❌ 添加预测回调失败: {e}")
    
    def get_analytics_stats(self) -> Dict[str, Any]:
        """获取分析统计"""
        try:
            return {
                'total_data_points': len(self.data_points),
                'total_analysis_results': len(self.analysis_results),
                'total_predictions': len(self.prediction_results),
                'analysis_enabled': self.analysis_enabled,
                'auto_analysis': self.auto_analysis,
                'analysis_interval': self.analysis_interval,
                'max_data_points': self.max_data_points,
                'retention_days': self.retention_days,
                'visualization_enabled': self.visualization_enabled,
                'output_path': self.output_path,
                'analysis_tasks': len(self.analysis_tasks),
                'analysis_queue': len(self.analysis_queue),
                'models': len(self.models),
                'scalers': len(self.scalers)
            }
            
        except Exception as e:
            self.logger.error(f"❌ 获取分析统计失败: {e}")
            return {'error': str(e)}


# 全局智能分析实例
smart_analytics = SmartAnalytics()


def get_smart_analytics() -> SmartAnalytics:
    """获取智能分析实例"""
    return smart_analytics
