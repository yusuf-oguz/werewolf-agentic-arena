import boto3, json, os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

client = boto3.client(
    "bedrock-runtime",
    region_name=os.getenv("AWS_DEFAULT_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

MODEL_ID = "eu.amazon.nova-micro-v1:0"

body = json.dumps({
    "messages": [{"role": "user", "content": [{"text": "Say exactly: test ok"}]}],
    "inferenceConfig": {"maxTokens": 50}
})

resp = client.invoke_model(modelId=MODEL_ID, body=body)
result = json.loads(resp["body"].read())

input_tok  = result["usage"]["inputTokens"]
output_tok = result["usage"]["outputTokens"]

print("Response   :", result["output"]["message"]["content"][0]["text"])
print("Input tok  :", input_tok)
print("Output tok :", output_tok)

# Nova Micro fiyatlari: $0.035/1M input, $0.14/1M output
input_price  = 0.035 / 1_000_000
output_price = 0.14  / 1_000_000
call_cost = input_tok * input_price + output_tok * output_price
print(f"Bu cagri maliyeti : ${call_cost:.6f}")

# 840 oyun tahmini (mevcut 6 oyun ortalamasindan)
avg_input  = 158_000
avg_output = 5_600
game_cost  = avg_input * input_price + avg_output * output_price
print(f"Tahmini oyun basi : ${game_cost:.4f}")
print(f"840 oyun toplam   : ${game_cost * 840:.2f}")
print(f"200 USD kredi ile kac oyun: {int(200 / game_cost)}")
