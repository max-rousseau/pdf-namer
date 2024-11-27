import os
import time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

models_path = os.path.expanduser("~/.llama/checkpoints/")
torch.manual_seed(42)  # For reproducibility
model_name = "Llama3.2-3B-Instruct"
model_path = os.path.join(models_path, model_name)

# Initialize tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(
    model_path, device_map="auto"
)

# Define test prompts
prompts = [
    "Once upon a time in a galaxy far, far away,",
    "The quick brown fox jumps over the lazy dog.",
    "In the beginning, there was nothing but darkness.",
]

# Determine device
device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
model.to(device)

# Process each prompt
for prompt in prompts:
    try:
        # Tokenize input
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        
        # Measure inference time
        start_time = time.time()
        outputs = model.generate(
            inputs["input_ids"],
            max_length=100,
            temperature=0.7,
            top_k=50,
            top_p=0.95,
        )
        end_time = time.time()
        
        # Calculate metrics
        inference_time = end_time - start_time
        input_length = inputs["input_ids"].shape[-1]
        output_length = outputs.shape[-1]
        generated_tokens = output_length - input_length
        tokens_per_second = generated_tokens / inference_time if inference_time > 0 else float('inf')
        
        # Get generated text
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Print results
        print(f"\nPrompt: {prompt}")
        print(f"Generated Text: {generated_text}")
        print(f"Inference Time: {inference_time:.2f} seconds")
        print(f"Tokens Generated: {generated_tokens}")
        print(f"Tokens per Second: {tokens_per_second:.2f}")
        print("-" * 80)
        
    except Exception as e:
        print(f"An error occurred with prompt '{prompt}': {e}")
