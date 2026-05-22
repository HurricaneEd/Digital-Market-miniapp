from http import HTTPStatus

from django.conf import settings  # 必须这样导入，它会自动加载 settings.py 里的配置
import dashscope

dashscope.api_key = settings.DASHSCOPE_API_KEY
def call_tongyi_model(user_query, product_context=""):
    """
    调用通义千问大模型进行智能推荐
    """
    # 1. 构造系统提示词，注入商品上下文
    system_prompt = (
        "你是一个专业的数码产品专家。你的任务是根据用户需求，从我们提供的产品库中推荐最合适的商品。"
        "推荐时请参考商品的价格、评分和具体参数。回复要专业、客观，并给出推荐理由。"
        f"当前可选的产品数据如下：{product_context}"
    )
    # 2. 组装对话消息
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_query}
    ]
    # 3. 发起模型请求
    try:
        response = dashscope.Generation.call( model='qwen-max', messages=messages,result_format='message',)
        # 4. 处理返回结果
        if response.status_code == HTTPStatus.OK:
            return response.output.choices[0].message.content
        else:
            return f"AI调用失败：{response.message} (错误码: {response.code})"
    except Exception as e:
        return f"模型调用发生异常：{str(e)}"