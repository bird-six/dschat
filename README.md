# Ollama部署本地大模型+可视化交互页面


Ollama 本地服务的默认访问地址是`http://localhost:11434`，如果`Ollama`服务启动后访问这个`url`会提示`Ollama is running`的内容。

### 1. 列出本地模型

GET请求：

```url
http://localhost:11434/api/tags
```

响应成功：

HTTP状态码：200，内容格式：JSON，响应示例：

```json
{
    "models":[ {
        "name":"deepseek-r1:1.5b",
        "model":"deepseek-r1:1.5b",
        "modified_at":"2025-07-15T10:13:29.0236489+08:00",
        "size":1117322768,
        "digest":"e0979632db5a88d1a53884cb2a941772d10ff5d055aabaa6801c4e36f3a6c2d7",
        "details": {
            "parent_model": "", "format":"gguf", "family":"qwen2", "families":["qwen2"], "parameter_size":"1.8B", "quantization_level":"Q4_K_M"
        }
    }
    ]
}
```



### 2. 文本生成

单次文本生成，无上下文

POST请求：

```url
http://localhost:11434/api/generate
```

请求格式：

```json
{
  "model": "deepseek-r1:1.5b",
  "prompt": "你好",
  "stream": false,
  "options": { 
    "temperature": 0.7, 
    "max_tokens": 100  
  }
}
```
| 字段                | 说明             |
| ------------------- | ---------------- |
| model               | 模型名称         |
| prompt              | 输入的提示词     |
| stream              | 是否启用流式响应 |
| options             | 可选参数         |
| options.temperature | 温度参数         |
| options.max_tokens  | 最大 token 数    |


响应成功：
HTTP状态码：200，内容格式：JSON，响应示例：



### 3. 聊天交互

支持多轮对话，模型会记录上下文

POST请求：

```url
http://localhost:11434/api/chat
```

请求格式：

```json
{
  "model": "deepseek-r1:1.5b",
  "stream": false,
  "messages": [
    {"role": "user", "content": "你好，我叫小明"},
    {"role": "assistant", "content": "你好小明！有什么可以帮你的吗？"},
    {"role": "user", "content": "我刚才告诉你我叫什么了吗？"}
  ]
}
```

| 字段               | 说明                           |
| ------------------ | ------------------------------ |
| model              | 模型名称                       |
| stream             | 流式响应                       |
| messages           | 消息列表                       |
| messages[].role    | 消息角色（如 user/assistant）  |
| messages[].content | 消息内容（用户问题 / AI 回答） |


响应成功：

HTTP状态码：200，内容格式：JSON，响应示例：

```json
{
    "model": "deepseek-r1:1.5b",
    "created_at": "2025-07-31T09:14:27.6278501Z",
    "message": {
        "role": "assistant",
        "content": "\n\n\n\n您好，小明同学。您提到的名字是“小明”，这是一个常见的中文名字，没有特殊的含义或要求。如果您需要帮助，请告诉我具体的问题或者需求，我会尽力为您提供帮助。"
    },
    "done_reason": "stop",
    "done": true,
    "total_duration": 626249000,
    "load_duration": 39893100,
    "prompt_eval_count": 30,
    "prompt_eval_duration": 3000000,
    "eval_count": 45,
    "eval_duration": 581000000
}
```

### 3.流式响应
流式响应与普通响应的区别在于数据传输方式，普通响应时，服务器会完整生成响应数据并发送给客户端，而流式响应无需等待所有数据生成完毕，而是**边生成数据边向客户端发送**，数据会被分成多个 “**块**”（chunk），每生成一块就立即发送一块，直到所有数据传输完成。例如：DeepSeek官网中的实时回复的打字效果（每生成一句就显示一句）。这种效果就是流式响应实现的。

处理`ollama`中的`chat`接口下的流式响应示例如下：

```python
def generate():
    url = 'http://localhost:11434/api/chat'
    model = 'deepseek-r1:1.5b'
    content = request.POST.get('message')
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": content},
        ]
    }
    # 向chat接口发送请求
    response = requests.post(url, json=payload, stream=True)	# stream=True启用流式响应

    with response as r:
        # 遍历流式响应的每行数据
        for line in r.iter_lines():
            if line:
                # 将传输的字节流转换为字符串，再解析为字典
                data = json.loads(line.decode('utf-8'))
                # 筛选出content内容
                if 'message' in data and 'content' in data['message']:
                    content = data['message']['content']
                    # 转换为SSE格式
                    yield f"data: {json.dumps({'content': content})}\n\n"
        # 流结束标志
        yield "data: {\"end\": true}\n\n"
```

之所以要定义一个生成器`generate`是因为要配合`Django`中的一个用于**流式传输数据**的特殊响应类`StreamingHttpResponse`逐步向客户端发送响应内容。`StreamingHttpResponse` 接收一个**迭代器**（如生成器函数）作为参数，迭代器每次返回的内容会被逐步发送到客户端。

### 4.SSE格式
SSE（Server-Sent Events，服务器发送事件）是一种基于 HTTP 的服务器向客户端单向推送实时数据的技术格式，允许服务器主动向客户端发送信息，而无需客户端频繁请求，适用于实时通知、数据更新等场景。

**SSE 的核心特点**

- **单向通信**：数据仅从服务器流向客户端，客户端无法通过 SSE 向服务器发送数据（需搭配其他方式如 HTTP POST 实现双向通信）。
- **基于 HTTP/HTTPS**：使用常规的 HTTP 协议，无需额外协议（如 WebSocket），兼容性更好，可穿过大多数防火墙。
- **文本格式**：传输的数据以文本形式编码，通常为 UTF-8，支持自定义数据格式（如 JSON、纯文本等）。
- **自动重连**：客户端在连接断开时会自动尝试重连，服务器可通过`retry`字段指定重连时间（毫秒）。

**SSE 的消息格式**

SSE 的消息由一系列字段组成，每个字段以**字段名 + 冒号 + 空格 + 值**的格式表示，每行以`\n`（换行符）分隔，消息之间以**两个换行符**（`\n\n`）分隔。常见字段包括：

- `data`：消息的核心数据，可多行（每行前都需加`data:`）。

  ```plaintext
  data: 这是第一行数据
  data: 这是第二行数据
  ```

- `event`：自定义事件类型，客户端可通过`addEventListener`监听特定事件（默认事件为`message`）。

  ```plaintext
  event: update
  data: 新数据
  ```

- `id`：消息的唯一标识，客户端会记录最后接收的`id`，重连时通过`Last-Event-ID`请求头告知服务器，便于服务器恢复数据传输。

  ```plaintext
  id: 123
  data: 带ID的消息
  ```

- `retry`：指定客户端重连的间隔时间（毫秒），若服务器不指定，客户端使用默认值。

  ```plaintext
  retry: 5000
  data: 5秒后重连
  ```

### 5.数据处理

**(1)后端生成流式数据**

- 接收用户消息，向本地 Ollama 模型发送请求，获取 AI 的流式响应（Ollama 返回的是分块的增量数据）。
- 将 Ollama 返回的原始流式数据**包装成符合 SSE（Server-Sent Events）协议的格式**（即 `data: {内容}\n\n`），以便前端能识别这是 “持续推送的流式数据”。
- 通过`StreamingHttpResponse`将数据**持续发送给前端**，而不是等待所有数据生成后一次性返回。


```python
def stream_response(request):
    if request.method == 'POST':
        # 获取用户消息
        user_content = request.POST.get('message')
        # 创建会话和用户消息
        conversation_id = request.POST.get('conversation_id')
        if conversation_id:
            conversation = get_object_or_404(Conversation, id=conversation_id)
        else:
            conversation = Conversation.objects.create()
        Message.objects.create(
            conversation=conversation,
            content=user_content,
            sender='user'
        )
        # 定义一个生成器
        def generate():
            url = 'http://localhost:11434/api/chat'
            model = 'deepseek-r1:1.5b'
            content = request.POST.get('message')
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": content},
                ]
            }
            # 向chat接口发送请求
            response = requests.post(url, json=payload, stream=True)

            # 初始化AI回复内容
            ai_content = ''
            with response as r:
                for line in r.iter_lines():
                    if line:
                        # 将传输的字节流转换为字符串，再解析为字典
                        data = json.loads(line.decode('utf-8'))
                        # 筛选出content内容
                        if 'message' in data and 'content' in data['message']:
                            content_chunk = data['message']['content']
                            ai_content += content_chunk
                            # 转换为SSE格式
                            yield f"data: {json.dumps({'content': content_chunk})}\n\n"
                # 保存AI消息
                Message.objects.create(
                    conversation=conversation,
                    content=ai_content,
                    sender='ai'
                )
                # 流结束标志
                yield "data: {\"end\": true}\n\n"

        response = StreamingHttpResponse(generate(), content_type="text/event-stream; charset=utf-8")
        response['Cache-Control'] = 'no-cache'
        return response

    return HttpResponse("Method not allowed", status=405)
```
**（2）前端消费流式数据**


后端发送的是符合 SSE 协议的字符串（如 `data: {"content": "你好"}\n\n`），前端需要：

- 通过`ReadableStream` API 读取持续推送的二进制流数据。

- 将二进制数据解码为文本（通过`TextDecoder`）。

- 按 SSE 格式拆分数据块（按`\n\n`分割），提取`data:`字段后的 JSON 内容。

  

  ```javascript
  // 前端解析流式数据的核心代码
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  function processStream({ done, value }) {
    if (done) return;
    const chunk = decoder.decode(value, { stream: true }); // 解码二进制流
    const lines = chunk.split('\n\n'); // 按SSE格式拆分
    lines.forEach(line => {
      if (line.startsWith('data:')) {
        const data = JSON.parse(line.substring(5).trim()); // 提取JSON内容
        // 处理数据...
      }
    });
    return reader.read().then(processStream); // 继续读取下一块
  }
  ```


流式响应的核心体验是 “AI 边思考边输出”，前端需要将每一个小数据块实时显示在聊天界面上：

- 累加每个数据块的内容（`fullResponse += data.content`）。

- 动态更新 DOM，将新增内容添加到 AI 消息框中。

- 实时滚动聊天区域到底部，确保用户能看到最新内容。

  ```javascript
  // 实时更新UI的核心代码
  if (data.content) {
    fullResponse += data.content;
    output.innerHTML = renderWithThinkContent(parsedContent); // 更新消息框内容
    chatMessages.scrollTop = chatMessages.scrollHeight; // 滚动到底部
  }
  ```


当后端发送完所有数据（返回 `data: {"end": true}\n\n`），前端需要：

- 完成最终的内容渲染（如处理 Markdown 格式、代码高亮等）。

  ```javascript
  // 流结束后的处理
  if (done) {
    output.innerHTML = renderWithThinkContent(parsedContent); // 最终渲染
    hljs.highlightAll(); // 代码高亮
  }
  ```


