import json
import requests
from django.http import StreamingHttpResponse, HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from chat_app.models import Conversation, Message


def index(request):
    conversations = Conversation.objects.all()
    messages = Message.objects.all()
    for conversation in conversations:
        conversation.first_ai_message = conversation.messages.filter(sender='ai').first()
    return render(request, 'index.html', {'conversations': conversations, 'messages': messages})

@csrf_exempt
def create_conversation(request):
    if request.method == 'POST':
        conversation = Conversation.objects.create()
        # 创建一个默认的AI欢迎消息
        Message.objects.create(
            conversation=conversation,
            content="您好！我是AI助手，有什么可以帮助您的吗？",
            sender='ai'
        )
        return JsonResponse({'id': conversation.id, 'title': conversation.title})

@csrf_exempt
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

@csrf_exempt
def delete_all_conversations(request):
    if request.method == 'POST':
        try:
            # 删除所有会话
            Conversation.objects.all().delete()
            return JsonResponse({'success': True, 'message': '所有会话已删除'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return HttpResponse("Method not allowed", status=405)

@csrf_exempt
def get_conversation_messages(request, conversation_id):
    if request.method == 'GET':
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            messages = conversation.messages.all().values('id', 'content', 'sender', 'time')
            return JsonResponse({'messages': list(messages)})
        except Conversation.DoesNotExist:
            return JsonResponse({'error': '会话不存在'}, status=404)
    return HttpResponse("Method not allowed", status=405)