"""三协议真实 HTTP 端到端验证：本地 mock server 模拟三种端点。

不访问公网，验证 CustomOpenAIModel 对三种 api_format 的真实请求形状：
  - /v1/messages       (anthropic)    校验 x-api-key / anthropic-version 头 + content 数组
  - /v1/responses      (openai_json)  校验 Authorization + output_text
  - /v1/chat/completions (openai_chat) 校验 Authorization + choices[0].message.content
"""
import sys, threading, json, time

sys.path.insert(0, "D:/rag-llm-test")

from fastapi import FastAPI, Request
from uvicorn import Server, Config
import uvicorn

app = FastAPI()


@app.post("/v1/messages")
async def anthropic_messages(request: Request):
    h = request.headers
    assert h.get("x-api-key") == "sk-ant-test", "missing x-api-key"
    assert h.get("anthropic-version") == "2023-06-01", "missing anthropic-version"
    body = await request.json()
    assert body["model"] == "claude-3"
    assert body["messages"][0]["role"] == "user"
    content = body["messages"][0]["content"]
    if "JSON" in content:
        text = '{"x": 9, "name": "anthropic-json"}'
    else:
        text = "Anthropic plain text reply"
    return {"content": [{"type": "text", "text": text}]}


@app.post("/v1/responses")
async def openai_responses(request: Request):
    assert request.headers.get("authorization") == "Bearer sk-test", "missing auth"
    body = await request.json()
    assert body["model"] == "gpt-r"
    fmt = (body.get("text") or {}).get("format", {}).get("type")
    if fmt == "json_object":
        text = '{"x": 1, "name": "resp"}'
    else:
        text = "OpenAI Responses plain reply"
    return {
        "id": "resp_mock", "object": "response", "created_at": 0,
        "status": "completed", "model": "gpt-r",
        "output": [{
            "type": "message", "id": "msg_mock", "role": "assistant",
            "content": [{"type": "output_text", "text": text, "annotations": []}],
        }],
    }


@app.post("/v1/chat/completions")
async def openai_chat(request: Request):
    assert request.headers.get("authorization") == "Bearer sk-test", "missing auth"
    body = await request.json()
    assert body["model"] == "deepseek-chat"
    rf = body.get("response_format")
    if rf and rf.get("type") == "json_object":
        return {"choices": [{"message": {"content": '{"x": 1, "name": "chat"}'}}]}
    return {"choices": [{"message": {"content": "Chat plain reply"}}]}


def run_server():
    cfg = Config(app, host="127.0.0.1", port=9199, log_level="error")
    srv = Server(cfg)
    srv.run()


from app.custom_model import CustomOpenAIModel
from pydantic import BaseModel


class V(BaseModel):
    x: int
    name: str


def main():
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(1.5)

    # ── anthropic ──
    a = CustomOpenAIModel(model_name="claude-3", api_key="sk-ant-test",
                          base_url="http://127.0.0.1:9199/v1", api_format="anthropic")
    print("[anthropic] plain:", a.generate("hello"))
    v = a.generate("evolve this", schema=V)
    print("[anthropic] schema:", v.x, v.name)

    # ── openai_json (Responses) ──
    r = CustomOpenAIModel(model_name="gpt-r", api_key="sk-test",
                          base_url="http://127.0.0.1:9199/v1", api_format="openai_json")
    print("[responses] plain:", r.generate("hi"))
    v2 = r.generate("make schema", schema=V)
    print("[responses] schema:", v2.x, v2.name)

    # ── openai_chat ──
    c = CustomOpenAIModel(model_name="deepseek-chat", api_key="sk-test",
                          base_url="http://127.0.0.1:9199/v1", api_format="openai_chat")
    print("[chat] plain:", c.generate("yo"))
    v3 = c.generate("json please", schema=V)
    print("[chat] schema:", v3.x, v3.name)

    print("FORMATS E2E OK")


if __name__ == "__main__":
    main()
