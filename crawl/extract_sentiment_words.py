"""
情感词频统计脚本
从数据库读取评论，对积极评论和消极评论分别做词频统计
输出到 positive.txt 和 negative.txt
"""
import os
import django
import jieba
from collections import Counter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DigRecSys.settings')
django.setup()

from Product.models import CleanReview

# 路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOPWORDS_PATH = os.path.join(BASE_DIR, 'AttachFile', 'stopwords_baidu.txt')
POSITIVE_OUTPUT = os.path.join(BASE_DIR, 'AttachFile', 'positive.txt')
NEGATIVE_OUTPUT = os.path.join(BASE_DIR, 'AttachFile', 'negative.txt')

# 加载停用词
stopwords = set()
if os.path.exists(STOPWORDS_PATH):
    with open(STOPWORDS_PATH, 'r', encoding='utf-8') as f:
        stopwords = set(line.strip() for line in f if line.strip())
print(f"加载停用词: {len(stopwords)} 个")

# 加载 all.txt 中已有的词（用于过滤）
ALL_WORDS_PATH = os.path.join(BASE_DIR, 'AttachFile', 'all.txt')
all_words = set()
if os.path.exists(ALL_WORDS_PATH):
    with open(ALL_WORDS_PATH, 'r', encoding='utf-8') as f:
        all_words = set(line.strip() for line in f if line.strip())
print(f"加载已记录词: {len(all_words)} 个")

# 统计词频
positive_counter = Counter()
negative_counter = Counter()

# 从数据库读取评论
print("从数据库读取评论...")
reviews = CleanReview.objects.filter(
    content__isnull=False,
    content__gt=''
).exclude(sentiment_score__isnull=True)

total = 0
for review in reviews:
    content = review.content.strip()
    if not content:
        continue

    score = review.sentiment_score or 0.5

    # 分词
    words = jieba.cut(content)
    valid_words = []

    for word in words:
        word = word.strip()
        # 过滤停用词、单字符、纯数字
        if word and len(word) > 1 and word not in stopwords and not word.isdigit():
            valid_words.append(word)

    # 根据情感分数分类
    if score > 0.5:  # 积极评论
        positive_counter.update(valid_words)
        total += 1
    elif score < 0.5:  # 消极评论
        negative_counter.update(valid_words)
        total += 1
    # score == 0.5 视为中性，不计入

print(f"处理完成，总评论数: {total}")
print(f"积极评论词数: {sum(positive_counter.values())}")
print(f"消极评论词数: {sum(negative_counter.values())}")

# 写入积极词频文件 (取前200个，过滤已存在的词)
print(f"\n写入积极词到: {POSITIVE_OUTPUT}")
with open(POSITIVE_OUTPUT, 'w', encoding='utf-8') as f:
    count = 0
    for word, cnt in positive_counter.most_common(200):
        if word in all_words:
            continue
        f.write(f"{word}\t{cnt}\n")
        count += 1
    print(f"写入积极词: {count} 个（过滤掉 {200 - count} 个已存在的）")

# 写入消极词频文件 (取前200个，过滤已存在的词)
print(f"写入消极词到: {NEGATIVE_OUTPUT}")
with open(NEGATIVE_OUTPUT, 'w', encoding='utf-8') as f:
    count = 0
    for word, cnt in negative_counter.most_common(200):
        if word in all_words:
            continue
        f.write(f"{word}\t{cnt}\n")
        count += 1
    print(f"写入消极词: {count} 个（过滤掉 {200 - count} 个已存在的）")

print("\n完成!")
print(f"积极词TOP10: {positive_counter.most_common(10)}")
print(f"消极词TOP10: {negative_counter.most_common(10)}")
