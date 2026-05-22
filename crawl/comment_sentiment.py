'''
对用户评论文本进行情感倾向计算
'''
import os
import django
import jieba
from snownlp import SnowNLP

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DigRecSys.settings')
django.setup()
from Product.models import CleanReview

# 加载停用词
with open('../AttachFile/stopwords_baidu.txt', 'r', encoding='utf-8') as f:
    stop_words = set(f.read().splitlines())


def get_sentiment_label(score):
    """根据情感分值返回标签"""
    if score <= 0.3:
        return '极度负面'
    elif score <= 0.45:
        return '负面'
    elif score <= 0.6:
        return '中性'
    elif score <= 0.8:
        return '正面'
    else:
        return '极度正面'


def process_review(content):
    """对评论文本进行分词、去停用词后计算情感分值"""
    if not content:
        return None, None, None
    # jieba分词
    words = jieba.cut(content)
    # 过滤停用词
    filtered_words = [w for w in words if w.strip() and w not in stop_words]
    # 如果过滤后没有内容，返回中性
    if not filtered_words:
        return 0.5, '中性', ''
    # 重新组合处理后的文本
    processed_text = ''.join(filtered_words)
    # 使用SnowNLP计算情感分值
    s = SnowNLP(processed_text)
    sentiment_score = s.sentiments  # 分值范围 [0, 1]
    # 获取标签
    sentiment_label = get_sentiment_label(sentiment_score)
    return sentiment_score, sentiment_label, processed_text

def update_all_reviews_sentiment():
    """更新所有评论的情感分值和标签"""
    reviews = CleanReview.objects.all()
    count = 0
    for review in reviews:
        if review.content:
            score, label = process_review(review.content)
            if score is not None:
                review.sentiment_score = score
                review.sentiment_label = label
                review.save()
                count += 1
    print(f"已完成 {count} 条评论的情感分析")


if __name__ == '__main__':
    # 更新所有评论的情感分析结果到数据库
    reviews = CleanReview.objects.all()
    count = 0

    for review in reviews:
        if review.content:
            score, label, processed_content = process_review(review.content)
            if score is not None:
                review.clean_content = processed_content
                review.sentiment_score = round(score, 4)
                review.sentiment_label = label
                review.save()
                count += 1

    print(f"已完成 {count} 条评论的情感分析并写入数据库")
