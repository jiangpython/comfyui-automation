"""ComfyUI API客户端"""

import subprocess
import time
import requests
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from ..config.settings import Settings

logger = logging.getLogger(__name__)

class ComfyUIClient:
    """ComfyUI API客户端"""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.comfyui_config = self.settings.comfyui
        self.process: Optional[subprocess.Popen] = None
        self.is_connected = False
    
    def start_service(self) -> bool:
        """启动ComfyUI服务"""
        startup_mode = self.comfyui_config.startup_mode.lower()
        
        if startup_mode == "check_only":
            return self._check_only_mode()
        elif startup_mode == "manual":
            return self._manual_mode()
        else:  # auto mode
            return self._auto_mode()
    
    def _check_only_mode(self) -> bool:
        """仅检查模式：不自动启动，只检查是否运行"""
        if self.is_service_running():
            logger.info("ComfyUI服务已在运行")
            self.is_connected = True
            return True
        else:
            logger.error("ComfyUI服务未运行，请手动启动")
            return False
    
    def _manual_mode(self) -> bool:
        """手动模式：等待用户确认已启动"""
        print("请启动ComfyUI服务，然后按回车继续...")
        input()
        
        if self.wait_for_service():
            logger.info("ComfyUI服务连接成功")
            self.is_connected = True
            return True
        else:
            logger.error("无法连接到ComfyUI服务")
            return False
    
    def _auto_mode(self) -> bool:
        """自动模式：自动启动ComfyUI"""
        if self.is_service_running():
            logger.info("ComfyUI服务已在运行")
            self.is_connected = True
            return True
        
        logger.info("启动ComfyUI服务...")
        if not self._launch_comfyui():
            return False
        
        if self.wait_for_service():
            logger.info("ComfyUI服务启动成功")
            self.is_connected = True
            return True
        else:
            logger.error("ComfyUI服务启动失败")
            return False
    
    def _launch_comfyui(self) -> bool:
        """启动ComfyUI进程"""
        try:
            comfyui_path = Path(self.comfyui_config.path)
            venv_python = self.comfyui_config.venv_python
            
            if not comfyui_path.exists():
                logger.error(f"ComfyUI路径不存在: {comfyui_path}")
                return False
            
            if not Path(venv_python).exists():
                logger.error(f"虚拟环境Python不存在: {venv_python}")
                return False
            
            # 启动ComfyUI进程
            self.process = subprocess.Popen([
                venv_python, "main.py", 
                "--listen", "127.0.0.1", 
                "--port", "8188"
            ], 
            cwd=str(comfyui_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
            )
            
            logger.info(f"ComfyUI进程已启动 (PID: {self.process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"启动ComfyUI失败: {e}")
            return False
    
    def is_service_running(self) -> bool:
        """检查ComfyUI服务是否运行"""
        try:
            response = requests.get(
                f"{self.comfyui_config.api_url}/system_stats", 
                timeout=3
            )
            return response.status_code == 200
        except:
            return False
    
    def wait_for_service(self, timeout: Optional[int] = None) -> bool:
        """等待服务就绪"""
        timeout = timeout or self.comfyui_config.startup_timeout
        start_time = time.time()
        
        logger.info(f"等待ComfyUI服务就绪 (超时: {timeout}秒)")
        
        while time.time() - start_time < timeout:
            if self.is_service_running():
                return True
            
            # 检查进程是否还在运行
            if self.process and self.process.poll() is not None:
                logger.error(f"ComfyUI进程已退出，退出代码: {self.process.returncode}")
                return False
            
            time.sleep(3)
        
        logger.error("ComfyUI服务启动超时")
        return False
    
    def get_system_stats(self) -> Optional[Dict[str, Any]]:
        """获取系统状态"""
        try:
            response = requests.get(
                f"{self.comfyui_config.api_url}/system_stats",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"获取系统状态失败，状态码: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"获取系统状态异常: {e}")
            return None
    
    def get_queue_status(self) -> Optional[Dict[str, Any]]:
        """获取队列状态"""
        try:
            response = requests.get(
                f"{self.comfyui_config.api_url}/queue",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"获取队列状态失败，状态码: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"获取队列状态异常: {e}")
            return None
    
    def get_history(self, prompt_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取历史记录"""
        try:
            url = f"{self.comfyui_config.api_url}/history"
            if prompt_id:
                url += f"/{prompt_id}"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"获取历史记录失败，状态码: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"获取历史记录异常: {e}")
            return None
    
    def submit_workflow(self, workflow: Dict[str, Any], client_id: Optional[str] = None) -> Optional[str]:
        """提交工作流"""
        try:
            import uuid
            client_id = client_id or str(uuid.uuid4())
            
            payload = {
                "prompt": workflow,
                "client_id": client_id
            }
            
            response = requests.post(
                f"{self.comfyui_config.api_url}/prompt",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                prompt_id = result.get("prompt_id")
                logger.info(f"工作流提交成功，Prompt ID: {prompt_id}")
                return prompt_id
            else:
                error_text = response.text
                logger.error(f"工作流提交失败，状态码: {response.status_code}")
                logger.error(f"错误详情: {error_text}")
                return None
                
        except Exception as e:
            logger.error(f"提交工作流异常: {e}")
            return None
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        result = {
            'service_running': False,
            'api_accessible': False,
            'process_alive': False,
            'system_stats': None,
            'queue_status': None
        }
        
        # 检查服务是否运行
        result['service_running'] = self.is_service_running()
        
        if result['service_running']:
            result['api_accessible'] = True
            
            # 获取系统状态
            result['system_stats'] = self.get_system_stats()
            
            # 获取队列状态
            result['queue_status'] = self.get_queue_status()
        
        # 检查进程状态
        if self.process:
            result['process_alive'] = self.process.poll() is None
        
        return result
    
    def cleanup(self):
        """清理资源"""
        if self.process:
            logger.info("关闭ComfyUI进程...")
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
                logger.info("ComfyUI进程已关闭")
            except subprocess.TimeoutExpired:
                logger.warning("强制关闭ComfyUI进程")
                self.process.kill()
        
        self.is_connected = False
    
    def __enter__(self):
        """上下文管理器入口"""
        if not self.start_service():
            raise Exception("无法启动ComfyUI服务")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.cleanup()