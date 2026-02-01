"""
Base tool class for agentic database investigation tools
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class ToolParameter(BaseModel):
    """Tool parameter definition"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum_values: Optional[List[str]] = None


class ToolDefinition(BaseModel):
    """Tool definition for function calling"""
    name: str
    description: str
    parameters: List[ToolParameter]


class ToolResult(BaseModel):
    """Standardized tool execution result"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = {}


class BaseTool(ABC):
    """Base class for all agentic database tools"""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for function calling"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM understanding"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """Tool parameters definition"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters"""
        pass
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Get tool definition in OpenAI function calling format"""
        properties = {}
        required = []
        
        for param in self.parameters:
            prop_def = {
                "type": param.type,
                "description": param.description
            }
            
            if param.enum_values:
                prop_def["enum"] = param.enum_values
            
            properties[param.name] = prop_def
            
            if param.required:
                required.append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    
    def validate_parameters(self, **kwargs) -> Dict[str, Any]:
        """Validate and process input parameters"""
        validated = {}
        
        for param in self.parameters:
            value = kwargs.get(param.name)
            
            if value is None:
                if param.required:
                    raise ValueError(f"Required parameter '{param.name}' is missing")
                value = param.default
            
            # Type validation could be added here
            validated[param.name] = value
        
        return validated
    
    async def safe_execute(self, **kwargs) -> ToolResult:
        """Execute tool with error handling and logging"""
        import time
        
        start_time = time.time()
        
        try:
            self.logger.info(f"Executing tool {self.name} with parameters: {kwargs}")
            
            # Validate parameters
            validated_params = self.validate_parameters(**kwargs)
            
            # Execute tool
            result = await self.execute(**validated_params)
            
            execution_time = (time.time() - start_time) * 1000
            result.execution_time_ms = execution_time
            
            self.logger.info(f"Tool {self.name} completed in {execution_time:.2f}ms")
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"Tool {self.name} failed: {str(e)}"
            self.logger.error(error_msg)
            
            return ToolResult(
                success=False,
                error=error_msg,
                execution_time_ms=execution_time
            )





