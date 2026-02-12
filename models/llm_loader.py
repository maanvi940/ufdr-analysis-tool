"""
Local LLM Loader for Offline AI Inference
Supports multiple backends: llama-cpp-python, transformers (with quantization)

For air-gapped deployment as per PHASE F requirements
"""

import logging
import os
from pathlib import Path
from typing import Optional
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMBackend(Enum):
    """Supported LLM inference backends"""
    LLAMA_CPP = "llama_cpp"  # For GGUF models (CPU/GPU)
    TRANSFORMERS = "transformers"  # For HuggingFace models with quantization
    VLLM = "vllm"  # For high-performance GPU inference
    NONE = "none"  # Fallback - no LLM available


class LocalLLM:
    """
    Local LLM interface for offline inference
    Designed for air-gapped forensic environments
    """
    
    def __init__(self, 
                 model_path: Optional[str] = None,
                 backend: str = "llama_cpp",
                 **kwargs):
        """
        Initialize local LLM
        
        Args:
            model_path: Path to model file (GGUF or safetensors)
            backend: Inference backend to use
            **kwargs: Backend-specific parameters
        """
        # Import hardware detector
        try:
            from utils.hardware_detector import get_capabilities, get_device
            self.hw_caps = get_capabilities()
            self.device = get_device()
            logger.info(f"Hardware: {self.hw_caps.device_name} ({self.hw_caps.execution_mode.value})")
        except Exception as e:
            logger.warning(f"Could not detect hardware: {e}")
            self.hw_caps = None
            self.device = "cpu"
        
        self.model_path = model_path
        self.backend = LLMBackend(backend) if backend != "none" else LLMBackend.NONE
        self.model = None
        self.is_available = False
        
        # Default model paths if not specified
        if not model_path:
            models_dir = Path(__file__).parent
            self.model_path = self._find_default_model(models_dir)
        
        if self.model_path and Path(self.model_path).exists():
            try:
                self._load_model(**kwargs)
                self.is_available = True
                logger.info(f"✓ Local LLM loaded successfully from {self.model_path}")
            except Exception as e:
                logger.warning(f"Failed to load LLM: {e}")
                logger.warning("Falling back to rule-based mode only")
                self.is_available = False
        else:
            logger.warning(f"No model found at {self.model_path}")
            logger.warning("LLM features disabled - using rule-based mode only")
            self.is_available = False
    
    def _find_default_model(self, models_dir: Path) -> Optional[str]:
        """
        Search for default model files
        
        Priority:
        1. mistral-7b*.gguf
        2. llama*.gguf
        3. *.gguf
        """
        patterns = [
            "mistral-7b*.gguf",
            "mistral*.gguf",
            "llama*.gguf",
            "*.gguf"
        ]
        
        for pattern in patterns:
            matches = list(models_dir.glob(pattern))
            if matches:
                return str(matches[0])
        
        return None
    
    def _load_model(self, **kwargs):
        """Load model based on selected backend"""
        if self.backend == LLMBackend.LLAMA_CPP:
            self._load_llama_cpp(**kwargs)
        elif self.backend == LLMBackend.TRANSFORMERS:
            self._load_transformers(**kwargs)
        elif self.backend == LLMBackend.VLLM:
            self._load_vllm(**kwargs)
        else:
            raise ValueError(f"Unsupported backend: {self.backend}")
    
    def _load_llama_cpp(self, **kwargs):
        """Load GGUF model using llama-cpp-python"""
        try:
            from llama_cpp import Llama
            
            # Auto-detect GPU layers based on hardware
            if self.hw_caps and self.hw_caps.cuda_available:
                # GPU available - offload layers to GPU
                if self.hw_caps.gpu_memory_gb >= 8:
                    n_gpu_layers = kwargs.get('n_gpu_layers', 35)  # Most layers on GPU
                elif self.hw_caps.gpu_memory_gb >= 6:
                    n_gpu_layers = kwargs.get('n_gpu_layers', 25)  # Moderate GPU usage
                elif self.hw_caps.gpu_memory_gb >= 4:
                    n_gpu_layers = kwargs.get('n_gpu_layers', 15)  # Limited GPU usage
                else:
                    n_gpu_layers = 0  # GPU too small
                logger.info(f"GPU detected: offloading {n_gpu_layers} layers to GPU")
            else:
                n_gpu_layers = 0  # CPU only
                logger.info("CPU-only mode")
            
            # Optimal thread count from hardware detector
            n_threads = kwargs.get('n_threads', 
                                 self.hw_caps.cpu_cores if self.hw_caps else (os.cpu_count() or 4))
            
            # Context length from hardware capabilities
            n_ctx = kwargs.get('n_ctx', 
                             self.hw_caps.max_context_length if self.hw_caps else 2048)
            
            # Default parameters optimized for forensic queries
            default_params = {
                'model_path': self.model_path,
                'n_ctx': n_ctx,
                'n_threads': n_threads,
                'n_gpu_layers': n_gpu_layers,
                'verbose': False
            }
            
            self.model = Llama(**default_params)
            logger.info(f"Loaded GGUF model with llama-cpp-python (ctx={n_ctx}, threads={n_threads}, gpu_layers={n_gpu_layers})")
            
        except ImportError:
            raise ImportError(
                "llama-cpp-python not installed. Install with:\n"
                "pip install llama-cpp-python\n"
                "Or for GPU support:\n"
                "CMAKE_ARGS='-DLLAMA_CUBLAS=on' pip install llama-cpp-python"
            )
    
    def _load_transformers(self, **kwargs):
        """Load model using transformers with quantization"""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            import torch
            
            # Auto-detect device and quantization
            device = self.device if hasattr(self, 'device') else 'cpu'
            
            if device == 'cuda' and self.hw_caps and self.hw_caps.cuda_available:
                # GPU available - use quantization
                logger.info("Using GPU with 4-bit quantization")
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16 if self.hw_caps.supports_fp16 else torch.float32,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
                
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_path,
                    quantization_config=quantization_config,
                    device_map="auto",
                    trust_remote_code=True
                )
            else:
                # CPU mode - load without quantization or with lighter quant
                logger.info("Using CPU mode (no GPU quantization)")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_path,
                    device_map="cpu",
                    low_cpu_mem_usage=True,
                    trust_remote_code=True
                )
            
            logger.info(f"Loaded model with transformers on {device}")
            
        except ImportError:
            raise ImportError(
                "transformers not installed. Install with:\n"
                "pip install transformers accelerate bitsandbytes"
            )
    
    def _load_vllm(self, **kwargs):
        """Load model using vLLM for high-performance inference"""
        try:
            from vllm import LLM as VLLM
            
            self.model = VLLM(
                model=self.model_path,
                tensor_parallel_size=kwargs.get('tensor_parallel_size', 1),
                gpu_memory_utilization=kwargs.get('gpu_memory_utilization', 0.9)
            )
            logger.info(f"Loaded model with vLLM")
            
        except ImportError:
            raise ImportError(
                "vLLM not installed. Install with:\n"
                "pip install vllm"
            )
    
    def generate(self, 
                 prompt: str,
                 max_tokens: int = 512,
                 temperature: float = 0.1,
                 stop: Optional[list] = None,
                 **kwargs) -> str:
        """
        Generate text from prompt
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic)
            stop: Stop sequences
            **kwargs: Backend-specific parameters
            
        Returns:
            Generated text
        """
        if not self.is_available:
            raise RuntimeError("LLM not available. Check logs for details.")
        
        if self.backend == LLMBackend.LLAMA_CPP:
            return self._generate_llama_cpp(prompt, max_tokens, temperature, stop, **kwargs)
        elif self.backend == LLMBackend.TRANSFORMERS:
            return self._generate_transformers(prompt, max_tokens, temperature, stop, **kwargs)
        elif self.backend == LLMBackend.VLLM:
            return self._generate_vllm(prompt, max_tokens, temperature, stop, **kwargs)
        else:
            raise ValueError(f"Unsupported backend: {self.backend}")
    
    def _generate_llama_cpp(self, prompt, max_tokens, temperature, stop, **kwargs) -> str:
        """Generate using llama-cpp-python"""
        response = self.model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop or [],
            echo=False
        )
        return response['choices'][0]['text'].strip()
    
    def _generate_transformers(self, prompt, max_tokens, temperature, stop, **kwargs) -> str:
        """Generate using transformers"""
        import torch
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=temperature > 0,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Remove the input prompt from response
        response = response[len(prompt):].strip()
        return response
    
    def _generate_vllm(self, prompt, max_tokens, temperature, stop, **kwargs) -> str:
        """Generate using vLLM"""
        from vllm import SamplingParams
        
        sampling_params = SamplingParams(
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop
        )
        
        outputs = self.model.generate([prompt], sampling_params)
        return outputs[0].outputs[0].text.strip()


# Global LLM instance (lazy loading)
_llm_instance: Optional[LocalLLM] = None


def get_llm(force_reload: bool = False, **kwargs) -> LocalLLM:
    """
    Get or create global LLM instance
    
    Args:
        force_reload: Force reload the model
        **kwargs: Parameters to pass to LocalLLM constructor
        
    Returns:
        LocalLLM instance
    """
    global _llm_instance
    
    if _llm_instance is None or force_reload:
        _llm_instance = LocalLLM(**kwargs)
    
    return _llm_instance


if __name__ == "__main__":
    # Test the loader
    print("Testing Local LLM Loader...")
    print("-" * 50)
    
    llm = get_llm()
    
    if llm.is_available:
        print("✓ LLM loaded successfully!")
        print(f"Backend: {llm.backend.value}")
        print(f"Model: {llm.model_path}")
        
        # Test generation
        test_prompt = "Translate this to Cypher: Find all persons named Kumar"
        print(f"\nTest prompt: {test_prompt}")
        try:
            response = llm.generate(test_prompt, max_tokens=128, temperature=0.1)
            print(f"Response: {response}")
        except Exception as e:
            print(f"Generation failed: {e}")
    else:
        print("⚠ LLM not available - rule-based mode only")
        print("\nTo enable LLM features:")
        print("1. Download a GGUF model (e.g., Mistral-7B-Instruct)")
        print("2. Place it in the models/ directory")
        print("3. Install llama-cpp-python: pip install llama-cpp-python")