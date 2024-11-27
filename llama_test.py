from transformers import AutoModelForCausalLM

models_path = "~/.llama/checkpoints/"
model_name = "Llama3.2-3B-Instruct"

model = AutoModelForCausalLM.from_pretrained(
    model_name, cache_dir=models_path, device_map="auto"
)

prompt = "Once upon a time in a galaxy far, far away,"
inputs = tokenizer(prompt, return_tensors="pt").to("mps")  # Use Metal backend
outputs = model.generate(inputs["input_ids"], max_length=100)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
