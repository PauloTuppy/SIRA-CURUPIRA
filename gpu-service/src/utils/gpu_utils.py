"""
GPU Utilities for NVIDIA GPU monitoring and management
"""

import os
import psutil
from typing import Dict, List, Optional, Any
import subprocess
import json

try:
    import pynvml
    NVIDIA_ML_AVAILABLE = True
except ImportError:
    NVIDIA_ML_AVAILABLE = False
    pynvml = None

from .logger import logger


class GPUInfo:
    """GPU information container"""
    
    def __init__(self):
        self.available = False
        self.device_count = 0
        self.devices = []
        self.driver_version = None
        self.cuda_version = None
        
        if NVIDIA_ML_AVAILABLE:
            self._init_nvidia_ml()
    
    def _init_nvidia_ml(self):
        """Initialize NVIDIA ML library"""
        try:
            pynvml.nvmlInit()
            self.available = True
            self.device_count = pynvml.nvmlDeviceGetCount()
            self.driver_version = pynvml.nvmlSystemGetDriverVersion().decode('utf-8')
            
            # Get CUDA version
            try:
                cuda_version = pynvml.nvmlSystemGetCudaDriverVersion()
                major = cuda_version // 1000
                minor = (cuda_version % 1000) // 10
                self.cuda_version = f"{major}.{minor}"
            except:
                self.cuda_version = "Unknown"
            
            # Get device information
            for i in range(self.device_count):
                device_info = self._get_device_info(i)
                self.devices.append(device_info)
                
        except Exception as e:
            logger.warning(f"Failed to initialize NVIDIA ML: {e}")
            self.available = False
    
    def _get_device_info(self, device_id: int) -> Dict[str, Any]:
        """Get information for a specific GPU device"""
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(device_id)
            
            # Basic device info
            name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
            
            # Memory info
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            memory_total = memory_info.total // (1024 ** 2)  # MB
            memory_used = memory_info.used // (1024 ** 2)    # MB
            memory_free = memory_info.free // (1024 ** 2)    # MB
            
            # Utilization
            try:
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu_util = utilization.gpu
                memory_util = utilization.memory
            except:
                gpu_util = 0
                memory_util = 0
            
            # Temperature
            try:
                temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            except:
                temperature = 0
            
            # Power
            try:
                power_draw = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Watts
                power_limit = pynvml.nvmlDeviceGetPowerManagementLimitConstraints(handle)[1] / 1000.0
            except:
                power_draw = 0
                power_limit = 0
            
            return {
                "id": device_id,
                "name": name,
                "memory_total": memory_total,
                "memory_used": memory_used,
                "memory_free": memory_free,
                "memory_usage_percent": (memory_used / memory_total * 100) if memory_total > 0 else 0,
                "utilization": gpu_util,
                "memory_utilization": memory_util,
                "temperature": temperature,
                "power_draw": power_draw,
                "power_limit": power_limit,
                "power_usage_percent": (power_draw / power_limit * 100) if power_limit > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get device info for GPU {device_id}: {e}")
            return {
                "id": device_id,
                "name": "Unknown",
                "memory_total": 0,
                "memory_used": 0,
                "memory_free": 0,
                "memory_usage_percent": 0,
                "utilization": 0,
                "memory_utilization": 0,
                "temperature": 0,
                "power_draw": 0,
                "power_limit": 0,
                "power_usage_percent": 0
            }


# Global GPU info instance
_gpu_info = None


def get_gpu_info() -> GPUInfo:
    """Get GPU information (cached)"""
    global _gpu_info
    if _gpu_info is None:
        _gpu_info = GPUInfo()
    return _gpu_info


def check_gpu_availability() -> bool:
    """Check if GPU is available"""
    gpu_info = get_gpu_info()
    return gpu_info.available and gpu_info.device_count > 0


def get_gpu_memory_info(device_id: int = 0) -> Dict[str, float]:
    """Get memory information for specific GPU device"""
    gpu_info = get_gpu_info()
    
    if not gpu_info.available or device_id >= len(gpu_info.devices):
        return {
            "total": 0.0,
            "used": 0.0,
            "free": 0.0,
            "usage_percent": 0.0
        }
    
    device = gpu_info.devices[device_id]
    return {
        "total": device["memory_total"] / 1024.0,  # GB
        "used": device["memory_used"] / 1024.0,    # GB
        "free": device["memory_free"] / 1024.0,    # GB
        "usage_percent": device["memory_usage_percent"]
    }


def monitor_gpu_usage(device_id: int = 0) -> Dict[str, Any]:
    """Monitor GPU usage for specific device"""
    gpu_info = get_gpu_info()
    
    if not gpu_info.available or device_id >= len(gpu_info.devices):
        return {
            "available": False,
            "utilization": 0.0,
            "memory_usage": 0.0,
            "temperature": 0.0,
            "power_usage": 0.0
        }
    
    # Refresh device info
    device = gpu_info._get_device_info(device_id)
    
    return {
        "available": True,
        "utilization": device["utilization"],
        "memory_usage": device["memory_usage_percent"],
        "temperature": device["temperature"],
        "power_usage": device["power_usage_percent"],
        "memory_used_gb": device["memory_used"] / 1024.0,
        "memory_total_gb": device["memory_total"] / 1024.0
    }


def get_system_info() -> Dict[str, Any]:
    """Get system information"""
    try:
        # CPU info
        cpu_count = psutil.cpu_count()
        cpu_usage = psutil.cpu_percent(interval=1)
        
        # Memory info
        memory = psutil.virtual_memory()
        memory_total = memory.total / (1024 ** 3)  # GB
        memory_used = memory.used / (1024 ** 3)    # GB
        memory_percent = memory.percent
        
        # Disk info
        disk = psutil.disk_usage('/')
        disk_total = disk.total / (1024 ** 3)  # GB
        disk_used = disk.used / (1024 ** 3)    # GB
        disk_percent = (disk_used / disk_total * 100) if disk_total > 0 else 0
        
        return {
            "cpu": {
                "count": cpu_count,
                "usage_percent": cpu_usage
            },
            "memory": {
                "total_gb": memory_total,
                "used_gb": memory_used,
                "usage_percent": memory_percent
            },
            "disk": {
                "total_gb": disk_total,
                "used_gb": disk_used,
                "usage_percent": disk_percent
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        return {
            "cpu": {"count": 0, "usage_percent": 0},
            "memory": {"total_gb": 0, "used_gb": 0, "usage_percent": 0},
            "disk": {"total_gb": 0, "used_gb": 0, "usage_percent": 0}
        }


def check_cuda_availability() -> Dict[str, Any]:
    """Check CUDA availability"""
    try:
        # Try to run nvidia-smi
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return {
                "available": True,
                "nvidia_smi": True,
                "output": result.stdout.strip()
            }
        else:
            return {
                "available": False,
                "nvidia_smi": False,
                "error": result.stderr
            }
            
    except subprocess.TimeoutExpired:
        return {
            "available": False,
            "nvidia_smi": False,
            "error": "nvidia-smi timeout"
        }
    except FileNotFoundError:
        return {
            "available": False,
            "nvidia_smi": False,
            "error": "nvidia-smi not found"
        }
    except Exception as e:
        return {
            "available": False,
            "nvidia_smi": False,
            "error": str(e)
        }
